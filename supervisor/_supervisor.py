from decimal import Decimal
from threading import Thread, Event
from time import sleep
from typing import Callable

from supervisor.core.utils.orders import make_order_dict, order_in_order_list, remove_order_from_order_list, \
    get_order_from_order_list


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
        filled_orders = self.exchange.get_filled_orders_ws()
        for order in self._orders:
            if order_in_order_list(order, filled_orders):
                # don`t place this order again, forget it
                remove_order_from_order_list(order, self._orders)
                # exec callback
                callback = order.get('callback', None)
                if callback is not None:
                    callback()

    ##########
    # Orders #
    ##########

    def add_limit_order(self, qty: int, price: Decimal, hidden=False, passive=False, reduce_only=False,
                        callback: Callable = None):
        exec_inst = []
        display_qty = None
        if hidden:
            display_qty = 0
        if passive:
            exec_inst.append('ParticipateDoNotInitiate')
        if reduce_only:
            exec_inst.append('Close')

        new_order = make_order_dict(order_type='Limit', qty=qty, price=price,
                                    exec_inst=','.join(exec_inst), display_qty=display_qty)
        self._orders.append(new_order)
        # add callback to order dict
        if callback is not None:
            new_order['callback'] = callback
        return new_order

    def add_stop_order(self, qty: int, stop_px: Decimal, reduce_only=False,
                       callback: Callable = None):
        exec_inst = ''
        if reduce_only:
            exec_inst = 'Close'
        new_order = make_order_dict(order_type='Stop', qty=qty, stop_px=stop_px, exec_inst=exec_inst)
        self._orders.append(new_order)
        # add callback to order dict
        if callback is not None:
            new_order['callback'] = callback
        return new_order

    def remove_order(self, order: dict):
        if order_in_order_list(order, self._orders):
            remove_order_from_order_list(order, self._orders)

    def move_order(self, order: dict, price: Decimal = None, stop_px: Decimal = None):
        if order_in_order_list(order, self._orders):
            order_to_move = get_order_from_order_list(order, self._orders)
        else:
            raise ValueError('Order not found.')
        if order_to_move['ordType'] == 'Limit':
            order_to_move['price'] = price
        elif order_to_move['ordType'] == 'Stop':
            order_to_move['stopPx'] = stop_px

    def place_unplaced_orders(self, real_orders):
        orders_to_place = []
        for o in self._orders:
            if not order_in_order_list(o, real_orders):
                orders_to_place.append(o)
        if orders_to_place:
            if len(orders_to_place) == 1:
                self.exchange.place_order(order_dict=orders_to_place[0])
            else:
                self.exchange.bulk_place_orders(orders=orders_to_place)

    def cancel_needless_orders(self, real_orders):
        orders_to_cancel_ids = []
        for o in real_orders:
            if not order_in_order_list(o, self._orders):
                orders_to_cancel_ids.append(o['orderID'])
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
