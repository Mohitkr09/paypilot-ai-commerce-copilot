import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.database import engine as local_engine
from app.models import Merchant, Product


# =========================================================
# RENDER DATABASE URL
# =========================================================

RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL")

if not RENDER_DATABASE_URL:
    raise RuntimeError(
        "RENDER_DATABASE_URL environment variable is not set."
    )


# =========================================================
# DATABASE CONNECTIONS
# =========================================================

LocalSession = sessionmaker(
    bind=local_engine,
    autocommit=False,
    autoflush=False,
)

render_engine = create_engine(
    RENDER_DATABASE_URL,
    pool_pre_ping=True,
)

RenderSession = sessionmaker(
    bind=render_engine,
    autocommit=False,
    autoflush=False,
)


# =========================================================
# COPY TABLE
# =========================================================

def copy_table(local_session, render_session, model):

    table = model.__table__

    print(f"\nCopying table: {table.name}")

    records = local_session.query(model).all()

    print(f"Local records found: {len(records)}")

    if not records:
        print("Nothing to copy.")
        return

    rows = []

    for record in records:

        row = {}

        for column in table.columns:
            row[column.name] = getattr(
                record,
                column.name
            )

        rows.append(row)

    existing_count = render_session.execute(
        text(
            f'SELECT COUNT(*) FROM "{table.name}"'
        )
    ).scalar()

    print(
        f"Render records currently present: "
        f"{existing_count}"
    )

    if existing_count > 0:

        print(
            f"Skipping {table.name} because "
            f"Render already contains data."
        )

        return

    render_session.execute(
        table.insert(),
        rows
    )

    render_session.commit()

    print(
        f"Successfully copied "
        f"{len(rows)} records into Render."
    )


# =========================================================
# RESET SEQUENCE
# =========================================================

def reset_sequence(render_session, model):

    table = model.__table__

    primary_keys = list(
        table.primary_key.columns
    )

    if not primary_keys:
        return

    primary_key = primary_keys[0]

    if primary_key.name != "id":
        return

    try:

        query = text(
            """
            SELECT setval(
                pg_get_serial_sequence(
                    :table_name,
                    :column_name
                ),
                COALESCE(
                    (
                        SELECT MAX(id)
                        FROM :table_name
                    ),
                    1
                ),
                true
            )
            """
        )

        # Use a safer table-specific statement
        sequence_query = text(
            f"""
            SELECT setval(
                pg_get_serial_sequence(
                    '{table.name}',
                    'id'
                ),
                COALESCE(
                    (
                        SELECT MAX(id)
                        FROM "{table.name}"
                    ),
                    1
                ),
                true
            )
            """
        )

        render_session.execute(sequence_query)

        render_session.commit()

        print(
            f"Sequence reset for {table.name}."
        )

    except Exception as e:

        render_session.rollback()

        print(
            f"Could not reset sequence "
            f"for {table.name}: {e}"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 60)
    print("PAYPILOT AI - RENDER DATABASE SEED")
    print("=" * 60)

    local_session = LocalSession()
    render_session = RenderSession()

    try:

        # -------------------------------------------------
        # Test Render connection
        # -------------------------------------------------

        print(
            "\nTesting Render PostgreSQL connection..."
        )

        render_session.execute(
            text("SELECT 1")
        )

        print(
            "Render PostgreSQL connection successful."
        )

        # -------------------------------------------------
        # Copy merchants
        # -------------------------------------------------

        copy_table(
            local_session,
            render_session,
            Merchant
        )

        # -------------------------------------------------
        # Copy products
        # -------------------------------------------------

        copy_table(
            local_session,
            render_session,
            Product
        )

        # -------------------------------------------------
        # Reset sequences
        # -------------------------------------------------

        reset_sequence(
            render_session,
            Merchant
        )

        reset_sequence(
            render_session,
            Product
        )

        print("\n" + "=" * 60)
        print("DATABASE SEED COMPLETED")
        print("=" * 60)

    except Exception as e:

        render_session.rollback()

        print("\n" + "=" * 60)
        print("DATABASE SEED FAILED")
        print("=" * 60)

        print(f"\nError: {e}")

        raise

    finally:

        local_session.close()
        render_session.close()
        render_engine.dispose()


if __name__ == "__main__":
    main()