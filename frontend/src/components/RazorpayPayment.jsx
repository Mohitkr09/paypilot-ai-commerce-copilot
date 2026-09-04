import React, { useState } from "react";

const API_URL = "http://127.0.0.1:8000";

const RAZORPAY_SCRIPT_URL =
  "https://checkout.razorpay.com/v1/checkout.js";

// =========================================================
// LOAD RAZORPAY SCRIPT
// =========================================================

const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      console.log("Razorpay SDK already loaded");
      resolve(true);
      return;
    }

    const existingScript = document.querySelector(
      `script[src="${RAZORPAY_SCRIPT_URL}"]`
    );

    if (existingScript) {
      existingScript.addEventListener("load", () => {
        console.log("Razorpay SDK loaded");
        resolve(true);
      });

      existingScript.addEventListener("error", () => {
        console.error("Failed to load Razorpay SDK");
        resolve(false);
      });

      return;
    }

    const script = document.createElement("script");

    script.src = RAZORPAY_SCRIPT_URL;
    script.async = true;

    script.onload = () => {
      console.log("Razorpay SDK loaded successfully");
      resolve(true);
    };

    script.onerror = () => {
      console.error("Failed to load Razorpay SDK");
      resolve(false);
    };

    document.body.appendChild(script);
  });
};

// =========================================================
// GET ERROR MESSAGE
// =========================================================

