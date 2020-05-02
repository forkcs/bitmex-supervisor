import json
import unittest
import responses

from supervisor.core import settings
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
        order1 = {'ordType': 'Limit', 'orderQty': 228, 'price': 1000}
        order2 = {'ordType': 'Limit', 'orderQty': 229, 'price': 1001}
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                settings.BASE_URL + '/order/bulk',
                json=[{}, {}]
            )
            self.exchange.bulk_place_orders(order1, order2)
            self.assertEqual(json.dumps({'orders': [order1, order2]}), rsps.calls[0].request.body)
