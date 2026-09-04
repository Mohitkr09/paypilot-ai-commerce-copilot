from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    name = Column(
        String(200),
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=False,
        index=True,
    )

    description = Column(Text)

    price = Column(
        Float,
        nullable=False,
    )

    cost_price = Column(
        Float,
        nullable=False,
    )

    stock_quantity = Column(
        Integer,
        default=0,
        nullable=False,
    )

    sku = Column(
        String(100),
        unique=True,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )