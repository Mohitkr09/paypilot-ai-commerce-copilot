from typing import Optional

from sqlalchemy.orm import Session

from app.models.product import Product


class RecommendationService:
    """
    PayPilot AI Growth Recommendation Engine.

    Responsibilities:
    - Upsell recommendations
    - Cross-sell recommendations

    Important:
    - Never creates an order
    - Never changes inventory
    - Never creates payment
    - Never applies a discount
    - Only recommends verified products
    - Only recommends active/in-stock products
    - Recommendations are bounded
    - Money actions require user confirmation
    """

    # =========================================================
    # SAFETY / BOUNDARY LIMITS
    # =========================================================

    MAX_RECOMMENDATIONS = 3

    # Maximum price of an upsell compared with base product.
    #
    # Example:
    #
    # Laptop = ₹60,000
    # Maximum upsell = ₹60,000 × 1.50
    #                = ₹90,000
    #
    # Premium Laptop = ₹85,000
    #
    # Therefore Premium Laptop qualifies.
    #
    MAX_UPSELL_PRICE_MULTIPLIER = 1.50

    # =========================================================
    # PRODUCT SERIALIZATION
    # =========================================================

    @staticmethod
    def product_to_dict(
        product: Product,
    ) -> dict:

        price = float(
            product.price or 0
        )

        cost_price = float(
            getattr(
                product,
                "cost_price",
                0,
            )
            or 0
        )

        if price > 0:

            margin_percent = round(
                (
                    (price - cost_price)
                    / price
                )
                * 100,
                2,
            )

        else:

            margin_percent = 0.0

        stock = int(
            getattr(
                product,
                "stock_quantity",
                0,
            )
            or 0
        )

        return {
            "product_id": product.id,

            "name": str(
                product.name
            ),

            "category": str(
                getattr(
                    product,
                    "category",
                    "",
                )
                or ""
            ),

            "description": str(
                getattr(
                    product,
                    "description",
                    "",
                )
                or ""
            ),

            "price": price,

            "cost_price": cost_price,

            "margin_percent": (
                margin_percent
            ),

            "stock_quantity": stock,

            "is_active": bool(
                getattr(
                    product,
                    "is_active",
                    True,
                )
            ),
        }

    # =========================================================
    # PRODUCT IS BUYABLE
    # =========================================================

    @staticmethod
    def is_buyable(
        product: Product,
    ) -> bool:

        is_active = bool(
            getattr(
                product,
                "is_active",
                True,
            )
        )

        stock = int(
            getattr(
                product,
                "stock_quantity",
                0,
            )
            or 0
        )

        return (
            is_active
            and stock > 0
        )

    # =========================================================
    # PRODUCT TEXT
    # =========================================================

    @staticmethod
    def product_text(
        product: Product,
    ) -> str:

        return " ".join(
            [
                str(
                    getattr(
                        product,
                        "name",
                        "",
                    )
                    or ""
                ),

                str(
                    getattr(
                        product,
                        "category",
                        "",
                    )
                    or ""
                ),

                str(
                    getattr(
                        product,
                        "description",
                        "",
                    )
                    or ""
                ),
            ]
        ).lower()

    # =========================================================
    # UPSELL
    # =========================================================

    @classmethod
    def find_upsell(
        cls,
        products: list[Product],
        base_product: Product,
    ) -> Optional[dict]:

        base_price = float(
            base_product.price or 0
        )

        if base_price <= 0:
            return None

        base_category = str(
            getattr(
                base_product,
                "category",
                "",
            )
            or ""
        ).lower()

        candidates = []

        # -----------------------------------------------------
        # BOUNDED PRICE LIMIT
        # -----------------------------------------------------

        max_price = (
            base_price
            * cls.MAX_UPSELL_PRICE_MULTIPLIER
        )

        # -----------------------------------------------------
        # FIND VALID UPSELL CANDIDATES
        # -----------------------------------------------------

        for product in products:

            # Never recommend the same product
            if product.id == base_product.id:
                continue

            # Only active + in-stock products
            if not cls.is_buyable(product):
                continue

            price = float(
                product.price or 0
            )

            # Upsell must actually cost more
            if price <= base_price:
                continue

            # Enforce bounded price increase
            if price > max_price:
                continue

            category = str(
                getattr(
                    product,
                    "category",
                    "",
                )
                or ""
            ).lower()

            # -------------------------------------------------
            # SAME CATEGORY MATCH
            # -------------------------------------------------

            category_match = (
                base_category
                and category
                and (
                    base_category == category
                    or base_category in category
                    or category in base_category
                )
            )

            if not category_match:
                continue

            candidates.append(
                product
            )

        # -----------------------------------------------------
        # NO UPSELL FOUND
        # -----------------------------------------------------

        if not candidates:
            return None

        # -----------------------------------------------------
        # SELECT CLOSEST HIGHER-PRICED PRODUCT
        # -----------------------------------------------------

        candidates.sort(
            key=lambda product: float(
                product.price or 0
            )
        )

        product = candidates[0]

        price = float(
            product.price or 0
        )

        # -----------------------------------------------------
        # RETURN UPSELL
        # -----------------------------------------------------

        return {
            **cls.product_to_dict(
                product
            ),

            "recommendation_type": (
                "UPSELL"
            ),

            "reason": (
                f"{product.name} is a "
                f"higher-value option in "
                f"the same category. It "
                f"costs ₹{price:,.2f}, "
                f"compared with "
                f"₹{base_price:,.2f} for "
                f"your selected "
                f"{base_product.name}."
            ),
        }

    # =========================================================
    # CROSS-SELL CATEGORY MAP
    # =========================================================

    COMPLEMENTARY_KEYWORDS = {

        "laptop": [
            "bag",
            "mouse",
            "keyboard",
            "stand",
            "charger",
            "sleeve",
            "accessory",
        ],

        "computer": [
            "mouse",
            "keyboard",
            "monitor",
            "stand",
            "speaker",
        ],

        "mobile": [
            "case",
            "cover",
            "charger",
            "earphone",
            "headphone",
            "power bank",
        ],

        "phone": [
            "case",
            "cover",
            "charger",
            "earphone",
            "headphone",
            "power bank",
        ],

        "camera": [
            "bag",
            "tripod",
            "memory",
            "battery",
            "lens",
        ],

        "television": [
            "soundbar",
            "speaker",
            "stand",
            "remote",
        ],

        "tv": [
            "soundbar",
            "speaker",
            "stand",
        ],

        "gaming": [
            "mouse",
            "keyboard",
            "headset",
            "controller",
            "pad",
        ],
    }

    # =========================================================
    # CROSS-SELL
    # =========================================================

    @classmethod
    def find_cross_sells(
        cls,
        products: list[Product],
        base_product: Product,
    ) -> list[dict]:

        base_text = cls.product_text(
            base_product
        )

        base_price = float(
            base_product.price or 0
        )

        # -----------------------------------------------------
        # DETERMINE COMPLEMENTARY KEYWORDS
        # -----------------------------------------------------

        matched_keywords = set()

        for (
            key,
            keywords,
        ) in cls.COMPLEMENTARY_KEYWORDS.items():

            if key in base_text:

                matched_keywords.update(
                    keywords
                )

        # -----------------------------------------------------
        # GENERIC ELECTRONICS FALLBACK
        # -----------------------------------------------------

        if not matched_keywords:

            category = str(
                getattr(
                    base_product,
                    "category",
                    "",
                )
                or ""
            ).lower()

            if "electronic" in category:

                matched_keywords.update(
                    [
                        "accessory",
                        "mouse",
                        "keyboard",
                        "charger",
                        "bag",
                        "case",
                    ]
                )

        candidates = []

        # -----------------------------------------------------
        # FIND CROSS-SELL CANDIDATES
        # -----------------------------------------------------

        for product in products:

            # Never recommend the base product
            if product.id == base_product.id:
                continue

            # Only active + in-stock products
            if not cls.is_buyable(product):
                continue

            product_text = (
                cls.product_text(
                    product
                )
            )

            matches = [
                keyword
                for keyword
                in matched_keywords
                if keyword in product_text
            ]

            # No complementary match
            if not matches:
                continue

            price = float(
                product.price or 0
            )

            # -------------------------------------------------
            # CROSS-SELL PRICE BOUND
            #
            # Cross-sell should remain relatively affordable
            # compared with the main product.
            # -------------------------------------------------

            if base_price > 0:

                if (
                    price
                    > base_price * 0.50
                ):
                    continue

            score = len(
                matches
            )

            candidates.append(
                (
                    score,
                    price,
                    product,
                    matches,
                )
            )

        # -----------------------------------------------------
        # SORT BY RELEVANCE
        # -----------------------------------------------------

        candidates.sort(
            key=lambda item: (
                -item[0],
                item[1],
            )
        )

        recommendations = []

        # -----------------------------------------------------
        # MAX 3 CROSS-SELL PRODUCTS
        # -----------------------------------------------------

        for (
            score,
            price,
            product,
            matches,
        ) in candidates[
            : cls.MAX_RECOMMENDATIONS
        ]:

            matched_text = ", ".join(
                matches[:3]
            )

            recommendations.append(
                {
                    **cls.product_to_dict(
                        product
                    ),

                    "recommendation_type": (
                        "CROSS_SELL"
                    ),

                    "reason": (
                        f"{product.name} pairs "
                        f"well with "
                        f"{base_product.name}. "
                        f"It matches "
                        f"complementary "
                        f"product needs such "
                        f"as "
                        f"{matched_text}."
                    ),
                }
            )

        return recommendations

    # =========================================================
    # MAIN RECOMMENDATION METHOD
    # =========================================================

    @classmethod
    def recommend(
        cls,
        db: Session,
        merchant_id: int,
        product_id: int,
    ) -> dict:

        # =====================================================
        # 1. FIND BASE PRODUCT
        # =====================================================

        base_product = (
            db.query(Product)
            .filter(
                Product.id == product_id,
                Product.merchant_id == merchant_id,
            )
            .first()
        )

        # =====================================================
        # 2. PRODUCT NOT FOUND
        # =====================================================

        if not base_product:

            return {
                "success": False,

                "message": (
                    "The selected product was "
                    "not found for this merchant."
                ),

                "base_product": None,

                "upsell": None,

                "cross_sells": [],
            }

        # =====================================================
        # 3. PRODUCT UNAVAILABLE
        # =====================================================

        if not cls.is_buyable(
            base_product
        ):

            return {
                "success": False,

                "message": (
                    f"{base_product.name} "
                    "is currently unavailable."
                ),

                "base_product": (
                    cls.product_to_dict(
                        base_product
                    )
                ),

                "upsell": None,

                "cross_sells": [],
            }

        # =====================================================
        # 4. LOAD MERCHANT PRODUCTS
        # =====================================================

        products = (
            db.query(Product)
            .filter(
                Product.merchant_id
                == merchant_id
            )
            .all()
        )

        # =====================================================
        # 5. GENERATE UPSELL
        # =====================================================

        upsell = cls.find_upsell(
            products,
            base_product,
        )

        # =====================================================
        # 6. GENERATE CROSS-SELL
        # =====================================================

        cross_sells = (
            cls.find_cross_sells(
                products,
                base_product,
            )
        )

        # =====================================================
        # 7. RETURN BOUNDED RECOMMENDATIONS
        # =====================================================

        return {

            "success": True,

            "message": (
                "AI growth recommendations "
                "generated successfully."
            ),

            "base_product": (
                cls.product_to_dict(
                    base_product
                )
            ),

            "upsell": upsell,

            "cross_sells": cross_sells,

            # -------------------------------------------------
            # SAFETY FLAGS
            # -------------------------------------------------

            "bounded": True,

            "money_action": False,

            "requires_user_confirmation": True,
        }