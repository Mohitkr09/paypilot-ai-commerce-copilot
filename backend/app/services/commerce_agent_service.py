# =========================================================
# COMMERCE AGENT SERVICE
# =========================================================
#
# Responsibilities:
#
#   - Product serialization
#   - Product catalog access
#   - Product search
#   - Product recommendation
#   - Natural language product queries
#   - Budget extraction
#   - Category detection
#   - Gemini integration
#
# Database remains the source of truth for:
#
#   - Product
#   - Price
#   - Stock
#   - Availability
#
# Gemini is used only for conversational responses.
#
# =========================================================

from decimal import Decimal
from typing import Optional
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.gemini_service import GeminiService


class CommerceAgentService:

    # =========================================================
    # PRODUCT SERIALIZATION
    # =========================================================

    @staticmethod
    def product_to_dict(
        product: Product,
    ) -> dict:
        """
        Convert a Product SQLAlchemy object into a
        normalized AI-readable dictionary.

        The existing Product model remains the
        source of truth.
        """

        def get_value(
            *names,
            default=None,
        ):
            """
            Safely get the first existing, non-null
            attribute from the Product model.
            """

            for name in names:

                if hasattr(
                    product,
                    name,
                ):

                    value = getattr(
                        product,
                        name,
                    )

                    if value is not None:
                        return value

            return default

        # =====================================================
        # BASIC FIELDS
        # =====================================================

        product_id = get_value(
            "id",
            default=None,
        )

        name = get_value(
            "name",
            "product_name",
            "title",
            default="Unknown Product",
        )

        description = get_value(
            "description",
            "product_description",
            default="",
        )

        category = get_value(
            "category",
            "product_category",
            default="",
        )

        brand = get_value(
            "brand",
            "brand_name",
            default="",
        )

        sku = get_value(
            "sku",
            "product_code",
            default=None,
        )

        currency = get_value(
            "currency",
            default="INR",
        )

        # =====================================================
        # PRICE
        # =====================================================

        price = get_value(
            "price",
            "selling_price",
            "final_price",
            "amount",
            default=0,
        )

        try:

            price = float(
                Decimal(
                    str(price)
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            price = 0.0

        # =====================================================
        # STOCK
        # =====================================================

        stock = get_value(
            "stock",
            "stock_quantity",
            "quantity",
            "inventory",
            default=0,
        )

        try:

            stock = int(stock)

        except (
            ValueError,
            TypeError,
        ):

            stock = 0

        # =====================================================
        # AVAILABILITY
        # =====================================================

        available = stock > 0

        # -----------------------------------------------------
        # Explicit model availability
        # -----------------------------------------------------

        if hasattr(
            product,
            "is_available",
        ):

            model_available = getattr(
                product,
                "is_available",
            )

            if model_available is not None:

                available = bool(
                    model_available
                )

        elif hasattr(
            product,
            "available",
        ):

            model_available = getattr(
                product,
                "available",
            )

            if model_available is not None:

                available = bool(
                    model_available
                )

        # =====================================================
        # NORMALIZED RESULT
        # =====================================================

        return {
            "id": product_id,

            "name": str(
                name
            ),

            "description": str(
                description or ""
            ),

            "category": str(
                category or ""
            ),

            "brand": str(
                brand or ""
            ),

            "sku": sku,

            "price": price,

            "currency": str(
                currency or "INR"
            ),

            "stock": stock,

            "available": available,
        }

    # =========================================================
    # ACTIVE PRODUCT QUERY
    # =========================================================

    @staticmethod
    def _active_query(
        db: Session,
    ):
        """
        Return a SQLAlchemy query containing active products.

        Supports both:
            Product.is_active
            Product.active
        """

        query = db.query(
            Product
        )

        if hasattr(
            Product,
            "is_active",
        ):

            query = query.filter(
                Product.is_active == True
            )

        elif hasattr(
            Product,
            "active",
        ):

            query = query.filter(
                Product.active == True
            )

        return query

    # =========================================================
    # GET CATALOG
    # =========================================================

    @staticmethod
    def get_catalog(
        db: Session,
        limit: int = 50,
    ):
        """
        Return products from the active catalog.
        """

        limit = max(
            1,
            min(
                limit,
                100,
            ),
        )

        query = (
            CommerceAgentService
            ._active_query(db)
        )

        if hasattr(
            Product,
            "id",
        ):

            query = query.order_by(
                Product.id.asc()
            )

        return (
            query
            .limit(limit)
            .all()
        )

    # =========================================================
    # GET SINGLE PRODUCT
    # =========================================================

    @staticmethod
    def get_product(
        db: Session,
        product_id: int,
    ) -> Optional[Product]:
        """
        Get one active product by ID.
        """

        query = (
            CommerceAgentService
            ._active_query(db)
        )

        query = query.filter(
            Product.id == product_id
        )

        return query.first()

    # =========================================================
    # SEARCH PRODUCTS
    # =========================================================

    @staticmethod
    def search_products(
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10,
    ):
        """
        Search products using database filters.

        IMPORTANT:

        This method is a strict database search.

        For flexible natural-language recommendations
        such as:

            "laptop under 80000"

        use recommend_products().
        """

        limit = max(
            1,
            min(
                limit,
                100,
            ),
        )

        products_query = (
            CommerceAgentService
            ._active_query(db)
        )

        # =====================================================
        # TEXT SEARCH
        # =====================================================

        if query:

            search_text = (
                query
                .strip()
                .lower()
            )

            if search_text:

                pattern = (
                    f"%{search_text}%"
                )

                conditions = []

                for field in (
                    "name",
                    "description",
                    "category",
                    "brand",
                    "sku",
                ):

                    if hasattr(
                        Product,
                        field,
                    ):

                        conditions.append(
                            getattr(
                                Product,
                                field,
                            ).ilike(
                                pattern
                            )
                        )

                if conditions:

                    products_query = (
                        products_query
                        .filter(
                            or_(
                                *conditions
                            )
                        )
                    )

        # =====================================================
        # CATEGORY FILTER
        # =====================================================

        if category:

            category_text = (
                category
                .strip()
                .lower()
            )

            if category_text:

                category_conditions = []

                for field in (
                    "category",
                    "product_category",
                ):

                    if hasattr(
                        Product,
                        field,
                    ):

                        category_conditions.append(
                            getattr(
                                Product,
                                field,
                            ).ilike(
                                f"%{category_text}%"
                            )
                        )

                if category_conditions:

                    products_query = (
                        products_query
                        .filter(
                            or_(
                                *category_conditions
                            )
                        )
                    )

        # =====================================================
        # FIND PRICE COLUMN
        # =====================================================

        price_column = None

        for field in (
            "price",
            "selling_price",
            "final_price",
            "amount",
        ):

            if hasattr(
                Product,
                field,
            ):

                price_column = getattr(
                    Product,
                    field,
                )

                break

        # =====================================================
        # MIN PRICE
        # =====================================================

        if (
            price_column is not None
            and min_price is not None
        ):

            products_query = (
                products_query
                .filter(
                    price_column >= min_price
                )
            )

        # =====================================================
        # MAX PRICE
        # =====================================================

        if (
            price_column is not None
            and max_price is not None
        ):

            products_query = (
                products_query
                .filter(
                    price_column <= max_price
                )
            )

        # =====================================================
        # ORDER
        # =====================================================

        if hasattr(
            Product,
            "id",
        ):

            products_query = (
                products_query
                .order_by(
                    Product.id.asc()
                )
            )

        return (
            products_query
            .limit(limit)
            .all()
        )

    # =========================================================
    # BUILD CATALOG
    # =========================================================

    @staticmethod
    def build_catalog(
        products,
    ) -> list:
        """
        Convert SQLAlchemy Product objects into
        normalized dictionaries.
        """

        return [
            CommerceAgentService
            .product_to_dict(product)
            for product in products
        ]

    # =========================================================
    # BUILD CATALOG CONTEXT
    # =========================================================

    @staticmethod
    def build_catalog_context(
        products,
    ) -> str:
        """
        Build AI-readable context from SQLAlchemy
        product objects.
        """

        catalog = (
            CommerceAgentService
            .build_catalog(
                products
            )
        )

        return (
            CommerceAgentService
            .build_catalog_context_from_dict(
                catalog
            )
        )

    # =========================================================
    # BUILD CONTEXT FROM DICTIONARIES
    # =========================================================

    @staticmethod
    def build_catalog_context_from_dict(
        products: list,
    ) -> str:
        """
        Build verified catalog context for Gemini.
        """

        if not products:

            return (
                "No matching products are "
                "currently available."
            )

        lines = [
            "VERIFIED PAYPILOT PRODUCT RESULTS",
            "================================",
        ]

        for product in products:

            availability = (
                "Available"
                if product["available"]
                else "Out of stock"
            )

            lines.extend(
                [
                    (
                        f"Product ID: "
                        f"{product['id']}"
                    ),

                    (
                        f"Name: "
                        f"{product['name']}"
                    ),

                    (
                        f"Brand: "
                        f"{product['brand']}"
                    ),

                    (
                        f"Category: "
                        f"{product['category']}"
                    ),

                    (
                        f"Description: "
                        f"{product['description']}"
                    ),

                    (
                        f"Price: "
                        f"{product['currency']} "
                        f"{product['price']:.2f}"
                    ),

                    (
                        f"Stock: "
                        f"{product['stock']}"
                    ),

                    (
                        f"Availability: "
                        f"{availability}"
                    ),

                    (
                        f"SKU: "
                        f"{product['sku']}"
                    ),

                    "--------------------------------",
                ]
            )

        return "\n".join(
            lines
        )

    # =========================================================
    # TOKENIZE QUERY
    # =========================================================

    @staticmethod
    def _tokenize_query(
        query: Optional[str],
    ) -> list:
        """
        Convert natural language into useful search
        keywords.

        Example:

            "I need a laptop under 80000"

        becomes approximately:

            ["laptop"]
        """

        if not query:

            return []

        words = re.findall(
            r"[a-zA-Z0-9]+",
            query.lower(),
        )

        # -----------------------------------------------------
        # Generic conversational / budget words
        # -----------------------------------------------------

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "need",
            "needs",
            "want",
            "wants",
            "looking",
            "look",
            "find",
            "show",
            "give",
            "get",
            "me",
            "please",
            "can",
            "you",
            "could",
            "would",
            "like",
            "buy",
            "purchase",
            "search",
            "searching",
            "product",
            "products",

            "under",
            "below",
            "less",
            "than",
            "upto",
            "up",
            "to",
            "maximum",
            "max",
            "minimum",
            "min",

            "price",
            "budget",
            "around",
            "about",

            "inr",
            "rs",

            "is",
            "are",
            "am",
            "a",
            "an",
            "of",
            "on",
            "at",
            "from",
            "my",
        }

        keywords = []

        for word in words:

            if len(word) < 3:
                continue

            if word in stop_words:
                continue

            # Ignore pure numeric values.
            if word.isdigit():
                continue

            if word not in keywords:

                keywords.append(
                    word
                )

        return keywords

    # =========================================================
    # RECOMMEND PRODUCTS
    # =========================================================

    @staticmethod
    def recommend_products(
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 5,
    ) -> dict:
        """
        Flexible product recommendation.

        IMPORTANT:

        The detected AI category is NOT treated as an
        exact database category filter.

        Example:

            User:
                "I need a laptop under 80000"

            Database:
                name = "Test Laptop"
                category = "Electronics"

        The product is still considered because
        "laptop" appears in its name.

        Flow:

            Natural language
                    ↓
            Price filtering
                    ↓
            Keyword matching
                    ↓
            Product scoring
                    ↓
            Available products
                    ↓
            Recommendations
        """

        limit = max(
            1,
            min(
                limit,
                20,
            ),
        )

        # =====================================================
        # STEP 1
        # GET PRODUCTS USING PRICE ONLY
        # =====================================================
        #
        # We intentionally DO NOT pass category here.
        #
        # Why?
        #
        # Database category may be:
        #
        #     Electronics
        #
        # while user's category is:
        #
        #     laptop
        #
        # We want "Test Laptop" to still match.
        # =====================================================

        products = (
            CommerceAgentService
            .search_products(
                db=db,
                query=None,
                category=None,
                max_price=max_price,
                limit=100,
            )
        )

        catalog = (
            CommerceAgentService
            .build_catalog(
                products
            )
        )

        # =====================================================
        # STEP 2
        # BUILD SEARCH KEYWORDS
        # =====================================================

        keywords = (
            CommerceAgentService
            ._tokenize_query(
                query
            )
        )

        # =====================================================
        # STEP 3
        # ADD DETECTED CATEGORY
        # =====================================================

        if category:

            category_words = re.findall(
                r"[a-zA-Z0-9]+",
                category.lower(),
            )

            for word in category_words:

                if len(word) < 3:
                    continue

                if word not in keywords:

                    keywords.append(
                        word
                    )

        # =====================================================
        # STEP 4
        # SCORE PRODUCTS
        # =====================================================

        scored = []

        for product in catalog:

            # -------------------------------------------------
            # NEVER recommend unavailable products
            # -------------------------------------------------

            if not product["available"]:

                continue

            # -------------------------------------------------
            # HARD BUDGET FILTER
            # -------------------------------------------------

            if (
                max_price is not None
                and product["price"] > max_price
            ):

                continue

            # -------------------------------------------------
            # Product text
            # -------------------------------------------------

            name = str(
                product.get(
                    "name",
                    "",
                )
            ).lower()

            description = str(
                product.get(
                    "description",
                    "",
                )
            ).lower()

            product_category = str(
                product.get(
                    "category",
                    "",
                )
            ).lower()

            brand = str(
                product.get(
                    "brand",
                    "",
                )
            ).lower()

            sku = str(
                product.get(
                    "sku",
                    "",
                )
            ).lower()

            searchable_text = " ".join(
                [
                    name,
                    description,
                    product_category,
                    brand,
                    sku,
                ]
            )

            score = 0

            matched_keywords = 0

            # =================================================
            # KEYWORD MATCHING
            # =================================================

            for keyword in keywords:

                if keyword not in searchable_text:

                    continue

                matched_keywords += 1

                # -------------------------------------------------
                # Product name = strongest signal
                # -------------------------------------------------

                if keyword in name:

                    score += 40

                # -------------------------------------------------
                # Description = second strongest
                # -------------------------------------------------

                elif keyword in description:

                    score += 25

                # -------------------------------------------------
                # Category
                # -------------------------------------------------

                elif keyword in product_category:

                    score += 20

                # -------------------------------------------------
                # Brand / SKU
                # -------------------------------------------------

                else:

                    score += 10

            # =================================================
            # EXPLICIT CATEGORY MATCH
            # =================================================

            if category:

                category_text = (
                    category.lower()
                )

                if category_text in name:

                    score += 40

                elif category_text in description:

                    score += 30

                elif category_text in product_category:

                    score += 30

            # =================================================
            # BUDGET SCORE
            # =================================================

            if max_price is not None:

                if product["price"] <= max_price:

                    # Every product within budget receives
                    # a basic budget score.
                    score += 20

                    # Prefer products reasonably close
                    # to the requested budget.
                    if max_price > 0:

                        ratio = (
                            product["price"]
                            / max_price
                        )

                        budget_bonus = int(
                            max(
                                0,
                                10
                                - abs(
                                    0.75
                                    - ratio
                                ) * 10,
                            )
                        )

                        score += (
                            budget_bonus
                        )

            # =================================================
            # REQUIRE ACTUAL MATCH
            # =================================================
            #
            # If user gave a meaningful query, at least
            # one keyword must match the product.
            #
            # This prevents unrelated products such as:
            #
            #     Keyboard
            #     Mouse
            #     Monitor
            #
            # from being returned for:
            #
            #     laptop under 80000
            # =================================================

            if keywords:

                if matched_keywords == 0:

                    continue

            # =================================================
            # SAVE SCORE
            # =================================================

            scored.append(
                (
                    score,
                    product,
                )
            )

        # =====================================================
        # STEP 5
        # SORT
        # =====================================================

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1]["price"],
            )
        )

        # =====================================================
        # STEP 6
        # LIMIT
        # =====================================================

        recommendations = [
            product
            for _, product
            in scored[:limit]
        ]

        # =====================================================
        # RESPONSE
        # =====================================================

        return {
            "recommendations": recommendations,

            "count": len(
                recommendations
            ),

            "message": (
                "Products found"
                if recommendations
                else "No matching products found"
            ),
        }

    # =========================================================
    # PROCESS NATURAL LANGUAGE QUERY
    # =========================================================

    @staticmethod
    def process_query(
        db: Session,
        user_message: str,
        limit: int = 10,
    ) -> dict:
        """
        Main AI Commerce workflow.

        Flow:

            Customer message
                    ↓
            Extract budget
                    ↓
            Detect category
                    ↓
            Flexible recommendation
                    ↓
            Verified products
                    ↓
            Gemini
                    ↓
            Conversational response
        """

        # =====================================================
        # CLEAN MESSAGE
        # =====================================================

        message = (
            user_message
            .strip()
        )

        # =====================================================
        # EMPTY MESSAGE
        # =====================================================

        if not message:

            return {
                "intent": "product_search",

                "message": (
                    "Please tell me what "
                    "product you are looking for."
                ),

                "query": "",

                "category": None,

                "max_price": None,

                "products": [],

                "count": 0,
            }

        # =====================================================
        # LIMIT
        # =====================================================

        limit = max(
            1,
            min(
                limit,
                20,
            ),
        )

        # =====================================================
        # EXTRACT BUDGET
        # =====================================================

        max_price = (
            CommerceAgentService
            .extract_max_price(
                message
            )
        )

        # =====================================================
        # DETECT CATEGORY
        # =====================================================

        category = (
            CommerceAgentService
            .detect_category(
                message
            )
        )

        # =====================================================
        # RECOMMEND PRODUCTS
        # =====================================================

        result = (
            CommerceAgentService
            .recommend_products(
                db=db,
                query=message,
                category=category,
                max_price=max_price,
                limit=limit,
            )
        )

        products = result[
            "recommendations"
        ]

        # =====================================================
        # FALLBACK SEARCH
        # =====================================================
        #
        # Only used if recommendation scoring finds
        # nothing.
        #
        # IMPORTANT:
        #
        # Do NOT send category=category because that would
        # turn "laptop" into an exact database category.
        #
        # Example:
        #
        # laptop != Electronics
        #
        # =====================================================

        if not products:

            fallback_products = (
                CommerceAgentService
                .search_products(
                    db=db,
                    query=message,
                    category=None,
                    max_price=max_price,
                    limit=50,
                )
            )

            fallback_catalog = (
                CommerceAgentService
                .build_catalog(
                    fallback_products
                )
            )

            products = [
                product
                for product
                in fallback_catalog
                if product["available"]
            ][:limit]

        # =====================================================
        # BUILD VERIFIED GEMINI CONTEXT
        # =====================================================

        catalog_context = (
            CommerceAgentService
            .build_catalog_context_from_dict(
                products
            )
        )

        # =====================================================
        # ASK GEMINI
        # =====================================================

        try:

            ai_response = (
                GeminiService
                .generate_commerce_response(
                    user_message=message,
                    catalog_context=catalog_context,
                    products=products,
                    category=category,
                    max_price=max_price,
                )
            )

        except Exception as error:

            print(
                "GEMINI COMMERCE ERROR:",
                repr(error),
            )

            # =================================================
            # SAFE DETERMINISTIC FALLBACK
            # =================================================

            if products:

                if len(products) == 1:

                    product = products[0]

                    ai_response = (
                        "I found a matching product: "
                        f"{product['name']} for "
                        f"{product['currency']} "
                        f"{product['price']:,.2f}. "
                        "It is currently available."
                    )

                else:

                    ai_response = (
                        f"I found {len(products)} "
                        "products that may match "
                        "your requirements."
                    )

            else:

                ai_response = (
                    "I couldn't find a product "
                    "matching your requirements."
                )

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        return {
            "intent": "product_search",

            "message": ai_response,

            "query": message,

            "category": category,

            "max_price": max_price,

            "products": products,

            "count": len(products),
        }

    # =========================================================
    # EXTRACT MAX PRICE
    # =========================================================

    @staticmethod
    def extract_max_price(
        message: str,
    ) -> Optional[float]:
        """
        Extract customer's maximum budget.

        Examples:

            under 80000
            below 50000
            less than 70000
            upto 90000
            max 60000
            budget 80000
            price 50000
            ₹80000
            INR 80000
            Rs 80000
        """

        text = (
            message
            .lower()
            .replace(
                ",",
                "",
            )
            .replace(
                "₹",
                " ₹ ",
            )
        )

        patterns = [

            # -------------------------------------------------
            # under / below / less than / upto / max
            # -------------------------------------------------

            r"""
            (?:under|below|less\s+than|upto|up\s+to|
               maximum|max)
            \s*
            (?:₹|rs\.?|inr)?
            \s*
            (\d+(?:\.\d+)?)
            """,

            # -------------------------------------------------
            # budget / price
            # -------------------------------------------------

            r"""
            (?:budget|price)
            \s*
            (?:of|is|around|about)?
            \s*
            (?:₹|rs\.?|inr)?
            \s*
            (\d+(?:\.\d+)?)
            """,

            # -------------------------------------------------
            # currency amount
            # -------------------------------------------------

            r"""
            (?:₹|rs\.?|inr)
            \s*
            (\d+(?:\.\d+)?)
            """,
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
                | re.VERBOSE,
            )

            if not match:
                continue

            try:

                value = float(
                    match.group(1)
                )

                if value > 0:

                    return value

            except (
                ValueError,
                TypeError,
            ):

                continue

        return None

    # =========================================================
    # DETECT CATEGORY
    # =========================================================

    @staticmethod
    def detect_category(
        message: str,
    ) -> Optional[str]:
        """
        Detect the product category from natural language.

        This category is used by the recommendation scorer.

        It is NOT necessarily the same as the database
        category.
        """

        text = (
            message
            .lower()
        )

        category_keywords = {

            # -------------------------------------------------
            # LAPTOP
            # -------------------------------------------------

            "laptop": [
                "laptop",
                "notebook",
                "macbook",
            ],

            # -------------------------------------------------
            # MOBILE
            # -------------------------------------------------

            "mobile": [
                "phone",
                "mobile",
                "smartphone",
                "iphone",
            ],

            # -------------------------------------------------
            # TABLET
            # -------------------------------------------------

            "tablet": [
                "tablet",
                "ipad",
            ],

            # -------------------------------------------------
            # HEADPHONES
            # -------------------------------------------------

            "headphones": [
                "headphone",
                "headphones",
                "earphone",
                "earphones",
                "earbuds",
                "airpods",
            ],

            # -------------------------------------------------
            # TELEVISION
            # -------------------------------------------------

            "television": [
                "tv",
                "television",
                "smart tv",
            ],

            # -------------------------------------------------
            # MONITOR
            # -------------------------------------------------

            "monitor": [
                "monitor",
                "display",
                "screen",
            ],

            # -------------------------------------------------
            # KEYBOARD
            # -------------------------------------------------

            "keyboard": [
                "keyboard",
            ],

            # -------------------------------------------------
            # MOUSE
            # -------------------------------------------------

            "mouse": [
                "mouse",
                "gaming mouse",
            ],

            # -------------------------------------------------
            # CAMERA
            # -------------------------------------------------

            "camera": [
                "camera",
                "dslr",
                "mirrorless",
            ],

            # -------------------------------------------------
            # WATCH
            # -------------------------------------------------

            "watch": [
                "watch",
                "smartwatch",
                "smart watch",
            ],

            # -------------------------------------------------
            # SPEAKER
            # -------------------------------------------------

            "speaker": [
                "speaker",
                "bluetooth speaker",
            ],

            # -------------------------------------------------
            # PRINTER
            # -------------------------------------------------

            "printer": [
                "printer",
                "printing",
            ],
        }

        # =====================================================
        # CHECK CATEGORY KEYWORDS
        # =====================================================

        for category, keywords in (
            category_keywords.items()
        ):

            for keyword in keywords:

                if keyword in text:

                    return category

        return None