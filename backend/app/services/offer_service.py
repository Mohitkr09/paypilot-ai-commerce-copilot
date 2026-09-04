from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product


class OfferService:

    @staticmethod
    def calculate_offer(
        db: Session,
        product_id: int,
        requested_discount_percent: float,
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

        price = product.price
        cost = product.cost_price

        minimum_margin = merchant.minimum_margin
        merchant_max_discount = merchant.maximum_discount_percent

        # Maximum selling price discount allowed by margin.
        #
        # margin = (selling_price - cost) / selling_price * 100
        #
        # Required selling price:
        # cost / (1 - minimum_margin / 100)

        required_price = cost / (
            1 - minimum_margin / 100
        )

        margin_based_discount = (
            (price - required_price) / price
        ) * 100

        safe_discount = min(
            merchant_max_discount,
            max(0, margin_based_discount),
        )

        approved_discount = min(
            requested_discount_percent,
            safe_discount,
        )

        final_price = price * (
            1 - approved_discount / 100
        )

        final_margin = (
            (final_price - cost) / final_price
        ) * 100

        return {
            "product_id": product.id,
            "product_name": product.name,

            "original_price": round(price, 2),
            "cost_price": round(cost, 2),

            "requested_discount_percent": round(
                requested_discount_percent,
                2,
            ),

            "merchant_max_discount_percent": round(
                merchant_max_discount,
                2,
            ),

            "minimum_margin_percent": round(
                minimum_margin,
                2,
            ),

            "maximum_safe_discount_percent": round(
                safe_discount,
                2,
            ),

            "approved_discount_percent": round(
                approved_discount,
                2,
            ),

            "final_price": round(
                final_price,
                2,
            ),

            "final_margin_percent": round(
                final_margin,
                2,
            ),

            "approved": (
                requested_discount_percent
                <= safe_discount
            ),
        }