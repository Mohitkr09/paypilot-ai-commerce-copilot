import requests

from app.db.database import SessionLocal
from app.models import Merchant, Product


# =========================================================
# RENDER BACKEND
# =========================================================

RENDER_API_URL = (
    "https://paypilot-ai-commerce-copilot-1.onrender.com"
)

IMPORT_ENDPOINT = (
    f"{RENDER_API_URL}/debug/import-catalog"
)


# =========================================================
# IMPORT TOKEN
# =========================================================
#
# IMPORTANT:
# Use the EXACT SAME token that you added to Render:
#
# DEBUG_IMPORT_TOKEN=xxxxxxxxxxxxxxxx
#
# Do NOT commit this file to GitHub if the token is written
# directly here.
# =========================================================

IMPORT_TOKEN = "PayPilotCatalogImport_2026_Mohit_8fK29xP7"


# =========================================================
# GET LOCAL CATALOG
# =========================================================

def get_local_catalog():

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Fetch local merchants
        # -------------------------------------------------

        merchants = db.query(Merchant).all()

        # -------------------------------------------------
        # Fetch local products
        # -------------------------------------------------

        products = db.query(Product).all()

        print("=" * 60)
        print("LOCAL DATABASE")
        print("=" * 60)

        print(
            f"Local merchants : {len(merchants)}"
        )

        print(
            f"Local products  : {len(products)}"
        )

        # =================================================
        # MERCHANT DATA
        # =================================================

        merchant_data = []

        for merchant in merchants:

            merchant_data.append({

                "id": merchant.id,

                "name": merchant.name,

                "email": merchant.email,

                "password_hash": merchant.password_hash,

                "role": merchant.role,

                "is_active": merchant.is_active,

                "maximum_discount_percent": (
                    merchant.maximum_discount_percent
                ),

                "minimum_margin": (
                    merchant.minimum_margin
                ),

                "auto_payment_limit": (
                    merchant.auto_payment_limit
                ),

                "bundle_allowed": (
                    merchant.bundle_allowed
                ),

                "created_at": (
                    merchant.created_at.isoformat()
                    if merchant.created_at
                    else None
                ),

                "updated_at": (
                    merchant.updated_at.isoformat()
                    if merchant.updated_at
                    else None
                ),
            })

        # =================================================
        # PRODUCT DATA
        # =================================================

        product_data = []

        for product in products:

            product_data.append({

                "id": product.id,

                "merchant_id": product.merchant_id,

                "name": product.name,

                "category": product.category,

                "description": product.description,

                "price": product.price,

                "cost_price": product.cost_price,

                "stock_quantity": (
                    product.stock_quantity
                ),

                "sku": product.sku,

                "is_active": product.is_active,
            })

        # =================================================
        # RETURN PAYLOAD
        # =================================================

        return {
            "merchants": merchant_data,
            "products": product_data,
        }

    finally:

        db.close()


# =========================================================
# TRANSFER CATALOG
# =========================================================

def transfer_catalog():

    print()
    print("=" * 60)
    print("PAYPILOT AI")
    print("LOCAL → RENDER CATALOG TRANSFER")
    print("=" * 60)

    # -----------------------------------------------------
    # Check token
    # -----------------------------------------------------

    if (
        not IMPORT_TOKEN
        or IMPORT_TOKEN
        == "PASTE_YOUR_DEBUG_IMPORT_TOKEN_HERE"
    ):

        print()
        print("ERROR:")
        print(
            "Please set your DEBUG_IMPORT_TOKEN "
            "inside transfer_catalog.py"
        )

        return

    # -----------------------------------------------------
    # Get local database data
    # -----------------------------------------------------

    data = get_local_catalog()

    print()
    print("=" * 60)
    print("CATALOG READY")
    print("=" * 60)

    print(
        f"Merchants to transfer : "
        f"{len(data['merchants'])}"
    )

    print(
        f"Products to transfer  : "
        f"{len(data['products'])}"
    )

    # -----------------------------------------------------
    # Check if local database is empty
    # -----------------------------------------------------

    if (
        len(data["merchants"]) == 0
        and len(data["products"]) == 0
    ):

        print()
        print(
            "ERROR: Local database contains "
            "no merchants or products."
        )

        return

    # -----------------------------------------------------
    # HTTP headers
    # -----------------------------------------------------

    headers = {
        "X-Import-Token": IMPORT_TOKEN,
        "Content-Type": "application/json",
    }

    # -----------------------------------------------------
    # Send catalog to Render
    # -----------------------------------------------------

    print()
    print("=" * 60)
    print("SENDING CATALOG TO RENDER...")
    print("=" * 60)

    try:

        response = requests.post(
            IMPORT_ENDPOINT,
            json=data,
            headers=headers,
            timeout=120,
        )

    except requests.exceptions.Timeout:

        print()
        print(
            "ERROR: Request timed out."
        )

        print(
            "Check whether your Render backend "
            "is running."
        )

        return

    except requests.exceptions.ConnectionError as e:

        print()
        print(
            "ERROR: Could not connect to Render."
        )

        print(e)

        return

    except requests.exceptions.RequestException as e:

        print()
        print(
            "ERROR: HTTP request failed."
        )

        print(e)

        return

    # -----------------------------------------------------
    # Response status
    # -----------------------------------------------------

    print()
    print("=" * 60)

    print(
        f"Render HTTP Status: "
        f"{response.status_code}"
    )

    print("=" * 60)

    # =====================================================
    # SUCCESS
    # =====================================================

    if response.status_code == 200:

        try:

            result = response.json()

            print()
            print("Render Response:")
            print(result)

        except ValueError:

            print()
            print(
                "Render returned:"
            )

            print(response.text)

        print()
        print("=" * 60)
        print("CATALOG TRANSFER COMPLETE")
        print("=" * 60)

    # =====================================================
    # UNAUTHORIZED
    # =====================================================

    elif response.status_code == 401:

        print()
        print(
            "ERROR: Unauthorized."
        )

        print()
        print(
            "Make sure the IMPORT_TOKEN in "
            "transfer_catalog.py exactly matches:"
        )

        print()
        print(
            "DEBUG_IMPORT_TOKEN"
        )

        print()
        print(
            "configured in Render."
        )

    # =====================================================
    # BACKEND NOT CONFIGURED
    # =====================================================

    elif response.status_code == 503:

        print()
        print(
            "ERROR: Render catalog import "
            "is not configured."
        )

        print()
        print(
            "Make sure DEBUG_IMPORT_TOKEN "
            "exists in Render Environment."
        )

    # =====================================================
    # SERVER ERROR
    # =====================================================

    elif response.status_code >= 500:

        print()
        print(
            "ERROR: Render backend returned "
            "a server error."
        )

        try:

            print(
                response.json()
            )

        except ValueError:

            print(
                response.text
            )

    # =====================================================
    # OTHER RESPONSE
    # =====================================================

    else:

        print()
        print(
            "Unexpected response from Render:"
        )

        try:

            print(
                response.json()
            )

        except ValueError:

            print(
                response.text
            )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    transfer_catalog()