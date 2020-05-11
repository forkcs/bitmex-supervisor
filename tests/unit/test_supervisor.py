import unittest
from unittest.mock import Mock, call

import requests

from supervisor import Supervisor
from supervisor.core.orders import Order


class SupervisorCycleTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_run_cycle(self):
        self.supervisor.run_cycle()
        self.assertTrue(self.supervisor._run_thread.is_set())
        self.assertFalse(self.supervisor._exit_sync_thread.is_set())
        self.assertFalse(self.supervisor._stopped.is_set())
        self.assertTrue(self.supervisor.sync_thread.is_alive())

    def test_exit_cycle(self):
        self.supervisor.run_cycle()
        self.assertTrue(self.supervisor.sync_thread.is_alive())

        self.supervisor.exit_cycle()
        self.assertFalse(self.supervisor.sync_thread.is_alive())

    def test_stop_cycle(self):
        self.supervisor.run_cycle()
        self.supervisor.stop_cycle()

        self.assertTrue(self.supervisor._stopped.is_set())
        self.assertFalse(self.supervisor._run_thread.is_set())

    def test_continue_cycle(self):
        self.supervisor.run_cycle()
        self.supervisor.stop_cycle()
        self.supervisor.run_cycle()

        # assert that events conditions are the same as in just-created supervisor
        self.assertTrue(self.supervisor._run_thread.is_set())
        self.assertFalse(self.supervisor._exit_sync_thread.is_set())
        self.assertFalse(self.supervisor._stopped.is_set())
        # cycle should also be alive of course :)
        self.assertTrue(self.supervisor.sync_thread.is_alive())

    def test_exit_from_exited_cycle(self):
        self.supervisor.run_cycle()
        self.supervisor.exit_cycle()
        self.assertFalse(self.supervisor.sync_thread.is_alive())

        self.supervisor.exit_cycle()  # must not raise anything
        self.assertFalse(self.supervisor.sync_thread.is_alive())

    def test_reset(self):
        self.supervisor.run_cycle()
        self.supervisor.reset()

        self.assertEqual(0, self.supervisor.position_size)
        self.assertListEqual([], self.supervisor._orders)


class SupervisorOrdersTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_add_order(self):
        new_order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        self.supervisor.add_order(new_order)

        self.assertIn(new_order, self.supervisor._orders)

    def test_add_empty_order(self):
        with self.assertRaises(ValueError):
            self.supervisor.add_order(Order())

    def test_remove_order(self):
        new_order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        self.supervisor.add_order(new_order)

        self.supervisor.remove_order(new_order)
        self.assertNotIn(new_order, self.supervisor._orders)

    def test_move_order(self):
        new_order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        self.supervisor.add_order(new_order)

        self.supervisor.move_order(new_order, 1001)
        # assert that modified object is the same object created before
        self.assertIn(new_order, self.supervisor._orders)
        # assert that order was moved
        self.assertEqual(1001, new_order.price)


