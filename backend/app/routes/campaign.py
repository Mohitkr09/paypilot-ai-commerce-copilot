from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.auth.dependencies import get_current_merchant

from app.models.campaign import Campaign

from app.schemas.campaign import (
    CampaignProposalCreate, 
    CampaignProposalResponse,
    CampaignListResponse,
)

from app.services.campaign_service import (
    CampaignOrchestratorService,
)
from app.services.audit_log_service import AuditLogService


# ============================================================
# ROUTEs
# ============================================================

router = APIRouter(
    prefix="/campaigns",
    tags=["Campaign Orchestrator"],
)


# ============================================================
# CAMPAIGN AUDIT HELPER
# ============================================================


def _safe_campaign_audit(
    db: Session,
    *,
    merchant_id: int,
    event: str,
    campaign,
    message: str,
    passed: bool | None = None,
    performed_by: str = "PAYPILOT_AI_AGENT",
):
    """
    Write a campaign lifecycle audit event without allowing an
    audit-write failure to break an already-completed campaign action.

    The centralized AuditLogService provides idempotency, so repeated
    frontend requests do not create duplicate logical campaign events.
    """

    try:
        campaign_id = int(campaign.id)
        campaign_name = str(
            getattr(campaign, "name", "") or f"Campaign #{campaign_id}"
        )

        if event == "PROPOSAL_CREATED":
            AuditLogService.log_campaign_proposal_created(
                db,
                merchant_id=merchant_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                performed_by=performed_by,
                commit=True,
            )
            return

        if event == "POLICY_VALIDATED":
            AuditLogService.log_campaign_validation(
                db,
                merchant_id=merchant_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                passed=bool(passed),
                message=message,
                performed_by=performed_by,
                commit=True,
            )
            return

        if event == "MERCHANT_APPROVED":
            AuditLogService.log_campaign_merchant_approval(
                db,
                merchant_id=merchant_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                approved=True,
                message=message,
                performed_by="MERCHANT",
                commit=True,
            )
            return

        if event == "MERCHANT_REJECTED":
            AuditLogService.log_campaign_merchant_approval(
                db,
                merchant_id=merchant_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                approved=False,
                message=message,
                performed_by="MERCHANT",
                commit=True,
            )
            return

        if event == "ACTIVATED":
            AuditLogService.log_campaign_activation(
                db,
                merchant_id=merchant_id,
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                message=message,
                performed_by="MERCHANT",
                commit=True,
            )
            return

    except Exception as audit_error:
        # The campaign operation has already completed successfully.
        # Never convert that success into a 500 just because audit
        # persistence failed. The failure is visible in server logs.
        db.rollback()
        print(
            "CAMPAIGN AUDIT LOGGING FAILED:",
            audit_error,
        )


# ============================================================
# PHASE 1
# CREATE CAMPAIGN PROPOSAL
# ============================================================

@router.post(
    "/proposals",
    response_model=CampaignProposalResponse,
    status_code=201,
)
def create_campaign_proposal(
    request: CampaignProposalCreate,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Phase 1:
    Generate and persist a campaign proposal.

    This endpoint does NOT:

    - activate the campaign
    - modify product prices
    - modify inventory
    - modify orders
    - create payments
    - move money
    - publish the campaign

    It only creates the proposal.

    Result:

        status = DRAFT
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.build_proposal(
        db=db,
        merchant_id=merchant_id,
        request=request,
    )

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="PROPOSAL_CREATED",
        campaign=campaign,
        message="Phase 1 campaign proposal created.",
    )

    return campaign


# ============================================================
# PHASE 1
# GET ALL CAMPAIGN PROPOSALS
# ============================================================

