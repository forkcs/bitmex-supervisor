from typing import List, Dict
from uuid import uuid4


def make_order_dict(*, order_type=None, qty=None, price=None, stop_px=None, exec_inst=None, clordid=None) -> Dict:
    order_dict = {}
    if order_type is not None:
        order_dict['ordType'] = order_type
    if qty is not None:
        order_dict['orderQty'] = qty
    if price is not None:
        order_dict['price'] = price
    if stop_px is not None:
        order_dict['stopPx'] = stop_px
    if exec_inst is not None:
        order_dict['execInst'] = exec_inst
    if clordid is not None:
        order_dict['clOrdID'] = clordid
    return order_dict


def orders_are_equal(order1: Dict, order2: Dict) -> bool:
    if order1['orderQty'] != order2['orderQty']:
        return False
    if order1['ordType'] != order2['ordType']:
        return False
    if order1.get('price', None) != order2.get('price', None):
        return False
    if order1.get('stopPx', None) != order2.get('stopPx', None):
        return False
    return True


def order_in_order_list(order: Dict, order_list: List[Dict]) -> bool:
    for o in order_list:
        if orders_are_equal(o, order):
            return True
    else:
        return False


def remove_order_from_order_list(order: Dict, order_list: List[Dict]) -> None:
    """ Should be used after order_in_order_list check!"""

    order_to_remove = list(filter(lambda o: orders_are_equal(o, order), order_list))[0]
    order_list.remove(order_to_remove)


def _generate_clordid() -> str:
    return str(uuid4())


def set_clordid(order: dict) -> str:
    new_clordid = _generate_clordid()
    order['clOrdID'] = new_clordid
    return new_clordid
