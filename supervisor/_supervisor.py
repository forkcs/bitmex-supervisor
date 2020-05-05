from decimal import Decimal
from threading import Thread, Event
from time import sleep
from typing import Callable

from supervisor.core.orders import Order


class Supervisor:
    """Class with high-level trading features."""

    def __init__(self, *, interface):
        self.exchange = interface

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
            if self._exit_sync_thread.is_set():
                break
            if self._run_thread.is_set():
                # Synchronize all here
                self.sync_orders()
            else:
                self._stopped.set()
                self._run_thread.wait()
            sleep(0.1)

    def sync_orders(self):
        for order in self._orders:
            if order.order_id is None:
                pass

    def sync_position(self):
        raise NotImplemented

    def check_orders_status(self):
        raise NotImplemented

    ##########
    # Orders #
    ##########

    def add_order(self, order: Order, callback: Callable = None) -> None:
        if order.is_valid():
            self._orders.append(order)
        # add callback to order dict
        if callback is not None:
            order.add_callback(callback)

    def remove_order(self, order: Order):
        self._orders.remove(order)

    def move_order(self, order: Order, to: Decimal):
        if order in self._orders:
            order.move(to=to)

    ###################
    # Control methods #
    ###################

    def run_cycle(self):
        # reset control event
        self._exit_sync_thread.clear()

        # start thread or continue the existing
        if self.sync_thread.is_alive():
            self._continue_cycle()
        else:
            self._run_thread.set()
            self.sync_thread.start()

    def stop_cycle(self):
        if self._run_thread.is_set():
            self._run_thread.clear()
            self._stopped.wait()

    def _continue_cycle(self):
        self._run_thread.set()
        self._stopped.clear()

    def exit_cycle(self):
        self._exit_sync_thread.set()
        # if cycle cannot reach exit_sync_thread check, release it
        if self._stopped:
            self._continue_cycle()
        # join if sync thread isn`t terminated yet
        try:
            self.sync_thread.join()
        except RuntimeError:
            pass

    def reset(self):
        self.stop_cycle()
        self.position_size = 0
        self._orders = []
