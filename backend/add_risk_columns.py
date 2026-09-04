from app.db.database import engine
from sqlalchemy import text


def add_risk_columns():
    columns = [
        ("risk_score", "FLOAT"),
        ("risk_level", "VARCHAR(50)"),
        ("risk_reason", "TEXT"),
        ("risk_factors", "TEXT"),
        ("ai_explanation", "TEXT"),
    ]

    with engine.begin() as connection:

        for column_name, column_type in columns:

            connection.execute(
                text(
                    f"""
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS {column_name} {column_type};
                    """
                )
            )

            print(
                f"Checked column: {column_name}"
            )

    print()
    print("Risk columns updated successfully.")


if __name__ == "__main__":
    add_risk_columns()