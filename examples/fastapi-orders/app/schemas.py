from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


class LineIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class CreateOrderIn(BaseModel):
    lines: list[LineIn] = Field(min_length=1)
    coupon: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    total: Decimal
