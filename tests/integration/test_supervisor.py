import unittest
from time import sleep
from unittest.mock import Mock

from supervisor import Supervisor
from supervisor.core.orders import Order


class SupervisorEntryTests(unittest.TestCase):

    def setUp(self) -> None:
        # self.exchange = Exchange(symbol=settings.TEST_SYMBOL, api_key=settings.TEST_API_KEY,
        #                          api_secret=settings.TEST_API_SECRET, test=True)
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
