from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogService:
    """
    Centralized audit logging service for PayPilot.

    IMPORTANT:
    Audit events are idempotent.

    The same logical event will NOT be inserted multiple times
    when the same code path is triggered repeatedly by:

        - Checkout verification
        - Razorpay webhook
        - Retry requests
        - Frontend duplicate requests
        - Payment initialization retries
        - Service-to-service calls

    Logical event identity:

        merchant_id
        order_id
        payment_id
        event_type
        old_status
        new_status

    Campaign events use a campaign-specific event_type suffix such as:

        CAMPAIGN_PROPOSAL_CREATED#5

    because the current AuditLog model does not contain a
    campaign_id column.
    """

    # =========================================================
    # CREATE AUDIT LOG
    # =========================================================

    @staticmethod
    def create_log(
        db: Session,
        *,
        merchant_id: int,
        event_type: str,
        message: str,
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        risk_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        performed_by: Optional[str] = None,
        commit: bool = False,
    ) -> AuditLog:

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if merchant_id is None:
            raise ValueError(
                "merchant_id is required"
            )

        if not event_type:
            raise ValueError(
                "event_type is required"
            )

        if not message:
            raise ValueError(
                "message is required"
            )

        # -----------------------------------------------------
        # NORMALIZE
        # -----------------------------------------------------

        event_type = str(
            event_type
        ).strip()

        message = str(
            message
        ).strip()

        if performed_by is not None:
            performed_by = str(
                performed_by
            ).strip()

        if old_status is not None:
            old_status = str(
                old_status
            ).strip()

        if new_status is not None:
            new_status = str(
                new_status
            ).strip()

        if risk_level is not None:
            risk_level = str(
                risk_level
            ).strip()

        # =====================================================
        # IDEMPOTENCY CHECK
        # =====================================================
        #
        # We consider an audit event duplicate when all of the
        # following are identical:
        #
        #   merchant_id
        #   order_id
        #   payment_id
        #   event_type
        #   old_status
        #   new_status
        #
        # message is intentionally NOT included.
        #
        # Why?
        #
        # The same event may have a slightly different message
        # depending on which service triggered it.
        #
        # Example:
        #
        # PaymentService:
        #     "Payment 10 captured successfully"
        #
        # Webhook:
        #     "Razorpay payment 10 captured"
        #
        # These are still the same logical event.
        #
        # =====================================================

        query = (
            db.query(AuditLog)
            .filter(
                AuditLog.merchant_id == merchant_id,
                AuditLog.event_type == event_type,
            )
        )

        # -----------------------------------------------------
        # ORDER ID
        # -----------------------------------------------------

        if order_id is None:

            query = query.filter(
                AuditLog.order_id.is_(None)
            )

        else:

            query = query.filter(
                AuditLog.order_id == order_id
            )

        # -----------------------------------------------------
        # PAYMENT ID
        # -----------------------------------------------------

        if payment_id is None:

            query = query.filter(
                AuditLog.payment_id.is_(None)
            )

        else:

            query = query.filter(
                AuditLog.payment_id == payment_id
            )

        # -----------------------------------------------------
        # OLD STATUS
        # -----------------------------------------------------

        if old_status is None:

            query = query.filter(
                AuditLog.old_status.is_(None)
            )

        else:

            query = query.filter(
                AuditLog.old_status == old_status
            )

        # -----------------------------------------------------
        # NEW STATUS
        # -----------------------------------------------------

        if new_status is None:

            query = query.filter(
                AuditLog.new_status.is_(None)
            )

        else:

            query = query.filter(
                AuditLog.new_status == new_status
            )

        # -----------------------------------------------------
        # FIND EXISTING EVENT
        # -----------------------------------------------------

        existing_log = (
            query
            .order_by(
                AuditLog.id.desc()
            )
            .first()
        )

        if existing_log:

            # -------------------------------------------------
            # IMPORTANT
            # -------------------------------------------------
            #
            # Do NOT create another audit row.
            #
            # Return the existing row instead.
            #
            # This is what prevents:
            #
            # PAYMENT_CAPTURED
            # PAYMENT_CAPTURED
            # PAYMENT_CAPTURED
            # PAYMENT_CAPTURED
            #
            # -------------------------------------------------

            return existing_log

        # =====================================================
        # CREATE NEW AUDIT LOG
        # =====================================================

        audit_log = AuditLog(
            merchant_id=merchant_id,
            order_id=order_id,
            payment_id=payment_id,
            event_type=event_type,
            message=message,
            old_status=old_status,
            new_status=new_status,
            risk_score=risk_score,
            risk_level=risk_level,
            performed_by=performed_by,
        )

        # -----------------------------------------------------
        # SAVE
        # -----------------------------------------------------

        db.add(audit_log)

        db.flush()

        # -----------------------------------------------------
        # OPTIONAL COMMIT
        # -----------------------------------------------------

        if commit:

            db.commit()

            db.refresh(
                audit_log
            )

        return audit_log

    # =========================================================
    # ORDER STATUS CHANGE
    # =========================================================

    @staticmethod
    def log_status_change(
        db: Session,
        *,
        merchant_id: int,
        order_id: int,
        event_type: str,
        old_status: Optional[str],
        new_status: Optional[str],
        message: str,
        payment_id: Optional[int] = None,
        performed_by: Optional[str] = "SYSTEM",
        risk_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        commit: bool = False,
    ) -> AuditLog:

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            order_id=order_id,
            payment_id=payment_id,
            event_type=event_type,
            message=message,
            old_status=old_status,
            new_status=new_status,
            risk_score=risk_score,
            risk_level=risk_level,
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # PAYMENT EVENT
    # =========================================================

    @staticmethod
    def log_payment_event(
        db: Session,
        *,
        merchant_id: int,
        order_id: int,
        payment_id: Optional[int],
        event_type: str,
        message: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        risk_score: Optional[float] = None,
        risk_level: Optional[str] = None,
        performed_by: Optional[str] = "SYSTEM",
        commit: bool = False,
    ) -> AuditLog:

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            order_id=order_id,
            payment_id=payment_id,
            event_type=event_type,
            message=message,
            old_status=old_status,
            new_status=new_status,
            risk_score=risk_score,
            risk_level=risk_level,
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # RISK EVENT
    # =========================================================

    @staticmethod
    def log_risk_event(
        db: Session,
        *,
        merchant_id: int,
        order_id: int,
        event_type: str,
        message: str,
        risk_score: Optional[float],
        risk_level: Optional[str],
        payment_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        performed_by: Optional[str] = "AI_RISK_ENGINE",
        commit: bool = False,
    ) -> AuditLog:

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            order_id=order_id,
            payment_id=payment_id,
            event_type=event_type,
            message=message,
            old_status=old_status,
            new_status=new_status,
            risk_score=risk_score,
            risk_level=risk_level,
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # CAMPAIGN ORCHESTRATOR EVENTS
    # =========================================================

    @staticmethod
    def _campaign_event_type(
        campaign_id: int,
        event_name: str,
    ) -> str:
        """
        Build a campaign-specific event type without changing
        the existing AuditLog database model.

        The current audit model does not have a campaign_id
        column.

        Therefore campaign id is embedded in event_type.

        Example:

            CAMPAIGN_PROPOSAL_CREATED#5

        This prevents campaign #5 and campaign #6 from being
        treated as duplicate audit events.
        """

        return (
            f"CAMPAIGN_{str(event_name).strip().upper()}"
            f"#{int(campaign_id)}"
        )

    # =========================================================
    # CAMPAIGN PHASE 1
    # PROPOSAL CREATED
    # =========================================================

    @staticmethod
    def log_campaign_proposal_created(
        db: Session,
        *,
        merchant_id: int,
        campaign_id: int,
        campaign_name: Optional[str] = None,
        performed_by: Optional[str] = "PAYPILOT_AI_AGENT",
        commit: bool = False,
    ) -> AuditLog:
        """
        Record Phase 1 campaign proposal creation.

        No money movement occurs here.
        No product price is changed.
        No inventory is changed.
        No order is changed.
        No payment is created.
        """

        name = (
            str(campaign_name).strip()
            if campaign_name
            else f"Campaign #{campaign_id}"
        )

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            event_type=AuditLogService._campaign_event_type(
                campaign_id,
                "PROPOSAL_CREATED",
            ),
            message=(
                f"Campaign #{campaign_id} ({name}) "
                "proposal created. "
                "Phase 1 is proposal-only; no price, "
                "inventory, order, or payment was changed."
            ),
            old_status=None,
            new_status="DRAFT",
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # CAMPAIGN PHASE 2
    # POLICY + MARGIN VALIDATION
    # =========================================================

    @staticmethod
    def log_campaign_validation(
        db: Session,
        *,
        merchant_id: int,
        campaign_id: int,
        campaign_name: Optional[str] = None,
        passed: bool,
        message: str,
        performed_by: Optional[str] = "PAYPILOT_AI_AGENT",
        commit: bool = False,
    ) -> AuditLog:
        """
        Record Phase 2 policy and margin validation.

        passed=True:
            POLICY_APPROVED

        passed=False:
            POLICY_REJECTED
        """

        name = (
            str(campaign_name).strip()
            if campaign_name
            else f"Campaign #{campaign_id}"
        )

        status = (
            "POLICY_APPROVED"
            if passed
            else "POLICY_REJECTED"
        )

        event_name = (
            "POLICY_VALIDATED"
            if passed
            else "POLICY_REJECTED"
        )

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            event_type=AuditLogService._campaign_event_type(
                campaign_id,
                event_name,
            ),
            message=(
                f"Campaign #{campaign_id} ({name}) "
                f"Phase 2 validation: {message}"
            ),
            old_status="DRAFT",
            new_status=status,
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # CAMPAIGN PHASE 3
    # MERCHANT APPROVAL / REJECTION
    # =========================================================

    @staticmethod
    def log_campaign_merchant_approval(
        db: Session,
        *,
        merchant_id: int,
        campaign_id: int,
        campaign_name: Optional[str] = None,
        approved: bool,
        message: str,
        performed_by: Optional[str] = "MERCHANT",
        commit: bool = False,
    ) -> AuditLog:
        """
        Record Phase 3 merchant authorization.

        This does NOT activate the campaign.
        """

        name = (
            str(campaign_name).strip()
            if campaign_name
            else f"Campaign #{campaign_id}"
        )

        new_status = (
            "MERCHANT_APPROVED"
            if approved
            else "MERCHANT_REJECTED"
        )

        event_name = (
            "MERCHANT_APPROVED"
            if approved
            else "MERCHANT_REJECTED"
        )

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            event_type=AuditLogService._campaign_event_type(
                campaign_id,
                event_name,
            ),
            message=(
                f"Campaign #{campaign_id} ({name}) "
                f"merchant decision: {message}"
            ),
            old_status="POLICY_APPROVED",
            new_status=new_status,
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # CAMPAIGN PHASE 4
    # ACTIVATION
    # =========================================================

    @staticmethod
    def log_campaign_activation(
        db: Session,
        *,
        merchant_id: int,
        campaign_id: int,
        campaign_name: Optional[str] = None,
        message: str,
        performed_by: Optional[str] = "MERCHANT",
        commit: bool = False,
    ) -> AuditLog:
        """
        Record Phase 4 explicit campaign activation.

        This should be called only after the backend has
        successfully completed the activation operation.
        """

        name = (
            str(campaign_name).strip()
            if campaign_name
            else f"Campaign #{campaign_id}"
        )

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            event_type=AuditLogService._campaign_event_type(
                campaign_id,
                "ACTIVATED",
            ),
            message=(
                f"Campaign #{campaign_id} ({name}) "
                f"activation: {message}"
            ),
            old_status="MERCHANT_APPROVED",
            new_status="ACTIVE",
            performed_by=performed_by,
            commit=commit,
        )

    # =========================================================
    # WEBHOOK EVENT
    # =========================================================

    @staticmethod
    def log_webhook_event(
        db: Session,
        *,
        merchant_id: int,
        order_id: Optional[int],
        event_type: str,
        message: str,
        payment_id: Optional[int] = None,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        performed_by: Optional[str] = "RAZORPAY_WEBHOOK",
        commit: bool = False,
    ) -> AuditLog:

        return AuditLogService.create_log(
            db=db,
            merchant_id=merchant_id,
            order_id=order_id,
            payment_id=payment_id,
            event_type=event_type,
            message=message,
            old_status=old_status,
            new_status=new_status,
            performed_by=performed_by,
            commit=commit,
        )