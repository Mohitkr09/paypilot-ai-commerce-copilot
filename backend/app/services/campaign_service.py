import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.merchant import Merchant
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignProposalCreate


class CampaignOrchestratorService:
    """
    PayPilot AI Campaign Orchestrator.

    Campaign lifecycle:

        PHASE 1
            DRAFT
            Proposal only.
            No product price changes.
            No inventory changes.
            No orders.
            No payments.

        PHASE 2
            POLICY_APPROVED / POLICY_REJECTED
            Merchant policy and margin validation.
            No product price changes.
            No inventory changes.
            No orders.
            No payments.

        PHASE 3
            MERCHANT_APPROVED / MERCHANT_REJECTED
            Merchant explicitly approves/rejects
            the policy-approved proposal.

            MERCHANT_APPROVED means:
                - campaign is approved for activation
                - campaign is NOT active yet
                - activation_status = PENDING
                - can_activate = True
                - no product price is changed

        PHASE 4
            ACTIVE
            Explicit activation is performed.

            Only Phase 4 may:
                - change product prices

            Phase 4 still does NOT:
                - change inventory
                - create orders
                - create payments

    IMPORTANT:
        Merchant approval and campaign activation are two
        separate operations.
    """

    MAX_PRODUCTS = 8

    # =========================================================
    # COMMON HELPERS
    # =========================================================

    @staticmethod
    def _merchant_active(merchant: Merchant) -> bool:
        if hasattr(merchant, "is_active"):
            return bool(merchant.is_active)

        if hasattr(merchant, "active"):
            return bool(merchant.active)

        return True

    @staticmethod
    def _product_active(product: Product) -> bool:
        if hasattr(product, "is_active"):
            return bool(product.is_active)

        if hasattr(product, "active"):
            return bool(product.active)

        return True

    @staticmethod
    def _stock(product: Product) -> int:
        if hasattr(product, "stock_quantity"):
            return int(product.stock_quantity or 0)

        if hasattr(product, "stock"):
            return int(product.stock or 0)

        return 0

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            str(text or "").strip().lower(),
        )

    @staticmethod
    def _status(campaign: Campaign) -> str:
        """
        Normalize SQLAlchemy Enum/string status values.

        Handles values such as:
            APPROVED
            MERCHANT_APPROVED
            CampaignStatus.APPROVED
        """
        status = str(campaign.status or "").upper()

        if "." in status:
            status = status.split(".")[-1]

        return status

    @staticmethod
    def _governance(campaign: Campaign) -> dict[str, Any]:
        if isinstance(campaign.governance, dict):
            return dict(campaign.governance)

        return {}

    # =========================================================
    # PHASE 1
    # STRATEGY
    # =========================================================

    @classmethod
    def _infer_strategy(cls, brief: str) -> str:
        text = cls._normalize(brief)

        if any(
            word in text
            for word in (
                "bundle",
                "combo",
                "together",
                "package",
            )
        ):
            return "BUNDLE"

        if any(
            word in text
            for word in (
                "cross-sell",
                "cross sell",
                "accessor",
                "add-on",
                "addon",
            )
        ):
            return "CROSS_SELL"

        if any(
            word in text
            for word in (
                "upsell",
                "upgrade",
                "premium",
            )
        ):
            return "UPSELL"

        if any(
            word in text
            for word in (
                "inventory",
                "stock",
                "clearance",
                "slow-moving",
                "slow moving",
            )
        ):
            return "INVENTORY"

        if any(
            word in text
            for word in (
                "discount",
                "off",
                "sale",
                "offer",
                "coupon",
            )
        ):
            return "DISCOUNT"

        return "GROWTH"

    @classmethod
    def _infer_objective(cls, brief: str) -> str:
        text = cls._normalize(brief)

        if any(
            word in text
            for word in (
                "inventory",
                "stock",
                "clearance",
                "slow-moving",
                "slow moving",
            )
        ):
            return "REDUCE_INVENTORY"

        if any(
            word in text
            for word in (
                "order value",
                "aov",
                "basket",
                "cart value",
            )
        ):
            return "INCREASE_ORDER_VALUE"

        if any(
            word in text
            for word in (
                "accessor",
                "cross-sell",
                "cross sell",
                "add-on",
                "addon",
            )
        ):
            return "INCREASE_CROSS_SELL"

        if any(
            word in text
            for word in (
                "premium",
                "upgrade",
                "upsell",
            )
        ):
            return "INCREASE_UPSELL"

        return "INCREASE_REVENUE"

    @classmethod
    def _requested_discount_from_text(
        cls,
        brief: str,
    ) -> float:
        match = re.search(
            r"(\d+(?:\.\d+)?)\s*%",
            brief or "",
        )

        if not match:
            return 0.0

        return max(
            0.0,
            min(
                float(match.group(1)),
                100.0,
            ),
        )

    # =========================================================
    # PHASE 1
    # PRODUCT SELECTION
    # =========================================================

    @classmethod
    def _select_products(
        cls,
        db: Session,
        merchant_id: int,
        brief: str,
        explicit_product_ids: list[int],
    ) -> list[Product]:

        base_query = (
            db.query(Product)
            .filter(
                Product.merchant_id == merchant_id
            )
        )

        # -----------------------------------------------------
        # Explicit products
        # -----------------------------------------------------

        if explicit_product_ids:

            requested_ids = list(
                dict.fromkeys(
                    int(x)
                    for x in explicit_product_ids
                )
            )

            products = (
                base_query
                .filter(
                    Product.id.in_(requested_ids)
                )
                .all()
            )

            found_ids = {
                int(product.id)
                for product in products
            }

            missing = [
                product_id
                for product_id in requested_ids
                if product_id not in found_ids
            ]

            if missing:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Product(s) not found for "
                        f"this merchant: {missing}"
                    ),
                )

            return products[: cls.MAX_PRODUCTS]

        # -----------------------------------------------------
        # AI-style keyword selection
        # -----------------------------------------------------

        products = base_query.all()

        if not products:
            return []

        text = cls._normalize(brief)

        tokens = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                text,
            )
            if len(token) >= 3
        }

        scored: list[tuple[int, Product]] = []

        for product in products:

            if (
                not cls._product_active(product)
                or cls._stock(product) <= 0
            ):
                continue

            haystack = cls._normalize(
                " ".join(
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
                )
            )

            product_tokens = set(
                re.findall(
                    r"[a-z0-9]+",
                    haystack,
                )
            )

            score = len(
                tokens & product_tokens
            ) * 10

            name = cls._normalize(
                getattr(
                    product,
                    "name",
                    "",
                )
            )

            category = cls._normalize(
                getattr(
                    product,
                    "category",
                    "",
                )
            )

            if name and name in text:
                score += 100

            if category and category in text:
                score += 50

            scored.append(
                (
                    score,
                    product,
                )
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                str(
                    getattr(
                        item[1],
                        "name",
                        "",
                    )
                ),
            )
        )

        selected = [
            product
            for score, product in scored
            if score > 0
        ][: cls.MAX_PRODUCTS]

        # Broad campaign fallback
        if not selected:
            selected = [
                product
                for product in products
                if (
                    cls._product_active(product)
                    and cls._stock(product) > 0
                )
            ][: cls.MAX_PRODUCTS]

        return selected

    # =========================================================
    # PHASE 1
    # BUILD PROPOSAL
    # =========================================================

    @classmethod
    def build_proposal(
        cls,
        db: Session,
        merchant_id: int,
        request: CampaignProposalCreate,
    ) -> Campaign:

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.id == merchant_id
            )
            .first()
        )

        if not merchant:
            raise HTTPException(
                status_code=404,
                detail="Merchant not found.",
            )

        if not cls._merchant_active(merchant):
            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

        selected = cls._select_products(
            db=db,
            merchant_id=merchant_id,
            brief=request.brief,
            explicit_product_ids=request.product_ids,
        )

        if not selected:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No active, in-stock products "
                    "could be selected for this "
                    "campaign proposal."
                ),
            )

        strategy = cls._infer_strategy(
            request.brief
        )

        objective = cls._infer_objective(
            request.brief
        )

        requested_discount = float(
            request.suggested_discount_percent or 0
        )

        if requested_discount == 0:
            requested_discount = (
                cls._requested_discount_from_text(
                    request.brief
                )
            )

        product_ids = [
            int(product.id)
            for product in selected
        ]

        product_names = [
            str(product.name)
            for product in selected
        ]

        actions: list[dict[str, Any]] = []

        if (
            strategy
            in {
                "DISCOUNT",
                "GROWTH",
                "INVENTORY",
            }
            and requested_discount > 0
        ):
            actions.append(
                {
                    "type": "DISCOUNT_PROPOSAL",
                    "discount_percent": requested_discount,
                    "product_ids": product_ids,
                    "description": (
                        f"Propose "
                        f"{requested_discount:.2f}% "
                        "discount for the "
                        "selected products."
                    ),
                    "money_action": True,
                }
            )

        else:
            actions.append(
                {
                    "type": "PRODUCT_PROMOTION",
                    "product_ids": product_ids,
                    "description": (
                        "Promote the selected "
                        "products through PayPilot "
                        "commerce recommendations."
                    ),
                    "money_action": False,
                }
            )

        if strategy in {
            "CROSS_SELL",
            "BUNDLE",
            "GROWTH",
        }:
            actions.append(
                {
                    "type": "CROSS_SELL",
                    "product_ids": product_ids,
                    "description": (
                        "Recommend complementary "
                        "selected products to "
                        "increase order value."
                    ),
                    "money_action": False,
                }
            )

        if strategy == "UPSELL":
            actions.append(
                {
                    "type": "UPSELL",
                    "product_ids": product_ids,
                    "description": (
                        "Recommend a higher-value "
                        "product from the selected "
                        "campaign set."
                    ),
                    "money_action": False,
                }
            )

        if strategy == "BUNDLE":
            actions.append(
                {
                    "type": "BUNDLE_PROPOSAL",
                    "product_ids": product_ids,
                    "description": (
                        "Propose a product bundle. "
                        "Bundle pricing is not "
                        "activated in Phase 1."
                    ),
                    "money_action": True,
                }
            )

        name = (
            request.campaign_name.strip()
            if (
                request.campaign_name
                and request.campaign_name.strip()
            )
            else (
                f"{objective.replace('_', ' ').title()} "
                "Campaign"
            )
        )

        explanation = (
            "PayPilot interpreted the merchant "
            f"request as "
            f"{objective.replace('_', ' ').lower()} "
            f"using a "
            f"{strategy.replace('_', ' ').lower()} "
            "strategy. "
            f"The proposal selected "
            f"{len(selected)} active, in-stock "
            "product(s): "
            f"{', '.join(product_names)}. "
            "This is a proposal only. No price, "
            "discount, inventory, order, or "
            "payment was changed. "
            "The proposed financial action must "
            "pass the Phase 2 policy/margin "
            "engine and Phase 3 merchant approval. "
            "After merchant approval, a separate "
            "Phase 4 activation step is required."
        )

        governance = {
            "proposal_only": True,
            "phase": 1,

            "money_action_present": any(
                bool(
                    action.get("money_action")
                )
                for action in actions
            ),

            "policy_check_required": True,
            "margin_check_required": True,
            "merchant_approval_required": True,

            "policy_validation_status": "PENDING",
            "margin_validation_status": "PENDING",

            "validation_passed": False,

            "can_activate": False,

            "payment_allowed": False,

            # Phase 3
            "merchant_approval_status": "PENDING",
            "merchant_approved": False,

            # Phase 4
            "campaign_activation_status": "NOT_STARTED",
            "activation_status": "NOT_STARTED",
            "campaign_active": False,

            # Safety
            "price_changed": False,
            "inventory_changed": False,
            "orders_changed": False,
            "payments_changed": False,
        }

        campaign = Campaign(
            merchant_id=merchant_id,
            name=name,
            objective=objective,
            brief=request.brief.strip(),
            strategy_type=strategy,
            status="DRAFT",
            suggested_discount_percent=requested_discount,
            product_ids=product_ids,
            proposed_actions=actions,
            governance=governance,
            explanation=explanation,
        )

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return campaign

    # =========================================================
    # PHASE 2
    # POLICY + MARGIN VALIDATION
    # =========================================================

    @classmethod
    def validate_proposal(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.merchant_id == merchant_id,
            )
            .first()
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign proposal not found.",
            )

        if cls._status(campaign) not in {
            "DRAFT",
            "POLICY_REJECTED",
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only DRAFT or previously rejected "
                    "campaign proposals can be validated."
                ),
            )

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.id == merchant_id
            )
            .first()
        )

        if not merchant:
            raise HTTPException(
                status_code=404,
                detail="Merchant not found.",
            )

        if not cls._merchant_active(merchant):
            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

        merchant_max_discount = float(
            merchant.maximum_discount_percent or 0
        )

        minimum_margin = float(
            merchant.minimum_margin or 0
        )

        if not 0 <= merchant_max_discount <= 100:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Merchant maximum discount must "
                    "be between 0 and 100%."
                ),
            )

        if not 0 <= minimum_margin < 100:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Merchant minimum margin must "
                    "be between 0 and 99.99%."
                ),
            )

        requested_discount = float(
            campaign.suggested_discount_percent or 0
        )

        if requested_discount < 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Campaign discount cannot "
                    "be negative."
                ),
            )

        if requested_discount > 100:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Campaign discount cannot "
                    "exceed 100%."
                ),
            )

        # -----------------------------------------------------
        # POLICY CHECK
        # -----------------------------------------------------

        policy_passed = (
            requested_discount
            <= merchant_max_discount
        )

        policy_reason = (
            "Requested discount is within "
            "merchant policy."
            if policy_passed
            else (
                f"Requested discount of "
                f"{requested_discount:.2f}% exceeds "
                f"merchant maximum discount of "
                f"{merchant_max_discount:.2f}%."
            )
        )

        # -----------------------------------------------------
        # LOAD PRODUCTS
        # -----------------------------------------------------

        product_ids = [
            int(product_id)
            for product_id in (
                campaign.product_ids or []
            )
        ]

        if not product_ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Campaign contains no products "
                    "to validate."
                ),
            )

        products = (
            db.query(Product)
            .filter(
                Product.merchant_id == merchant_id,
                Product.id.in_(product_ids),
            )
            .all()
        )

        products_by_id = {
            int(product.id): product
            for product in products
        }

        missing_products = [
            product_id
            for product_id in product_ids
            if product_id not in products_by_id
        ]

        if missing_products:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Campaign contains products that "
                    "do not belong to this merchant: "
                    f"{missing_products}"
                ),
            )

        # -----------------------------------------------------
        # VALIDATE EACH PRODUCT
        # -----------------------------------------------------

        product_results: list[dict[str, Any]] = []

        margin_passed = True

        for product_id in product_ids:

            product = products_by_id[product_id]

            product_name = str(
                getattr(
                    product,
                    "name",
                    f"Product #{product_id}",
                )
            )

            price = float(
                product.price or 0
            )

            cost_price = float(
                product.cost_price or 0
            )

            stock_quantity = cls._stock(product)

            active = cls._product_active(product)

            product_errors: list[str] = []

            if not active:
                product_errors.append(
                    "Product is inactive."
                )

            if stock_quantity <= 0:
                product_errors.append(
                    "Product is out of stock."
                )

            if price <= 0:
                product_errors.append(
                    "Product price must be greater than zero."
                )

            if cost_price < 0:
                product_errors.append(
                    "Product cost price cannot be negative."
                )

            # -------------------------------------------------
            # MARGIN CALCULATION
            # -------------------------------------------------

            minimum_safe_price = 0.0

            if price > 0 and cost_price >= 0:

                denominator = (
                    1 - minimum_margin / 100
                )

                if denominator <= 0:

                    product_errors.append(
                        "Invalid minimum margin configuration."
                    )

                    safe_discount = 0.0

                else:

                    minimum_safe_price = (
                        cost_price / denominator
                    )

                    safe_discount = (
                        (
                            price
                            - minimum_safe_price
                        )
                        / price
                    ) * 100

                    safe_discount = max(
                        0.0,
                        safe_discount,
                    )

            else:
                safe_discount = 0.0

            safe_discount = round(
                safe_discount,
                2,
            )

            # -------------------------------------------------
            # REQUESTED DISCOUNT VS MARGIN
            # -------------------------------------------------

            product_margin_passed = (
                requested_discount
                <= safe_discount
            )

            if not product_margin_passed:

                margin_passed = False

                product_errors.append(
                    (
                        f"Requested discount of "
                        f"{requested_discount:.2f}% would "
                        f"violate the minimum margin of "
                        f"{minimum_margin:.2f}%. "
                        f"Maximum safe discount for this "
                        f"product is "
                        f"{safe_discount:.2f}%."
                    )
                )

            product_passed = (
                len(product_errors) == 0
                and product_margin_passed
            )

            product_results.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,

                    "original_price": round(
                        price,
                        2,
                    ),

                    "cost_price": round(
                        cost_price,
                        2,
                    ),

                    "stock_quantity": stock_quantity,
                    "active": active,

                    "minimum_margin_percent": round(
                        minimum_margin,
                        2,
                    ),

                    "minimum_safe_price": round(
                        minimum_safe_price,
                        2,
                    ),

                    "maximum_safe_discount_percent": (
                        safe_discount
                    ),

                    "requested_discount_percent": round(
                        requested_discount,
                        2,
                    ),

                    "policy_max_discount_percent": round(
                        merchant_max_discount,
                        2,
                    ),

                    "policy_passed": policy_passed,
                    "margin_passed": product_margin_passed,
                    "passed": product_passed,

                    "errors": product_errors,
                }
            )

        # -----------------------------------------------------
        # FINAL DECISION
        # -----------------------------------------------------

        overall_margin_passed = (
            margin_passed
            and all(
                result["margin_passed"]
                for result in product_results
            )
        )

        overall_product_passed = all(
            result["passed"]
            for result in product_results
        )

        validation_passed = (
            policy_passed
            and overall_margin_passed
            and overall_product_passed
        )

        # -----------------------------------------------------
        # SAFE DISCOUNT
        # -----------------------------------------------------

        if product_results:

            maximum_safe_discount = min(
                result[
                    "maximum_safe_discount_percent"
                ]
                for result in product_results
            )

        else:
            maximum_safe_discount = 0.0

        approved_discount = min(
            requested_discount,
            merchant_max_discount,
            maximum_safe_discount,
        )

        approved_discount = round(
            max(
                0.0,
                approved_discount,
            ),
            2,
        )

        # -----------------------------------------------------
        # FINAL STATUS
        # -----------------------------------------------------

        if validation_passed:

            campaign.status = "POLICY_APPROVED"

            validation_status = "PASSED"

            validation_message = (
                f"Policy and margin validation passed. "
                f"Requested discount of "
                f"{requested_discount:.2f}% is within "
                f"merchant policy and the minimum margin "
                f"requirements for all selected products. "
                f"Maximum safe campaign discount is "
                f"{maximum_safe_discount:.2f}%."
            )

        else:

            campaign.status = "POLICY_REJECTED"

            validation_status = "FAILED"

            reasons: list[str] = []

            if not policy_passed:
                reasons.append(
                    policy_reason
                )

            for result in product_results:

                if result["errors"]:
                    reasons.extend(
                        result["errors"]
                    )

            validation_message = (
                "Policy and/or margin validation failed. "
                + " ".join(reasons)
            )

        # -----------------------------------------------------
        # GOVERNANCE
        # -----------------------------------------------------

        existing_governance = (
            campaign.governance
            if isinstance(
                campaign.governance,
                dict,
            )
            else {}
        )

        governance = {
            **existing_governance,

            "phase": 2,

            "proposal_only": True,

            "policy_validation_status": (
                validation_status
            ),

            "margin_validation_status": (
                "PASSED"
                if overall_margin_passed
                else "FAILED"
            ),

            "policy_check": {
                "passed": policy_passed,
                "requested_discount_percent": round(
                    requested_discount,
                    2,
                ),
                "maximum_discount_percent": round(
                    merchant_max_discount,
                    2,
                ),
                "reason": policy_reason,
            },

            "margin_check": {
                "passed": overall_margin_passed,
                "minimum_margin_percent": round(
                    minimum_margin,
                    2,
                ),
                "maximum_safe_discount_percent": round(
                    maximum_safe_discount,
                    2,
                ),
            },

            "approved_discount_percent": (
                approved_discount
            ),

            "validation_passed": (
                validation_passed
            ),

            "validation_message": (
                validation_message
            ),

            "products": product_results,

            # -------------------------------------------------
            # PHASE 3
            # -------------------------------------------------

            "merchant_approval_required": True,

            "merchant_approval_status": (
                "PENDING"
                if validation_passed
                else "BLOCKED"
            ),

            "merchant_approved": False,

            "campaign_activation_status": (
                "READY_FOR_APPROVAL"
                if validation_passed
                else "BLOCKED"
            ),

            "activation_status": (
                "NOT_STARTED"
                if validation_passed
                else "BLOCKED"
            ),

            "can_activate": False,

            # -------------------------------------------------
            # PHASE 4
            # -------------------------------------------------

            "campaign_active": False,

            # -------------------------------------------------
            # SAFETY FLAGS
            # -------------------------------------------------

            "payment_allowed": False,

            "price_changed": False,

            "inventory_changed": False,

            "orders_changed": False,

            "payments_changed": False,
        }

        campaign.governance = governance

        # -----------------------------------------------------
        # EXPLANATION
        # -----------------------------------------------------

        campaign.explanation = (
            f"{campaign.explanation} "
            f"Phase 2 validation: "
            f"{validation_message} "
            f"No product price, inventory, order, "
            f"or payment was changed."
        )

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return campaign

    # =========================================================
    # PHASE 3
    # MERCHANT APPROVAL
    # =========================================================

    @classmethod
    def approve_proposal(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.merchant_id == merchant_id,
            )
            .first()
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign proposal not found.",
            )

        # -----------------------------------------------------
        # ONLY POLICY APPROVED CAN BE MERCHANT APPROVED
        # -----------------------------------------------------

        if cls._status(campaign) != "POLICY_APPROVED":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign must pass Phase 2 "
                    "policy and margin validation "
                    "before merchant approval."
                ),
            )

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.id == merchant_id
            )
            .first()
        )

        if not merchant:
            raise HTTPException(
                status_code=404,
                detail="Merchant not found.",
            )

        if not cls._merchant_active(merchant):
            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

        governance = cls._governance(campaign)

        validation_passed = bool(
            governance.get(
                "validation_passed",
                False,
            )
        )

        if not validation_passed:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign cannot be approved "
                    "because Phase 2 validation "
                    "has not passed."
                ),
            )

        # -----------------------------------------------------
        # APPROVED DISCOUNT
        # -----------------------------------------------------

        approved_discount = float(
            governance.get(
                "approved_discount_percent",
                campaign.suggested_discount_percent
                or 0,
            )
            or 0
        )

        requested_discount = float(
            campaign.suggested_discount_percent
            or 0
        )

        merchant_max_discount = float(
            merchant.maximum_discount_percent or 0
        )

        if approved_discount > merchant_max_discount:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved discount exceeds "
                    "merchant policy."
                ),
            )

        if approved_discount < 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved discount cannot "
                    "be negative."
                ),
            )

        # -----------------------------------------------------
        # MERCHANT APPROVAL
        # -----------------------------------------------------

        approved_at = datetime.now(
            timezone.utc
        ).isoformat()

        campaign.status = "MERCHANT_APPROVED"

        governance.update(
            {
                "phase": 3,

                "proposal_only": False,

                "merchant_approval_required": False,

                "merchant_approval_status": "APPROVED",

                "merchant_approved": True,

                "approved_by_merchant_id": merchant_id,

                "approved_at": approved_at,

                # IMPORTANT:
                # Approval does NOT activate.
                "campaign_activation_status": "PENDING",

                "activation_status": "PENDING",

                "can_activate": True,

                "campaign_active": False,

                "approved_discount_percent": round(
                    approved_discount,
                    2,
                ),

                "requested_discount_percent": round(
                    requested_discount,
                    2,
                ),

                # -------------------------------------------------
                # PHASE 3 SAFETY GUARANTEES
                # -------------------------------------------------

                "payment_allowed": False,

                "price_changed": False,

                "inventory_changed": False,

                "orders_changed": False,

                "payments_changed": False,
            }
        )

        campaign.governance = governance

        # -----------------------------------------------------
        # CORRECT PHASE 3 EXPLANATION
        # -----------------------------------------------------

        campaign.explanation = (
            f"{campaign.explanation} "
            "Phase 3 merchant approval completed. "
            f"The merchant approved the campaign with "
            f"an approved discount of "
            f"{approved_discount:.2f}%. "
            "The campaign is approved for activation, "
            "but it is not active yet. "
            "A separate Phase 4 activation step is "
            "required before the campaign becomes active. "
            "No product price, inventory, order, "
            "or payment was changed by the approval "
            "operation."
        )

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return campaign

    # =========================================================
    # PHASE 3
    # MERCHANT REJECTION
    # =========================================================

    @classmethod
    def reject_proposal(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.merchant_id == merchant_id,
            )
            .first()
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign proposal not found.",
            )

        if cls._status(campaign) != "POLICY_APPROVED":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only POLICY_APPROVED campaign "
                    "proposals can be merchant-rejected."
                ),
            )

        governance = cls._governance(campaign)

        if not governance.get(
            "validation_passed",
            False,
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign proposal has not "
                    "passed Phase 2 validation."
                ),
            )

        rejected_at = datetime.now(
            timezone.utc
        ).isoformat()

        campaign.status = "MERCHANT_REJECTED"

        governance.update(
            {
                "phase": 3,

                "proposal_only": False,

                "merchant_approval_required": False,

                "merchant_approved": False,

                "merchant_approval_status": "REJECTED",

                "approved_by_merchant_id": merchant_id,

                "rejected_at": rejected_at,

                "can_activate": False,

                "campaign_active": False,

                "campaign_activation_status": "REJECTED",

                "activation_status": "REJECTED",

                "payment_allowed": False,

                "price_changed": False,

                "inventory_changed": False,

                "orders_changed": False,

                "payments_changed": False,
            }
        )

        campaign.governance = governance

        campaign.explanation = (
            f"{campaign.explanation} "
            "Phase 3 merchant approval: rejected "
            "by merchant. "
            "The campaign is not active and cannot "
            "be activated. "
            "No product price, inventory, order, "
            "or payment was changed."
        )

        db.add(campaign)
        db.commit()
        db.refresh(campaign)

        return campaign

    # =========================================================
    # PHASE 4
    # EXPLICIT CAMPAIGN ACTIVATION
    # =========================================================

    @classmethod
    def activate_campaign(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        # -----------------------------------------------------
        # LOAD CAMPAIGN
        # -----------------------------------------------------

        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.merchant_id == merchant_id,
            )
            .first()
        )

        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found.",
            )

        # -----------------------------------------------------
        # PHASE 4 GATE
        # -----------------------------------------------------

        status = cls._status(campaign)

        # Backward compatibility:
        # Older records may have been saved as APPROVED.
        # They must still have explicit merchant approval
        # before activation.
        if status not in {
            "MERCHANT_APPROVED",
            "APPROVED",
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign must be explicitly "
                    "approved by the merchant before "
                    "activation."
                ),
            )

        governance = cls._governance(campaign)

        # -----------------------------------------------------
        # VERIFY MERCHANT APPROVAL
        # -----------------------------------------------------

        if not bool(
            governance.get(
                "merchant_approved",
                False,
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Merchant approval is required "
                    "before campaign activation."
                ),
            )

        if (
            governance.get(
                "merchant_approval_status"
            )
            != "APPROVED"
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign does not have a valid "
                    "merchant approval."
                ),
            )

        # -----------------------------------------------------
        # VERIFY PHASE 2 VALIDATION
        # -----------------------------------------------------

        if not bool(
            governance.get(
                "validation_passed",
                False,
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign cannot be activated "
                    "because Phase 2 validation "
                    "did not pass."
                ),
            )

        # -----------------------------------------------------
        # VERIFY ACTIVATION PERMISSION
        # -----------------------------------------------------

        if governance.get(
            "can_activate"
        ) is not True:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign is not eligible "
                    "for activation."
                ),
            )

        # -----------------------------------------------------
        # PREVENT DOUBLE ACTIVATION
        # -----------------------------------------------------

        if (
            governance.get(
                "campaign_active",
                False,
            )
            is True
            or status == "ACTIVE"
        ):
            raise HTTPException(
                status_code=409,
                detail="Campaign is already active.",
            )

        # -----------------------------------------------------
        # VERIFY MERCHANT
        # -----------------------------------------------------

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.id == merchant_id
            )
            .first()
        )

        if not merchant:
            raise HTTPException(
                status_code=404,
                detail="Merchant not found.",
            )

        if not cls._merchant_active(merchant):
            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

        # -----------------------------------------------------
        # READ APPROVED DISCOUNT
        # -----------------------------------------------------

        approved_discount = float(
            governance.get(
                "approved_discount_percent",
                campaign.suggested_discount_percent
                or 0,
            )
            or 0
        )

        if approved_discount < 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved discount cannot "
                    "be negative."
                ),
            )

        if approved_discount > 100:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved discount cannot "
                    "exceed 100%."
                ),
            )

        merchant_max_discount = float(
            merchant.maximum_discount_percent
            or 0
        )

        if approved_discount > merchant_max_discount:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approved discount exceeds "
                    "current merchant policy."
                ),
            )

        # -----------------------------------------------------
        # VERIFY PRODUCTS
        # -----------------------------------------------------

        product_ids = [
            int(product_id)
            for product_id in (
                campaign.product_ids or []
            )
        ]

        if not product_ids:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign cannot be activated "
                    "because it contains no products."
                ),
            )

        products = (
            db.query(Product)
            .filter(
                Product.merchant_id == merchant_id,
                Product.id.in_(product_ids),
            )
            .all()
        )

        products_by_id = {
            int(product.id): product
            for product in products
        }

        missing_products = [
            product_id
            for product_id in product_ids
            if product_id not in products_by_id
        ]

        if missing_products:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign cannot be activated "
                    "because one or more products "
                    "are no longer available: "
                    f"{missing_products}"
                ),
            )

        # -----------------------------------------------------
        # RE-VALIDATE PRODUCTS BEFORE MONEY ACTION
        # -----------------------------------------------------

        invalid_products: list[int] = []

        for product_id in product_ids:

            product = products_by_id[product_id]

            if not cls._product_active(product):
                invalid_products.append(product_id)
                continue

            if cls._stock(product) <= 0:
                invalid_products.append(product_id)
                continue

            current_price = float(
                product.price or 0
            )

            cost_price = float(
                product.cost_price or 0
            )

            if current_price <= 0:
                invalid_products.append(product_id)
                continue

            if cost_price < 0:
                invalid_products.append(product_id)
                continue

        if invalid_products:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Campaign cannot be activated "
                    "because these products are "
                    "inactive, out of stock, or "
                    "have invalid pricing: "
                    f"{invalid_products}"
                ),
            )

        # -----------------------------------------------------
        # FINAL MARGIN SAFETY CHECK
        #
        # This is deliberately repeated at Phase 4.
        #
        # Product prices could have changed between
        # Phase 2 validation and Phase 4 activation.
        # -----------------------------------------------------

        minimum_margin = float(
            merchant.minimum_margin or 0
        )

        if not 0 <= minimum_margin < 100:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Merchant minimum margin "
                    "configuration is invalid."
                ),
            )

        activation_results: list[
            dict[str, Any]
        ] = []

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # We calculate EVERYTHING first.
        #
        # No product is modified until all products
        # pass the Phase 4 safety check.
        # -----------------------------------------------------

        for product_id in product_ids:

            product = products_by_id[product_id]

            old_price = float(
                product.price or 0
            )

            cost_price = float(
                product.cost_price or 0
            )

            denominator = (
                1 - minimum_margin / 100
            )

            if denominator <= 0:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Invalid minimum margin "
                        "configuration."
                    ),
                )

            minimum_safe_price = (
                cost_price / denominator
            )

            new_price = round(
                old_price
                * (1 - approved_discount / 100),
                2,
            )

            if new_price < minimum_safe_price:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Product {product_id} cannot "
                        f"be activated with the approved "
                        f"{approved_discount:.2f}% discount "
                        f"because the resulting price "
                        f"{new_price:.2f} would be below "
                        f"the minimum safe price "
                        f"{minimum_safe_price:.2f}."
                    ),
                )

            activation_results.append(
                {
                    "product_id": product_id,

                    "product_name": str(
                        getattr(
                            product,
                            "name",
                            f"Product #{product_id}",
                        )
                    ),

                    "old_price": round(
                        old_price,
                        2,
                    ),

                    "new_price": round(
                        new_price,
                        2,
                    ),

                    "cost_price": round(
                        cost_price,
                        2,
                    ),

                    "discount_percent": round(
                        approved_discount,
                        2,
                    ),

                    "minimum_safe_price": round(
                        minimum_safe_price,
                        2,
                    ),
                }
            )

        # -----------------------------------------------------
        # PHASE 4
        # ACTUAL PRODUCT PRICE CHANGE
        # -----------------------------------------------------

        try:

            for result in activation_results:

                product = products_by_id[
                    result["product_id"]
                ]

                product.price = result[
                    "new_price"
                ]

                db.add(product)

            # -------------------------------------------------
            # MARK CAMPAIGN ACTIVE
            # -------------------------------------------------

            activated_at = datetime.now(
                timezone.utc
            ).isoformat()

            campaign.status = "ACTIVE"

            governance.update(
                {
                    "phase": 4,

                    "proposal_only": False,

                    "merchant_approval_required": False,

                    "merchant_approval_status": "APPROVED",

                    "merchant_approved": True,

                    "can_activate": True,

                    "campaign_active": True,

                    "campaign_activation_status": "ACTIVE",

                    "activation_status": "ACTIVE",

                    "activated_at": activated_at,

                    "approved_discount_percent": round(
                        approved_discount,
                        2,
                    ),

                    # -----------------------------------------
                    # PHASE 4 SAFETY FLAGS
                    # -----------------------------------------

                    "payment_allowed": False,

                    "price_changed": True,

                    "inventory_changed": False,

                    "orders_changed": False,

                    "payments_changed": False,

                    # -----------------------------------------
                    # ACTIVATION RECORD
                    # -----------------------------------------

                    "activation_result": {
                        "success": True,

                        "approved_discount_percent": (
                            round(
                                approved_discount,
                                2,
                            )
                        ),

                        "products_changed": (
                            activation_results
                        ),

                        "activated_at": activated_at,
                    },
                }
            )

            campaign.governance = governance

            campaign.explanation = (
                f"{campaign.explanation} "
                "Phase 4 activation completed "
                "successfully. "
                f"The merchant-approved "
                f"{approved_discount:.2f}% discount "
                f"was applied to "
                f"{len(activation_results)} "
                "product(s). "
                "The campaign is now ACTIVE. "
                "Product prices were changed as "
                "part of explicit Phase 4 activation. "
                "Inventory, orders, and payments "
                "were not changed."
            )

            db.add(campaign)

            # -------------------------------------------------
            # SINGLE TRANSACTION COMMIT
            #
            # If any database error occurs, all price
            # changes and campaign changes roll back.
            # -------------------------------------------------

            db.commit()

            db.refresh(campaign)

            return campaign

        except HTTPException:
            db.rollback()
            raise

        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Campaign activation failed. "
                    "All Phase 4 changes were rolled back. "
                    f"Reason: {str(exc)}"
                ),
            )

    # =========================================================
    # PHASE 4 ALIAS
    #
    # Useful if router/frontend uses the name
    # activate_proposal.
    # =========================================================

    @classmethod
    def activate_proposal(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        return cls.activate_campaign(
            db=db,
            merchant_id=merchant_id,
            campaign_id=campaign_id,
        )

    # =========================================================
    # LEGACY COMPATIBILITY
    #
    # IMPORTANT:
    # This method performs BOTH Phase 3 approval and Phase 4
    # activation. It should NOT be used by the new frontend
    # workflow.
    #
    # New workflow:
    #
    #     approve_proposal()
    #             ↓
    #     activate_campaign()
    #
    # =========================================================

    @classmethod
    def approve_and_activate(
        cls,
        db: Session,
        merchant_id: int,
        campaign_id: int,
    ) -> Campaign:

        campaign = cls.approve_proposal(
            db=db,
            merchant_id=merchant_id,
            campaign_id=campaign_id,
        )

        return cls.activate_campaign(
            db=db,
            merchant_id=merchant_id,
            campaign_id=campaign.id,
        )