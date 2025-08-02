from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User
from ..schemas.user import UserCreate, UserRead
from db import get_db
from ..utils.hashing import hash_password

router = APIRouter()

@router.post("/users", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/users", response_model=list[UserRead])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
