from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.errors import OutOfStock, UnknownProduct
from app.models import User
from app.schemas import CreateOrderIn, OrderOut
from app.services.orders import place_order

router = APIRouter()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(
    body: CreateOrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> OrderOut:
    try:
        order = place_order(db, user.id, body)
    except UnknownProduct as exc:
        raise HTTPException(404, detail=str(exc))
    except OutOfStock as exc:
        raise HTTPException(409, detail=str(exc))
    return OrderOut.model_validate(order)
