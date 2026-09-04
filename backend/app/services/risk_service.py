from typing import Dict, Any


class RiskService:
    """
    Service responsible for evaluating transaction risk.

    Uses deterministic and explainable business rules.

    Inputs:
        quantity
        discount_percent
        final_amount

    Outputs:
        risk_score
        risk_level
        risk_reason
        decision
    """

    # =========================================================
    # RISK LEVEL CONSTANTS
    # =========================================================

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    # =========================================================
    # DECISION CONSTANTS
    # =========================================================

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"

    # =========================================================
    # MAIN RISK CALCULATION
    # =========================================================

    @staticmethod
    def calculate_risk(
        quantity: int,
        discount_percent: float,
        final_amount: float,
    ) -> Dict[str, Any]:
        """
        Calculate transaction risk using deterministic
        and explainable business rules.

        Returns:
            {
                "risk_score": int,
                "risk_level": str,
                "risk_reason": str,
                "decision": str
            }
        """

        # =====================================================
        # VALIDATION
        # =====================================================

        if quantity is None:
            raise ValueError(
                "Quantity is required for risk evaluation."
            )

        if discount_percent is None:
            raise ValueError(
                "Discount percentage is required "
                "for risk evaluation."
            )

        if final_amount is None:
            raise ValueError(
                "Final amount is required for risk evaluation."
            )

        # =====================================================
        # SAFE CONVERSION
        # =====================================================

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError(
                "Quantity must be a valid integer."
            )

        try:
            discount_percent = float(discount_percent)
        except (TypeError, ValueError):
            raise ValueError(
                "Discount percentage must be a valid number."
            )

        try:
            final_amount = float(final_amount)
        except (TypeError, ValueError):
            raise ValueError(
                "Final amount must be a valid number."
            )

        # =====================================================
        # BASIC VALIDATION
        # =====================================================

        if quantity <= 0:
            raise ValueError(
                "Quantity must be greater than zero."
            )

        if discount_percent < 0:
            raise ValueError(
                "Discount percentage cannot be negative."
            )

        if discount_percent > 100:
            raise ValueError(
                "Discount percentage cannot exceed 100."
            )

        if final_amount < 0:
            raise ValueError(
                "Final amount cannot be negative."
            )

        # =====================================================
        # INITIALIZE
        # =====================================================

        risk_score = 0
        reasons = []

        # =====================================================
        # DISCOUNT RISK
        # =====================================================

        if discount_percent >= 30:

            risk_score += 40

            reasons.append(
                "Very high discount percentage"
            )

        elif discount_percent >= 20:

            risk_score += 30

            reasons.append(
                "High discount percentage"
            )

        elif discount_percent >= 10:

            risk_score += 15

            reasons.append(
                "Elevated discount percentage"
            )

        # =====================================================
        # QUANTITY RISK
        # =====================================================

        if quantity >= 20:

            risk_score += 30

            reasons.append(
                "Unusually large order quantity"
            )

        elif quantity >= 10:

            risk_score += 20

            reasons.append(
                "High order quantity"
            )

        elif quantity >= 5:

            risk_score += 10

            reasons.append(
                "Above-normal order quantity"
            )

        # =====================================================
        # TRANSACTION VALUE RISK
        # =====================================================

        if final_amount >= 50000:

            risk_score += 30

            reasons.append(
                "Very high transaction value"
            )

        elif final_amount >= 25000:

            risk_score += 20

            reasons.append(
                "High transaction value"
            )

        elif final_amount >= 10000:

            risk_score += 10

            reasons.append(
                "Elevated transaction value"
            )

        # =====================================================
        # LIMIT SCORE
        # =====================================================

        risk_score = min(risk_score, 100)

        # =====================================================
        # DETERMINE RISK LEVEL
        # =====================================================

        if risk_score >= 80:

            risk_level = RiskService.CRITICAL

        elif risk_score >= 60:

            risk_level = RiskService.HIGH

        elif risk_score >= 30:

            risk_level = RiskService.MEDIUM

        else:

            risk_level = RiskService.LOW

        # =====================================================
        # RISK REASON
        # =====================================================

        if reasons:

            risk_reason = "; ".join(reasons)

        else:

            risk_reason = (
                "No significant risk factors detected"
            )

        # =====================================================
        # BUSINESS DECISION
        # =====================================================

        decision = RiskService.get_decision(
            risk_level=risk_level
        )

        # =====================================================
        # RETURN
        # =====================================================

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "decision": decision,
        }

    # =========================================================
    # RISK LEVEL → BUSINESS DECISION
    # =========================================================

    @staticmethod
    def get_decision(
        risk_level: str,
    ) -> str:
        """
        Convert risk level into business decision.

        LOW       -> APPROVE
        MEDIUM    -> REVIEW
        HIGH      -> REVIEW
        CRITICAL  -> BLOCK
        """

        risk_level = (
            str(risk_level)
            .upper()
            .strip()
        )

        if risk_level == RiskService.LOW:
            return RiskService.APPROVE

        if risk_level == RiskService.MEDIUM:
            return RiskService.REVIEW

        if risk_level == RiskService.HIGH:
            return RiskService.REVIEW

        if risk_level == RiskService.CRITICAL:
            return RiskService.BLOCK

        raise ValueError(
            f"Unknown risk level: {risk_level}"
        )

    # =========================================================
    # HUMAN-READABLE SUMMARY
    # =========================================================

    @staticmethod
    def build_summary(
        risk_score: int,
        risk_level: str,
        risk_reason: str,
        decision: str,
    ) -> str:
        """
        Build a human-readable risk explanation.
        """

        return (
            f"Risk score: {risk_score}/100. "
            f"Risk level: {risk_level}. "
            f"Decision: {decision}. "
            f"Reason: {risk_reason}."
        )