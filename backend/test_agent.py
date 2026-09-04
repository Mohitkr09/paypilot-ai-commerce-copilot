from app.db.database import SessionLocal
from app.agents.graph.workflow import build_paypilot_workflow


def run_test(
    merchant_id: int,
    product_id: int,
    quantity: int,
    requested_discount: float,
):

    db = SessionLocal()

    try:

        workflow = build_paypilot_workflow(db)

        initial_state = {
            "merchant_id": merchant_id,
            "product_id": product_id,
            "quantity": quantity,
            "requested_discount_percent": requested_discount,
        }

        result = workflow.invoke(initial_state)

        print("\n" + "=" * 60)
        print("PAYPILOT AI AGENT RESULT")
        print("=" * 60)

        print(
            f"Product: "
            f"{result['product_name']}"
        )

        print(
            f"Quantity: "
            f"{result['quantity']}"
        )

        print(
            f"Original Unit Price: "
            f"₹{result['original_price']:.2f}"
        )

        print(
            f"Original Amount: "
            f"₹{result['original_amount']:.2f}"
        )

        print(
            f"Requested Discount: "
            f"{result['requested_discount_percent']:.2f}%"
        )

        print(
            f"Maximum Safe Discount: "
            f"{result['maximum_safe_discount_percent']:.2f}%"
        )

        print(
            f"Approved Discount: "
            f"{result['approved_discount_percent']:.2f}%"
        )

        print(
            f"Final Unit Price: "
            f"₹{result['final_price']:.2f}"
        )

        print(
            f"Discount Amount: "
            f"₹{result['discount_amount']:.2f}"
        )

        print(
            f"Final Amount: "
            f"₹{result['final_amount']:.2f}"
        )

        print(
            f"Final Margin: "
            f"{result['final_margin_percent']:.2f}%"
        )

        print(
            f"Payment Amount: "
            f"₹{result['payment_amount']:.2f}"
        )

        print(
            f"Payment Limit: "
            f"₹{result['auto_payment_limit']:.2f}"
        )

        print(
            f"Payment Approved: "
            f"{result['payment_approved']}"
        )

        print(
            f"Manual Review Required: "
            f"{result.get('manual_review_required', False)}"
        )

        print(
            f"Status: "
            f"{result['status']}"
        )

        print(
            f"Message: "
            f"{result['message']}"
        )

        print("=" * 60)

        return result

    finally:
        db.close()


def main():

    # =====================================================
    # TEST 1
    # Quantity = 1
    #
    # Expected:
    # Payment Approved = True
    # =====================================================

    print("\n")
    print("#" * 60)
    print("TEST 1: SINGLE PRODUCT")
    print("#" * 60)

    run_test(
        merchant_id=1,
        product_id=5,
        quantity=1,
        requested_discount=20.0,
    )

    # =====================================================
    # TEST 2
    # Quantity = 4
    #
    # Expected:
    # Final amount > ₹50,000
    # Payment Approved = False
    # Manual Review = True
    # =====================================================

    print("\n")
    print("#" * 60)
    print("TEST 2: MULTIPLE PRODUCTS")
    print("#" * 60)

    run_test(
        merchant_id=1,
        product_id=5,
        quantity=4,
        requested_discount=20.0,
    )


if __name__ == "__main__":
    main()