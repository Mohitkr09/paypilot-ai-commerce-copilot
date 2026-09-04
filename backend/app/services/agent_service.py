import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.merchant import Merchant


class AgentService:

    # =========================================================
    # STOP WORDS
    # =========================================================

    STOP_WORDS = {
        "i",
        "want",
        "would",
        "like",
        "to",
        "the",
        "a",
        "an",
        "for",
        "me",
        "please",
        "can",
        "you",
        "give",
        "get",
        "buy",
        "order",
        "purchase",
        "checkout",
        "place",
        "my",
        "of",
        "with",
        "and",
        "or",
        "is",
        "are",
        "this",
        "that",
        "it",
        "product",
        "products",
        "item",
        "items",
        "unit",
        "units",
        "piece",
        "pieces",
    }

    # =========================================================
    # EXTRACT QUANTITY
    # =========================================================

    @staticmethod
    def extract_quantity(message: str) -> int:

        if not message:
            return 1

        message_text = str(message).strip().lower()

        # -----------------------------------------------------
        # WORD-NUMBER QUANTITIES
        # -----------------------------------------------------

        word_numbers = {
            "zero": 0,
            "one": 1,
            "a": 1,
            "an": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20,
        }

        word_quantity_patterns = [
            r"\b(?:buy|order|purchase|get)\s+"
            r"(one|a|an|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
            r"eighteen|nineteen|twenty)\b",

            r"\b(one|a|an|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
            r"eighteen|nineteen|twenty)\s+"
            r"(?:units?|pieces?|products?|items?)?\s*"
            r"(?:of\s+)?[a-zA-Z0-9]",

            r"\b(?:quantity|qty)\s*[:=]?\s*"
            r"(one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
            r"eighteen|nineteen|twenty)\b",
        ]

        for pattern in word_quantity_patterns:

            match = re.search(
                pattern,
                message_text,
                re.IGNORECASE,
            )

            if match:
                word = match.group(1).lower()
                quantity = word_numbers.get(word)

                if quantity is not None and quantity > 0:
                    return quantity

        # -----------------------------------------------------
        # NUMERIC QUANTITIES
        # -----------------------------------------------------

        patterns = [
            r"\bquantity\s*[:=]?\s*(\d+)",
            r"\bqty\s*[:=]?\s*(\d+)",
            r"\bbuy\s+(\d+)",
            r"\border\s+(\d+)",
            r"\bpurchase\s+(\d+)",
            r"\bget\s+(\d+)",
            r"\b(\d+)\s+(?:units?|pieces?)\b",
            r"\b(\d+)\s+(?:products?|items?)\b",
            r"\bfor\s+(\d+)\b",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                message_text,
                re.IGNORECASE,
            )

            if match:

                quantity = int(
                    match.group(1)
                )

                if quantity > 0:
                    return quantity

        return 1


    # =========================================================
    # EXTRACT DISCOUNT
    # =========================================================

    @staticmethod
    def extract_discount(
        message: str,
    ) -> float:

        if not message:
            return 0.0

        patterns = [

            # 10% discount
            r"(\d+(?:\.\d+)?)\s*%\s*(?:discount|off)?",

            # discount 10
            r"\bdiscount\s*[:=]?\s*(?:of\s*)?(\d+(?:\.\d+)?)",

            # discount of 10%
            r"\bdiscount\s+of\s+(\d+(?:\.\d+)?)",

            # 10 percent discount
            r"(\d+(?:\.\d+)?)\s*percent\s*(?:discount|off)?",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                message,
                re.IGNORECASE,
            )

            if match:

                discount = float(
                    match.group(1)
                )

                if discount < 0:
                    return 0.0

                return discount

        return 0.0

    # =========================================================
    # TOKENIZE MESSAGE
    # =========================================================

    @staticmethod
    def tokenize(message: str):

        if not message:
            return []

        words = re.findall(
            r"[a-zA-Z0-9]+",
            message.lower(),
        )

        tokens = []

        for word in words:

            if word in AgentService.STOP_WORDS:
                continue

            if word.isdigit():
                continue

            if len(word) < 2:
                continue

            tokens.append(word)

        return tokens

    # =========================================================
    # NORMALIZE TEXT
    # =========================================================

    @staticmethod
    def normalize_text(value: Optional[str]) -> str:

        if not value:
            return ""

        value = str(value).lower()

        value = re.sub(
            r"[^a-zA-Z0-9\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    # =========================================================
    # PRODUCT TOKEN MATCH SCORE
    # =========================================================

    @staticmethod
    def product_match_score(
        product: Product,
        message: str,
    ) -> int:

        message_normalized = (
            AgentService.normalize_text(
                message
            )
        )

        message_tokens = set(
            AgentService.tokenize(message)
        )

        if not message_tokens:
            return 0

        score = 0

        product_name = (
            AgentService.normalize_text(
                product.name
            )
        )

        product_name_tokens = set(
            AgentService.tokenize(
                product.name or ""
            )
        )

        if not product_name:
            return 0

        # Strong exact phrase match.
        if product_name in message_normalized:
            score += 1000
            score += len(product_name_tokens) * 100
            score += len(product_name.split()) * 25

        # Product-name token matching.
        if product_name_tokens:

            matched_name_tokens = (
                product_name_tokens
                & message_tokens
            )

            matched_count = len(
                matched_name_tokens
            )

            score += matched_count * 40

            if matched_count == len(
                product_name_tokens
            ):
                score += 150

        # SKU matching.
        sku = (
            AgentService.normalize_text(
                getattr(product, "sku", "")
            )
        )

        if sku and sku in message_normalized:
            score += 900

        # Category matching.
        category = (
            AgentService.normalize_text(
                getattr(product, "category", "")
            )
        )

        category_tokens = set(
            AgentService.tokenize(
                getattr(product, "category", "")
                or ""
            )
        )

        if category and category in message_normalized:
            score += 120

        if category_tokens:

            matched_category_tokens = (
                category_tokens
                & message_tokens
            )

            score += (
                len(matched_category_tokens) * 15
            )

        return score


    # =========================================================
    # FIND PRODUCT
    # =========================================================
    #
    # Matching priority:
    #
    # 1. Exact product name
    # 2. SKU
    # 3. Category
    # 4. Product keywords
    #
    # Example:
    #
    # "I want 1 gaming laptop"
    #
    # can match:
    #
    # "Gaming Laptop"
    #
    # even when the user does not type the exact
    # database product name.
    #
    # =========================================================

    @staticmethod
    def find_product(
        db: Session,
        merchant_id: int,
        message: str,
    ):

        products = (
            db.query(Product)
            .filter(
                Product.merchant_id
                == merchant_id,
                Product.is_active == True,
            )
            .all()
        )

        if not products:
            return None

        message_normalized = (
            AgentService.normalize_text(
                message
            )
        )

        if not message_normalized:
            return None

        # -----------------------------------------------------
        # 1. EXACT PRODUCT NAME
        #
        # Longest/more specific product name wins.
        #
        # "Premium Laptop" is checked before "Laptop".
        # -----------------------------------------------------

        exact_name_matches = []

        for product in products:

            product_name = (
                AgentService.normalize_text(
                    product.name
                )
            )

            if not product_name:
                continue

            if re.search(
                r"(?<![a-z0-9])"
                + re.escape(product_name)
                + r"(?![a-z0-9])",
                message_normalized,
            ):
                exact_name_matches.append(
                    (
                        len(product_name.split()),
                        len(product_name),
                        product,
                    )
                )

        if exact_name_matches:

            exact_name_matches.sort(
                key=lambda item: (
                    item[0],
                    item[1],
                    -int(
                        getattr(
                            item[2],
                            "id",
                            0,
                        )
                        or 0
                    ),
                ),
                reverse=True,
            )

            return exact_name_matches[0][2]

        # -----------------------------------------------------
        # 2. EXACT SKU
        # -----------------------------------------------------

        for product in products:

            sku = (
                AgentService.normalize_text(
                    getattr(product, "sku", "")
                )
            )

            if not sku:
                continue

            if re.search(
                r"(?<![a-z0-9])"
                + re.escape(sku)
                + r"(?![a-z0-9])",
                message_normalized,
            ):
                return product

        # -----------------------------------------------------
        # 3. KEYWORD / SCORE MATCH
        # -----------------------------------------------------

        scored_products = []

        for product in products:

            score = (
                AgentService.product_match_score(
                    product,
                    message,
                )
            )

            if score > 0:

                product_name = (
                    AgentService.normalize_text(
                        getattr(
                            product,
                            "name",
                            "",
                        )
                    )
                )

                scored_products.append(
                    (
                        score,
                        len(
                            product_name.split()
                        ),
                        len(product_name),
                        product,
                    )
                )

        if not scored_products:
            return None

        scored_products.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                -int(
                    getattr(
                        item[3],
                        "id",
                        0,
                    )
                    or 0
                ),
            ),
            reverse=True,
        )

        best_score = scored_products[0][0]
        best_product = scored_products[0][3]

        if best_score < 40:
            return None

        return best_product


    # =========================================================
    # DETECT INTENT
    # =========================================================

    @staticmethod
    def detect_intent(
        message: str,
    ) -> str:

        message_lower = (
            str(message or "")
            .strip()
            .lower()
        )

        if not message_lower:
            return "GENERAL_QUERY"

        # -----------------------------------------------------
        # ORDER / PURCHASE INTENT
        # -----------------------------------------------------

        order_patterns = [

            r"\bbuy\b",
            r"\border\b",
            r"\bpurchase\b",
            r"\bcheckout\b",
            r"\bplace\s+(?:an?\s+)?order\b",
            r"\bi\s+want\s+to\s+buy\b",
            r"\bi\s+want\s+to\s+order\b",
            r"\bi\s+would\s+like\s+to\s+buy\b",
            r"\bget\s+me\b",
        ]

        for pattern in order_patterns:

            if re.search(
                pattern,
                message_lower,
            ):
                return "CREATE_ORDER"

        # -----------------------------------------------------
        # CATALOG INTENT
        # -----------------------------------------------------

        catalog_patterns = [

            r"\bproduct\b",
            r"\bproducts\b",
            r"\bcatalog\b",
            r"\binventory\b",
            r"\bstock\b",
            r"\bavailable\b",
            r"\bwhat\s+do\s+you\s+have\b",
            r"\bshow\s+me\b",
        ]

        for pattern in catalog_patterns:

            if re.search(
                pattern,
                message_lower,
            ):
                return "CATALOG_QUERY"

        # -----------------------------------------------------
        # DISCOUNT / POLICY
        # -----------------------------------------------------

        discount_patterns = [

            r"\bdiscount\b",
            r"\bdiscounts\b",
            r"\boff\b",
            r"\bpromotion\b",
            r"\bpromo\b",
            r"\bmaximum\s+discount\b",
        ]

        for pattern in discount_patterns:

            if re.search(
                pattern,
                message_lower,
            ):
                return "DISCOUNT_QUERY"

        # -----------------------------------------------------
        # RISK
        # -----------------------------------------------------

        risk_patterns = [

            r"\brisk\b",
            r"\bfraud\b",
            r"\brisk\s+score\b",
            r"\brisk\s+level\b",
        ]

        for pattern in risk_patterns:

            if re.search(
                pattern,
                message_lower,
            ):
                return "RISK_QUERY"

        return "GENERAL_QUERY"

    # =========================================================
    # CATALOG RESPONSE
    # =========================================================

    @staticmethod
    def catalog_response(
        db: Session,
        merchant_id: int,
    ):

        products = (
            db.query(Product)
            .filter(
                Product.merchant_id
                == merchant_id,
                Product.is_active == True,
            )
            .order_by(
                Product.name.asc()
            )
            .all()
        )

        if not products:

            return {
                "message": (
                    "No active products were found "
                    "for this merchant."
                ),
                "products": [],
            }

        product_lines = []

        product_data = []

        for product in products:

            stock = int(
                product.stock_quantity or 0
            )

            price = float(
                product.price or 0
            )

            if stock <= 0:

                stock_status = (
                    "OUT_OF_STOCK"
                )

            elif stock <= 5:

                stock_status = (
                    "LOW_STOCK"
                )

            else:

                stock_status = (
                    "IN_STOCK"
                )

            product_lines.append(
                (
                    f"{product.name} "
                    f"(₹{price:.2f}) - "
                    f"{stock_status}, "
                    f"stock: {stock}"
                )
            )

            product_data.append(
                {
                    "id": product.id,
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "category": product.category,
                    "price": price,
                    "stock_quantity": stock,
                    "stock": stock,
                    "stock_status": stock_status,
                    "is_active": bool(
                        product.is_active
                    ),
                }
            )

        return {
            "message": (
                "Available products:\n"
                + "\n".join(product_lines)
            ),
            "products": product_data,
        }

    # =========================================================
    # PRODUCT NOT FOUND RESPONSE
    # =========================================================

    @staticmethod
    def product_not_found_response(
        message: str,
        merchant_id: int,
        quantity: int = 1,
    ):

        return {
            "message": (
                "I could not identify a product "
                "from your request. Please provide "
                "the product name or SKU."
            ),
            "intent": "CREATE_ORDER",
            "merchant_id": merchant_id,
            "product_id": None,
            "product_name": None,
            "quantity": quantity,
            "requested_discount_percent": (
                AgentService.extract_discount(
                    message
                )
            ),
            "original_amount": None,
            "final_amount": None,
            "approved_discount_percent": None,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "order_id": None,
            "order_status": "UNKNOWN",
            "manual_review_required": False,
            "products": [],
        }

    # =========================================================
    # PRODUCT FOUND RESPONSE
    # =========================================================

    @staticmethod
    def product_response(
        product: Product,
        quantity: int,
        requested_discount: float,
        merchant_id: int,
    ):

        stock = int(
            product.stock_quantity or 0
        )

        price = float(
            product.price or 0
        )

        original_amount = (
            price * quantity
        )

        return {
            "product_id": product.id,
            "product_name": product.name,
            "quantity": quantity,
            "price": price,
            "stock_quantity": stock,
            "requested_discount_percent": (
                requested_discount
            ),
            "original_amount": (
                original_amount
            ),
            "merchant_id": merchant_id,
        }

    # =========================================================
    # VALIDATE INVENTORY
    # =========================================================

    @staticmethod
    def validate_inventory(
        product: Product,
        quantity: int,
    ):

        stock = int(
            product.stock_quantity or 0
        )

        if quantity <= 0:

            return {
                "allowed": False,
                "reason": (
                    "Quantity must be greater than zero."
                ),
            }

        if stock <= 0:

            return {
                "allowed": False,
                "reason": (
                    f"{product.name} is "
                    "currently out of stock."
                ),
            }

        if quantity > stock:

            return {
                "allowed": False,
                "reason": (
                    f"Only {stock} unit(s) of "
                    f"{product.name} are available."
                ),
            }

        return {
            "allowed": True,
            "reason": "Inventory available.",
        }

    # =========================================================
    # SAFE DISCOUNT CALCULATION
    # =========================================================

    @staticmethod
    def calculate_discount_amount(
        original_amount: float,
        discount_percent: float,
    ):

        safe_discount = max(
            0.0,
            min(
                float(discount_percent),
                100.0,
            ),
        )

        discount_amount = (
            original_amount
            * safe_discount
            / 100.0
        )

        final_amount = (
            original_amount
            - discount_amount
        )

        return {
            "discount_percent": safe_discount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
        }

    # =========================================================
    # MERCHANT VALIDATION
    # =========================================================

    @staticmethod
    def merchant_exists(
        db: Session,
        merchant_id: int,
    ):

        return (
            db.query(Merchant)
            .filter(
                Merchant.id == merchant_id
            )
            .first()
            is not None
        )