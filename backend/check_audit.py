from sqlalchemy import text
from app.db.database import SessionLocal


db = SessionLocal()

try:
    query = text("""
        SELECT
            id,
            order_id,
            payment_id,
            event_type,
            old_status,
            new_status,
            performed_by,
            created_at
        FROM audit_logs
        WHERE order_id = 116
        ORDER BY created_at ASC, id ASC
    """)

    rows = db.execute(query).mappings().all()

    print("\n========== AUDIT LOGS FOR ORDER 116 ==========\n")

    if not rows:
        print("NO AUDIT LOGS FOUND")
    else:
        for row in rows:
            print("--------------------------------------------")
            print(f"ID           : {row['id']}")
            print(f"Order ID     : {row['order_id']}")
            print(f"Payment ID   : {row['payment_id']}")
            print(f"Event        : {row['event_type']}")
            print(f"Old Status   : {row['old_status']}")
            print(f"New Status   : {row['new_status']}")
            print(f"Performed By : {row['performed_by']}")
            print(f"Created At   : {row['created_at']}")

finally:
    db.close()