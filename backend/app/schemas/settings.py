from pydantic import BaseModel, Field, ConfigDict


class SettingsBase(BaseModel):

    risk_engine_enabled: bool = True

    low_risk_threshold: float = Field(
        default=30,
        ge=0,
        le=100,
    )

    high_risk_threshold: float = Field(
        default=70,
        ge=0,
        le=100,
    )

    manual_review_enabled: bool = True

    manual_review_threshold: float = Field(
        default=50,
        ge=0,
        le=100,
    )

    max_discount: float = Field(
        default=30,
        ge=0,
        le=100,
    )

    require_review_discount: float = Field(
        default=20,
        ge=0,
        le=100,
    )


class SettingsUpdate(BaseModel):

    risk_engine_enabled: bool | None = None

    low_risk_threshold: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    high_risk_threshold: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    manual_review_enabled: bool | None = None

    manual_review_threshold: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    max_discount: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    require_review_discount: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class SettingsResponse(SettingsBase):

    id: int

    model_config = ConfigDict(
        from_attributes=True
    )