from app.db.database import engine, Base

from app.models import (
    Merchant,
    Product,
    Order,
    Payment,
    ManualReview,
    AuditLog,
    Settings,
)


print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")