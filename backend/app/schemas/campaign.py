from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class CampaignProposalCreate(BaseModel):
    """Merchant intent for Phase 1 proposal generation."""

    brief: str = Field(min_length=5, max_length=2000)
    campaign_name: str | None = Field(default=None, max_length=160)
    product_ids: list[int] = Field(default_factory=list, max_length=20)
    suggested_discount_percent: float = Field(default=0, ge=0, le=100)


class CampaignProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: int
    name: str
    objective: str
    brief: str
    strategy_type: str
    status: str
    suggested_discount_percent: float
    product_ids: list[int]
    proposed_actions: list[dict[str, Any]]
    governance: dict[str, Any]
    explanation: str
    created_at: datetime
    updated_at: datetime


class CampaignListResponse(BaseModel):
    campaigns: list[CampaignProposalResponse]
    total: int
