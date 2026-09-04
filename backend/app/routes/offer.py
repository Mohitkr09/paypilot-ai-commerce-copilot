from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.offer_service import OfferService


router = APIRouter(
    prefix="/offers",
    tags=["Offers"],
)


@router.get("/calculate/{product_id}")
def calculate_offer(
    product_id: int,
    discount_percent: float = Query(
        ...,
        ge=0,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    result = OfferService.calculate_offer(
        db=db,
        product_id=product_id,
        requested_discount_percent=discount_percent,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product or merchant not found",
        )

    return result