@router.get(
    "/proposals",
    response_model=CampaignListResponse,
)
def get_campaign_proposals(
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Return all campaign proposals belonging to
    the currently authenticated merchant.
    """

    merchant_id = int(current_merchant.id)

    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.merchant_id == merchant_id
        )
        .order_by(
            Campaign.created_at.desc()
        )
        .all()
    )

    return {
        "campaigns": campaigns,
        "total": len(campaigns),
    }


# ============================================================
# PHASE 2
# VALIDATE POLICY + MARGIN
# ============================================================

@router.post(
    "/proposals/{proposal_id}/validate",
    response_model=CampaignProposalResponse,
)
def validate_campaign_proposal(
    proposal_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Phase 2:

    Validate a campaign proposal against:

    1. Merchant maximum discount policy
    2. Product minimum margin requirement
    3. Product availability
    4. Product price/cost validity

    IMPORTANT:

    This endpoint does NOT:

    - change product price
    - apply the discount
    - modify inventory
    - modify orders
    - create payments
    - activate the campaign
    - publish the campaign

    It only validates the proposal and stores
    the validation result.

    Successful result:

        status = POLICY_APPROVED

    Failed result:

        status = POLICY_REJECTED
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.validate_proposal(
        db=db,
        merchant_id=merchant_id,
        campaign_id=proposal_id,
    )

    governance = campaign.governance if isinstance(campaign.governance, dict) else {}
    validation_passed = bool(governance.get("validation_passed", False))
    validation_message = str(
        governance.get("validation_message")
        or (
            "Policy and margin validation passed."
            if validation_passed
            else "Policy and margin validation failed."
        )
    )

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="POLICY_VALIDATED",
        campaign=campaign,
        passed=validation_passed,
        message=validation_message,
    )

    return campaign


# ============================================================
# PHASE 3
# MERCHANT APPROVAL
# ============================================================

@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=CampaignProposalResponse,
)
def approve_campaign_proposal(
    proposal_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Phase 3:

    Merchant approves a campaign proposal after
    successful Phase 2 policy and margin validation.

    A proposal can only be approved when its status is:

        POLICY_APPROVED

    This endpoint:

    - records merchant approval
    - changes campaign status to MERCHANT_APPROVED
    - marks the campaign as ready for activation
    - sets activation_status = PENDING
    - sets can_activate = True
    - updates governance information

    IMPORTANT:

    THIS ENDPOINT DOES NOT ACTIVATE THE CAMPAIGN.

    It does NOT:

    - change product prices
    - apply discounts
    - modify inventory
    - modify orders
    - create payments
    - move money
    - publish the campaign

    Actual campaign activation happens only through:

        POST /campaigns/proposals/{proposal_id}/activate
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.approve_proposal(
        db=db,
        merchant_id=merchant_id,
        campaign_id=proposal_id,
    )

    governance = campaign.governance if isinstance(campaign.governance, dict) else {}
    approved_discount = float(
        governance.get("approved_discount_percent", 0) or 0
    )

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="MERCHANT_APPROVED",
        campaign=campaign,
        message=(
            "Merchant approval recorded successfully. "
            f"Approved discount: {approved_discount:.2f}%. "
            "The campaign is authorized for Phase 4 activation; "
            "approval itself does not change products, inventory, "
            "orders, or payments."
        ),
        performed_by="MERCHANT",
    )

    return campaign


# ============================================================
# PHASE 3
# MERCHANT REJECTION
# ============================================================

@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=CampaignProposalResponse,
)
def reject_campaign_proposal(
    proposal_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Phase 3:

    Merchant rejects a campaign proposal after
    Phase 2 validation.

    A proposal can only be rejected from:

        POLICY_APPROVED

    This endpoint:

    - records merchant rejection
    - changes campaign status to MERCHANT_REJECTED
    - prevents activation
    - updates governance information

    IMPORTANT:

    No product price, inventory, order, or payment
    is changed.
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.reject_proposal(
        db=db,
        merchant_id=merchant_id,
        campaign_id=proposal_id,
    )

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="MERCHANT_REJECTED",
        campaign=campaign,
        message=(
            "Merchant rejected the campaign proposal. "
            "The campaign cannot proceed to activation and no "
            "product price, inventory, order, or payment was changed."
        ),
        performed_by="MERCHANT",
    )

    return campaign


# ============================================================
# PHASE 4
# EXPLICIT CAMPAIGN ACTIVATION
# ============================================================

@router.post(
    "/proposals/{proposal_id}/activate",
    response_model=CampaignProposalResponse,
)
def activate_campaign_proposal(
    proposal_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Phase 4:

    Explicitly activate a merchant-approved campaign.

    The campaign must already be:

        MERCHANT_APPROVED

    and must have:

        merchant_approved = True
        validation_passed = True
        can_activate = True

    Only this endpoint performs actual campaign activation.

    This is the ONLY campaign endpoint that may cause
    product prices to change.

    Phase 4 may:

    - apply the approved campaign discount
    - change product prices
    - mark campaign as ACTIVE

    Phase 4 does NOT:

    - modify inventory
    - create orders
    - create payments
    - move money

    If activation fails, the service rolls back
    the Phase 4 database transaction.
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.activate_campaign(
        db=db,
        merchant_id=merchant_id,
        campaign_id=proposal_id,
    )

    governance = campaign.governance if isinstance(campaign.governance, dict) else {}
    approved_discount = float(
        governance.get("approved_discount_percent", 0) or 0
    )
    price_changed = bool(governance.get("price_changed", False))

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="ACTIVATED",
        campaign=campaign,
        message=(
            "Phase 4 activation completed successfully. "
            f"Approved discount: {approved_discount:.2f}%. "
            f"Product prices changed: {'Yes' if price_changed else 'No'}. "
            "Inventory, orders, and payments were not changed."
        ),
        performed_by="MERCHANT",
    )

    return campaign


# ============================================================
# PHASE 1 / PHASE 2 / PHASE 3 / PHASE 4
# GET SINGLE CAMPAIGN PROPOSAL
# ============================================================

@router.get(
    "/proposals/{proposal_id}",
    response_model=CampaignProposalResponse,
)
def get_campaign_proposal(
    proposal_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Return one campaign proposal belonging to
    the authenticated merchant.
    """

    merchant_id = int(current_merchant.id)

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == proposal_id,
            Campaign.merchant_id == merchant_id,
        )
        .first()
    )

    if not campaign:
        raise HTTPException(
            status_code=404,
            detail="Campaign proposal not found.",
        )

    return campaign


