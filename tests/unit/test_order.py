import unittest
from decimal import Decimal

from supervisor.core.orders import Order


class OrderCreationTests(unittest.TestCase):

    def test_add_full_order(self):
        order = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        self.assertTrue(order.is_valid())

    def test_make_empty_order(self):
        order = Order()
        self.assertFalse(order.is_valid())

    def test_make_order_with_no_order_type(self):
        order = Order(qty=228, side='Buy', price=Decimal(1000))
        self.assertFalse(order.is_valid())

    def test_add_clear_callback(self):
        def callback(): pass
        def callback2(): pass
        order = Order(qty=228, side='Buy', price=Decimal(1000))
        order.add_callback(callback)
        self.assertListEqual([callback], order._callbacks)

        order.add_callback(callback2)
        self.assertListEqual([callback, callback2], order._callbacks)

        order.clear_callbacks()
        self.assertListEqual([], order._callbacks)

    ################
    # Limit orders #
    ################

    def test_make_limit_order_with_stop_px(self):
        order = Order(order_type='Limit', qty=228, stop_px=Decimal(1000))
        self.assertFalse(order.is_valid())

    def test_make_limit_order_without_price(self):
        order = Order(order_type='Limit', qty=228, side='Buy')
        self.assertFalse(order.is_valid())

    def test_make_limit_order_without_side(self):
        order = Order(order_type='Limit', qty=228, price=Decimal(1000))
        self.assertFalse(order.is_valid())

    def test_make_limit_order_with_negative_qty(self):
        order = Order(order_type='Limit', qty=-228, side='Buy', price=Decimal(1000))
        self.assertFalse(order.is_valid())

    def test_make_limit_order_with_negative_price(self):
        order = Order(order_type='Limit', qty=228, side='Buy', price=Decimal(-1000))
        self.assertFalse(order.is_valid())

    def test_make_limit_order_with_bad_side(self):
        order = Order(order_type='Limit', qty=228, side='Bad side', price=Decimal(1000))
        self.assertFalse(order.is_valid())

    ###############
    # Stop orders #
    ###############

    def test_make_correct_stop_order(self):
        order = Order(order_type='Stop', qty=228, side='Sell', stop_px=Decimal(1000))
        self.assertTrue(order.is_valid())

    def test_make_stop_order_without_stop_px(self):
        order = Order(order_type='Stop', qty=228, side='Sell')
        self.assertFalse(order.is_valid())

    def test_make_stop_order_with_negative_stop_px(self):
        order = Order(order_type='Stop', qty=228, side='Sell', stop_px=Decimal(-1000))
        self.assertFalse(order.is_valid())

    ####################
    # Comparison tests #
    ####################

    def test_same_orders_equality(self):
        order1 = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        order2 = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        self.assertEqual(order1, order2)

    def test_orders_are_not_equal(self):
        order1 = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        order2 = Order(
            order_type='Limit',
            qty=229,  # Other quantity
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        self.assertNotEqual(order1, order2)

    def test_compare_only_needed_params(self):
        """Test that while comparing only certain parameters are considered."""

        order1 = Order(
            clordid='cl123',  # various params
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        order2 = Order(
            clordid='cl124',  # various params
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=False,
            reduce_only=False,
            passive=True
        )
        self.assertEqual(order1, order2)
