from typing import Callable


class Order:
    def __init__(self,
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

        self._on_reject: Callable = None
        self._on_cancel: Callable = None
        self._on_fill: Callable = None

    def __eq__(self, other):
        """Custom == for use 'order in orders' expressions."""

        if self.get_comparison_params() == other.get_comparison_params():
            return True
        return False

    def on_reject(self, *args, **kwargs) -> None:
        if self._on_reject is not None:
            self._on_reject(*args, **kwargs)

    def on_cancel(self, *args, **kwargs) -> None:
        if self._on_cancel is not None:
            self._on_cancel(*args, **kwargs)

    def on_fill(self, *args, **kwargs) -> None:
        if self._on_fill is not None:
            self._on_fill(*args, **kwargs)

    def is_valid(self) -> bool:
        """Validate order parameters for common errors.

        Method made for prevent 4xx errors on API requests.
        """

        # all orders must have order type
        if self.order_type is None:
            return False
        # limit orders must have price
        if self.order_type == 'Limit' and self.price is None:
            return False
        # stop-loss orders must have stop_px
        if self.order_type == 'Stop' and self.stop_px is None:
            return False
        # price must be positive
        if self.price is not None and self.price < 0:
            return False
        # stop_px must be positive
        if self.stop_px is not None and self.stop_px < 0:
            return False
        # for sell orders use side='Sell'
        if self.qty <= 0:
            return False
        # side only can be Buy or Sell
        if self.side not in ['Buy', 'Sell']:
            return False
        return True

    def get_comparison_params(self) -> list:
        """Get essential parameters, that are used to distinguish orders."""

        parameters = [
            self.order_type,
            self.qty,
            self.side,
            self.price,
            self.stop_px,
            self.hidden,
            self.close,
            self.reduce_only,
            self.passive
        ]
        return parameters

    def as_dict(self, include_empty=False) -> dict:
        """This order representation made to be similar to BitMEX API order objects."""

        order_dict = {}
        exec_inst = []

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

        if exec_inst or include_empty:
            exec_inst_str = ','.join(exec_inst)
            order_dict['execInst'] = exec_inst_str

        return order_dict

    @staticmethod
    def from_dict(order_dict: dict):
        """This method creates new Order object from standart BitMEX API order dictionary."""

        new_order = Order()
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

        new_order.hidden = order_dict.get('displayQty', None) == 0

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
