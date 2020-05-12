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

    # you can disable managing position or orders by set to False needed properties
    # supervisor.manage_position = False
    # supervisor.manage_orders = False

    # create Order objects
    stop_loss = Order(order_type='Stop', stop_px=2000, qty=10, side='Sell')
    tp1 = Order(order_type='Limit', price=15000, qty=6, side='Sell', passive=True)
    tp2 = Order(order_type='Limit', price=20000, qty=4, side='Sell', hidden=True)

    trailing_stop = Order(order_type='Stop', stop_px=3000, qty=10, side='Sell')

    # attach some callbacks to stop-loss, note that events starts with "_"
    # DO NOT USE stop_cycle() method into callbacks!!! It causes the deadlock
    stop_loss._on_reject = lambda: print('Rejected')
    stop_loss._on_fill = lambda: print('We lost position(')
    stop_loss._on_cancel = lambda: print('Trading without stops is risking ;)')

    input('Enter to run cycle')
    supervisor.run_cycle()
    input('Enter to add orders to needed')
    supervisor.add_order(stop_loss)
    supervisor.add_order(tp1)
    supervisor.add_order(tp2)
    supervisor.add_trailing_order(trailing_stop, offset=10)  # order will trail on 10% distance from currenr price
    input('Enter to enter position')
    supervisor.stop_cycle()
    supervisor.enter_by_market_order(10)
    supervisor.run_cycle()
    input('Enter to exit cycle')
    supervisor.exit_cycle()
