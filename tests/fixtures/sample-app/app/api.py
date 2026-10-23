from app.models import Order, make_order
from . import models


class Handler(models.Base):
    def get(self):
        return make_order(1, 2.0).total()


def serve():
    return Handler()
