import hmac
import hashlib

from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

from typing import (
    Optional,
    Dict,
    Any,
    Union,
)

import razorpay

from app.core.config import settings


class RazorpayService:
    """
    Razorpay integration service.

    Responsibilities:
        - Initialize Razorpay client
        - Create Razorpay orders
        - Fetch Razorpay orders
        - Fetch Razorpay payments
        - Verify checkout payment signatures
        - Verify webhook signatures
        - Capture payments
        - Refund payments

    This service does NOT modify our database.

    Database state changes belong to:
        - PaymentService
        - OrderService
        - API routes
    """

    # =========================================================
    # CONFIGURATION
    # =========================================================

    @staticmethod
    def _get_key_id() -> str:
        """
        Get Razorpay public key.

        Safe to expose to frontend.
        """

        key_id = getattr(
            settings,
            "RAZORPAY_KEY_ID",
            None,
        )

        if key_id is None:
            raise ValueError(
                "RAZORPAY_KEY_ID is not configured"
            )

        key_id = str(key_id).strip()

        if not key_id:
            raise ValueError(
                "RAZORPAY_KEY_ID is empty"
            )

        return key_id

    # =========================================================
    # RAZORPAY API KEY SECRET
    # =========================================================

    @staticmethod
    def _get_key_secret() -> str:
        """
        Get Razorpay API key secret.

        NEVER expose this to frontend.

        Used for:
            - Razorpay API authentication
            - Checkout payment signature verification
        """

        key_secret = getattr(
            settings,
            "RAZORPAY_KEY_SECRET",
            None,
        )

        if key_secret is None:
            raise ValueError(
                "RAZORPAY_KEY_SECRET is not configured"
            )

        key_secret = str(
            key_secret
        ).strip()

        if not key_secret:
            raise ValueError(
                "RAZORPAY_KEY_SECRET is empty"
            )

        return key_secret

    # =========================================================
    # RAZORPAY WEBHOOK SECRET
    # =========================================================

    @staticmethod
    def _get_webhook_secret() -> str:
        """
        Get Razorpay webhook secret.

        IMPORTANT:

        This is different from:

            RAZORPAY_KEY_SECRET

        The webhook secret is the secret manually configured
        in Razorpay Dashboard -> Webhooks.
        """

        webhook_secret = getattr(
            settings,
            "RAZORPAY_WEBHOOK_SECRET",
            None,
        )

        if webhook_secret is None:
            raise ValueError(
                "RAZORPAY_WEBHOOK_SECRET is not configured"
            )

        webhook_secret = str(
            webhook_secret
        ).strip()

        if not webhook_secret:
            raise ValueError(
                "RAZORPAY_WEBHOOK_SECRET is empty"
            )

        return webhook_secret

    # =========================================================
    # RAZORPAY CLIENT
    # =========================================================

    @staticmethod
    def get_client():
        """
        Create and return Razorpay client.
        """

        return razorpay.Client(
            auth=(
                RazorpayService._get_key_id(),
                RazorpayService._get_key_secret(),
            )
        )

    # =========================================================
    # PUBLIC KEY
    # =========================================================

    @staticmethod
    def get_key_id() -> str:
        """
        Return public Razorpay key.

        Safe for frontend APIs.
        """

        return RazorpayService._get_key_id()

    # =========================================================
    # CURRENCY
    # =========================================================

    @staticmethod
    def _normalize_currency(
        currency: str = "INR",
    ) -> str:

        if currency is None:
            currency = "INR"

        currency = str(
            currency
        ).strip().upper()

        if len(currency) != 3:
            raise ValueError(
                "Currency must be a valid "
                "3-letter currency code"
            )

        return currency

    # =========================================================
    # DECIMAL AMOUNT
    # =========================================================

    @staticmethod
    def _decimal_amount(
        amount,
    ) -> Decimal:
        """
        Convert amount to normalized Decimal.

        Examples:

            100
            100.0
            "100.00"

        become:

            Decimal("100.00")
        """

        if amount is None:
            raise ValueError(
                "Payment amount is required"
            )

        try:

            value = Decimal(
                str(amount)
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):

            raise ValueError(
                "Invalid payment amount"
            )

        if value <= 0:

            raise ValueError(
                "Payment amount must be "
                "greater than zero"
            )

        return value

    # =========================================================
    # AMOUNT -> SMALLEST CURRENCY UNIT
    # =========================================================

    @staticmethod
    def _amount_to_smallest_unit(
        amount,
    ) -> int:
        """
        Convert major currency unit to smallest unit.

        INR:

            100.00
              ->
            10000 paise
        """

        amount_decimal = (
            RazorpayService._decimal_amount(
                amount
            )
        )

        smallest_unit = int(
            amount_decimal * Decimal("100")
        )

        if smallest_unit <= 0:

            raise ValueError(
                "Payment amount must be "
                "greater than zero"
            )

        return smallest_unit

    # =========================================================
    # CREATE RAZORPAY ORDER
    # =========================================================

    @staticmethod
    def create_order(
        amount,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order.
        """

        currency = (
            RazorpayService._normalize_currency(
                currency
            )
        )

        amount_decimal = (
            RazorpayService._decimal_amount(
                amount
            )
        )

        amount_in_smallest_unit = (
            RazorpayService._amount_to_smallest_unit(
                amount_decimal
            )
        )

        data: Dict[str, Any] = {
            "amount": amount_in_smallest_unit,
            "currency": currency,
        }

        if receipt:

            data["receipt"] = str(
                receipt
            )

        if notes:

            data["notes"] = {
                str(key): str(value)
                for key, value in notes.items()
            }

        print()
        print("=" * 60)
        print("CREATING RAZORPAY ORDER")
        print("=" * 60)

        print(
            "Amount:",
            amount_decimal,
        )

        print(
            "Smallest unit:",
            amount_in_smallest_unit,
        )

        print(
            "Currency:",
            currency,
        )

        print(
            "Receipt:",
            receipt,
        )

        try:

            client = (
                RazorpayService.get_client()
            )

        except Exception as e:

            raise RuntimeError(
                "Unable to initialize Razorpay client: "
                f"{e}"
            )

        try:

            razorpay_order = (
                client.order.create(
                    data=data
                )
            )

        except Exception as e:

            raise RuntimeError(
                "Failed to create Razorpay order: "
                f"{e}"
            )

        if not razorpay_order:

            raise RuntimeError(
                "Razorpay returned an empty "
                "order response"
            )

        # -----------------------------------------------------
        # VALIDATE ORDER ID
        # -----------------------------------------------------

        razorpay_order_id = (
            razorpay_order.get("id")
        )

        if not razorpay_order_id:

            raise RuntimeError(
                "Razorpay response does not "
                "contain an order ID"
            )

        # -----------------------------------------------------
        # VALIDATE AMOUNT
        # -----------------------------------------------------

        returned_amount = (
            razorpay_order.get("amount")
        )

        if returned_amount is None:

            raise RuntimeError(
                "Razorpay response does not "
                "contain an amount"
            )

        try:

            returned_amount = int(
                returned_amount
            )

        except (
            ValueError,
            TypeError,
        ):

            raise RuntimeError(
                "Invalid amount returned "
                "by Razorpay"
            )

        if returned_amount != (
            amount_in_smallest_unit
        ):

            raise RuntimeError(
                "Razorpay returned an amount "
                "different from the requested amount"
            )

        # -----------------------------------------------------
        # VALIDATE CURRENCY
        # -----------------------------------------------------

        returned_currency = str(
            razorpay_order.get(
                "currency",
                "",
            )
        ).upper()

        if returned_currency != currency:

            raise RuntimeError(
                "Razorpay returned a currency "
                "different from the requested currency"
            )

        print(
            "Razorpay Order ID:",
            razorpay_order_id,
        )

        print(
            "Razorpay order created successfully."
        )

        print("=" * 60)
        print()

        return razorpay_order

    # =========================================================
    # FETCH RAZORPAY ORDER
    # =========================================================

    @staticmethod
    def get_order(
        razorpay_order_id: str,
    ) -> Dict[str, Any]:

        if not razorpay_order_id:

            raise ValueError(
                "Razorpay order ID is required"
            )

        razorpay_order_id = str(
            razorpay_order_id
        ).strip()

        if not razorpay_order_id:

            raise ValueError(
                "Razorpay order ID is empty"
            )

        client = (
            RazorpayService.get_client()
        )

        try:

            order = (
                client.order.fetch(
                    razorpay_order_id
                )
            )

        except Exception as e:

            raise RuntimeError(
                "Failed to fetch Razorpay order: "
                f"{e}"
            )

        if not order:

            raise RuntimeError(
                "Razorpay returned an empty "
                "order response"
            )

        return order

    # =========================================================
    # VERIFY CHECKOUT PAYMENT SIGNATURE
    # =========================================================

    @staticmethod
    def verify_payment_signature(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verify Razorpay Checkout payment signature.

        Formula:

            HMAC_SHA256(
                razorpay_order_id + "|" + razorpay_payment_id,
                RAZORPAY_KEY_SECRET
            )
        """

        if not razorpay_order_id:

            raise ValueError(
                "Razorpay order ID is required"
            )

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is required"
            )

        if not razorpay_signature:

            raise ValueError(
                "Razorpay signature is required"
            )

        order_id = str(
            razorpay_order_id
        ).strip()

        payment_id = str(
            razorpay_payment_id
        ).strip()

        signature = str(
            razorpay_signature
        ).strip()

        if not order_id:

            raise ValueError(
                "Razorpay order ID is empty"
            )

        if not payment_id:

            raise ValueError(
                "Razorpay payment ID is empty"
            )

        if not signature:

            raise ValueError(
                "Razorpay signature is empty"
            )

        key_secret = (
            RazorpayService._get_key_secret()
        )

        message = (
            f"{order_id}|{payment_id}"
        )

        generated_signature = hmac.new(
            key_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            generated_signature,
            signature,
        )

    # =========================================================
    # VERIFY WEBHOOK SIGNATURE
    # =========================================================

    @staticmethod
    def verify_webhook_signature(
        webhook_body: Union[bytes, str],
        webhook_signature: str,
    ) -> bool:
        """
        Verify Razorpay webhook signature.

        IMPORTANT:

        webhook_body must be the RAW HTTP request body.

        Do NOT parse and re-serialize JSON before verification.

        Razorpay generates:

            HMAC_SHA256(
                raw_request_body,
                RAZORPAY_WEBHOOK_SECRET
            )

        and sends it through:

            X-Razorpay-Signature
        """

        if webhook_body is None:

            raise ValueError(
                "Webhook body is required"
            )

        if not webhook_signature:

            raise ValueError(
                "Webhook signature is required"
            )

        webhook_signature = str(
            webhook_signature
        ).strip()

        if not webhook_signature:

            raise ValueError(
                "Webhook signature is empty"
            )

        webhook_secret = (
            RazorpayService._get_webhook_secret()
        )

        # -----------------------------------------------------
        # PRESERVE EXACT RAW BODY
        # -----------------------------------------------------

        if isinstance(webhook_body, bytes):

            body_bytes = webhook_body

        elif isinstance(webhook_body, str):

            body_bytes = webhook_body.encode(
                "utf-8"
            )

        else:

            raise ValueError(
                "Webhook body must be bytes or string"
            )

        # -----------------------------------------------------
        # GENERATE EXPECTED SIGNATURE
        # -----------------------------------------------------

        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

        # -----------------------------------------------------
        # CONSTANT-TIME COMPARISON
        # -----------------------------------------------------

        return hmac.compare_digest(
            expected_signature,
            webhook_signature,
        )

    # =========================================================
    # BACKWARD COMPATIBILITY
    # =========================================================

    @staticmethod
    def verify_payment(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:

        return (
            RazorpayService.verify_payment_signature(
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
            )
        )

    # =========================================================
    # FETCH RAZORPAY PAYMENT
    # =========================================================

    @staticmethod
    def get_payment(
        razorpay_payment_id: str,
    ) -> Dict[str, Any]:

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is required"
            )

        razorpay_payment_id = str(
            razorpay_payment_id
        ).strip()

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is empty"
            )

        client = (
            RazorpayService.get_client()
        )

        try:

            payment = (
                client.payment.fetch(
                    razorpay_payment_id
                )
            )

        except Exception as e:

            raise RuntimeError(
                "Failed to fetch Razorpay payment: "
                f"{e}"
            )

        if not payment:

            raise RuntimeError(
                "Razorpay returned an empty "
                "payment response"
            )

        return payment

    # =========================================================
    # CAPTURE PAYMENT
    # =========================================================

    @staticmethod
    def capture_payment(
        razorpay_payment_id: str,
        amount,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """
        Capture an authorized Razorpay payment.
        """

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is required"
            )

        razorpay_payment_id = str(
            razorpay_payment_id
        ).strip()

        currency = (
            RazorpayService._normalize_currency(
                currency
            )
        )

        amount_in_smallest_unit = (
            RazorpayService._amount_to_smallest_unit(
                amount
            )
        )

        client = (
            RazorpayService.get_client()
        )

        try:

            result = (
                client.payment.capture(
                    razorpay_payment_id,
                    amount_in_smallest_unit,
                    {
                        "currency": currency
                    },
                )
            )

        except Exception as e:

            raise RuntimeError(
                "Failed to capture Razorpay payment: "
                f"{e}"
            )

        if not result:

            raise RuntimeError(
                "Razorpay returned an empty "
                "capture response"
            )

        return result

    # =========================================================
    # REFUND PAYMENT
    # =========================================================

    @staticmethod
    def refund_payment(
        razorpay_payment_id: str,
        amount=None,
    ) -> Dict[str, Any]:
        """
        Refund a Razorpay payment.

        amount=None
            -> full refund

        amount=<value>
            -> partial refund
        """

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is required"
            )

        razorpay_payment_id = str(
            razorpay_payment_id
        ).strip()

        if not razorpay_payment_id:

            raise ValueError(
                "Razorpay payment ID is empty"
            )

        client = (
            RazorpayService.get_client()
        )

        # -----------------------------------------------------
        # FULL REFUND
        # -----------------------------------------------------

        if amount is None:

            try:

                refund = (
                    client.payment.refund(
                        razorpay_payment_id
                    )
                )

            except Exception as e:

                raise RuntimeError(
                    "Failed to refund Razorpay payment: "
                    f"{e}"
                )

            if not refund:

                raise RuntimeError(
                    "Razorpay returned an empty "
                    "refund response"
                )

            return refund

        # -----------------------------------------------------
        # PARTIAL REFUND
        # -----------------------------------------------------

        amount_in_smallest_unit = (
            RazorpayService._amount_to_smallest_unit(
                amount
            )
        )

        refund_data = {
            "amount": amount_in_smallest_unit,
        }

        try:

            refund = (
                client.payment.refund(
                    razorpay_payment_id,
                    refund_data,
                )
            )

        except Exception as e:

            raise RuntimeError(
                "Failed to refund Razorpay payment: "
                f"{e}"
            )

        if not refund:

            raise RuntimeError(
                "Razorpay returned an empty "
                "refund response"
            )

        return refund