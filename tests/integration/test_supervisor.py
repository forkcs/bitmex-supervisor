import unittest
from time import sleep
from unittest.mock import Mock

from supervisor import Supervisor
from supervisor.core.orders import Order


class SupervisorEntryTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_market_position_enter_while_running_cycle(self):
        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_by_market_order(qty=20)
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        # assert that Supervisor change position only once
        self.exchange_mock.place_market_order.assert_called_once_with(qty=20)

    def test_fb_last_position_enter_while_running_cycle(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_fb_method(
            qty=20,
            price_type='last',
            timeout=5,
            max_retry=3
        )
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        order = Order(order_type='Limit', qty=20, price=1000, side='Buy', passive=True)
        # assert that Supervisor change position only once with limit order
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_first_ob_position_enter_while_running_cycle(self):
        self.exchange_mock.get_first_orderbook_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_fb_method(
            qty=20,
            price_type='first_ob',
            timeout=5,
            max_retry=3
        )
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        order = Order(order_type='Limit', qty=20, price=1000, side='Buy', passive=True)
        # assert that Supervisor change position only once with limit order
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_third_ob_position_enter_while_running_cycle(self):
        self.exchange_mock.get_third_orderbook_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_fb_method(
            qty=20,
            price_type='third_ob',
            timeout=5,
            max_retry=3
        )
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        order = Order(order_type='Limit', qty=20, price=1000, side='Buy', passive=True)
        # assert that Supervisor change position only once with limit order
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_positive_deviant_position_enter_while_running_cycle(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_fb_method(
            qty=20,
            price_type='deviant',
            timeout=5,
            max_retry=3,
            deviation=15
        )
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        order = Order(order_type='Limit', qty=20, price=1150, side='Buy', passive=True)
        # assert that Supervisor change position only once with limit order
        self.exchange_mock.place_order.assert_called_once_with(order)

    def test_fb_negative_deviant_position_enter_while_running_cycle(self):
        self.exchange_mock.get_last_price_ws.return_value = 1000
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

        self.supervisor.run_cycle()

        self.supervisor.stop_cycle()
        self.supervisor.enter_fb_method(
            qty=20,
            price_type='deviant',
            timeout=5,
            max_retry=3,
            deviation=-15
        )
        self.exchange_mock.get_position_size_ws.return_value = 20
        self.supervisor.run_cycle()

        sleep(1)

        order = Order(order_type='Limit', qty=20, price=850, side='Buy', passive=True)
        # assert that Supervisor change position only once with limit order
        self.exchange_mock.place_order.assert_called_once_with(order)


class OrdersCallbacksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_filled_callback_will_be_called(self):

        order = Order(order_type='Limit', side='Sell', qty=228, price=1000)
        order.order_id = 123456

        callback = Mock()
        order._on_fill = callback
        self.supervisor.add_order(order)

        self.exchange_mock.get_order_status_ws.return_value = 'Filled'

        self.supervisor.run_cycle()

        sleep(1)

        callback.assert_called_once()
        self.assertListEqual([], self.supervisor._orders)

    def test_rejected_callback_will_be_called(self):
        order = Order(order_type='Limit', side='Sell', qty=228, price=1000)
        order.order_id = 123456

        callback = Mock()
        order._on_reject = callback
        self.supervisor.add_order(order)

        self.exchange_mock.get_order_status_ws.return_value = 'Rejected'

        self.supervisor.run_cycle()

        sleep(1)

        callback.assert_called_once()
        self.assertListEqual([], self.supervisor._orders)

    def test_several_filled_orders_at_the_same_time(self):
        order_1 = Order(order_type='Limit', side='Sell', qty=228, price=1000)
        order_1.order_id = 123456
        order_2 = Order(order_type='Limit', side='Sell', qty=229, price=1001)
        order_2.order_id = 123457
        order_3 = Order(order_type='Limit', side='Sell', qty=2210, price=1002)
        order_3.order_id = 123458
        order_4 = Order(order_type='Limit', side='Sell', qty=2211, price=1003)
        order_4.order_id = 123459

        callback_1 = Mock()
        callback_2 = Mock()
        callback_3 = Mock()
        callback_4 = Mock()
        order_1._on_fill = callback_1
        order_2._on_fill = callback_2
        order_3._on_fill = callback_3
        order_4._on_fill = callback_4
        self.supervisor.add_order(order_1)
        self.supervisor.add_order(order_2)
        self.supervisor.add_order(order_3)
        self.supervisor.add_order(order_4)

        self.exchange_mock.get_order_status_ws.return_value = 'Filled'

        self.supervisor.run_cycle()

        sleep(1)

        callback_1.assert_called_once()
        callback_2.assert_called_once()
        callback_3.assert_called_once()
        callback_4.assert_called_once()
        self.assertListEqual([], self.supervisor._orders)
