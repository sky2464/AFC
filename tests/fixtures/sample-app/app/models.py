import json
from dataclasses import dataclass


class Base:
    def to_json(self):
        return json.dumps(vars(self))


@dataclass
class Order(Base):
    qty: int
    price: float

    def total(self):
        return self.qty * self.price


def make_order(qty, price):
    return Order(qty, price)
