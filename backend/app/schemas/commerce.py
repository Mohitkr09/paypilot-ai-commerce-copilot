from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =========================================================
# COMMERCE AGENT REQUEST
# =========================================================

class CommerceAgentRequest(BaseModel):
    """
    Request sent by the frontend/customer to the
    AI Commerce Agent.
    """

    message: str = Field(
        ...,
        min_length=1,
        description="Customer's natural language request",
    )

    merchant_id: Optional[int] = Field(
        default=1,
        description="Merchant for which the agent is operating",
    )

    customer_id: Optional[int] = Field(
        default=None,
        description="Optional customer identifier",
    )

    session_id: Optional[str] = Field(
        default=None,
        description="Conversation/session identifier",
    )


# =========================================================
# PRODUCT RESULT
# =========================================================

class CommerceProductResponse(BaseModel):
    """
    Product returned by the Commerce Agent.
    """

    id: int

    name: str

    description: Optional[str] = None

    price: Optional[float] = None

    currency: str = "INR"

    category: Optional[str] = None

    stock: Optional[int] = None

    available: bool = True

    score: Optional[float] = None


# =========================================================
# AGENT ACTION
# =========================================================

class CommerceAgentAction(BaseModel):
    """
    Action recommended or executed by the AI Commerce Agent.
    """

    action: str

    status: str = "suggested"

    data: Dict[str, Any] = Field(
        default_factory=dict
    )


# =========================================================
# COMMERCE AGENT RESPONSE
# =========================================================

class CommerceAgentResponse(BaseModel):
    """
    Final response returned by the AI Commerce Agent.
    """

    message: str

    intent: Optional[str] = None

    products: List[CommerceProductResponse] = Field(
        default_factory=list
    )

    actions: List[CommerceAgentAction] = Field(
        default_factory=list
    )

    session_id: Optional[str] = None

    success: bool = True

    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )


# =========================================================
# PRODUCT SEARCH REQUEST
# =========================================================

class CommerceProductSearchRequest(BaseModel):
    """
    Structured product-search request.
    """

    query: str = Field(
        ...,
        min_length=1,
    )

    merchant_id: Optional[int] = 1

    category: Optional[str] = None

    min_price: Optional[float] = None

    max_price: Optional[float] = None

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
    )


# =========================================================
# PRODUCT SEARCH RESPONSE
# =========================================================

class CommerceProductSearchResponse(BaseModel):

    products: List[CommerceProductResponse] = Field(
        default_factory=list
    )

    query: str

    total: int

    success: bool = True