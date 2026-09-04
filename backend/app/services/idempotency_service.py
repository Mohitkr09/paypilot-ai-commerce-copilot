import hashlib
import json
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.idempotency import IdempotencyKey


class IdempotencyService:

    # =========================================================
    # CONSTANTS
    # =========================================================

    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    # =========================================================
    # NORMALIZE REQUEST
    # =========================================================

    @staticmethod
    def normalize_payload(
        payload: Any,
    ) -> str:
        """
        Convert request data into a deterministic JSON string.

        The same logical request must always generate the same
        string and therefore the same SHA-256 hash.
        """

        if payload is None:
            payload = {}

        if hasattr(
            payload,
            "model_dump",
        ):
            payload = payload.model_dump(
                mode="json"
            )

        elif hasattr(
            payload,
            "dict",
        ):
            payload = payload.dict()

        elif not isinstance(
            payload,
            (dict, list, tuple, str, int, float, bool),
        ):
            payload = str(payload)

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    # =========================================================
    # REQUEST HASH
    # =========================================================

    @staticmethod
    def generate_request_hash(
        payload: Any,
    ) -> str:
        """
        Generate SHA-256 hash for request payload.
        """

        normalized = (
            IdempotencyService
            .normalize_payload(payload)
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    # =========================================================
    # VALIDATE KEY
    # =========================================================

    @staticmethod
    def validate_key(
        key: Optional[str],
    ) -> str:
        """
        Validate and normalize an idempotency key.
        """

        if key is None:
            raise ValueError(
                "Idempotency-Key is required"
            )

        key = str(key).strip()

        if not key:
            raise ValueError(
                "Idempotency-Key cannot be empty"
            )

        if len(key) > 255:
            raise ValueError(
                "Idempotency-Key cannot exceed 255 characters"
            )

        return key

    # =========================================================
    # FIND EXISTING KEY
    # =========================================================

    @staticmethod
    def get_existing(
        db: Session,
        *,
        merchant_id: int,
        operation: str,
        key: str,
    ) -> Optional[IdempotencyKey]:
        """
        Find an existing idempotency record.
        """

        key = (
            IdempotencyService
            .validate_key(key)
        )

        operation = str(
            operation or ""
        ).strip().upper()

        if not operation:
            raise ValueError(
                "Idempotency operation is required"
            )

        return (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.merchant_id
                == merchant_id,

                IdempotencyKey.operation
                == operation,

                IdempotencyKey.key
                == key,
            )
            .first()
        )

    # =========================================================
    # START REQUEST
    # =========================================================

    @staticmethod
    def start(
        db: Session,
        *,
        merchant_id: int,
        operation: str,
        key: str,
        request_payload: Any,
    ) -> tuple[IdempotencyKey, bool]:
        """
        Start an idempotent operation.

        Returns:

            (record, True)
                -> newly created request

            (record, False)
                -> existing request

        Important:

        The unique database constraint protects us from two
        concurrent requests trying to create the same key.
        """

        key = (
            IdempotencyService
            .validate_key(key)
        )

        operation = str(
            operation or ""
        ).strip().upper()

        if not operation:
            raise ValueError(
                "Idempotency operation is required"
            )

        request_hash = (
            IdempotencyService
            .generate_request_hash(
                request_payload
            )
        )

        # -----------------------------------------------------
        # CHECK EXISTING
        # -----------------------------------------------------

        existing = (
            IdempotencyService.get_existing(
                db=db,
                merchant_id=merchant_id,
                operation=operation,
                key=key,
            )
        )

        if existing:

            IdempotencyService.ensure_same_request(
                existing=existing,
                request_hash=request_hash,
            )

            return existing, False

        # -----------------------------------------------------
        # CREATE NEW RECORD
        # -----------------------------------------------------

        record = IdempotencyKey(
            merchant_id=merchant_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
            status=(
                IdempotencyService.PROCESSING
            ),
        )

        db.add(record)

        try:

            db.flush()

            return record, True

        except IntegrityError:

            # -------------------------------------------------
            # CONCURRENT REQUEST
            # -------------------------------------------------
            #
            # Another transaction may have inserted the same
            # key between our SELECT and INSERT.
            #
            # Roll back the failed INSERT transaction and
            # retrieve the already-created record.
            #
            # -------------------------------------------------

            db.rollback()

            existing = (
                IdempotencyService.get_existing(
                    db=db,
                    merchant_id=merchant_id,
                    operation=operation,
                    key=key,
                )
            )

            if not existing:

                raise

            IdempotencyService.ensure_same_request(
                existing=existing,
                request_hash=request_hash,
            )

            return existing, False

    # =========================================================
    # VERIFY SAME REQUEST
    # =========================================================

    @staticmethod
    def ensure_same_request(
        *,
        existing: IdempotencyKey,
        request_hash: str,
    ) -> None:
        """
        Prevent the same idempotency key from being reused
        with a different request body.
        """

        if (
            existing.request_hash
            != request_hash
        ):

            raise ValueError(
                "Idempotency-Key has already "
                "been used with a different request"
            )

    # =========================================================
    # CHECK COMPLETED
    # =========================================================

    @staticmethod
    def is_completed(
        record: IdempotencyKey,
    ) -> bool:

        return (
            record.status
            == IdempotencyService.COMPLETED
        )

    # =========================================================
    # CHECK PROCESSING
    # =========================================================

    @staticmethod
    def is_processing(
        record: IdempotencyKey,
    ) -> bool:

        return (
            record.status
            == IdempotencyService.PROCESSING
        )

    # =========================================================
    # CHECK FAILED
    # =========================================================

    @staticmethod
    def is_failed(
        record: IdempotencyKey,
    ) -> bool:

        return (
            record.status
            == IdempotencyService.FAILED
        )

    # =========================================================
    # SAVE SUCCESS RESPONSE
    # =========================================================

    @staticmethod
    def complete(
        db: Session,
        *,
        record: IdempotencyKey,
        response_body: Any,
        status_code: int = 200,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
    ) -> IdempotencyKey:
        """
        Mark an idempotent request as completed and store
        the response that can be replayed on duplicate requests.
        """

        record.status = (
            IdempotencyService.COMPLETED
        )

        record.response_status_code = (
            int(status_code)
        )

        record.response_body = (
            IdempotencyService.serialize_response(
                response_body
            )
        )

        record.error_message = None

        if resource_type is not None:

            record.resource_type = str(
                resource_type
            ).upper()

        if resource_id is not None:

            record.resource_id = int(
                resource_id
            )

        db.flush()

        return record

    # =========================================================
    # SAVE FAILURE
    # =========================================================

    @staticmethod
    def fail(
        db: Session,
        *,
        record: IdempotencyKey,
        error_message: str,
        status_code: int = 500,
    ) -> IdempotencyKey:
        """
        Mark request as failed.

        We keep the record so the request history remains
        visible and the same key cannot silently create
        another resource.
        """

        record.status = (
            IdempotencyService.FAILED
        )

        record.response_status_code = (
            int(status_code)
        )

        record.error_message = str(
            error_message
        )

        db.flush()

        return record

    # =========================================================
    # SERIALIZE RESPONSE
    # =========================================================

    @staticmethod
    def serialize_response(
        response_body: Any,
    ) -> str:
        """
        Convert response data to JSON text.
        """

        if response_body is None:
            response_body = {}

        if hasattr(
            response_body,
            "model_dump",
        ):

            response_body = (
                response_body.model_dump(
                    mode="json"
                )
            )

        elif hasattr(
            response_body,
            "dict",
        ):

            response_body = (
                response_body.dict()
            )

        return json.dumps(
            response_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    # =========================================================
    # DESERIALIZE RESPONSE
    # =========================================================

    @staticmethod
    def deserialize_response(
        record: IdempotencyKey,
    ) -> Any:
        """
        Convert stored response JSON back into Python data.
        """

        if not record.response_body:

            return None

        try:

            return json.loads(
                record.response_body
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):

            return record.response_body

    # =========================================================
    # REPLAY RESPONSE
    # =========================================================

    @staticmethod
    def replay(
        record: IdempotencyKey,
    ) -> dict:
        """
        Return the previously stored response information.

        The route can use this to return exactly the same
        business result without creating another order/payment.
        """

        if not IdempotencyService.is_completed(
            record
        ):

            raise ValueError(
                "Idempotency record is not completed"
            )

        return {
            "status_code": (
                record.response_status_code
                or 200
            ),
            "body": (
                IdempotencyService
                .deserialize_response(
                    record
                )
            ),
            "resource_type": (
                record.resource_type
            ),
            "resource_id": (
                record.resource_id
            ),
        }

    # =========================================================
    # RESET PROCESSING
    # =========================================================

    @staticmethod
    def reset_processing(
        db: Session,
        *,
        record: IdempotencyKey,
    ) -> IdempotencyKey:
        """
        Reset a PROCESSING record.

        Useful during development/testing when an operation
        was interrupted before completion.

        Production retry/recovery logic should be handled
        carefully before using this automatically.
        """

        if not IdempotencyService.is_processing(
            record
        ):

            return record

        record.status = (
            IdempotencyService.PROCESSING
        )

        record.error_message = None
        record.response_body = None
        record.response_status_code = None
        record.resource_type = None
        record.resource_id = None

        db.flush()

        return record