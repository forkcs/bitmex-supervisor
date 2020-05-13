from supervisor.core.api import BitMEX
from supervisor.core.orders import Order


class Exchange:
    """High-level BitMEX API interface.

    Operates with Order objects
    """

    def __init__(self, symbol, api_key, api_secret, test=False, connect_ws=True):
        self.symbol = symbol
        self.conn = BitMEX(symbol=symbol, api_key=api_key, api_secret=api_secret, test=test, init_ws=connect_ws)

    def restart_ws(self):
        self.conn.reinit_ws()

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

    def get_position_size_ws(self):
        return self.conn.ws.position(self.symbol)['currentQty']

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
        return [Order.from_dict(o) for o in self.conn.open_orders()]

    def get_filled_orders_ws(self):
        return [Order.from_dict(o) for o in self.conn.filled_orders()]

    def get_order_by_clordid_ws(self, clordid):
        orders = self.conn.get_orders()
        orders = list(filter(lambda x: x['clOrdID'] == clordid, orders))
        if len(orders) == 1:
            return Order.from_dict(orders[0])
        return None

    def get_order_status_ws(self, order):
        orders = self.conn.get_orders()
        orders = list(filter(lambda x: x.get('orderID', None) == order.order_id, orders))
        if len(orders) == 1:
            return orders[0].get('ordStatus')
        elif len(orders) == 0:
            return None

    def get_order_executions_ws(self, clordid):
        return self.conn.get_executions(clordid=clordid)

    def move_order(self, order, to: float = None):
        if to is not None:
            order.move(to=to)
        self.conn.order_edit(**order.as_dict())

    def place_order(self, order):
        new_order = self.conn.order_create(**order.as_dict())
        order.order_id = new_order.get('orderID', '')

    def place_market_order(self, qty: int) -> dict:
        return self.conn.order_create(ordType='Market', orderQty=qty)

    def bulk_place_orders(self, orders):
        order_dicts = [order.as_dict() for order in orders]

        response = self.conn.order_bulk_create(order_dicts)
        for order_dict, order in zip(response, orders):
            order.order_id = order_dict['orderID']

    def cancel_order(self, order):
        if order.clordid is not None:
            self.conn.order_cancel(clOrdID=order.clordid)
        elif order.order_id is not None:
            self.conn.order_cancel(orderID=order.order_id)
        else:
            raise ValueError('clordid or order id must be given.')

    def bulk_cancel_orders(self, orders):
        clordid_list = [o.clordid for o in orders if o.clordid is not None]
        order_id_list = [o.order_id for o in orders if o.order_id is not None]
        self.conn.order_cancel(orderID=order_id_list, clOrdID=clordid_list)

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
