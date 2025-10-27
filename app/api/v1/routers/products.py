# app/api/v1/routers/products.py
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.db.models import Product
from app.db.core import get_session

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/", response_model=list[Product])
def list_products(db: Session = Depends(get_session)):
    return db.exec(select(Product)).all()