from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
)

from sqlalchemy.orm import relationship

from datetime import datetime, timezone

from app.db.database import Base


# =========================================================
# USER MODEL
# =========================================================

class User(Base):

    __tablename__ = "users"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # USERNAME
    # =====================================================

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # EMAIL
    # =====================================================

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # PASSWORD
    # =====================================================

    # IMPORTANT:
    # Never store the actual password.
    # Store only the hashed password.

    password_hash = Column(
        String(255),
        nullable=False,
    )

    # =====================================================
    # ROLE
    # =====================================================

    # Supported roles:
    #
    # ADMIN
    # MERCHANT
    # REVIEWER
    # USER
    #
    # Authorization will use this field.

    role = Column(
        String(50),
        nullable=False,
        default="USER",
        index=True,
    )

    # =====================================================
    # MERCHANT ID
    # =====================================================

    # If this user belongs to a merchant,
    # store the merchant ID here.
    #
    # ADMIN / REVIEWER may have NULL merchant_id.

    merchant_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    # =====================================================
    # ACTIVE STATUS
    # =====================================================

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =====================================================
    # CREATED AT
    # =====================================================

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # =====================================================
    # UPDATED AT
    # =====================================================

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # =====================================================
    # OPTIONAL RELATIONSHIP
    # =====================================================

    # Uncomment this only if your Merchant model has:
    #
    #     users = relationship("User", ...)
    #
    # and a proper ForeignKey is added to merchant_id.
    #
    # merchant = relationship(
    #     "Merchant",
    #     back_populates="users",
    # )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self):

        return (
            f"<User("
            f"id={self.id}, "
            f"username='{self.username}', "
            f"email='{self.email}', "
            f"role='{self.role}', "
            f"active={self.is_active}"
            f")>"
        )