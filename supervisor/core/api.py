"""BitMEX API Connector."""
import requests
import time
import datetime
import json
import logging

from supervisor.core.auth import APIKeyAuthWithExpires
from supervisor.core.ws_thread import BitMEXWebsocket
from supervisor.core import settings
from supervisor.core.utils import errors
from supervisor.core.utils.log import setup_api_logger


# https://www.bitmex.com/api/explorer/
class BitMEX(object):

    def __init__(self, test=True, symbol=None, api_key=None, api_secret=None, init_ws=True):
        self.logger = setup_api_logger('core', logging.INFO)
        self.base_url = settings.BASE_URL if not test else settings.BASE_TEST_URL
        self.symbol = symbol
        self.api_key = api_key
        self.api_secret = api_secret

        # Prepare HTTPS session
        self.session = requests.Session()
        # These headers are always sent
        self.session.headers.update({'content-type': 'application/json'})
        self.session.headers.update({'accept': 'application/json'})

        self.retries = 0  # initialize counter

        self.init_ws = init_ws

        if self.init_ws:
            # Create websocket for streaming data
            self.ws = BitMEXWebsocket(self.base_url, api_key, api_secret)
            self.ws.connect(symbol=self.symbol, shouldAuth=True)

    def reinit_ws(self):
        if self.init_ws:
            del self.ws

            self.ws = BitMEXWebsocket(self.base_url, self.api_key, self.api_secret)
            self.ws.connect(symbol=self.symbol, shouldAuth=True)

    # Public methods ws
    def ticker_data(self):
        """Get ticker data."""
        return self.ws.get_ticker(self.symbol)

    def get_tick_size(self):
        return self.ws.get_tick_size(self.symbol)

    def ticker_all_data(self):
        """Get ticker data."""
        return self.ws.get_instrument(self.symbol)

    def instrument(self):
        """Get an instrument's details."""
        return self.ws.get_instrument(self.symbol)

    def order_book(self, depth):
        """Get orderbook."""
        return self.ws.get_order_book(depth=depth)

    def recent_trades(self):
        """Get recent trades."""
        return self.ws.recent_trades()

    # public methods
    def announcements(self, columns=None, query=None):
        """Get site announcements."""
        if query is None:
            query = {
                'columns': columns if columns else ''
            }
        return self.call_api(path='/announcement', query=query, verb='GET')

    def announcements_urgent(self, query=None):
        """Get urgent (banner) announcements."""
        if query is None:
            query = {}
        return self.call_api(path='/announcement/urgent', query=query, verb='GET')

    # private methods
    def authentication_required(fn):
        """Annotation for methods that require auth."""

        def wrapped(self, *args, **kwargs):
            if not self.api_key:
                msg = "You must be authenticated to use this method"
                raise errors.AuthenticationError(msg)
            else:
                return fn(self, *args, **kwargs)

        return wrapped

    # private methods ws
    @authentication_required
    def funds(self):
        """Get your current balance."""
        return self.ws.funds()['amount']

    @authentication_required
    def ws_position(self):
        """Get your open position."""
        return self.ws.position(self.symbol)

    @authentication_required
    def get_executions(self, clordid):
        """Get executions."""
        return self.ws.get_execution(clordid, self.symbol)

    @authentication_required
    def get_funding_executions(self):
        """Get funding executions."""
        return self.ws.get_funding_execution(self.symbol)

    @authentication_required
    def get_liquidation_executions(self):
        """Get liquidation executions."""
        return self.ws.get_liquidation_execution(self.symbol)

    @authentication_required
    def get_orders(self):
        """Get all orders"""
        return self.ws.get_orders(symbol=self.symbol)

    @authentication_required
    def open_orders(self):
        """Get open orders."""
        return self.ws.open_orders()

    @authentication_required
    def filled_orders(self):
        """Get filled orders."""
        return self.ws.filled_orders()

    @authentication_required
    def canceled_orders(self):
        """Get canceled orders."""
        return self.ws.canceled_orders()

    @authentication_required
    def rejected_orders(self):
        return self.ws.rejected_orders()

    # private methods
    @authentication_required
    def get_api_key(self, reverse=None, query=None):
        """Get your API Keys."""
        if query is None:
            query = {
                'reverse': reverse if reverse else False
            }
        path = "/apiKey"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def create_api_key(self, name=None, cidr=None, permissions=None, enabled=None, token=None, postdict=None):
        """Create a new API Key."""
        if postdict is None:
            postdict = {
                'name': name if name else '',
                'cidr': cidr if cidr else '',
                'permissions': permissions if permissions else '',
                'enabled': enabled if enabled else False,
                'token': token if token else ''
            }
        path = "/apiKey"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def remove_api_key(self, apiKeyID=None, postdict=None):
        """Remove an API Key."""
        if postdict is None:
            postdict = {
                'apiKeyID': apiKeyID if apiKeyID else ''
            }
        path = "/apiKey"
        return self.call_api(path=path, postdict=postdict, verb="DELETE")

    @authentication_required
    def disable_api_key(self, apiKeyID=None, postdict=None):
        """Disable an API Key."""
        if postdict is None:
            postdict = {
                'apiKeyID': apiKeyID if apiKeyID else ''
            }
        path = "/apiKey/disable"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def enable_api_key(self, apiKeyID=None, postdict=None):
        """Enable an API Key."""
        if postdict is None:
            postdict = {
                'apiKeyID': apiKeyID if apiKeyID else ''
            }
        path = "/apiKey/enable"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def execution(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None, startTime=None, endTime=None, query=None):
        """Get all raw executions for your account."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/execution"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def execution_trade_history(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None, startTime=None, endTime=None, query=None):
        """Get all balance-affecting executions. This includes each trade, insurance charge, and settlement."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/execution/tradeHistory"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def funding(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                startTime=None, endTime=None, query=None):
        """Get funding history."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/funding"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def global_notification(self, query=None):
        """Get your current GlobalNotifications."""
        if query is None:
            query = {}
        path = "/globalNotification"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def get_instrument(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                startTime=None, endTime=None, query=None):
        """Get instruments."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/instrument"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def instrument_active(self, query=None):
        """Get all active instruments and instruments that have expired in <24hrs."""
        if query is None:
            query = {}
        path = "/instrument/active"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def instrument_active_and_indices(self, query=None):
        """Helper method. Gets all active instruments and all indices. This is a join of the result of /indices and /active."""
        if query is None:
            query = {}
        path = "/instrument/activeAndIndices"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def instrument_active_intervals(self, query=None):
        """Return all active contract series and interval pairs."""
        if query is None:
            query = {}
        path = "/instrument/activeIntervals"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def instrument_composite_index(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                   startTime=None, endTime=None, query=None):
        """Show constituent parts of an index."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/instrument/compositeIndex"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def instrument_indices(self, query=None):
        """Get all price indices."""
        if query is None:
            query = {}
        path = "/instrument/indices"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def insurance(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                  startTime=None, endTime=None, query=None):
        """Get insurance fund history."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/insurance"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def leaderboard(self, method=None, query=None):
        """Get current leaderboard."""
        if query is None:
            query = {
                'method': method if method else ''
            }
        path = "/leaderboard"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def leaderboard_name(self, query=None):
        """Get your alias on the leaderboard."""
        if query is None:
            query = {}
        path = "/leaderboard/name"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def liquidation(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                  startTime=None, endTime=None, query=None):
        """Get liquidation orders."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/liquidation"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def order(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                    startTime=None, endTime=None, query=None):
        """Get your orders."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/order"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def order_edit(self, orderID=None, origClOrdID=None, clOrdID=None, orderQty=None, leavesQty=None, price=None, stopPx=None, pegOffsetValue=None, text=None, postdict=None, **kwargs):
        """Amend the quantity or price of an open order."""
        if postdict is None:
            postdict = {}
            if orderID:
                postdict['orderID'] = orderID
            if origClOrdID:
                postdict['origClOrdID'] = origClOrdID
            if clOrdID:
                postdict['clOrdID'] = clOrdID
            if text:
                postdict['text'] = text
            if orderQty:
                postdict['orderQty'] = orderQty
            if leavesQty:
                postdict['leavesQty'] = leavesQty
            if price:
                postdict['price'] = price
            if stopPx:
                postdict['stopPx'] = stopPx
            if pegOffsetValue:
                postdict['pegOffsetValue'] = pegOffsetValue
        path = "/order"
        return self.call_api(path=path, postdict=postdict, verb="PUT")

    @authentication_required
    def buy(self, **kwargs):
        """Place a buy order.
        Returns order object. ID: orderID
        """
        return self.place_order(**kwargs)

    @authentication_required
    def sell(self, **kwargs):
        """Place a sell order.
        Returns order object. ID: orderID
        """
        kwargs['orderQty'] = -kwargs['orderQty']
        return self.place_order(**kwargs)

    @authentication_required
    def place_order(self, **kwargs):
        """Place an order."""
        if kwargs['ordType'] != "Market":
            try:
                price = kwargs['price']
            except KeyError:
                price = None

            if price:
                if kwargs['price'] < 0:
                    raise Exception("Price must be positive.")

        # Generate a unique clOrdID with our prefix so we can identify it.
        # clOrdID = orderIDPrefix + base64.b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')
        postdict = {
            'symbol': self.symbol,
            'orderQty': kwargs['orderQty'],
            # 'clOrdID': clOrdID,
            'ordType': kwargs['ordType']
        }

        try:
            clOrdID = kwargs['clOrdID']
        except KeyError:
            clOrdID = None

        if clOrdID:
            postdict.update({'clOrdID': kwargs['clOrdID']})

        try:
            execInst = kwargs['execInst']
        except KeyError:
            execInst = None

        if execInst:
            postdict.update({'execInst': kwargs['execInst']})

        try:
            displayQty = kwargs['displayQty']
        except KeyError:
            displayQty = None

        if displayQty is not None:
            postdict.update({'displayQty': kwargs['displayQty']})

        if kwargs['ordType'] != "Market":
            try:
                price = kwargs['price']
            except KeyError:
                price = None

            if price:
                postdict.update({'price': kwargs['price']})
            if kwargs['ordType'] in ['StopLimit', 'LimitIfTouched', 'Stop']:
                try:
                    stopPx = kwargs['stopPx']
                except KeyError:
                    stopPx = None

                if stopPx:
                    postdict.update({'stopPx': kwargs['stopPx']})

        return self.order_create(postdict=postdict)

    @authentication_required
    def place_sl_order(self, trailing=False, **kwargs):
        """Place an sl_order."""
        if kwargs['ordType'] != "Stop":
            try:
                price = kwargs['price']
            except KeyError:
                price = None

            if price:
                if kwargs['price'] < 0:
                    raise Exception("Price must be positive.")

        # Generate a unique clOrdID with our prefix so we can identify it.
        # clOrdID = orderIDPrefix + base64.b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')
        postdict = {
            'symbol': self.symbol,
            'orderQty': kwargs['orderQty'],
            # 'clOrdID': clOrdID,
            'ordType': kwargs['ordType'],
        }
        try:
            clOrdID = kwargs['clOrdID']
        except KeyError:
            clOrdID = None

        if clOrdID:
            postdict.update({'clOrdID': kwargs['clOrdID']})

        try:
            stopPx = kwargs['stopPx']
        except KeyError:
            stopPx = None

        if stopPx:
            postdict.update({'stopPx': kwargs['stopPx']})

        if kwargs['ordType'] != "Stop":
            try:
                price = kwargs['price']
            except KeyError:
                price = None

            if price:
                postdict.update({'price': kwargs['price']})
        try:
            execInst = kwargs['execInst']
        except KeyError:
            execInst = None

        if execInst:
            postdict.update({'execInst': kwargs['execInst']})

        try:
            pegPriceType = kwargs['pegPriceType']
        except KeyError:
            pegPriceType = None

        if pegPriceType:
            postdict.update({'pegPriceType': kwargs['pegPriceType']})

        try:
            pegOffsetValue = kwargs['pegOffsetValue']
        except KeyError:
            pegOffsetValue = None

        if pegOffsetValue:
            postdict.update({'pegOffsetValue': kwargs['pegOffsetValue']})

        return self.order_create(postdict=postdict, need_repeat=True)

    @authentication_required
    def place_tp_order(self, **kwargs):
        """Place an tp;_order."""
        try:
            price = kwargs['price']
        except KeyError:
            price = None

        if price:
            if kwargs['price'] < 0:
                raise Exception("Price must be positive.")

        # Generate a unique clOrdID with our prefix so we can identify it.
        # clOrdID = orderIDPrefix + base64.b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')
        postdict = {
            'symbol': self.symbol,
            'orderQty': kwargs['orderQty'],
            # 'clOrdID': clOrdID,
            'ordType': kwargs['ordType'],
            'side': kwargs['side']
        }
        try:
            clOrdID = kwargs['clOrdID']
        except KeyError:
            clOrdID = None

        if clOrdID:
            postdict.update({'clOrdID': kwargs['clOrdID']})

        try:
            price = kwargs['price']
        except KeyError:
            price = None

        if price:
            postdict.update({'price': kwargs['price']})

        return self.order_create(postdict=postdict, need_repeat=True)

    @authentication_required
    def order_create(self, symbol=None, side=None, orderQty=None, price=None, displayQty=None, stopPx=None, clOrdID=None,
                     pegOffsetValue=None, pegPriceType=None, ordType=None, timeInForce=None, execInst=None, text=None, postdict=None, need_repeat=False, **kwargs):
        """Create a new order."""
        if postdict is None:
            postdict = {
                'symbol': self.symbol,
                'clOrdID': clOrdID if clOrdID else '',
                'pegPriceType': pegPriceType if pegPriceType else '',
                'ordType': ordType if ordType else '',
                'timeInForce': timeInForce if timeInForce else '',
                'execInst': execInst if execInst else '',
                'text': text if text else '',
            }
            if side:
                postdict['side'] = side
            if orderQty:
                postdict['orderQty'] = orderQty
            if price:
                postdict['price'] = price
            if displayQty:
                postdict['displayQty'] = displayQty
            if stopPx:
                postdict['stopPx'] = stopPx
            if pegOffsetValue:
                postdict['pegOffsetValue'] = pegOffsetValue
        path = "/order"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def close_position(self, orderQty, clOrdID=None):
        postdict = {'execlnst': 'Close',
                    'symbol': self.symbol,
                    'orderQty': orderQty
                    }
        if clOrdID:
            postdict['clOrdID'] = clOrdID
        return self.order_create(postdict=postdict)

    @authentication_required
    def order_cancel_all(self):
        """Cancels all of your orders."""
        postdict = {
            'symbol': self.symbol,
        }
        path = "/order/all"
        return self.call_api(path=path, postdict=postdict, verb="DELETE")

    @authentication_required
    def order_cancel(self, orderID=None, clOrdID=None, text=None, postdict=None):
        """Cancel order(s). Send multiple order IDs to cancel in bulk."""
        if postdict is None:
            postdict = {}
            if orderID:
                postdict['orderID'] = orderID
            if clOrdID:
                postdict['clOrdID'] = clOrdID
            if text:
                postdict['text'] = text
        path = "/order"
        return self.call_api(path=path, postdict=postdict, verb="DELETE")

    @authentication_required
    def order_bulk_edit(self, orders=None, postdict=None):
        """Cancel order(s). Send multiple order IDs to cancel in bulk."""
        if postdict is None:
            postdict = {
                'orders': orders if orders else '',
            }
        path = "/order/bulk"
        return self.call_api(path=path, postdict=postdict, verb="PUT")

    @authentication_required
    def order_bulk_create(self, order_dicts=None, postdict=None):
        """Create multiple new orders for the same symbol."""
        if postdict is None:
            postdict = {
                'orders': order_dicts if order_dicts else '',
            }
        path = "/order/bulk"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def order_cancel_all_after(self, timeout=None, postdict=None):
        """Automatically cancel all your orders after a specified timeout."""
        if postdict is None:
            postdict = {
                'timeout': timeout if timeout else 0,
            }
        path = "/order/cancelAllAfter"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def order_book_l2(self, symbol=None, depth=None, query=None):
        """Get current orderbook in vertical format."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'depth': depth if depth else 0,
            }
        path = "/orderBook/L2"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def position(self, count=None):
        """Get your positions."""
        query = {}
        if count:
            query['count'] = count
        path = "/position"
        return self.call_api(path=path, query=query, verb="GET")[0]

    @authentication_required
    def position_isolate(self, symbol=None, enabled=None, postdict=None):
        """Enable isolated margin or cross margin per-position."""
        if postdict is None:
            postdict = {
                'symbol': symbol if symbol else '',
                'enabled': enabled if enabled else True,
            }
        path = "/position/isolate"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def position_leverage(self, leverage):
        """Choose leverage for a position."""
        postdict = {
            'symbol': self.symbol,
            'leverage': leverage,
        }
        path = "/position/leverage"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def position_risk_limit(self, symbol=None, riskLimit=None, postdict=None):
        """Update your risk limit."""
        if postdict is None:
            postdict = {
                'symbol': symbol if symbol else '',
                'riskLimit': riskLimit if riskLimit else 0,
            }
        path = "/position/riskLimit"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def position_transfer_margin(self, symbol=None, amount=None, postdict=None):
        """Transfer equity in or out of a position."""
        if postdict is None:
            postdict = {
                'symbol': symbol if symbol else '',
                'amount': amount if amount else 0,
            }
        path = "/position/transferMargin"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def quote(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
              startTime=None, endTime=None, query=None):
        """Get Quotes."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/quote"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def quote_bucketed(self, binSize=None, partial=None, symbol=None, filter=None, columns=None, count=None, start=None,
                       reverse=None, startTime=None, endTime=None, query=None):
        """Get previous quotes in time buckets."""
        if query is None:
            query = {
                'binSize': binSize if binSize else '1m',
                'partial': partial if partial else False,
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/quote/bucketed"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def schema(self, model=None, query=None):
        """Get model schemata for data objects returned by this APIs."""
        if query is None:
            query = {
                'model': model if model else '',
            }
        path = "/schema"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def schema_websocket_help(self, query=None):
        """Returns help text & subject list for websocket usage."""
        if query is None:
            query = {}
        path = "/schema/websocketHelp"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def settlement(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
              startTime=None, endTime=None, query=None):
        """Get settlement history."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/settlement"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def stats(self, query=None):
        """Get exchange-wide and per-series turnover and volume statistics."""
        if query is None:
            query = {}
        path = "/stats"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def stats_history(self, query=None):
        """Get historical exchange-wide and per-series turnover and volume statistic."""
        if query is None:
            query = {}
        path = "/stats/history"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def stats_history_usd(self, query=None):
        """Get a summary of exchange statistics in USD."""
        if query is None:
            query = {}
        path = "/stats/historyUSD"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def get_trade(self, symbol=None, filter=None, columns=None, count=None, start=None, reverse=None,
                   startTime=None, endTime=None, query=None):
        """Get Trades."""
        if query is None:
            query = {
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False
            }
            if symbol:
                query['symbol'] = symbol
            if filter:
                query['filter'] = filter
            if columns:
                query['columns'] = columns
            if startTime:
                query['startTime'] = startTime
            if endTime:
                query['endTime'] = endTime
        path = "/trade"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def trade_bucketed(self, binSize=None, partial=None, symbol=None, filter=None, columns=None, count=None, start=None,
                       reverse=None, startTime=None, endTime=None, query=None):
        """Get previous trades in time buckets."""
        if query is None:
            query = {
                'binSize': binSize if binSize else '1m',
                'partial': partial if partial else False,
                'symbol': symbol if symbol else '',
                'filter': filter if filter else '',
                'columns': columns if columns else '',
                'count': count if count else 100,
                'start': start if start else 0,
                'reverse': reverse if reverse else False,
                'startTime': startTime if startTime else '',
                'endTime': endTime if endTime else ''
            }
        path = "/trade/bucketed"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user(self, query=None):
        """Get your user model."""
        if query is None:
            query = {}
        path = "/user"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_affiliate_status(self, query=None):
        """Get your current affiliate/referral status."""
        if query is None:
            query = {}
        path = "/user/affiliateStatus"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_cancel_withdrawal(self, token=None, postdict=None):
        """Cancel a withdrawal."""
        if postdict is None:
            postdict = {
                'token': token if token else '',
            }
        path = "/user/cancelWithdrawal"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_check_referral_code(self, referralCode=None, query=None):
        """Check if a referral code is valid."""
        if query is None:
            query = {
                'referralCode': referralCode if referralCode else ''
            }
        path = "/user/checkReferralCode"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_commission(self, query=None):
        """Get your account's commission status."""
        if query is None:
            query = {}
        path = "/user/commission"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_communication_token(self, token=None, platformAgent=None, postdict=None):
        """Register your communication token for mobile clients."""
        if postdict is None:
            postdict = {
                'token': token if token else '',
                'platformAgent': platformAgent if platformAgent else '',
            }
        path = "/user/communicationToken"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_confirm_email(self, token=None, postdict=None):
        """Confirm your email address with a token."""
        if postdict is None:
            postdict = {
                'token': token if token else '',
            }
        path = "/user/confirmEmail"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_confirm_withdrawal(self, token=None, postdict=None):
        """Confirm a withdrawal."""
        if postdict is None:
            postdict = {
                'token': token if token else '',
            }
        path = "/user/confirmWithdrawal"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_deposit_address(self, currency=None, query=None):
        """Get a deposit address."""
        if query is None:
            query = {
                'currency': currency if currency else ''
            }
        path = "/user/depositAddress"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_execution_history(self, symbol=None, timestamp=None, query=None):
        """Get the execution history by day."""
        if query is None:
            query = {
                'symbol': symbol if symbol else '',
                'timestamp': timestamp if timestamp else ''
            }
        path = "/user/executionHistory"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_logout(self, postdict=None):
        """Log out of BitMEX."""
        if postdict is None:
            postdict = {}
        path = "/user/logout"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_margin(self, currency=None, query=None):
        """Get your account's margin status. Send a currency of "all" to receive an array of all supported currencies."""
        if query is None:
            query = {
                'currency': currency if currency else ''
            }
        path = "/user/margin"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_min_withdrawal_fee(self, currency=None, query=None):
        """Get the minimum withdrawal fee for a currency."""
        if query is None:
            query = {
                'currency': currency if currency else ''
            }
        path = "/user/minWithdrawalFee"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_preferences(self, prefs=None, overwrite=None, postdict=None):
        """Save user preferences."""
        if postdict is None:
            postdict = {
                'prefs': prefs if prefs else '',
                'overwrite': overwrite if overwrite is not None else False
            }
        path = "/user/preferences"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_request_withdrawal(self, otpToken=None, currency=None, amount=None, address=None, fee=None, text=None, postdict=None):
        """Request a withdrawal to an external wallet."""
        if postdict is None:
            postdict = {
                'otpToken': otpToken if otpToken else '',
                'currency': currency if currency else '',
                'amount': amount if amount else 0,
                'address': address if address else '',
                'text': text if text else '',
            }
            if fee:
                postdict['fee'] = fee
        path = "/user/preferences"
        return self.call_api(path=path, postdict=postdict, verb="POST")

    @authentication_required
    def user_wallet(self, currency=None, query=None):
        """Get your current wallet information."""
        if query is None:
            query = {
                'currency': currency if currency else ''
            }
        path = "/user/wallet"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_wallet_history(self, currency=None, count=None, start=None, query=None):
        """Get a history of all of your wallet transactions (deposits, withdrawals, PNL)."""
        if query is None:
            query = {
                'currency': currency if currency else '',
                'count': count if count else 100,
                'start': start if start else 0
            }
        path = "/user/walletHistory"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_wallet_summary(self, currency=None, query=None):
        """Get a summary of all of your wallet transactions (deposits, withdrawals, PNL)."""
        if query is None:
            query = {
                'currency': currency if currency else ''
            }
        path = "/user/walletSummary"
        return self.call_api(path=path, query=query, verb="GET")

    @authentication_required
    def user_event(self, count=None, startId=None, query=None):
        """Get your user events."""
        if query is None:
            query = {
                'count': count if count else 100,
                'startId': startId if startId else 0
            }
        path = "/userEvent"
        return self.call_api(path=path, query=query, verb="GET")

    def call_api(self, path, query=None, postdict=None, timeout=7, verb=None, rethrow_errors=True,
                 max_retries=None):
        """Send a request to BitMEX Servers."""
        # Handle URL
        url = self.base_url + path

        # Default to POST if data is attached, GET otherwise
        if not verb:
            verb = 'POST' if postdict else 'GET'

        # By default don't retry POST or PUT. Retrying GET/DELETE is okay because they are idempotent.
        # In the future we could allow retrying PUT, so long as 'leavesQty' is not used (not idempotent),
        # or you could change the clOrdID (set {"clOrdID": "new", "origClOrdID": "old"}) so that an amend
        # can't erroneously be applied twice.
        if max_retries is None:
            max_retries = 0 if verb in ['POST', 'PUT'] else 3

        # Auth: API Key/Secret
        auth = APIKeyAuthWithExpires(self.api_key, self.api_secret)

        def exit_or_throw(e):
            if rethrow_errors:
                raise e
            else:
                exit(1)

        def retry():
            if self.retries > max_retries:
                raise errors.MaxRetriesReachedError("Max retries on %s (%s) hit, raising." % (path, json.dumps(postdict or '')))
            return self.call_api(path, query, postdict, timeout, verb, rethrow_errors, max_retries)

        # Make the request
        response = None
        try:
            data = json.dumps(postdict)
            if data == 'null':
                data = ''
            self.logger.info("sending req to %s: %s" % (url, data or query or ''))
            req = requests.Request(verb, url, data=data, auth=auth, params=query, )
            prepped = self.session.prepare_request(req)
            response = self.session.send(prepped, timeout=timeout)
            # Make non-200s throw
            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            if response is None:
                raise e

            # 401 - Auth error. This is fatal.
            if response.status_code == 401:
                self.logger.error("API Key or Secret incorrect, please check and restart.")
                self.logger.error("Error: " + response.text)
                if postdict:
                    self.logger.error(postdict)
                # Always exit, even if rethrow_errors, because this is fatal
                exit_or_throw(errors.AuthenticationError)

            # 404, can be thrown if order canceled or does not exist.
            elif response.status_code == 404:
                if verb == 'DELETE':
                    self.logger.error("Order not found: %s" % postdict['orderID'])
                    return
                self.logger.error("Unable to contact the BitMEX API (404). " +
                                  "Request: %s \n %s" % (url, json.dumps(postdict)))
                exit_or_throw(e)

            # 429, ratelimit; cancel orders & wait until X-RateLimit-Reset
            elif response.status_code == 429:
                self.logger.error("Ratelimited on current request. Sleeping, then trying again. Try fewer " +
                                  "order pairs or contact support@bitmex.com to raise your limits. " +
                                  "Request: %s \n %s" % (url, json.dumps(postdict)))
                # Figure out how long we need to wait.
                ratelimit_reset = response.headers['X-RateLimit-Reset']
                to_sleep = int(ratelimit_reset) - int(time.time())
                reset_str = datetime.datetime.fromtimestamp(int(ratelimit_reset)).strftime('%X')

                self.logger.error("Your ratelimit will reset at %s. Sleeping for %d seconds." % (reset_str, to_sleep))
                time.sleep(to_sleep)

                # Retry the request.
                return retry()

            # 503 - BitMEX temporary downtime, likely due to a deploy. Try again
            elif response.status_code == 503:
                self.logger.warning("Unable to contact the BitMEX API (503), retrying. " +
                                    "Request: %s \n %s" % (url, json.dumps(postdict)))
                time.sleep(3)
                return retry()

            elif response.status_code == 400:
                error = response.json()['error']
                message = error['message'].lower() if error else ''

                # Duplicate clOrdID: that's fine, probably a deploy, go get the order(s) and return it
                if 'duplicate clordid' in message:
                    orders = postdict['orders'] if 'orders' in postdict else postdict

                    ids = json.dumps({'clOrdID': [order['clOrdID'] for order in orders]})
                    order_results = self.call_api('/order', query={'filter': ids}, verb='GET')

                    for i, order in enumerate(order_results):
                        if (
                                order['orderQty'] != abs(postdict['orderQty']) or
                                order['side'] != ('Buy' if postdict['orderQty'] > 0 else 'Sell') or
                                order['price'] != postdict['price'] or
                                order['symbol'] != postdict['symbol']):
                            raise errors.DuplicateClordid('Attempted to recover from duplicate clOrdID, but order '
                                                          'returned from API ' +
                                                          'did not match POST.\nPOST data: %s\nReturned order: %s' % (
                                                              json.dumps(orders[i]), json.dumps(order)))
                    # All good
                    return order_results

                elif 'insufficient available balance' in message:
                    self.logger.error('Account out of funds. The message: %s' % error['message'])
                    exit_or_throw(errors.InsufficientBalanceError)

            # If we haven't returned or re-raised yet, we get here.
            self.logger.error("Unhandled Error: %s: %s" % (e, response.text))
            self.logger.error("Endpoint was: %s %s: %s" % (verb, path, json.dumps(postdict)))
            exit_or_throw(e)

        except requests.exceptions.Timeout as e:
            # Timeout, re-run this request
            self.logger.warning("Timed out on request: %s (%s), retrying..." % (path, json.dumps(postdict or '')))
            return retry()

        except requests.exceptions.ConnectionError as e:
            self.logger.warning("Unable to contact the BitMEX API (%s). Please check the URL. Retrying. " +
                                "Request: %s %s \n %s" % (e, url, json.dumps(postdict)))
            time.sleep(1)
            return retry()

        # Reset retry counter on success
        self.retries = 0

        self.logger.info(f'req has been sent, response: {response.json()}')

        return response.json()

    def __del__(self):
        self.exit()

    def exit(self):
        if self.init_ws:
            self.ws.exit()
