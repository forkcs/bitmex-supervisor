import time
import unittest
from decimal import Decimal
from unittest.mock import Mock, call

from supervisor import Supervisor


class OrdersSupervisingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exchange_mock = Mock()
        cls.exchange_mock.get_filled_orders_ws.return_value = []
        cls.supervisor = Supervisor(interface=cls.exchange_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.supervisor.exit_cycle()

    def tearDown(self) -> None:
        self.supervisor.reset()
        self.exchange_mock.reset_mock()

    def test_place_limit_order(self):
        mock_calls: int = 0

        def get_open_orders_ws_mock():
            nonlocal mock_calls
            order = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228}
            if mock_calls == 0:
                result = []
            else:
                result = [order]
            mock_calls += 1
            return result

        self.exchange_mock.get_open_orders_ws.side_effect = get_open_orders_ws_mock

        self.supervisor.add_limit_order(qty=1000, price=Decimal(228))
        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)

        # Assert that supervisor only place the one order
        expected_order_dict = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228, 'execInst': ''}
        self.exchange_mock.place_order.assert_called_once_with(order_dict=expected_order_dict)

    def test_place_order_after_manual_cancel(self):
        mock_calls: int = 0

        def get_open_orders_ws_mock():
            nonlocal mock_calls
            order = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228}
            # initially no orders placed
            if mock_calls == 0:
                result = []
            # then supervisor places the order
            elif mock_calls == 1:
                result = [order]
            # imitate manual order cancellation
            elif mock_calls == 2:
                result = []
            # supervisor places the order again
            else:
                result = [order]
            mock_calls += 1
            return result

        self.exchange_mock.get_open_orders_ws.side_effect = get_open_orders_ws_mock

        self.supervisor.add_limit_order(qty=1000, price=Decimal(228))
        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)

        # Assert that supervisor place the order exactly 2 times
        expected_order_dict = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228, 'execInst': ''}
        expected_calls = [call(order_dict=expected_order_dict)] * 2
        self.exchange_mock.place_order.assert_has_calls(expected_calls)

    def test_place_two_same_limit_orders(self):
        mock_calls: int = 0

        def get_open_orders_ws_mock():
            nonlocal mock_calls
            order = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228}
            if mock_calls == 0:
                result = []
            elif mock_calls == 1:
                result = [order]
            else:
                result = [order, order]
            mock_calls += 1
            return result

        self.exchange_mock.get_open_orders_ws.side_effect = get_open_orders_ws_mock

        self.supervisor.add_limit_order(qty=1000, price=Decimal(228))
        self.supervisor.add_limit_order(qty=1000, price=Decimal(228))
        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)

        # Assert that supervisor only place the one order
        expected_order_dict = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228, 'execInst': ''}
        expected_calls = [call(orders=[expected_order_dict, expected_order_dict])]
        self.exchange_mock.bulk_place_orders.assert_has_calls(expected_calls)


class OrderCallbacksTests(unittest.TestCase):
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

    def test_callback_will_be_called(self):
        mock_calls: int = 0

        def get_open_orders_ws_mock():
            nonlocal mock_calls
            order = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228, 'orderID': 123}
            if mock_calls == 0:
                result = []
            else:
                result = [order]
            mock_calls += 1
            return result

        self.exchange_mock.get_open_orders_ws.side_effect = get_open_orders_ws_mock
        self.exchange_mock.get_filled_orders_ws.return_value = []

        callback_mock = Mock()
        new_order = self.supervisor.add_limit_order(qty=1000, price=Decimal(228), callback=callback_mock)
        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)
        self.supervisor.stop_cycle()
        self.exchange_mock.get_open_orders_ws.retutn_value = []
        self.exchange_mock.get_filled_orders_ws.return_value = [new_order]

        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)

        # assert that get_filled_orders_ws was called
        self.exchange_mock.get_filled_orders_ws.assert_called()
        # assert that supervisor won`t try to place the order after it became filled
        self.exchange_mock.place_order.assert_called_once()
        # assert that callback was called
        callback_mock.assert_called_once()

    def test_two_filled_orders_together(self):
        mock_calls: int = 0

        def get_open_orders_ws_mock():
            nonlocal mock_calls
            order_1 = {'ordType': 'Limit', 'orderQty': 1000, 'price': 228, 'orderID': 123}
            order_2 = {'ordType': 'Limit', 'orderQty': 1001, 'price': 229, 'orderID': 124}
            if mock_calls == 0:
                result = []
            else:
                result = [order_1, order_2]
            mock_calls += 1
            return result

        self.exchange_mock.get_open_orders_ws.side_effect = get_open_orders_ws_mock
        self.exchange_mock.get_filled_orders_ws.return_value = []

        callback_mock_1 = Mock()
        callback_mock_2 = Mock()
        new_order_1 = self.supervisor.add_limit_order(qty=1000, price=Decimal(228), callback=callback_mock_1)
        new_order_2 = self.supervisor.add_limit_order(qty=1001, price=Decimal(229), callback=callback_mock_2)
        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)
        self.supervisor.stop_cycle()
        self.exchange_mock.get_open_orders_ws.retutn_value = []
        self.exchange_mock.get_filled_orders_ws.return_value = [new_order_1, new_order_2]

        self.supervisor.run_cycle()

        # Sleep for let the supervisor make multiple checks and order place tries
        time.sleep(0.5)

        # assert that get_filled_orders_ws was called
        self.exchange_mock.get_filled_orders_ws.assert_called()
        # assert that supervisor won`t try to place the order after it became filled
        self.exchange_mock.place_order.assert_not_called()
        self.exchange_mock.bulk_place_orders.assert_called_once()
        # assert that callbacks were called
        callback_mock_1.assert_called_once()
        callback_mock_2.assert_called_once()
