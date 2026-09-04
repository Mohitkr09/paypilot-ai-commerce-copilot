from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product


class PolicyService:

    @staticmethod
    def get_product_context(
        db: Session,
        product_id: int,
    ):
        product = (
            db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if not product:
            return None

        merchant = (
            db.query(Merchant)
            .filter(Merchant.id == product.merchant_id)
            .first()
        )

        if not merchant:
            return None

        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "cost_price": product.cost_price,
                "stock_quantity": product.stock_quantity,
                "sku": product.sku,
                "is_active": product.is_active,
            },
            "merchant_policy": {
                "merchant_id": merchant.id,
                "merchant_name": merchant.name,
                "maximum_discount_percent": (
                    merchant.maximum_discount_percent
                ),
                "minimum_margin": merchant.minimum_margin,
                "auto_payment_limit": merchant.auto_payment_limit,
                "bundle_allowed": merchant.bundle_allowed,
                "is_active": merchant.is_active,
            },
        }