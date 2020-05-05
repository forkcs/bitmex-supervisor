import unittest
from unittest.mock import Mock
from decimal import Decimal

from supervisor import Supervisor
from supervisor.core.orders import Order


class SupervisorCycleTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
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

        self.assertTrue(self.supervisor._stopped.is_set())


class SupervisorOrdersTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_add_order(self):
        new_order = Order(order_type='Limit', qty=228, price=Decimal(1000), side='Buy')
        self.supervisor.add_order(new_order)

        self.assertIn(new_order, self.supervisor._orders)

    def test_add_empty_order(self):
        with self.assertRaises(ValueError):
            self.supervisor.add_order(Order())

    def test_add_order_with_callback(self):
        def callback(): pass
        new_order = Order(order_type='Limit', qty=228, price=Decimal(1000), side='Buy')
        self.supervisor.add_order(new_order, callback=callback)

        self.assertIn(new_order, self.supervisor._orders)
        self.assertIn(callback, self.supervisor._orders[0]._callbacks)

    def test_remove_order(self):
        new_order = Order(order_type='Limit', qty=228, price=Decimal(1000), side='Buy')
        self.supervisor.add_order(new_order)

        self.supervisor.remove_order(new_order)
        self.assertNotIn(new_order, self.supervisor._orders)

    def test_remove_orer_with_callback(self):
        def callback(): pass
        new_order = Order(order_type='Limit', qty=228, price=Decimal(1000), side='Buy')
        self.supervisor.add_order(new_order, callback=callback)

        self.supervisor.remove_order(new_order)
        self.assertNotIn(new_order, self.supervisor._orders)

    def test_move_order(self):
        new_order = Order(order_type='Limit', qty=228, price=Decimal(1000), side='Buy')
        self.supervisor.add_order(new_order)

        self.supervisor.move_order(new_order, Decimal(1001))
        # assert that modified object is the same object created before
        self.assertIn(new_order, self.supervisor._orders)
        # assert that order was moved
        self.assertEqual(Decimal(1001), new_order.price)


class SupervisorTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
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
