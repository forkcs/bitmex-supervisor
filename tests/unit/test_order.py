import unittest
from decimal import Decimal

from supervisor.core.orders import Order


class OrderCRUDTests(unittest.TestCase):

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

    def test_move_limit_order(self):
        order = Order(order_type='Limit', qty=228, side='Buy', price=Decimal(1000))
        order.move(to=Decimal(1001))
        self.assertEqual(Decimal(1001), order.price)

    def test_move_stop_order(self):
        order = Order(order_type='Stop', qty=228, side='Buy', stop_px=Decimal(1000))
        order.move(to=Decimal(1001))
        self.assertEqual(Decimal(1001), order.stop_px)

    def test_move_bad_order(self):
        # Nothing to move: no price or stop_px
        order = Order(order_type='Stop', qty=228, side='Buy')
        with self.assertRaises(RuntimeError):
            order.move(to=Decimal(1234))

    def test_move_with_bad_argument(self):
        order = Order(order_type='Limit', qty=228, side='Buy', price=Decimal(1000))
        with self.assertRaises(TypeError):
            order.move(to=1001)

    def test_make_correct_stop_order(self):
        order = Order(order_type='Stop', qty=228, side='Sell', stop_px=Decimal(1000))
        self.assertTrue(order.is_valid())

    def test_make_stop_order_without_stop_px(self):
        order = Order(order_type='Stop', qty=228, side='Sell')
        self.assertFalse(order.is_valid())

    def test_make_stop_order_with_negative_stop_px(self):
        order = Order(order_type='Stop', qty=228, side='Sell', stop_px=Decimal(-1000))
        self.assertFalse(order.is_valid())


class OrdersComparisonTests(unittest.TestCase):

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
        """Assert that while comparing only certain parameters are considered."""

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


class ExportImportOrdersTests(unittest.TestCase):

    def test_export_order_to_api_dict_include_empty(self):
        order = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            stop_px=None,
            hidden=True,
            close=True,
            reduce_only=True,
            passive=True
        )
        expected_order_dict = {
            'clOrdID': None,
            'orderID': None,
            'ordType': 'Limit',
            'orderQty': 228,
            'side': 'Buy',
            'price': 1000.0,
            'stopPx': None,
            'displayQty': 0,
            'execInst': 'Close,ReduceOnly,ParticipateDoNotInitiate'
        }
        api_order_dict = order.as_dict(include_empty=True)
        self.assertEqual(expected_order_dict, api_order_dict)

    def test_export_order_to_api_dict_no_empty(self):
        """Do not include empty parameters to result dict."""

        order = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000)
        )
        expected_order_dict = {
            'ordType': 'Limit',
            'orderQty': 228,
            'side': 'Buy',
            'price': 1000.0,
        }
        api_order_dict = order.as_dict(include_empty=False)
        self.assertEqual(expected_order_dict, api_order_dict)

    def test_import_limit_order_from_dict(self):
        order_dict = {
            'clOrdID': None,
            'orderID': None,
            'ordType': 'Limit',
            'orderQty': 228,
            'side': 'Buy',
            'price': 1000.0,
            'stopPx': None,
            'displayQty': 0,
            'execInst': 'Close,ReduceOnly,ParticipateDoNotInitiate'
        }
        expected_order = Order(
            order_type='Limit',
            qty=228,
            side='Buy',
            price=Decimal(1000),
            hidden=True,
            close=True,
            reduce_only=True,
            passive=True
        )
        self.assertTrue(expected_order == Order.from_dict(order_dict))

    def test_import_stop_order_from_dict(self):
        order_dict = {
            'clOrdID': None,
            'orderID': None,
            'ordType': 'Stop',
            'orderQty': 228,
            'side': 'Buy',
            'price': None,
            'stopPx': 1000.0,
            'displayQty': 0,
            'execInst': 'Close,ReduceOnly,ParticipateDoNotInitiate'
        }
        expected_order = Order(
            order_type='Stop',
            qty=228,
            side='Buy',
            stop_px=Decimal(1000),
            hidden=True,
            close=True,
            reduce_only=True,
            passive=True
        )
        self.assertTrue(expected_order == Order.from_dict(order_dict))

    def test_import_order_from_empty_dict(self):
        # try to create order from dict with {} parameter
        self.assertEqual(Order(), Order.from_dict({}))