# ============================================================
# LEGACY
# CREATE CAMPAIGN
# ============================================================

# Kept for backward compatibility.
#
# POST /campaigns/
#
# New frontend should use:
#
# POST /campaigns/proposals
#
# ============================================================

@router.post(
    "/",
    response_model=CampaignProposalResponse,
    status_code=201,
)
def create_campaign_proposal_legacy(
    request: CampaignProposalCreate,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Backward-compatible alias for creating
    a campaign proposal.

    This still performs Phase 1 only.
    """

    merchant_id = int(current_merchant.id)

    campaign = CampaignOrchestratorService.build_proposal(
        db=db,
        merchant_id=merchant_id,
        request=request,
    )

    _safe_campaign_audit(
        db,
        merchant_id=merchant_id,
        event="PROPOSAL_CREATED",
        campaign=campaign,
        message="Phase 1 legacy campaign proposal endpoint created a proposal.",
    )

    return campaign


# ============================================================
# LEGACY
# GET ALL CAMPAIGNS
# ============================================================

@router.get(
    "/",
    response_model=CampaignListResponse,
)
def get_campaigns(
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Backward-compatible endpoint.

    Returns the authenticated merchant's
    campaign proposals.
    """

    merchant_id = int(current_merchant.id)

    campaigns = (
        db.query(Campaign)
        .filter(
            Campaign.merchant_id == merchant_id
        )
        .order_by(
            Campaign.created_at.desc()
        )
        .all()
    )

    return {
        "campaigns": campaigns,
        "total": len(campaigns),
    }


# ============================================================
# GET CAMPAIGN BY ID
# ============================================================

# IMPORTANT:
#
# This dynamic route MUST remain AFTER:
#
# /proposals
# /proposals/{proposal_id}/validate
# /proposals/{proposal_id}/approve
# /proposals/{proposal_id}/reject
# /proposals/{proposal_id}/activate
# /proposals/{proposal_id}
#
# Otherwise FastAPI may try to interpret:
#
# "proposals"
#
# as:
#
# campaign_id: int
#
# ============================================================

@router.get(
    "/{campaign_id}",
    response_model=CampaignProposalResponse,
)
def get_campaign(
    campaign_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Return a campaign by ID belonging to
    the authenticated merchant.
    """

    merchant_id = int(current_merchant.id)

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

    return campaign


# ============================================================
# DELETE DRAFT CAMPAIGN
# ============================================================

@router.delete(
    "/{campaign_id}",
)
def delete_draft_campaign(
    campaign_id: int,
    current_merchant=Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """
    Delete a campaign proposal.

    Only DRAFT campaign proposals can be deleted.

    A campaign that has already passed Phase 2
    cannot be deleted through this endpoint.

    This endpoint never modifies products,
    inventory, orders, or payments.
    """

    merchant_id = int(current_merchant.id)

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

    # --------------------------------------------------------
    # Normalize status
    # --------------------------------------------------------

    status = str(
        campaign.status
    ).upper()

    # SQLAlchemy enum can sometimes produce:
    #
    # CampaignStatus.DRAFT
    #
    # Convert it to:
    #
    # DRAFT

    if "." in status:
        status = status.split(".")[-1]

    # --------------------------------------------------------
    # Only DRAFT can be deleted
    # --------------------------------------------------------

    if status != "DRAFT":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only DRAFT campaign proposals "
                "can be deleted."
            ),
        )



    db.delete(campaign)
    db.commit()

    return {
        "message": "Campaign proposal deleted.",
        "campaign_id": campaign_id,
    }