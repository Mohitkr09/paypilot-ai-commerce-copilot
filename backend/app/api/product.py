from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.database import get_db
from app.models.product import Product

from app.routes.product import router as crud_router
from app.schemas.product import ProductResponse


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.get(
    "/search",
    response_model=list[ProductResponse],
)
def search_products(
    query: str | None = None,
    category: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_stock: int = Query(default=1, ge=0),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .filter(
            Product.is_active.is_(True),
            Product.stock_quantity >= min_stock,
        )
    )

    if query:
        search = f"%{query}%"

        products = products.filter(
            or_(
                Product.name.ilike(search),
                Product.description.ilike(search),
                Product.category.ilike(search),
                Product.sku.ilike(search),
            )
        )

    if category:
        products = products.filter(
            Product.category.ilike(f"%{category}%")
        )

    if min_price is not None:
        products = products.filter(
            Product.price >= min_price
        )

    if max_price is not None:
        products = products.filter(
            Product.price <= max_price
        )

    return products.limit(limit).all()