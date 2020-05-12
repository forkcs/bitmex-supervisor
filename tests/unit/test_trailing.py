import unittest
from unittest.mock import Mock, patch

from supervisor.core.orders import Order
from supervisor.core.trailing_orders import TrailingShell
from supervisor.core.utils.math import to_nearest


class TrailingShellMethodsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.order = Order(order_type='Stop', qty=228, stop_px=900, side='Sell')
        self.trailing_order = TrailingShell(order=self.order, offset=10, tick_size=0.5, test=True, init_ws=False)

    def tearDown(self):
        self.trailing_order.exit()

    def test_calculate_new_price_for_sale_order(self):
        """
        expected price:
        15000 * (1 - (10 / 100))
        = 13500
        """

        new_price = self.trailing_order.calculate_new_price(15000)
        self.assertEqual(13500, new_price)

    def test_calculate_new_price_for_buy_order(self):
        """
        expected price:
        15000 * (1 + (10 / 100))
        = 16500
        """

        self.order.side = 'Buy'
        new_price = self.trailing_order.calculate_new_price(15000)
        self.assertEqual(16500, new_price)

    def test_calculate_new_price_with_rounding(self):
        """
        expected price:
        1234 * (1 - (10 / 100))
        = 1110.6000000000001
        correct price after rounding is 1110.5
        """

        new_price = self.trailing_order.calculate_new_price(1234)
        self.assertEqual(1110.5, new_price)

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