class SyncOrdersTests(unittest.TestCase):
    """All methods that associated with placing and cancelling orders in cycle."""

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_cancel_needless_order(self):
        order1 = Order()
        self.exchange_mock.get_open_orders_ws.return_value = [order1]
        expected_orders = [order1]
        self.supervisor.cancel_needless_orders()

        # assert that Supervisor try to cancel needless order
        self.exchange_mock.bulk_cancel_orders.assert_called_once_with(expected_orders)

    def test_cancel_several_needless_orders(self):
        order1 = Order()
        order2 = Order()
        order3 = Order()
        self.exchange_mock.get_open_orders_ws.return_value = [order1, order2, order3]
        expected_orders = [order1, order2, order3]
        self.supervisor.cancel_needless_orders()

        # assert that Supervisor try to cancel needless order
        self.exchange_mock.bulk_cancel_orders.assert_called_once_with(expected_orders)

    def test_check_unplaced_order(self):
        order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        self.supervisor.add_order(order)
        self.supervisor.check_needed_orders()

        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_check_several_unplaced_orders(self):
        order1 = Order(order_type='Limit', qty=228, price=1001, side='Buy')
        order2 = Order(order_type='Limit', qty=229, price=1002, side='Buy')
        order3 = Order(order_type='Limit', qty=2210, price=1003, side='Buy')
        self.supervisor.add_order(order1)
        self.supervisor.add_order(order2)
        self.supervisor.add_order(order3)
        self.supervisor.check_needed_orders()

        self.exchange_mock.bulk_place_orders.assert_called_once_with([order1, order2, order3])

    def test_check_canceled_order(self):
        def order_status_mock(_order):
            if _order == order:
                return 'Canceled'

        on_cancel_mock = Mock()

        self.exchange_mock.get_order_status_ws.side_effect = order_status_mock

        order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        order.order_id = '1234'
        order._on_cancel = on_cancel_mock
        self.supervisor.add_order(order)

        self.supervisor.check_needed_orders()
        # assert that Supervisor place order anew
        self.exchange_mock.place_order.assert_called_once_with(order)
        # assert that Supervisor call matching callback
        on_cancel_mock.assert_called_once()

    def test_check_rejected_order(self):
        def order_status_mock(_order):
            if _order == order:
                return 'Rejected'

        on_reject_mock = Mock()

        self.exchange_mock.get_order_status_ws.side_effect = order_status_mock

        order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        order.order_id = '1234'
        order._on_reject = on_reject_mock
        self.supervisor.add_order(order)
        self.supervisor.check_needed_orders()

        # assert that we didn`t place this order
        self.exchange_mock.place_order.not_called(order)
        # assert that Supervisor forget this order
        self.assertNotIn(order, self.supervisor._orders)
        # assert that Supervisor call matching callback
        on_reject_mock.assert_called_once()

    def test_check_filled_order(self):
        def order_status_mock(_order):
            if _order == order:
                return 'Filled'

        on_filled_mock = Mock()

        self.exchange_mock.get_order_status_ws.side_effect = order_status_mock

        order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        order.order_id = '1234'
        order._on_fill = on_filled_mock
        self.supervisor.add_order(order)
        self.supervisor.check_needed_orders()

        # assert that we didn`t place this order
        self.exchange_mock.place_order.not_called(order)
        # assert that Supervisor forget this order
        self.assertNotIn(order, self.supervisor._orders)
        # assert that Supervisor call matching callback
        on_filled_mock.assert_called_once()

    def test_check_filled_stop_order(self):
        def order_status_mock(_order):
            if _order == order:
                return 'Triggered'

        on_filled_mock = Mock()

        self.exchange_mock.get_order_status_ws.side_effect = order_status_mock

        order = Order(order_type='Stop', qty=228, stop_px=1000, side='Buy')
        order.order_id = '1234'
        order._on_fill = on_filled_mock
        self.supervisor.add_order(order)
        self.supervisor.check_needed_orders()

        # assert that we didn`t place this order
        self.exchange_mock.place_order.not_called(order)
        # assert that Supervisor forget this order
        self.assertNotIn(order, self.supervisor._orders)
        # assert that Supervisor call matching callback
        on_filled_mock.assert_called_once()

    def test_validation_error_while_placing_order(self):
        validation_error = requests.HTTPError()
        validation_error.response = Mock()
        validation_error.response.text = 'Order price is above the liquidation price of current'
        self.exchange_mock.place_order.side_effect = validation_error

        order = Order(order_type='Limit', qty=228, price=1000, side='Buy')
        self.supervisor.add_order(order)
        self.supervisor.check_needed_orders()

        # assert that method has been called
        self.exchange_mock.place_order.assert_called_once_with(order)
        # assert that we catch the exception and forget the order
        self.assertNotIn(order, self.supervisor._orders)


class SyncPositionTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_enter_long_position(self):
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor.correct_position_size = Mock()

        self.supervisor.position_size = 100
        self.supervisor.sync_position()

        self.supervisor.correct_position_size.assert_called_once_with(qty=100)


class SupervisorEntryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_market_entry(self):
        self.supervisor.enter_by_market_order(228)

        self.exchange_mock.place_market_order.assert_called_once_with(qty=228)

    def test_fb_entry_last_price(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5
        self.supervisor.enter_fb_method(
            qty=228,
            price_type='last',
            max_retry=5,
            timeout=3
        )
        order = Order(order_type='Limit', qty=228, price=1000, side='Buy', passive=True)
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_entry_last_price_timeouted(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'New'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5
        self.supervisor.enter_fb_method(
            qty=228,
            price_type='last',
            max_retry=5,
            timeout=1
        )
        order = Order(order_type='Limit', qty=228, price=1000, side='Buy', passive=True)
        expected_calls = [call(order)] * 5
        self.exchange_mock.place_order.assert_has_calls(expected_calls)

        self.exchange_mock.place_market_order.assert_called_once_with(qty=228)

    def test_fb_entry_first_orderbook_price(self):
        self.exchange_mock.get_first_orderbook_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5
        self.supervisor.enter_fb_method(
            qty=228,
            price_type='first_ob',
            max_retry=5,
            timeout=1
        )
        order = Order(order_type='Limit', qty=228, price=1000, side='Buy', passive=True)
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_entry_third_orderbook_price(self):
        self.exchange_mock.get_third_orderbook_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5
        self.supervisor.enter_fb_method(
            qty=228,
            price_type='third_ob',
            max_retry=5,
            timeout=1
        )
        order = Order(order_type='Limit', qty=228, price=1000, side='Buy', passive=True)
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_entry_with_deviation(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5
        self.supervisor.enter_fb_method(
            qty=228,
            price_type='deviant',
            max_retry=5,
            timeout=1,
            deviation=-10
        )
        order = Order(order_type='Limit', qty=228, price=900, side='Buy', passive=True)
        self.exchange_mock.place_order.assert_called_once_with(order)
