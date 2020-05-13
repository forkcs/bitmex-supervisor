import json
import decimal
import threading
import websocket
from time import sleep
from supervisor.core.utils.math import to_nearest


def find_item_by_keys(keys, table, match_data):
    for item in table:
        matched = True
        for key in keys:
            if item[key] != match_data[key]:
                matched = False
        if matched:
            return item


class TrailingShell:
    # Don't grow a table larger than this amount. Helps cap memory usage.
    MAX_TABLE_LEN = 200

    def __init__(self, order, offset: int, tick_size: float, test=True, init_ws=True):
        self.tick_size = tick_size
        self.exited = False
        self.test = test

        self.order = order
        self.offset = offset

        self.last_price = 0
        self._min_price = float('inf')
        self._max_price = -1

        self.initial_price = float('nan')

        self.tracking = False
        self.ws = None

        self.__reset()

        if init_ws:
            self.connect()

    def __del__(self):
        self.exit()

    def exit(self):
        self.exited = True
        if self.ws is not None:
            self.ws.close()

    def __reset(self):
        self.data = {}
        self.keys = {}
        self.exited = False
        self._error = None

    def get_instrument(self, symbol):
        instruments = self.data.get('instrument', None)
        if instruments is None:
            return None
        matching_instruments = [i for i in instruments if i['symbol'] == symbol]
        if len(matching_instruments) == 0:
            raise Exception("Unable to find instrument or index with symbol: " + symbol)
        instrument = matching_instruments[0]
        # Turn the 'tickSize' into 'tickLog' for use in rounding
        # http://stackoverflow.com/a/6190291/832202
        instrument['tickLog'] = decimal.Decimal(str(instrument['tickSize'])).as_tuple().exponent * -1
        return instrument

    def calculate_new_price(self, extremum) -> float:
        if self.order.side == 'Sell':
            needed_price = extremum * (1 - self.offset / 100)
        else:
            needed_price = extremum * (1 + self.offset / 100)
        needed_price = to_nearest(needed_price, tickSize=self.tick_size)

        return needed_price

    @property
    def min_price(self):
        return self._min_price

    @min_price.setter
    def min_price(self, value):
        if value < self.initial_price:
            new_price = self.calculate_new_price(value)
            self.order.move(to=new_price)
        self._min_price = value

    @property
    def max_price(self):
        return self._max_price

    @max_price.setter
    def max_price(self, value):
        if value > self.initial_price:
            new_price = self.calculate_new_price(value)
            self.order.move(to=new_price)
        self._max_price = value

    def stop_trailing(self):
        self.tracking = False

    def start_trailing(self, initial_price: float):
        """

        :param initial_price: the price after reaching which order will be moving
        """

        self._max_price = -1
        self._min_price = float('inf')
        self.initial_price = initial_price
        self.tracking = True

    def connect(self):
        """Connect to the websocket and initialize data stores."""

        symbol = self.order.symbol

        if self.test:
            host = 'wss://testnet.bitmex.com/realtime'
        else:
            host = 'wss://bitmex.com/realtime'
        # Get WS URL and connect.
        endpoint = f"realtime?subscribe=instrument:{symbol}"
        ws_url = host + endpoint
        self.__connect(ws_url)

        # Connected. Wait for partials
        self.__wait_for_symbol()

    def __connect(self, ws_url):
        self.ws = websocket.WebSocketApp(ws_url,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         header=[])

        self.wst = threading.Thread(target=lambda: self.ws.run_forever())
        self.wst.daemon = True
        self.wst.start()

        # Wait for connect before continuing
        conn_timeout = 5
        while (not self.ws.sock or not self.ws.sock.connected) and conn_timeout and not self._error:
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout or self._error:
            self.exit()

    def __wait_for_symbol(self):
        while not {'instrument'} <= set(self.data):
            sleep(0.1)

    def __on_message(self, message):
        """Handler for parsing WS messages."""

        message = json.loads(message)

        table = message['table'] if 'table' in message else None
        action = message['action'] if 'action' in message else None

        if 'subscribe' in message:
            if not message['success']:
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
                self.data[table] += message['data']
                # Keys are communicated on partials to let you know how to uniquely identify
                # an item. We use it for updates.
                self.keys[table] = message['keys']
            elif action == 'insert':
                self.data[table] += message['data']

                # Limit the max length of the table to avoid excessive memory usage.
                # Don't trim orders because we'll lose valuable state if we do.
                if table not in ['order', 'orderBookL2'] and len(self.data[table]) > TrailingShell.MAX_TABLE_LEN:
                    self.data[table] = self.data[table][(TrailingShell.MAX_TABLE_LEN // 2):]

            elif action == 'update':
                # Locate the item in the collection and update it.
                for updateData in message['data']:
                    item = find_item_by_keys(self.keys[table], self.data[table], updateData)
                    if not item:
                        continue  # No item found to update. Could happen before push

                    # Update this item.
                    item.update(updateData)

                    # Remove canceled / filled orders
                    # if table == 'order' and item['leavesQty'] <= 0:
                    #     self.data[table].remove(item)

            elif action == 'delete':
                # Locate the item in the collection and remove it.
                for deleteData in message['data']:
                    item = find_item_by_keys(self.keys[table], self.data[table], deleteData)
                    self.data[table].remove(item)
            else:
                raise Exception("Unknown action: %s" % action)

        instrument = self.get_instrument(symbol=self.order.symbol)
        if instrument is not None:
            self.last_price = instrument['lastPrice']
            if self.tracking:
                if self.last_price > self.max_price and self.order.side == 'Sell':
                    self.max_price = self.last_price
                elif self.last_price < self.min_price and self.order.side == 'Buy':
                    self.min_price = self.last_price

    def __on_close(self):
        self.exit()

    def __on_open(self):
        pass

    def __on_error(self, error):
        if not self.exited:
            self.error(error)

    def error(self, err):
        self.exit()
