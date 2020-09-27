import json
import unittest
import responses

from supervisor.core import settings
from supervisor.core.orders import Order
from supervisor.core.interface import Exchange


class InterfaceHttpMethodsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.exchange = Exchange(symbol=settings.TEST_SYMBOL, api_key=settings.TEST_API_KEY,
                                api_secret=settings.TEST_API_SECRET, test=False, connect_ws=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.exchange.exit()

    @responses.activate
    def test_get_position_size(self):
        responses.add(
            responses.GET,
            settings.BASE_URL + '/position',
            json=[{'currentQty': 228}]
        )
        pos_size = self.exchange.get_position_size()
        self.assertEqual(pos_size, 228)

    def test_get_average_position_entry_price(self):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                settings.BASE_URL + '/position',
                json=[{'avgEntryPrice': 228}]
            )
            avg_entry_price = self.exchange.get_average_position_entry_price()
            self.assertEqual(avg_entry_price, 228)

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                settings.BASE_URL + '/position',
                json=[{'avgEntryPrice': None}]
            )
            avg_entry_price = self.exchange.get_average_position_entry_price()
            self.assertEqual(avg_entry_price, 0)

    def test_get_leverage(self):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                settings.BASE_URL + '/position',
                json=[{'leverage': 13}]
            )
            leverage = self.exchange.get_leverage()
            self.assertEqual(leverage, 13)

    def test_bulk_place_orders(self):
        order1 = Order(order_type='Limit', price=1000, qty=228)
        order2 = Order(order_type='Limit', price=1001, qty=229)

        expected_orders = [
            {
                'symbol': settings.TEST_SYMBOL,
                'ordType': 'Limit',
                'orderQty': 228,
                'price': 1000.0,
            },
            {
                'symbol': settings.TEST_SYMBOL,
                'ordType': 'Limit',
                'orderQty': 229,
                'price': 1001.0,
            }

        ]
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                settings.BASE_URL + '/order/bulk',
                json=[{'orderID': 123}, {'orderID': 124}]
            )
            self.exchange.bulk_place_orders(orders=[order1, order2])
            self.assertEqual(json.dumps({'orders': expected_orders}), rsps.calls[0].request.body)

    def test_move_order(self):
        order1 = Order(order_type='Limit', price=1000, qty=228, side='Sell')
        order1.order_id = 1234

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.PUT,
                settings.BASE_URL + '/order',
                json={}
            )
            expected_order = {
                'orderID': 1234,
                'orderQty': 228,
                'price': 1001.0,
            }

            self.exchange.move_order(order1, to=1001)
            self.assertEqual(1, len(rsps.calls))
            self.assertEqual(json.dumps(expected_order), rsps.calls[0].request.body)
