from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProductRow


def load_products(db: Session, ids: list[int]) -> dict[int, ProductRow]:
    rows = db.scalars(
        select(ProductRow).where(ProductRow.id.in_(ids)).with_for_update()
    ).all()
    return {row.id: row for row in rows}
