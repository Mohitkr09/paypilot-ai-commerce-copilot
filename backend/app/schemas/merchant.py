from pydantic import BaseModel, EmailStr, ConfigDict


class MerchantCreate(BaseModel):
    name: str
    email: EmailStr
    maximum_discount_percent: float
    minimum_margin: float
    auto_payment_limit: float
    bundle_allowed: bool = False
    is_active: bool = True


class MerchantUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    maximum_discount_percent: float | None = None
    minimum_margin: float | None = None
    auto_payment_limit: float | None = None
    bundle_allowed: bool | None = None
    is_active: bool | None = None


class MerchantResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    maximum_discount_percent: float
    minimum_margin: float
    auto_payment_limit: float
    bundle_allowed: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)