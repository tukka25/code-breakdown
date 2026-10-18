from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User


def current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> User:
    # Example only: the bearer token is the user id.
    token = authorization.removeprefix("Bearer ").strip()
    user = db.get(User, int(token)) if token.isdigit() else None
    if user is None:
        raise HTTPException(401, detail="Unknown user")
    return user
