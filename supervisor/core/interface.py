from supervisor.core.api import BitMEX


class Exchange:
    """High-level BitMEX API interface."""

    def __init__(self, symbol, api_key, api_secret, test=False, connect_ws=True):
        self.symbol = symbol
        self.conn = BitMEX(symbol=symbol, api_key=api_key, api_secret=api_secret, test=test, init_ws=connect_ws)

    def is_open(self):
        """Check that websockets are still open."""

        return not self.conn.ws.exited

    #
    # Price-related methods
    #

    def get_ticker_ws(self):
        """Return ticker object.

        Ticker is a dictionary with 'last', 'buy', 'sell' and 'mid' keys.
        """
        return self.conn.ticker_data()

    def get_last_price_ws(self):
        return self.get_ticker_ws()['last']

    def get_first_orderbook_price_ws(self, bid):
        # first list element for bid and last for ask
        index = 0 if bid else -1
        return self.conn.order_book(depth=1)[index]['price']

    def get_third_orderbook_price_ws(self, bid):
        # first list element for bid and last for ask
        index = 0 if bid else -1
        return self.conn.order_book(depth=3)[index]['price']

    #
    # Position-related methods
    #

    def get_position_size(self):
        return self.conn.position()['currentQty']

    def get_average_position_entry_price(self):
        return self.conn.position()['avgEntryPrice'] or 0

    def get_leverage(self):
        return self.conn.position().get('leverage', None)

    def set_leverage(self, leverage):
        """Set leverage to a given value, set to cross margin if value is 0"""

        if leverage < 0:
            raise ValueError('Leverage must be positive or 0 for cross-margin.')
        if leverage > 100:
            raise ValueError('Leverage must be lesser than 100')
        self.conn.position_leverage(leverage)

    #
    # Orders-related methods
    #

    def get_open_orders_ws(self):
        return self.conn.open_orders()

    def get_filled_orders_ws(self):
        return self.conn.filled_orders()

    def get_order_ws(self, clordid):
        orders = self.conn.get_orders()
        orders = list(filter(lambda x: x['clOrdID'] == clordid, orders))
        if len(orders) == 1:
            return orders[0]
        return {}

    def get_order_status_ws(self, clordid):
        orders = self.conn.get_orders()
        orders = list(filter(lambda x: x['clOrdID'] == clordid, orders))
        if len(orders) == 1:
            return orders[0].get('ordStatus')
        elif len(orders) == 0:
            return ''

    def get_order_executions_ws(self, clordid):
        return self.conn.get_executions(clordid=clordid)

    def place_order(self, order_dict=None, qty=None, price=None, exec_inst=None, hidden=False, stop_px=None,
                    order_type='Market', clordid=''):
        if order_dict:
            return self.conn.order_create(**order_dict)
        if qty == 0:
            return
        display_qty = None
        if hidden and order_type == 'Limit':
            display_qty = 0
        return self.conn.order_create(orderQty=qty, price=price, ordType=order_type, displayQty=display_qty,
                                      clOrdID=clordid, execInst=exec_inst, stopPx=stop_px)

    def bulk_place_orders(self, orders):
        for o in orders:
            o['symbol'] = self.symbol
        return self.conn.order_bulk_create(orders=orders)

    def cancel_order(self, *, clordid=None, order_id=None):
        if clordid is not None:
            self.conn.order_cancel(clOrdID=clordid)
        elif order_id is not None:
            self.conn.order_cancel(orderID=order_id)
        else:
            raise ValueError('clordid or order id must be given.')

    def bulk_cancel_orders(self, *, clordid_list=None, order_id_list=None):
        if clordid_list:
            self.conn.order_cancel(clOrdID=clordid_list)
        elif order_id_list:
            self.conn.order_cancel(orderID=order_id_list)
        else:
            raise ValueError('clordid list or order id list must be given.')

    def cancel_all_orders(self):
        self.conn.order_cancel_all()

    #
    # Account-related methods
    #

    def get_margin_ws(self):
        """Return account balance in XBt."""

        return self.conn.funds()

    #
    # Control methods
    #

    def exit(self):
        self.conn.exit()
