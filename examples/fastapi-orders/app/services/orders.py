from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import OutOfStock, UnknownProduct
from app.models import CouponRow, OrderRow, ProductRow
from app.repositories.orders import insert_order
from app.repositories.products import load_products
from app.schemas import CreateOrderIn, LineIn


def place_order(db: Session, user_id: int, body: CreateOrderIn) -> OrderRow:
    products = load_products(db, [line.product_id for line in body.lines])
    total = price_lines(body.lines, products)
    if body.coupon:
        total = apply_coupon(db, body.coupon, total)
    reserve_stock(products, body.lines)
    order = insert_order(db, user_id, body.lines, total)
    db.commit()
    return order


def price_lines(lines: list[LineIn], products: dict[int, ProductRow]) -> Decimal:
    total = Decimal("0")
    for line in lines:
        product = products.get(line.product_id)
        if product is None:
            raise UnknownProduct(line.product_id)
        total += product.price * line.quantity
    return total


def apply_coupon(db: Session, code: str, total: Decimal) -> Decimal:
    coupon = db.scalar(
        select(CouponRow).where(CouponRow.code == code, CouponRow.active)
    )
    if coupon is None:
        return total
    return max(total - coupon.amount_off, Decimal("0"))


def reserve_stock(products: dict[int, ProductRow], lines: list[LineIn]) -> None:
    for line in lines:
        product = products[line.product_id]
        if product.stock < line.quantity:
            raise OutOfStock(product.name)
        product.stock -= line.quantity
