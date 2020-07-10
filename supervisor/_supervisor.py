from time import sleep
from threading import Thread, Event
from requests.exceptions import HTTPError

from supervisor.core.orders import Order
from supervisor.core.utils.math import to_nearest
from supervisor.core.trailing_orders import TrailingShell
from supervisor.core.utils.log import setup_supervisor_logger


class Supervisor:
    """Class with high-level trading features."""

    def __init__(self, *, interface):
        self.exchange = interface

        self.manage_orders = True
        self.manage_position = True

        self.logger = setup_supervisor_logger('supervisor')

        self.position_size = 0
        self.orders = []
        self._trackers = []

        self.sync_thread = Thread(target=self._synchronization_cycle)
        self._exit_sync_thread = Event()  # signal for terminate thread
        self._run_thread = Event()  # when event is set, cycle is running
        self._stopped = Event()  # stop thread confirmation

    ###########################
    # Synchronization methods #
    ###########################

    def _synchronization_cycle(self):
        while True:

            # keep ws connection open
            if not self.exchange.is_open():
                self.logger.warning('Websocket connection unexpectly closed, restarting...')
                self.exchange.reinit_ws()
                continue

            # if exit Event were sent, exiting cycle
            if self._exit_sync_thread.is_set():
                break

            # if all right, do the job)
            if self._run_thread.is_set():
                # Synchronize all here
                if self.manage_orders:
                    self.sync_orders()
                if self.manage_position:
                    self.sync_position()
            # if it`s not all right, enter the stopped condition
            else:
                self._stopped.set()
                self._run_thread.wait()
            sleep(0.1)

    def sync_position(self):
        pos_size = self.exchange.get_position_size_ws()
        if pos_size != self.position_size:
            self.correct_position_size(qty=self.position_size - pos_size)
            self.logger.info(f'Correct position size on {self.position_size - pos_size}.')

    def sync_orders(self):
        """ All the orders synchronization logic should be here."""

        # cancel orders at first, it`s important
        self.cancel_needless_orders()
        # dealing with orders from self._orders
        self.check_needed_orders()

    def check_needed_orders(self):
        """Check ever order from self._orders.

        If order has no order id, it`s considered as unplaced, so try to place them.
        If order has order id, but isn`t actually placed, there are 3 cases:
            - order is cancelled. Then we try to place it anew;
            - order is rejected. It`s useless to try placing it, so forget this order;
            - order is filled. We needn`t place it anymore, so just forget this order.
        """

        orders_to_place = []
        for order in self.orders:
            if order.order_id is None:
                orders_to_place.append(order)
            else:
                status = self.exchange.get_order_status_ws(order)
                if status in ['Filled', 'Triggered']:

                    if order.is_trailing:
                        order.tracker.exit()
                    self.orders.remove(order)

                    if order.side == 'Buy':
                        self.position_size += order.qty
                    else:
                        self.position_size -= order.qty
                    self.logger.info(f'Order filled: {order.order_id} {order.order_type} {order.side} {order.qty} by '
                                     f'{order.price or order.stop_px}')
                    order.on_fill()
                elif status == 'Canceled':
                    orders_to_place.append(order)
                    self.logger.info(f'Order cancelled, trying to place it: '
                                     f'{order.order_type} {order.side} {order.qty} by {order.price or order.stop_px}')
                elif status == 'Rejected':
                    self.orders.remove(order)
                    self.logger.info(f'Order rejected: {order.order_id} {order.order_type} '
                                     f'{order.side} {order.qty} by {order.price or order.stop_px}')
                    order.on_reject()
        self.place_needed_orders(orders_to_place)

    def place_needed_orders(self, orders_to_place: list):
        try:
            if len(orders_to_place) == 1:
                order = orders_to_place[0]
                self.exchange.place_order(order)
                self.logger.info(f'Place {order.order_type} order: '
                                 f'{order.side} {order.qty} by {order.price or order.stop_px}.')
            elif len(orders_to_place) > 1:
                self.exchange.bulk_place_orders(orders_to_place)
                for order in orders_to_place:
                    self.logger.info(f'Place {order.order_type} order: '
                                     f'{order.side} {order.qty} by {order.price or order.stop_px}.')
        except HTTPError as e:
            if 'Order price is above the liquidation price of current' in e.response.text:
                order = orders_to_place[0]
                self.orders.remove(order)
                self.logger.warning(f'Order price is above the liquidation price of current position: '
                                    f'{order.order_type} {order.side} {order.qty} by {order.price or order.stop_px}')

    def cancel_needless_orders(self):
        real_orders = self.exchange.get_open_orders_ws().copy()
        needed_orders = self.orders.copy()

        # difference of the lists with duplicates
        for _ in range(len(real_orders)):
            for o in real_orders:
                if o in needed_orders:
                    real_orders.remove(o)
                    needed_orders.remove(o)

        orders_to_cancel = real_orders

        for o_to_c in orders_to_cancel:
            for o in needed_orders:
                if o.almost_equal(o_to_c):
                    self.exchange.move_order(order=o)
                    orders_to_cancel.remove(o_to_c)
                    self.logger.info(f'Moved {o.order_type} order with {o.qty} quantity.')

        if len(orders_to_cancel) > 0:
            self.exchange.bulk_cancel_orders(orders_to_cancel)
            self.logger.info(f'Cancel {len(orders_to_cancel)} needless orders.')

    ############
    # Position #
    ############

    def correct_position_size(self, qty: int) -> None:
        self.exchange.place_market_order(qty=qty)

    def enter_by_market_order(self, qty: int) -> None:
        self.exchange.place_market_order(qty=qty)
        self.position_size += qty
        self.logger.info(f'Enter position by market order on {qty} contracts.')

    def enter_fb_method(self, qty: int, price_type: str, timeout: int, max_retry: int, deviation: int = None) -> None:
        """
        Fb method is placing n orders after timeout seconds, then entry market.

        :param qty: entry position size
        :param timeout: timeout before replacing the order
        :param price_type: may be last, first_ob, third_ob and deviant
        :param deviation: deviation from last price in percents
        :param max_retry: max order placing count
        """

        if price_type == 'first_ob':
            init_price = self.exchange.get_first_orderbook_price_ws(bid=qty > 0)
        elif price_type == 'third_ob':
            init_price = self.exchange.get_third_orderbook_price_ws(bid=qty > 0)
        elif price_type == 'deviant':
            if qty > 0:
                init_price = self.exchange.get_last_price_ws() * (100 + deviation) / 100
            else:
                init_price = self.exchange.get_last_price_ws() * (100 - deviation) / 100
        # if price_type is 'last'
        else:
            ticker = self.exchange.get_ticker_ws()
            if qty > 0:
                init_price = ticker['buy']
            else:
                init_price = ticker['sell']

        init_price = to_nearest(init_price, self.exchange.conn.get_tick_size())

        entry_order = Order(order_type='Limit', qty=qty, side='Buy' if qty > 0 else 'Sell',
                            price=init_price, passive=False)
        for _ in range(max_retry):
            self.exchange.place_order(entry_order)
            for _ in range(timeout):
                if self.exchange.get_order_status_ws(entry_order) == 'Filled':
                    return
                sleep(1)
            self.exchange.cancel_order(entry_order)
        self.enter_by_market_order(qty=qty)

    ##########
    # Orders #
    ##########

    def add_order(self, order: Order) -> None:
        if order.is_valid():
            self.orders.append(order)
            self.logger.info(f'New order: {order.order_type} {order.side} {order.qty} by '
                             f'{order.price or order.stop_px}')
        else:
            raise ValueError('Order is not valid.')

    def add_trailing_order(self, order: Order, offset: int) -> None:
        """

        :param order: Order instance
        :param offset: value in percents, distance from extremum
        """

        if order.is_valid():
            order.is_trailing = True
            tick_size = self.exchange.conn.get_tick_size()
            test = 'testnet' in self.exchange.conn.base_url
            order.tracker = TrailingShell(order=order, offset=offset, tick_size=tick_size, test=test)
            order.tracker.start_trailing(initial_price=self.exchange.get_last_price_ws())
            self.orders.append(order)

    def remove_order(self, order: Order):
        if order in self.orders:
            self.orders.remove(order)
            self.logger.info(f'Forget the order: {order.order_type} {order.side} {order.qty} by '
                             f'{order.price or order.stop_px}')

    ###################
    # Control methods #
    ###################

    def run_cycle(self):
        """Start thread or continue the existing."""

        if self.sync_thread.is_alive():
            self._continue_cycle()
        else:
            self._run_thread.set()
            self.sync_thread.start()
            self.logger.info(f'Started Supervisor thread.')

    def stop_cycle(self):
        if self._run_thread.is_set():
            self._run_thread.clear()
            self._stopped.wait()
            self.logger.info(f'Supervisor cycle has been stopped.')

    def _continue_cycle(self):
        self._run_thread.set()
        self._stopped.clear()
        self.logger.info(f'Supervisor cycle has been continued.')

    def exit_cycle(self):
        self._exit_sync_thread.set()
        # if cycle cannot reach exit_sync_thread check, release it
        if self._stopped:
            self._continue_cycle()

        # join if sync thread isn`t terminated yet
        if self.sync_thread.is_alive():
            self.sync_thread.join()
        self.logger.info(f'Exited from Supervisor.')

    def reset(self):
        self.position_size = 0
        self.orders = []
