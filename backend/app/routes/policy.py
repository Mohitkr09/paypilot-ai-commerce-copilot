from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.policy_service import PolicyService


router = APIRouter(
    prefix="/policy",
    tags=["Policy"],
)


@router.get("/product/{product_id}")
def get_product_policy(
    product_id: int,
    db: Session = Depends(get_db),
):
    context = PolicyService.get_product_context(
        db=db,
        product_id=product_id,
    )

    if not context:
        raise HTTPException(
            status_code=404,
            detail="Product or merchant not found",
        )

    return context