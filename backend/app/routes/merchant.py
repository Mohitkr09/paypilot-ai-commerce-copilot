from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.merchant import Merchant
from app.schemas.merchant import (
    MerchantCreate,
    MerchantUpdate,
    MerchantResponse,
)


router = APIRouter(
    prefix="/merchants",
    tags=["Merchants"],
)


@router.post(
    "/",
    response_model=MerchantResponse,
    status_code=201,
)
def create_merchant(
    merchant_data: MerchantCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Merchant)
        .filter(Merchant.email == merchant_data.email)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Merchant with this email already exists",
        )

    merchant = Merchant(
        name=merchant_data.name,
        email=merchant_data.email,
        maximum_discount_percent=merchant_data.maximum_discount_percent,
        minimum_margin=merchant_data.minimum_margin,
        auto_payment_limit=merchant_data.auto_payment_limit,
        bundle_allowed=merchant_data.bundle_allowed,
        is_active=merchant_data.is_active,
    )

    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    return merchant


@router.get(
    "/",
    response_model=list[MerchantResponse],
)
def get_merchants(
    db: Session = Depends(get_db),
):
    return db.query(Merchant).all()


@router.get(
    "/{merchant_id}",
    response_model=MerchantResponse,
)
def get_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id)
        .first()
    )

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Merchant not found",
        )

    return merchant


@router.put(
    "/{merchant_id}",
    response_model=MerchantResponse,
)
def update_merchant(
    merchant_id: int,
    merchant_data: MerchantUpdate,
    db: Session = Depends(get_db),
):
    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id)
        .first()
    )

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Merchant not found",
        )

    update_data = merchant_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(merchant, key, value)

    db.commit()
    db.refresh(merchant)

    return merchant


@router.delete(
    "/{merchant_id}",
)
def delete_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id)
        .first()
    )

    if not merchant:
        raise HTTPException(
            status_code=404,
            detail="Merchant not found",
        )

    db.delete(merchant)
    db.commit()

    return {
        "message": "Merchant deleted successfully"
    }