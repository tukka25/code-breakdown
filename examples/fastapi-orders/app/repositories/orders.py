from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import OrderLineRow, OrderRow, OrderStatus
from app.schemas import LineIn


def insert_order(
    db: Session, user_id: int, lines: list[LineIn], total: Decimal
) -> OrderRow:
    order = OrderRow(user_id=user_id, total=total, status=OrderStatus.PENDING)
    order.lines = [
        OrderLineRow(product_id=line.product_id, quantity=line.quantity)
        for line in lines
    ]
    db.add(order)
    db.flush()
    return order
