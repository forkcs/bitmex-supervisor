from typing import Callable


ORDER_TYPES = [
    'Limit',
    'Stop'
]

ORDER_SIDE_TYPES = [
    'Buy',
    'Sell'
]


class Order:
    def __init__(self,
                 symbol: str = 'XBTUSD',
                 order_type: str = None,
                 clordid: str = None,
                 qty: int = None,
                 side: str = None,
                 price: float = None,
                 stop_px: float = None,
                 hidden: bool = False,
                 close: bool = False,
                 reduce_only: bool = False,
                 passive: bool = False):

        self.symbol = symbol
        self.order_id = None
        self.order_type = order_type
        self.clordid = clordid
        self.qty = qty
        self.side = side
        self.price = price
        self.stop_px = stop_px
        self.hidden = hidden
        self.close = close
        self.reduce_only = reduce_only
        self.passive = passive

        self.is_trailing = False

        # DO NOT USE Supervisor.stop_cycle() in callbacks!!!
        # It causes 100% deadlock
        self._on_reject: Callable = None
        self._on_fill: Callable = None

    def __eq__(self, other):
        """Custom == for use 'order in orders' expressions."""

        if self.get_comparison_params() == other.get_comparison_params():
            return True
        return False

    def almost_equal(self, other):
        """If ordes are same at all except price or stop_ps."""

        if self.get_not_price_comparison_params() == other.get_not_price_comparison_params():
            return True
        return False

    def on_reject(self, *args, **kwargs) -> None:
        if self._on_reject is not None:
            self._on_reject(*args, **kwargs)

    def on_fill(self, *args, **kwargs) -> None:
        if self._on_fill is not None:
            self._on_fill(*args, **kwargs)

    def is_valid(self) -> bool:
        """Validate order parameters for common errors.

        Method made for prevent 4xx errors on API requests.
        """

        # all orders must has a symbol
        if self.symbol is None:
            return False
        # all orders must has an order type
        if self.order_type is None:
            return False
        # all orders must has a  side
        if self.side is None:
            return False
        # Only Close orders may has no quantity
        if self.qty is None and not self.close:
            return False
        # quantity must be positive
        if self.qty is not None and self.qty <= 0:
            return False

        # Check limit orders below:
        if self.order_type == 'Limit':
            if self.price is None:
                return False
            # price must be positive
            if self.price <= 0:
                return False

        # Check stop orders below:
        elif self.order_type == 'Stop':
            if self.stop_px is None:
                return False
            # stop_px must be positive
            if self.stop_px <= 0:
                return False

        # bad arguments check
        if self.side not in ORDER_SIDE_TYPES:
            return False
        if self.order_type not in ORDER_TYPES:
            return False

        # all checks has passed
        return True

    def get_comparison_params(self) -> list:
        """Get essential parameters, that are used to distinguish orders."""

        parameters = [
            self.symbol,
            self.order_type,
            self.qty,
            self.side,
            self.price,
            self.stop_px,
        ]
        return parameters

    def get_not_price_comparison_params(self) -> list:
        """Get several comparison parameters, that are used to move orders."""

        parameters = [
            self.symbol,
            self.order_type,
            self.qty,
            self.side
        ]
        return parameters

    def as_dict(self, include_empty=False) -> dict:
        """This order representation made to be similar to BitMEX API order objects."""

        order_dict = {}
        exec_inst = []

        order_dict['symbol'] = self.symbol
        if self.order_id is not None or include_empty:
            order_dict['orderID'] = self.order_id
        if self.order_type is not None or include_empty:
            order_dict['ordType'] = self.order_type
        if self.clordid is not None or include_empty:
            order_dict['clOrdID'] = self.clordid
        if self.qty is not None or include_empty:
            order_dict['orderQty'] = self.qty
        if self.side is not None or include_empty:
            order_dict['side'] = self.side
        if self.price is not None or include_empty:
            # float(Decimal) for json.dumps works correctly
            order_dict['price'] = float(self.price) if self.price is not None else None
        if self.stop_px is not None or include_empty:
            # float(Decimal) for json.dumps works correctly
            order_dict['stopPx'] = float(self.stop_px) if self.stop_px is not None else None
        if self.hidden:
            order_dict['displayQty'] = 0
        if self.close:
            exec_inst.append('Close')
        if self.reduce_only:
            exec_inst.append('ReduceOnly')
        if self.passive:
            exec_inst.append('ParticipateDoNotInitiate')
        if self.order_type == 'Stop':
            exec_inst.append('LastPrice')

        if exec_inst or include_empty:
            exec_inst_str = ','.join(exec_inst)
            order_dict['execInst'] = exec_inst_str

        return order_dict

    @staticmethod
    def from_dict(order_dict: dict):
        """This method creates new Order object from standart BitMEX API order dictionary."""

        new_order = Order()
        new_order.symbol = order_dict.get('symbol', 'XBTUSD')
        new_order.order_id = order_dict.get('orderID', None)
        new_order.order_type = order_dict.get('ordType', None)
        new_order.qty = order_dict.get('orderQty', None)
        new_order.side = order_dict.get('side', None)

        price = order_dict.get('price', None)
        if price is not None:
            new_order.price = price

        stop_px = order_dict.get('stopPx', None)
        if stop_px is not None:
            new_order.stop_px = stop_px

        new_order.hidden = order_dict.get('displayQty', 1) == 0

        new_order.close = 'Close' in order_dict.get('execInst', '')
        new_order.reduce_only = 'ReduceOnly' in order_dict.get('execInst', '')
        new_order.passive = 'ParticipateDoNotInitiate' in order_dict.get('execInst', '')

        return new_order

    def move(self, to: float) -> None:
        # if type(to) is not float:
        #     raise TypeError('Attribute to must be a float instance.')
        if self.price is not None:
            self.price = to
            return
        elif self.stop_px is not None:
            self.stop_px = to
            return
        raise RuntimeError('Cannot move order with both stop_px and price are absent.')
