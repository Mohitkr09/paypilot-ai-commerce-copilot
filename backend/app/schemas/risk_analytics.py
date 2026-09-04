from pydantic import BaseModel


class RiskDistribution(BaseModel):
    LOW: int = 0
    MEDIUM: int = 0
    HIGH: int = 0


class RiskAnalyticsSummary(BaseModel):
    total_orders: int

    approved_orders: int
    rejected_orders: int
    manual_review_orders: int

    average_risk_score: float

    approval_rate: float
    rejection_rate: float
    manual_review_rate: float

    risk_distribution: RiskDistribution