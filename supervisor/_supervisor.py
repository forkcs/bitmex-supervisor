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
                self.check_filled_orders()
            else:
                self._stopped.set()
                self._run_thread.wait()
            sleep(0.1)

    def sync_orders(self):
        real_orders = self.exchange.get_open_orders_ws()
        self.cancel_needless_orders(real_orders)
        self.place_unplaced_orders(real_orders)

    def sync_position(self):
        raise NotImplementedError

    def check_filled_orders(self):
        filled_orders = [Order.from_dict(order_dict) for order_dict in self.exchange.get_filled_orders_ws()]
        for order in self._orders:
            if order in filled_orders:
                # don`t place this order again, forget it
                self._orders.remove(order)
                # exec callback
                callback = order.get('callback', None)
                if callback is not None:
                    callback()

    ##########
    # Orders #
    ##########

    def add_order(self, order: Order, callback: Callable = None) -> None:
        self._orders.append(order)
        # add callback to order dict
        if callback is not None:
            order.add_callback(callback)

    def remove_order(self, order: Order):
        self._orders.remove(order)

    def move_order(self, order: Order, to: Decimal):
        if order in self._orders:
            Order.move(to=to)

    def place_unplaced_orders(self, real_order_dicts: list):
        real_orders = [Order.from_dict(order_dict) for order_dict in real_order_dicts]
        orders_to_place = []
        for order in self._orders:
            if order not in real_orders:
                orders_to_place.append(order.as_dict())
        if orders_to_place:
            if len(orders_to_place) == 1:
                self.exchange.place_order(order_dict=orders_to_place[0])
            else:
                self.exchange.bulk_place_orders(orders_to_place)

    def cancel_needless_orders(self, real_order_dicts):
        real_orders = [Order.from_dict(order_dict) for order_dict in real_order_dicts]
        orders_to_cancel_ids = []
        for o in real_orders:
            if o not in self._orders:
                orders_to_cancel_ids.append(o.order_id)
        if orders_to_cancel_ids:
            self.exchange.bulk_cancel_orders(order_id_list=orders_to_cancel_ids)

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
