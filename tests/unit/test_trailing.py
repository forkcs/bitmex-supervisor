import unittest

from supervisor.core.orders import Order
from supervisor.core.trailing_orders import TrailingShell
from supervisor.core.utils.math import to_nearest


class Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.order = Order(order_type='Stop', qty=228, stop_px=900, side='Sell')
        self.trailing_order = TrailingShell(order=self.order, offset=10, tick_size=0.5, test=True)

    def tearDown(self):
        pass

    def test_update_max_price(self):
        self.trailing_order.initial_price = 1000
        self.trailing_order.max_price = 1001

        # assert order was moved
        expected_price = to_nearest(1001 * 0.9, 0.5)
        self.assertEqual(expected_price, self.order.stop_px)

    def test_update_min_price(self):
        self.order.side = 'Buy'

        self.trailing_order.initial_price = 1000
        self.trailing_order.min_price = 999

        # assert order was moved
        expected_price = to_nearest(999 * 1.1, 0.5)
        self.assertEqual(expected_price, self.order.stop_px)
