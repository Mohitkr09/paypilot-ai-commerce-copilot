from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    merchant_id: int
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = None

    price: float = Field(ge=0)
    cost_price: float = Field(ge=0)
    stock_quantity: int = Field(default=0, ge=0)

    sku: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class ProductUpdate(BaseModel):
    merchant_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None

    price: float | None = Field(default=None, ge=0)
    cost_price: float | None = Field(default=None, ge=0)
    stock_quantity: int | None = Field(default=None, ge=0)

    sku: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    id: int
    merchant_id: int
    name: str
    category: str
    description: str | None
    price: float
    cost_price: float
    stock_quantity: int
    sku: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)