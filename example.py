from decimal import Decimal

from supervisor.core.interface import Exchange
from supervisor.core.orders import Order
from supervisor import Supervisor

TEST_API_KEY = 'your-api-key'
TEST_API_SECRET = 'your-api-secret'

if __name__ == '__main__':
    # Exchange is a interface-like class to call api methods
    exchange = Exchange(api_key=TEST_API_KEY, api_secret=TEST_API_SECRET,
                        test=True, symbol='XBTUSD')
    supervisor = Supervisor(interface=exchange)

    # create Order objects
    stop_loss = Order(order_type='Stop', stop_px=Decimal(2000), qty=10, side='Sell')
    tp1 = Order(order_type='Limit', price=Decimal(15000), qty=6, side='Sell', passive=True, reduce_only=True)
    tp2 = Order(order_type='Limit', price=Decimal(20000), qty=4, side='Sell', hidden=True)

    # set needed position price
    supervisor.position_size = 10

    # attach some callbacks to stop-loss, note that events starts with "_"
    stop_loss._on_reject = lambda: print('Rejected')
    stop_loss._on_fill = lambda: print('We lost position(')
    stop_loss._on_cancel = lambda: print('Trading without stops is risking ;)')

    input('Enter to run cycle')
    supervisor.run_cycle()
    input('Enter to add orders to needed')
    supervisor.add_order(stop_loss)
    supervisor.add_order(tp1)
    supervisor.add_order(tp2)
    input('Enter to exit cycle')
    supervisor.exit_cycle()
