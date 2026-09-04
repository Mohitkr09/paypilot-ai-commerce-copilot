from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.settings import Settings

from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdate,
)


router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
)


# =========================================================
# GET SETTINGS
# =========================================================

@router.get(
    "/",
    response_model=SettingsResponse,
)
def get_settings(
    db: Session = Depends(get_db),
):

    settings = (
        db.query(Settings)
        .first()
    )

    # Create default settings
    # if none exist.

    if not settings:

        settings = Settings()

        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


# =========================================================
# UPDATE SETTINGS
# =========================================================

@router.put(
    "/",
    response_model=SettingsResponse,
)
def update_settings(
    settings_data: SettingsUpdate,
    db: Session = Depends(get_db),
):

    settings = (
        db.query(Settings)
        .first()
    )

    # Create settings if they don't exist.

    if not settings:

        settings = Settings()

        db.add(settings)
        db.commit()
        db.refresh(settings)


    update_data = settings_data.model_dump(
        exclude_unset=True
    )


    # =====================================================
    # VALIDATE RISK THRESHOLDS
    # =====================================================

    low_threshold = update_data.get(
        "low_risk_threshold",
        settings.low_risk_threshold,
    )

    high_threshold = update_data.get(
        "high_risk_threshold",
        settings.high_risk_threshold,
    )

    if low_threshold >= high_threshold:

        raise HTTPException(
            status_code=400,
            detail=(
                "Low risk threshold must be "
                "less than high risk threshold."
            ),
        )


    # =====================================================
    # UPDATE
    # =====================================================

    for key, value in update_data.items():

        setattr(
            settings,
            key,
            value,
        )


    db.commit()
    db.refresh(settings)

    return settings