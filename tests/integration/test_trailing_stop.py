import unittest
from time import sleep
from unittest.mock import Mock

from supervisor import Supervisor
from supervisor.core.orders import Order


class TrailingStopTests(unittest.TestCase):

    def setUp(self) -> None:
        self.exchange_mock = Mock()
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_position_size_ws.return_value = 0
        self.supervisor = Supervisor(interface=self.exchange_mock)

        self.exchange_mock.conn.base_url = 'https://testnet.bitmex.com/api/v1'
        self.exchange_mock.conn.get_tick_size.return_value = 0.5

    def tearDown(self) -> None:
        self.supervisor.exit_cycle()

    def test_buy_order_will_follow_the_price(self):
        order = Order(order_type='Stop', side='Buy', qty=228, stop_px=10000)
        self.exchange_mock.get_open_orders_ws.return_value = [order]

        self.exchange_mock.get_last_price_ws.return_value = 9000

        self.supervisor.add_trailing_order(order, offset=10)
        self.supervisor.run_cycle()

        self.exchange_mock.get_last_price_ws.return_value = 8000
        order.tracker.min_price = 8000
        self.assertEqual(8800, order.stop_px)

        self.exchange_mock.get_last_price_ws.return_value = 7000
        order.tracker.min_price = 7000
        self.assertEqual(7700, order.stop_px)

    def test_sell_order_will_follow_the_price(self):
        order = Order(order_type='Stop', side='Sell', qty=228, stop_px=1000)
        self.exchange_mock.get_open_orders_ws.return_value = [order]

        self.exchange_mock.get_last_price_ws.return_value = 1000

        self.supervisor.add_trailing_order(order, offset=10)
        self.supervisor.run_cycle()

        self.exchange_mock.get_last_price_ws.return_value = 7000
        order.tracker.max_price = 7000
        self.assertEqual(6300, order.stop_px)

        self.exchange_mock.get_last_price_ws.return_value = 8000
        order.tracker.max_price = 8000
        self.assertEqual(7200, order.stop_px)

    def test_stop_tracking_after_fill_order(self):
        order = Order(order_type='Stop', side='Sell', qty=228, stop_px=1000)
        self.exchange_mock.get_open_orders_ws.return_value = [order]
        self.exchange_mock.get_last_price_ws.return_value = 9000

        self.supervisor.add_trailing_order(order, 10)

        self.supervisor.run_cycle()

        order.order_id = 1234
        self.exchange_mock.get_open_orders_ws.return_value = []
        self.exchange_mock.get_order_status_ws.return_value = 'Filled'

        sleep(0.5)

        self.assertTrue(order.tracker.exited)