const getErrorMessage = async (response) => {
  try {
    const text = await response.text();

    if (!text) {
      return `Request failed with status ${response.status}`;
    }

    let data;

    try {
      data = JSON.parse(text);
    } catch {
      return text;
    }

    console.error("API Error Response:", data);

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (Array.isArray(data.detail)) {
      return data.detail
        .map((error) => {
          const field =
            Array.isArray(error.loc)
              ? error.loc.join(".")
              : "field";

          return `${field}: ${
            error.msg || "Invalid value"
          }`;
        })
        .join(", ");
    }

    if (
      data.detail &&
      typeof data.detail === "object"
    ) {
      if (data.detail.message) {
        return String(data.detail.message);
      }

      if (data.detail.error) {
        return String(data.detail.error);
      }
    }

    if (data.message) {
      return String(data.message);
    }

    if (data.error) {
      return String(data.error);
    }

    return `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
};

// =========================================================
// COMPONENT
// =========================================================

function RazorpayPayment({ paymentId }) {
  const [loading, setLoading] = useState(false);

  const [message, setMessage] = useState("");

  const [payment, setPayment] = useState(null);

  const [paymentMethod, setPaymentMethod] =
    useState("razorpay");

  // =======================================================
  // GET PAYMENT
  // =======================================================

  const getPayment = async () => {
    console.log("=================================");
    console.log("GET PAYMENT");
    console.log("=================================");

    console.log("Payment ID:", paymentId);

    const response = await fetch(
      `${API_URL}/payments/${paymentId}`,
      {
        method: "GET",

        headers: {
          Accept: "application/json",
        },

        cache: "no-store",
      }
    );

    if (!response.ok) {
      const errorMessage =
        await getErrorMessage(response);

      throw new Error(errorMessage);
    }

    const data = await response.json();

    console.log("Payment data:", data);

    return data;
  };

  // =======================================================
  // CREATE RAZORPAY ORDER
  // =======================================================

  const createRazorpayOrder = async (orderId) => {
    console.log("=================================");
    console.log("CREATE RAZORPAY ORDER");
    console.log("=================================");

    console.log("Application Order ID:", orderId);

    const response = await fetch(
      `${API_URL}/payments/`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },

        body: JSON.stringify({
          order_id: orderId,
          currency: "INR",
        }),
      }
    );

    if (!response.ok) {
      const errorMessage =
        await getErrorMessage(response);

      throw new Error(
        `Unable to create Razorpay order: ${errorMessage}`
      );
    }

    const data = await response.json();

    console.log(
      "Payment / Razorpay order created:",
      data
    );

    return data;
  };

  // =======================================================
  // BUILD IDEMPOTENCY KEY
  // =======================================================

  const buildIdempotencyKey = (
    currentPayment,
    razorpayPaymentId
  ) => {
    if (
      !currentPayment?.id ||
      !razorpayPaymentId
    ) {
      return null;
    }

    return (
      `payment-${currentPayment.id}-verify-` +
      razorpayPaymentId
    );
  };

  // =======================================================
  // VERIFY PAYMENT
  //
  // IMPORTANT:
  // currentPayment is passed directly.
  //
  // DO NOT depend on React "payment" state here.
  // =======================================================

  const verifyPayment = async (
    razorpayResponse,
    currentPayment,
    selectedPaymentMethod
  ) => {
    try {
      setLoading(true);
      setMessage("Verifying payment...");

      console.log(
        "================================="
      );

      console.log(
        "RAZORPAY PAYMENT VERIFICATION"
      );

      console.log(
        "================================="
      );

      console.log(
        "Current application payment:",
        currentPayment
      );

      console.log(
        "Razorpay response:",
        razorpayResponse
      );

      // ===================================================
      // VALIDATE APPLICATION PAYMENT
      // ===================================================

      if (!currentPayment) {
        throw new Error(
          "Payment information is missing."
        );
      }

      if (!currentPayment.id) {
        throw new Error(
          "Application payment ID is missing."
        );
      }

      // ===================================================
      // VALIDATE RAZORPAY ORDER ID
      // ===================================================

      if (
        !razorpayResponse?.razorpay_order_id
      ) {
        throw new Error(
          "Razorpay order ID was not returned."
        );
      }

      // ===================================================
      // VALIDATE RAZORPAY PAYMENT ID
      // ===================================================

      if (
        !razorpayResponse?.razorpay_payment_id
      ) {
        throw new Error(
          "Razorpay payment ID was not returned."
        );
      }

      // ===================================================
      // VALIDATE SIGNATURE
      // ===================================================

      if (
        !razorpayResponse?.razorpay_signature
      ) {
        throw new Error(
          "Razorpay signature was not returned."
        );
      }

      // ===================================================
      // VERIFY ORDER ID MATCH
      // ===================================================

      if (
        currentPayment.razorpay_order_id &&
        razorpayResponse.razorpay_order_id !==
          currentPayment.razorpay_order_id
      ) {
        throw new Error(
          "Razorpay order ID does not match the application payment."
        );
      }

      // ===================================================
      // IDEMPOTENCY KEY
      // ===================================================

      const idempotencyKey =
        buildIdempotencyKey(
          currentPayment,
          razorpayResponse.razorpay_payment_id
        );

      if (!idempotencyKey) {
        throw new Error(
          "Unable to generate payment verification idempotency key."
        );
      }

      console.log(
        "Idempotency-Key:",
        idempotencyKey
      );

      // ===================================================
      // VERIFICATION PAYLOAD
      // ===================================================

      const requestBody = {
        payment_id: Number(currentPayment.id),

        razorpay_order_id:
          razorpayResponse.razorpay_order_id,

        razorpay_payment_id:
          razorpayResponse.razorpay_payment_id,

        razorpay_signature:
          razorpayResponse.razorpay_signature,

        payment_method:
          selectedPaymentMethod || "razorpay",
      };

      console.log(
        "================================="
      );

      console.log(
        "VERIFICATION REQUEST"
      );

      console.log(
        "================================="
      );

      console.log({
        ...requestBody,

        razorpay_signature:
          requestBody.razorpay_signature
            ? "[PRESENT]"
            : "[MISSING]",
      });

      // ===================================================
      // CALL BACKEND
      // ===================================================

      const verifyUrl =
        `${API_URL}/payments/${currentPayment.id}/verify`;

      console.log(
        "Verification URL:",
        verifyUrl
      );

      const response = await fetch(
        verifyUrl,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",

            Accept:
              "application/json",

            "Idempotency-Key":
              idempotencyKey,
          },

          body: JSON.stringify(
            requestBody
          ),
        }
      );

      // ===================================================
      // READ RESPONSE
      // ===================================================

      const responseText =
        await response.text();

      let data = null;

      try {
        data = responseText
          ? JSON.parse(responseText)
          : null;
      } catch {
        data = responseText;
      }

      console.log(
        "================================="
      );

      console.log(
        "VERIFICATION RESPONSE"
      );

      console.log(
        "================================="
      );

      console.log(
        "HTTP STATUS:",
        response.status
      );

      console.log(
        "Response:",
        data
      );

      // ===================================================
      // ERROR
      // ===================================================

      if (!response.ok) {
        let errorMessage =
          "Payment verification failed.";

        if (
          typeof data?.detail === "string"
        ) {
          errorMessage = data.detail;
        } else if (
          Array.isArray(data?.detail)
        ) {
          errorMessage =
            data.detail
              .map((error) => {
                const field =
                  Array.isArray(error.loc)
                    ? error.loc.join(".")
                    : "field";

                return `${field}: ${
                  error.msg ||
                  "Invalid value"
                }`;
              })
              .join(", ");
        } else if (
          data?.detail?.message
        ) {
          errorMessage =
            data.detail.message;
        } else if (
          data?.detail?.error
        ) {
          errorMessage =
            data.detail.error;
        } else if (
          data?.message
        ) {
          errorMessage =
            data.message;
        } else if (
          data?.error
        ) {
          errorMessage =
            data.error;
        }

        throw new Error(
          errorMessage
        );
      }

      // ===================================================
      // SUCCESS
      // ===================================================

      console.log(
        "================================="
      );

      console.log(
        "PAYMENT VERIFIED SUCCESSFULLY"
      );

      console.log(
        "================================="
      );

      console.log(
        "Verified payment:",
        data
      );

      setPayment(data);

      setMessage(
        "Payment successful! Payment verified."
      );

      setLoading(false);

    } catch (error) {
      console.error(
        "================================="
      );

      console.error(
        "VERIFY PAYMENT ERROR"
      );

      console.error(
        "================================="
      );

      console.error(error);

      setLoading(false);

      setMessage(
        error?.message ||
          "Payment verification failed."
      );
    }
  };

  // =======================================================
  // START PAYMENT
  // =======================================================

  const startPayment = async () => {
    try {
      setLoading(true);
      setMessage("Loading payment...");

      // ===================================================
      // 1. GET APPLICATION PAYMENT
      // ===================================================

      let paymentData =
        await getPayment();

      console.log(
        "Initial application payment:",
        paymentData
      );

      // ===================================================
      // 2. CHECK STATUS
      // ===================================================

      const status =
        String(
          paymentData.status || ""
        ).toUpperCase();

      if (status === "CAPTURED") {
        setPayment(paymentData);

        setLoading(false);

        setMessage(
          "This payment has already been completed."
        );

        return;
      }

      if (status === "REFUNDED") {
        throw new Error(
          "This payment has already been refunded."
        );
      }

      if (status === "CANCELLED") {
        throw new Error(
          "This payment has been cancelled."
        );
      }

      // ===================================================
      // 3. CREATE RAZORPAY ORDER IF NEEDED
      // ===================================================

      if (
        !paymentData.razorpay_order_id
      ) {
        console.log(
          "Razorpay order ID missing."
        );

        setMessage(
          "Creating Razorpay order..."
        );

        if (!paymentData.order_id) {
          throw new Error(
            "Order ID is missing from payment."
          );
        }

        paymentData =
          await createRazorpayOrder(
            paymentData.order_id
          );

        console.log(
          "New payment data:",
          paymentData
        );
      }

      // ===================================================
      // IMPORTANT
      //
      // Update UI state, BUT ALSO KEEP USING
      // paymentData DIRECTLY BELOW.
      //
      // This fixes the React state timing bug.
      // ===================================================

      setPayment(paymentData);

      // ===================================================
      // 4. VALIDATE RAZORPAY ORDER
      // ===================================================

      if (
        !paymentData.razorpay_order_id
      ) {
        throw new Error(
          "Razorpay order ID is missing."
        );
      }

      // ===================================================
      // 5. RAZORPAY KEY
      // ===================================================

      const razorpayKey =
        import.meta.env
          .VITE_RAZORPAY_KEY_ID;

      if (!razorpayKey) {
        throw new Error(
          "Razorpay key is missing. Add VITE_RAZORPAY_KEY_ID to your frontend .env file."
        );
      }

      console.log(
        "Razorpay Key:",
        razorpayKey
      );

      // ===================================================
      // 6. LOAD RAZORPAY
      // ===================================================

      setMessage(
        "Loading Razorpay Checkout..."
      );

      const razorpayLoaded =
        await loadRazorpayScript();

      if (!razorpayLoaded) {
        throw new Error(
          "Unable to load Razorpay Checkout."
        );
      }

      if (!window.Razorpay) {
        throw new Error(
          "Razorpay Checkout is not available."
        );
      }

      // ===================================================
      // 7. AMOUNT
      // ===================================================

      const amountInPaise =
        Math.round(
          Number(paymentData.amount) *
            100
        );

      if (
        !Number.isFinite(
          amountInPaise
        )
      ) {
        throw new Error(
          "Invalid payment amount."
        );
      }

      if (
        amountInPaise <= 0
      ) {
        throw new Error(
          "Payment amount must be greater than zero."
        );
      }

      console.log(
        "Amount:",
        paymentData.amount
      );

      console.log(
        "Amount in paise:",
        amountInPaise
      );

      // ===================================================
      // 8. CAPTURE CURRENT PAYMENT
      //
      // This is VERY IMPORTANT.
      //
      // The handler below uses this exact object.
      // It does NOT depend on React state.
      // ===================================================

      const currentPayment =
        paymentData;

      // ===================================================
      // 9. RAZORPAY OPTIONS
      // ===================================================

      const options = {
        key: razorpayKey,

        amount: amountInPaise,

        currency:
          paymentData.currency ||
          "INR",

        order_id:
          paymentData.razorpay_order_id,

        name: "PayPilot AI",

        description:
          `Payment for Order #${paymentData.order_id}`,

        // =================================================
        // PREFILL
        // =================================================

        prefill: {
          name:
            "PayPilot Customer",

          email:
            "customer@example.com",

          contact:
            "9999999999",
        },

        // =================================================
        // NOTES
        // =================================================

        notes: {
          application_payment_id:
            String(
              currentPayment.id
            ),

          application_order_id:
            String(
              currentPayment.order_id
            ),
        },

        // =================================================
        // THEME
        // =================================================

        theme: {
          color: "#2563eb",
        },

        // =================================================
        // SUCCESS
        // =================================================

        handler:
          async function (
            razorpayResponse
          ) {
            console.log(
              "================================="
            );

            console.log(
              "RAZORPAY PAYMENT SUCCESS"
            );

            console.log(
              "================================="
            );

            console.log(
              "Application Payment ID:",
              currentPayment.id
            );

            console.log(
              "Application Order ID:",
              currentPayment.order_id
            );

            console.log(
              "Razorpay Order ID:",
              razorpayResponse?.razorpay_order_id
            );

            console.log(
              "Razorpay Payment ID:",
              razorpayResponse?.razorpay_payment_id
            );

            console.log(
              "Signature:",
              razorpayResponse
                ?.razorpay_signature
                ? "[PRESENT]"
                : "[MISSING]"
            );

            // =============================================
            // IMPORTANT FIX
            //
            // Pass currentPayment directly.
            //
            // DO NOT call:
            //
            // verifyPayment(razorpayResponse)
            //
            // because React state may still be null.
            // =============================================

            await verifyPayment(
              razorpayResponse,
              currentPayment,
              paymentMethod
            );
          },

        // =================================================
        // MODAL
        // =================================================

        modal: {
          confirm_close: true,

          escape: true,

          backdropclose: false,

          ondismiss:
            function () {
              console.log(
                "Razorpay checkout closed."
              );

              setLoading(false);

              setMessage(
                "Payment window closed."
              );
            },
        },

        // =================================================
        // RETRY
        // =================================================

        retry: {
          enabled: true,
        },
      };

      // ===================================================
      // LOG OPTIONS
      // ===================================================

      console.log(
        "================================="
      );

      console.log(
        "RAZORPAY CHECKOUT OPTIONS"
      );

      console.log(
        "================================="
      );

      console.log({
        key: "[CONFIGURED]",

        amount:
          options.amount,

        currency:
          options.currency,

        order_id:
          options.order_id,

        application_payment_id:
          currentPayment.id,

        application_order_id:
          currentPayment.order_id,
      });

      // ===================================================
      // 10. CREATE RAZORPAY INSTANCE
      // ===================================================

      const razorpay =
        new window.Razorpay(
          options
        );

      // ===================================================
      // 11. PAYMENT FAILED
      // ===================================================

      razorpay.on(
        "payment.failed",
        function (response) {
          console.error(
            "================================="
          );

          console.error(
            "RAZORPAY PAYMENT FAILED"
          );

          console.error(
            "================================="
          );

          console.error(
            response
          );

          const reason =
            response?.error
              ?.description ||
            response?.error
              ?.reason ||
            "Payment failed.";

          setLoading(false);

          setMessage(reason);
        }
      );

      // ===================================================
      // 12. OPEN CHECKOUT
      // ===================================================

      setMessage(
        "Opening Razorpay Checkout..."
      );

      setLoading(false);

      razorpay.open();

    } catch (error) {
      console.error(
        "================================="
      );

      console.error(
        "START PAYMENT ERROR"
      );

      console.error(
        "================================="
      );

      console.error(error);

      setLoading(false);

      setMessage(
        error?.message ||
          "Unable to start payment."
      );
    }
  };

  // =========================================================
  // UI
  // =========================================================

  return (
    <div
      className="
        w-full
        max-w-md
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-6
        shadow-lg
      "
    >
      {/* HEADER */}

      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900">
          Pay with Razorpay
        </h2>

        <p className="mt-1 text-sm text-slate-500">
          Secure payment powered by Razorpay
        </p>
      </div>

      {/* PAYMENT INFORMATION */}

      <div
        className="
          mb-5
          rounded-xl
          bg-slate-50
          p-4
        "
      >
        <div className="flex justify-between">
          <span className="text-sm text-slate-500">
            Payment ID
          </span>

          <span className="font-semibold text-slate-900">
            {payment?.id || paymentId}
          </span>
        </div>

        {payment && (
          <>
            <div className="mt-3 flex justify-between">
              <span className="text-sm text-slate-500">
                Order ID
              </span>

              <span className="font-semibold text-slate-900">
                #{payment.order_id}
              </span>
            </div>

            <div className="mt-3 flex justify-between">
              <span className="text-sm text-slate-500">
                Amount
              </span>

              <span className="font-semibold text-slate-900">
                {payment.currency || "INR"}{" "}
                {Number(
                  payment.amount
                ).toFixed(2)}
              </span>
            </div>

            <div className="mt-3 flex justify-between">
              <span className="text-sm text-slate-500">
                Status
              </span>

              <span
                className={`
                  font-semibold
                  ${
                    String(
                      payment.status
                    ).toUpperCase() ===
                    "CAPTURED"
                      ? "text-green-600"
                      : String(
                          payment.status
                        ).toUpperCase() ===
                        "FAILED"
                      ? "text-red-600"
                      : "text-slate-900"
                  }
                `}
              >
                {payment.status}
              </span>
            </div>

            {payment.razorpay_order_id && (
              <div className="mt-3 flex justify-between gap-4">
                <span className="text-sm text-slate-500">
                  Razorpay Order
                </span>

                <span className="max-w-[220px] truncate text-right text-xs font-semibold text-slate-700">
                  {payment.razorpay_order_id}
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* PAYMENT METHOD */}

      <div className="mb-5">
        <label
          htmlFor="payment-method"
          className="mb-2 block text-sm font-semibold text-slate-700"
        >
          Payment Method
        </label>

        <select
          id="payment-method"
          value={paymentMethod}
          onChange={(event) =>
            setPaymentMethod(
              event.target.value
            )
          }
          disabled={loading}
          className="
            w-full
            rounded-xl
            border
            border-slate-300
            bg-white
            px-4
            py-3
            text-slate-900
            outline-none
            focus:border-blue-500
            focus:ring-2
            focus:ring-blue-200
          "
        >
          <option value="razorpay">
            Razorpay Checkout
          </option>

          <option value="card">
            Card
          </option>

          <option value="upi">
            UPI
          </option>

          <option value="netbanking">
            Net Banking
          </option>

          <option value="wallet">
            Wallet
          </option>
        </select>

        <p className="mt-2 text-xs text-slate-400">
          Razorpay will display the available payment
          methods in Checkout.
        </p>
      </div>

      {/* PAY BUTTON */}

      <button
        type="button"
        onClick={startPayment}
        disabled={loading}
        className="
          w-full
          rounded-xl
          bg-blue-600
          px-5
          py-3
          font-semibold
          text-white
          shadow-lg
          shadow-blue-600/20
          transition
          hover:bg-blue-700
          disabled:cursor-not-allowed
          disabled:opacity-60
        "
      >
        {loading
          ? "Processing..."
          : String(
              payment?.status || ""
            ).toUpperCase() ===
            "CAPTURED"
          ? "Payment Completed"
          : "Pay Now"}
      </button>

      {/* MESSAGE */}

      {message && (
        <div
          className={`
            mt-4
            rounded-xl
            p-3
            text-center
            text-sm
            ${
              message
                .toLowerCase()
                .includes("success")
                ? "bg-green-50 text-green-700"
                : message
                    .toLowerCase()
                    .includes("failed")
                  ? "bg-red-50 text-red-700"
                  : "bg-slate-50 text-slate-700"
            }
          `}
        >
          {message}
        </div>
      )}

      {/* SECURITY */}

      <p className="mt-4 text-center text-xs text-slate-400">
        Your payment is securely processed by Razorpay.
      </p>
    </div>
  );
}

export default RazorpayPayment;