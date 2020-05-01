import unittest
from decimal import Decimal
from unittest.mock import Mock

from supervisor import Supervisor


class AddOrderTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.exchange_mock = Mock()
        cls.supervisor = Supervisor(interface=cls.exchange_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.supervisor.exit_cycle()

    def tearDown(self) -> None:
        self.supervisor.reset()
        self.exchange_mock.reset_mock()

    def test_add_limit_order(self):
        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': ''
        }

        self.supervisor.add_limit_order(qty=228, price=Decimal(1000))
        self.assertIn(expected_order, self.supervisor._orders)

    def test_add_limit_passive_order(self):
        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': 'ParticipateDoNotInitiate'
        }
        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), passive=True)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_add_limit_close_order(self):
        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': 'Close'
        }
        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), reduce_only=True)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_add_limit_close_passive_order(self):
        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': 'ParticipateDoNotInitiate,Close'
        }
        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), passive=True, reduce_only=True)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_add_limit_hidden_order(self):
        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': '',
            'displayQty': 0
        }
        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), hidden=True)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_remove_limit_order(self):
        order = self.supervisor.add_limit_order(qty=228, price=Decimal(1000))
        self.supervisor.remove_order(order)
        self.assertListEqual(self.supervisor._orders, [])

        self.supervisor.reset()
        # test remove order with 2 existing equal orders
        order1 = self.supervisor.add_limit_order(qty=228, price=Decimal(1000))
        order2 = self.supervisor.add_limit_order(qty=228, price=Decimal(1000))
        self.supervisor.remove_order(order1)
        self.assertListEqual(self.supervisor._orders, [order2])

    def test_add_stop_order(self):
        expected_order = {
            'ordType': 'Stop',
            'orderQty': 228,
            'stopPx': 1000,
            'execInst': ''
        }
        self.supervisor.add_stop_order(qty=228, stop_px=Decimal(1000))
        self.assertIn(expected_order, self.supervisor._orders)

    def test_add_stop_close_order(self):
        expected_order = {
            'ordType': 'Stop',
            'orderQty': 228,
            'stopPx': 1000,
            'execInst': 'Close'
        }
        self.supervisor.add_stop_order(qty=228, stop_px=Decimal(1000), reduce_only=True)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_place_several_unplaced_orders(self):
        """Expect that supervisor use bulk create method."""

        order1 = self.supervisor.add_limit_order(qty=228, price=Decimal(1000))
        order2 = self.supervisor.add_limit_order(qty=229, price=Decimal(1001))

        # imitate no open orders condition
        self.supervisor.place_unplaced_orders(real_orders=[])

        # assert that supervisor use the only request for place 2 orders
        self.exchange_mock.bulk_place_orders.assert_called_once_with(orders=[order1, order2])


class FilledOrderCallbackTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.exchange = Mock()
        cls.supervisor = Supervisor(interface=cls.exchange)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.supervisor.exit_cycle()

    def tearDown(self) -> None:
        self.supervisor.reset()

    def test_add_callback(self):

        def callback():
            print('Hello, QA!')

        expected_order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': '',
            'callback': callback
        }
        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), callback=callback)
        self.assertIn(expected_order, self.supervisor._orders)

    def test_check_filled_1_order(self):
        callback_mock = Mock()
        order = {
            'ordType': 'Limit',
            'orderQty': 228,
            'price': 1000,
            'execInst': '',
            'callback': callback_mock
        }
        self.exchange.get_filled_orders_ws.return_value = [order]

        self.supervisor.add_limit_order(qty=228, price=Decimal(1000), callback=callback_mock)
        self.supervisor.check_filled_orders()
        # assert supervisor forget the order
        self.assertNotIn(order, self.supervisor._orders)
        # assert the callback was called
        callback_mock.assert_called_once()
