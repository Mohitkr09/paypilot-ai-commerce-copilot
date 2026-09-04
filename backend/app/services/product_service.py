from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.product import Product


class ProductService:

    @staticmethod
    def search_products(
        db: Session,
        query: str | None = None,
        category: str | None = None,
        max_price: float | None = None,
        min_price: float | None = None,
        min_stock: int = 1,
        limit: int = 10,
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

        if max_price is not None:
            products = products.filter(
                Product.price <= max_price
            )

        if min_price is not None:
            products = products.filter(
                Product.price >= min_price
            )

        return products.limit(limit).all()