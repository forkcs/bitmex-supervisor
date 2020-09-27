import sys
import websocket
import threading
import traceback
import ssl
from time import sleep
import json
import decimal
import logging
from supervisor.core.auth import generate_expires, generate_signature
from supervisor.core.utils.log import setup_api_logger
from supervisor.core.utils.math import to_nearest
from urllib.parse import urlparse, urlunparse
from future.utils import iteritems


class BitMEXWebsocket:

    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200

    def __init__(self, base_url, apiKey, apiSecret):
        self.apiKey = apiKey
        self.apiSecret = apiSecret

        self.base_url = base_url

        self.logger = logging.getLogger('core')
        self.__reset()

    def __del__(self):
        self.exit()

    def connect(self, endpoint=None, symbol="XBTUSD", shouldAuth=True):
        '''Connect to the websocket and initialize data stores.'''

        self.logger.debug("Connecting WebSocket.")
        self.symbol = symbol
        self.shouldAuth = shouldAuth

        if endpoint is None:
            endpoint = self.base_url

        # We can subscribe right in the connection querystring, so let's build that.
        # Subscribe to all pertinent endpoints
        subscriptions = [sub + ':' + symbol for sub in ["quote", "trade", "orderBookL2_25"]]
        subscriptions += ["instrument"]  # We want all of them
        if self.shouldAuth:
            subscriptions += [sub + ':' + symbol for sub in ["order", "execution"]]
            subscriptions += ["margin", "position"]

        # Get WS URL and connect.
        urlParts = list(urlparse(endpoint))
        urlParts[0] = urlParts[0].replace('http', 'ws')
        urlParts[2] = "/realtime?subscribe=" + ",".join(subscriptions)
        wsURL = urlunparse(urlParts)
        self.logger.info("Connecting to %s" % wsURL)
        self.__connect(wsURL)
        self.logger.info('Connected to WS. Waiting for data images, this may take a moment...')

        # Connected. Wait for partials
        self.__wait_for_symbol(symbol)
        if self.shouldAuth:
            self.__wait_for_account()
        self.logger.info('Got all market data. Starting.')

    #
    # Data methods
    #
    def get_instrument(self, symbol):
        instruments = self.data['instrument']
        matchingInstruments = [i for i in instruments if i['symbol'] == symbol]
        if len(matchingInstruments) == 0:
            raise Exception("Unable to find instrument or index with symbol: " + symbol)
        instrument = matchingInstruments[0]
        # Turn the 'tickSize' into 'tickLog' for use in rounding
        # http://stackoverflow.com/a/6190291/832202
        instrument['tickLog'] = decimal.Decimal(str(instrument['tickSize'])).as_tuple().exponent * -1
        return instrument

    def get_ticker(self, symbol):
        '''Return a ticker object. Generated from instrument.'''

        instrument = self.get_instrument(symbol)

        # If this is an index, we have to get the data from the last trade.
        if instrument['symbol'][0] == '.':
            ticker = {}
            ticker['mid'] = ticker['buy'] = ticker['sell'] = ticker['last'] = instrument['markPrice']
        # Normal instrument
        else:
            bid = instrument['bidPrice'] or instrument['lastPrice']
            ask = instrument['askPrice'] or instrument['lastPrice']
            ticker = {
                "last": instrument['lastPrice'],
                "buy": bid,
                "sell": ask,
                "mid": (bid + ask) / 2
            }

        # The instrument has a tickSize. Use it to round values.
        return {k: to_nearest(float(v or 0), instrument['tickSize']) for k, v in iteritems(ticker)}

    def get_tick_size(self, symbol):
        instrument = self.get_instrument(symbol)
        return instrument['tickSize']

    def funds(self):
        return self.data['margin'][0]

    def market_depth(self, symbol):
        raise NotImplementedError('orderBook is not subscribed; use askPrice and bidPrice on instrument')
        # return self.data['orderBook25'][0]

    def open_orders(self):
        orders = self.data['order']
        # Filter to only open orders (leavesQty > 0) and those that we actually placed
        return [o for o in orders if o['leavesQty'] > 0]

    def position(self, symbol):
        positions = self.data['position']
        pos = [p for p in positions if p['symbol'] == symbol]
        if len(pos) == 0:
            # No position found; stub it
            return {'avgCostPrice': 0, 'avgEntryPrice': 0, 'currentQty': 0, 'symbol': symbol}
        return pos[0]

    def recent_trades(self):
        return self.data['trade']

    #
    # Custom methods
    #

    def get_order_book(self, depth=25):
        if not (0 <= depth <= 25):
            raise ValueError('Depth must be positive integer under or equal 25')
        order_book = self.data['orderBookL2_25']
        filtered = list(sorted(order_book, key=lambda x: x['price']))
        return filtered[25 - depth:25 + depth]

    def get_execution(self, clordid, symbol):
        executions = self.data['execution']
        return [o for o in executions if
                o['symbol'] == symbol and o['clOrdID'] == clordid and o['execComm'] is not None]

    def get_funding_execution(self, symbol):
        executions = self.data['execution']
        return [o for o in executions if o['symbol'] == symbol and o['execComm'] is not None and o['text'] == 'Funding']

    def get_liquidation_execution(self, symbol):
        executions = self.data['execution']
        return [o for o in executions if
                o['symbol'] == symbol and o['execComm'] is not None and o['text'] == 'Liquidation']

    def get_orders(self, symbol):
        orders = self.data['order']
        return [o for o in orders if o['symbol'] == symbol]

    def filled_orders(self):
        orders = self.data['order']
        # Filter to only open orders (leavesQty <= 0) and those that we actually placed
        return [o for o in orders if o['leavesQty'] == 0 and o['ordStatus'] != 'Canceled']

    def canceled_orders(self):
        orders = self.data['order']
        # Filter to only open orders (leavesQty <= 0) and those that we actually placed
        return [o for o in orders if o['leavesQty'] == 0 and o['ordStatus'] == 'Canceled']

    def rejected_orders(self):
        orders = self.data['order']
        # Filter to only open orders (leavesQty <= 0) and those that we actually placed
        return [o for o in orders if o['leavesQty'] == 0 and o['ordStatus'] == 'Rejected']

    #
    # Lifecycle methods
    #
    def error(self, err):
        self._error = err
        self.logger.error(err)
        self.exit()

    def exit(self):
        self.exited = True
        self.ws.close()

    #
    # Private methods
    #

    def __connect(self, wsURL):
        '''Connect to the websocket in a thread.'''
        self.logger.debug("Starting thread")

        ssl_defaults = ssl.get_default_verify_paths()
        sslopt_ca_certs = {'ca_certs': ssl_defaults.cafile}
        self.ws = websocket.WebSocketApp(wsURL,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         header=self.__get_auth()
                                         )

        setup_api_logger('websocket', log_level=logging.INFO)
        self.wst = threading.Thread(target=lambda: self.ws.run_forever(sslopt=sslopt_ca_certs))
        self.wst.daemon = True
        self.wst.start()
        self.logger.info("Started thread")

        # Wait for connect before continuing
        conn_timeout = 5
        while (not self.ws.sock or not self.ws.sock.connected) and conn_timeout and not self._error:
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout or self._error:
            self.logger.error("Couldn't connect to WS! Exiting.")
            self.exit()
            sys.exit(1)

    def __get_auth(self):
        """Return auth headers. Will use API Keys if present in settings."""

        if self.shouldAuth is False:
            return []

        self.logger.info("Authenticating with API Key.")
        # To auth to the WS using an API key, we generate a signature of a nonce and
        # the WS API endpoint.
        nonce = generate_expires()
        return [
            "api-expires: " + str(nonce),
            "api-signature: " + generate_signature(self.apiSecret, 'GET', '/realtime', nonce, ''),
            "api-key:" + self.apiKey
        ]

    def __wait_for_account(self):
        '''On subscribe, this data will come down. Wait for it.'''
        # Wait for the keys to show up from the ws
        while not {'margin', 'position', 'order'} <= set(self.data):
            sleep(0.1)

    def __wait_for_symbol(self, symbol):
        '''On subscribe, this data will come down. Wait for it.'''
        while not {'instrument', 'trade', 'quote'} <= set(self.data):
            sleep(0.1)

    def __send_command(self, command, args):
        """Send a raw command."""
        self.ws.send(json.dumps({"op": command, "args": args or []}))

    def __on_message(self, message):
        '''Handler for parsing WS messages.'''
        message = json.loads(message)
        self.logger.debug(json.dumps(message))

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None
        try:
            if 'subscribe' in message:
                if message['success']:
                    self.logger.debug("Subscribed to %s." % message['subscribe'])
                else:
                    self.error("Unable to subscribe to %s. Error: \"%s\" Please check and restart." %
                               (message['request']['args'][0], message['error']))
            elif 'status' in message:
                if message['status'] == 400:
                    self.error(message['error'])
                if message['status'] == 401:
                    self.error("API Key incorrect, please check and restart.")
            elif action:

                if table not in self.data:
                    self.data[table] = []

                if table not in self.keys:
                    self.keys[table] = []

                # There are four possible actions from the WS:
                # 'partial' - full table image
                # 'insert'  - new row
                # 'update'  - update row
                # 'delete'  - delete row
                if action == 'partial':
                    self.logger.debug("%s: partial" % table)
                    self.data[table] += message['data']
                    # Keys are communicated on partials to let you know how to uniquely identify
                    # an item. We use it for updates.
                    self.keys[table] = message['keys']
                elif action == 'insert':
                    self.logger.debug('%s: inserting %s' % (table, message['data']))
                    self.data[table] += message['data']

                    # Limit the max length of the table to avoid excessive memory usage.
                    # Don't trim orders because we'll lose valuable state if we do.
                    if table not in ['order', 'orderBookL2'] and len(self.data[table]) > BitMEXWebsocket.MAX_TABLE_LEN:
                        self.data[table] = self.data[table][(BitMEXWebsocket.MAX_TABLE_LEN // 2):]

                elif action == 'update':
                    self.logger.debug('%s: updating %s' % (table, message['data']))
                    # Locate the item in the collection and update it.
                    for updateData in message['data']:
                        item = findItemByKeys(self.keys[table], self.data[table], updateData)
                        if not item:
                            continue  # No item found to update. Could happen before push

                        # Log executions
                        if table == 'order':
                            is_canceled = 'ordStatus' in updateData and updateData['ordStatus'] == 'Canceled'
                            if 'cumQty' in updateData and not is_canceled:
                                contExecuted = updateData['cumQty'] - item['cumQty']
                                if contExecuted > 0:
                                    instrument = self.get_instrument(item['symbol'])
                                    # self.logger.info("Execution: %s %d Contracts of %s at %.*f" %
                                    #          (item['side'], contExecuted, item['symbol'],
                                    #           instrument['tickLog'], item['price']))

                        # Update this item.
                        item.update(updateData)

                        # Remove canceled / filled orders
                        # if table == 'order' and item['leavesQty'] <= 0:
                        #     self.data[table].remove(item)

                elif action == 'delete':
                    self.logger.debug('%s: deleting %s' % (table, message['data']))
                    # Locate the item in the collection and remove it.
                    for deleteData in message['data']:
                        item = findItemByKeys(self.keys[table], self.data[table], deleteData)
                        self.data[table].remove(item)
                else:
                    raise Exception("Unknown action: %s" % action)
        except:
            self.logger.error(traceback.format_exc())

    def __on_open(self):
        self.logger.debug("Websocket Opened.")

    def __on_close(self):
        self.logger.info('Websocket Closed')
        self.exit()

    def __on_error(self, error):
        if not self.exited:
            self.error(error)

    def __reset(self):
        self.data = {}
        self.keys = {}
        self.exited = False
        self._error = None


def findItemByKeys(keys, table, matchData):
    for item in table:
        matched = True
        for key in keys:
            if item[key] != matchData[key]:
                matched = False
        if matched:
            return item
