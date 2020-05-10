from time import sleep
from threading import Thread, Event
from requests.exceptions import HTTPError

from supervisor.core.orders import Order
from supervisor.core.utils.log import setup_supervisor_logger


class Supervisor:
    """Class with high-level trading features."""

    def __init__(self, *, interface):
        self.exchange = interface

        self.manage_orders = True
        self.manage_position = True

        self.logger = setup_supervisor_logger('supervisor')

        self.position_size = 0
        self._orders = []

        self.sync_thread = Thread(target=self._synchronization_cycle)
        # signal for terminate thread
        self._exit_sync_thread = Event()
        # when event is set, cycle is running
        self._run_thread = Event()
        # stop thread confirmation
        self._stopped = Event()

    ###########################
    # Synchronization methods #
    ###########################

    def _synchronization_cycle(self):
        while True:
            if not self.exchange.is_open():
                self.logger.warning('Websocket connection unexpectly closed, restarting...')
                self.exchange.reinit_ws()
                continue
            if self._exit_sync_thread.is_set():
                break
            if self._run_thread.is_set():
                # Synchronize all here
                if self.manage_orders:
                    self.sync_orders()
                if self.manage_position:
                    self.sync_position()
            else:
                self._stopped.set()
                self._run_thread.wait()
            sleep(0.1)

    def sync_position(self):
        pos_size = self.exchange.get_position_size_ws()
        if pos_size != self.position_size:
            self.entry(method='Market', qty=self.position_size - pos_size)
            self.logger.info(f'Enter position on {self.position_size - pos_size}.')

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
        for order in self._orders:
            if order.order_id is None:
                orders_to_place.append(order)
            else:
                status = self.exchange.get_order_status_ws(order)
                if status in ['Filled', 'Triggered']:
                    self._orders.remove(order)
                    if order.side == 'Buy':
                        self.position_size -= order.qty
                    else:
                        self.position_size += order.qty
                    self.logger.info(f'Order filled: {order.order_id} {order.order_type} {order.side} {order.qty} by '
                                     f'{order.price or order.stop_px}')
                    order.on_fill()
                elif status == 'Canceled':
                    orders_to_place.append(order)
                    self.logger.info(f'Order cancelled, trying to place it: '
                                     f'{order.order_type} {order.side} {order.qty} by {order.price or order.stop_px}')
                    order.on_cancel()
                elif status == 'Rejected':
                    self._orders.remove(order)
                    self.logger.info(f'Order rejected: {order.order_id} {order.order_type} '
                                     f'{order.side} {order.qty} by {order.price or order.stop_px}')
                    order.on_reject()
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
                self._orders.remove(order)
                self.logger.warning(f'Order price is above the liquidation price of current position: '
                                    f'{order.order_type} {order.side} {order.qty} by {order.price or order.stop_px}')

    def cancel_needless_orders(self):
        real_orders = self.exchange.get_open_orders_ws()
        orders_to_cancel = []
        for o in real_orders:
            if o not in self._orders:
                orders_to_cancel.append(o)
        if len(orders_to_cancel) > 0:
            self.exchange.bulk_cancel_orders(orders_to_cancel)
            self.logger.info(f'Cancel {len(orders_to_cancel)} needless orders.')

    ############
    # Position #
    ############

    def entry(self, method: str, qty: int) -> None:
        if method == 'Market':
            self._entry_by_market_order(qty)

    def _entry_by_market_order(self, qty: int) -> None:
        self.exchange.place_market_order(qty=qty)

    ##########
    # Orders #
    ##########

    def add_order(self, order: Order) -> None:
        if order.is_valid():
            self._orders.append(order)
            self.logger.info(f'New order: {order.order_type} {order.side} {order.qty} by '
                             f'{order.price or order.stop_px}')
        else:
            raise ValueError('Order is not valid.')

    def remove_order(self, order: Order):
        if order in self._orders:
            self._orders.remove(order)
            self.logger.info(f'Forget the order: {order.order_type} {order.side} {order.qty} by '
                             f'{order.price or order.stop_px}')

    def move_order(self, order: Order, to: int):
        if order in self._orders:
            order.move(to=to)

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
        self.stop_cycle()
        self.position_size = 0
        self._orders = []
