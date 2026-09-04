class AIService:
    """
    Explainable AI helper for PayPilot.

    This service converts transaction information
    into human-readable risk factors.
    """

    @staticmethod
    def generate_explanation(
        quantity: int,
        requested_discount_percent: float,
        risk_score: float,
        risk_level: str,
        risk_reasons=None,
    ):
        factors = []

        # ---------------------------------------------
        # Quantity risk
        # ---------------------------------------------

        if quantity >= 10:
            factors.append({
                "factor": "High Order Quantity",
                "value": quantity,
                "impact": "HIGH",
                "reason": (
                    "Large order quantities can increase "
                    "transaction and fraud risk."
                ),
            })

        elif quantity >= 5:
            factors.append({
                "factor": "Elevated Order Quantity",
                "value": quantity,
                "impact": "MEDIUM",
                "reason": (
                    "The order quantity is higher than "
                    "a typical small transaction."
                ),
            })

        else:
            factors.append({
                "factor": "Normal Order Quantity",
                "value": quantity,
                "impact": "LOW",
                "reason": (
                    "The requested quantity is within "
                    "a normal transaction range."
                ),
            })

        # ---------------------------------------------
        # Discount risk
        # ---------------------------------------------

        if requested_discount_percent >= 20:
            factors.append({
                "factor": "Very High Discount",
                "value": requested_discount_percent,
                "impact": "HIGH",
                "reason": (
                    "A very large discount can indicate "
                    "unusual transaction behavior."
                ),
            })

        elif requested_discount_percent >= 10:
            factors.append({
                "factor": "High Discount",
                "value": requested_discount_percent,
                "impact": "MEDIUM",
                "reason": (
                    "The requested discount is above "
                    "the normal discount threshold."
                ),
            })

        else:
            factors.append({
                "factor": "Normal Discount",
                "value": requested_discount_percent,
                "impact": "LOW",
                "reason": (
                    "The requested discount is within "
                    "the normal range."
                ),
            })

        # ---------------------------------------------
        # Workflow risk reasons
        # ---------------------------------------------

        if isinstance(risk_reasons, list):

            for reason in risk_reasons:

                if not str(reason).strip():
                    continue

                factors.append({
                    "factor": "AI Risk Signal",
                    "value": str(reason),
                    "impact": risk_level,
                    "reason": str(reason),
                })

        elif risk_reasons:

            factors.append({
                "factor": "AI Risk Signal",
                "value": str(risk_reasons),
                "impact": risk_level,
                "reason": str(risk_reasons),
            })

        # ---------------------------------------------
        # Overall explanation
        # ---------------------------------------------

        if risk_level == "CRITICAL":
            summary = (
                "This transaction was classified as critical "
                "risk and requires immediate attention."
            )

        elif risk_level == "HIGH":
            summary = (
                "This transaction was classified as high risk "
                "because multiple risk signals were detected."
            )

        elif risk_level == "MEDIUM":
            summary = (
                "This transaction contains moderate risk signals "
                "and may require additional verification."
            )

        else:
            summary = (
                "This transaction appears to have a low risk "
                "based on the available transaction signals."
            )

        return {
            "summary": summary,
            "factors": factors,
            "risk_score": float(risk_score),
            "risk_level": risk_level,
        }