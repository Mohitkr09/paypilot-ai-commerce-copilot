import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { API_URL } from "../App";

// =========================================================
// RAZORPAY KEY
// =========================================================

const RAZORPAY_KEY_ID =
  import.meta.env.VITE_RAZORPAY_KEY_ID;

// =========================================================
// LOAD RAZORPAY SCRIPT
// =========================================================

function loadRazorpayScript() {
  return new Promise((resolve) => {
    // Already loaded
    if (window.Razorpay) {
      console.log("Razorpay already loaded");
      resolve(true);
      return;
    }

    // Check whether script is already loading
    const existingScript = document.querySelector(
      'script[src="https://checkout.razorpay.com/v1/checkout.js"]'
    );

    if (existingScript) {
      existingScript.addEventListener("load", () => {
        console.log("Razorpay script loaded successfully");
        resolve(true);
      });

      existingScript.addEventListener("error", () => {
        console.error("Failed to load Razorpay script");
        resolve(false);
      });

      return;
    }

    // Create Razorpay script
    const script = document.createElement("script");

    script.src =
      "https://checkout.razorpay.com/v1/checkout.js";

    script.async = true;

    script.onload = () => {
      console.log(
        "Razorpay script loaded successfully"
      );

      resolve(true);
    };

    script.onerror = () => {
      console.error(
        "Failed to load Razorpay script"
      );

      resolve(false);
    };

    document.body.appendChild(script);
  });
}

// =========================================================
// PAYMENT COMPONENT
// =========================================================

function Payment() {
  const { paymentId } = useParams();
  const navigate = useNavigate();

  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // =======================================================
  // FETCH PAYMENT
  // =======================================================

  useEffect(() => {
    if (paymentId) {
      fetchPayment();
    }
  }, [paymentId]);

  async function fetchPayment() {
    try {
      setLoading(true);
      setError("");

      console.log("=================================");
      console.log("FETCH PAYMENT");
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
        "FETCH PAYMENT STATUS:",
        response.status
      );

      console.log(
        "PAYMENT DATA:",
        data
      );

      if (!response.ok) {
        throw new Error(
          getBackendErrorMessage(data)
        );
      }

      setPayment(data);

      // Already captured
      if (
        String(data?.status).toUpperCase() ===
        "CAPTURED"
      ) {
        setSuccess(true);
      }
    } catch (err) {
      console.error(
        "FETCH PAYMENT ERROR:",
        err
      );

      setError(
        err?.message ||
          "Unable to load payment."
      );
    } finally {
      setLoading(false);
    }
  }

  // =======================================================
  // BACKEND ERROR MESSAGE
  // =======================================================

  function getBackendErrorMessage(data) {
    if (!data) {
      return "Payment request failed.";
    }

    // Normal FastAPI error
    if (
      typeof data.detail === "string"
    ) {
      return data.detail;
    }

    // FastAPI validation errors
    if (
      Array.isArray(data.detail)
    ) {
      return data.detail
        .map((item) => {
          const location =
            Array.isArray(item.loc)
              ? item.loc.join(" → ")
              : "unknown";

          const message =
            item.msg ||
            "Invalid value";

          return `${location}: ${message}`;
        })
        .join(" | ");
    }

    // Custom backend object
    if (
      data.detail &&
      typeof data.detail === "object"
    ) {
      if (data.detail.message) {
        return String(
          data.detail.message
        );
      }

      if (data.detail.error) {
        return String(
          data.detail.error
        );
      }
    }

    if (data.message) {
      return String(data.message);
    }

    if (data.error) {
      return String(data.error);
    }

    return "Payment request failed.";
  }

  // =======================================================
  // CREATE VERIFICATION IDEMPOTENCY KEY
  // =======================================================

  function buildVerificationIdempotencyKey(
    razorpayPaymentId
  ) {
    if (
      !payment?.id ||
      !razorpayPaymentId
    ) {
      return null;
    }

    /*
      Same application payment + same Razorpay payment
      always gets the same idempotency key.

      Example:

      payment-29-verify-pay_xxxxx
    */

    return (
      `payment-${payment.id}-verify-` +
      razorpayPaymentId
    );
  }

  // =======================================================
  // VERIFY PAYMENT
  // =======================================================

  async function verifyPayment(
    razorpayResponse
  ) {
    console.log("=================================");
    console.log(
      "VERIFYING RAZORPAY PAYMENT"
    );
    console.log("=================================");

    // =====================================================
    // APPLICATION PAYMENT CHECK
    // =====================================================

    if (!payment) {
      throw new Error(
        "Payment information is missing."
      );
    }

    // =====================================================
    // RAZORPAY RESPONSE VALIDATION
    // =====================================================

    if (
      !razorpayResponse?.razorpay_order_id
    ) {
      throw new Error(
        "Razorpay order ID was not returned."
      );
    }

    if (
      !razorpayResponse?.razorpay_payment_id
    ) {
      throw new Error(
        "Razorpay payment ID was not returned."
      );
    }

    if (
      !razorpayResponse?.razorpay_signature
    ) {
      throw new Error(
        "Razorpay signature was not returned."
      );
    }

    // =====================================================
    // CHECK RAZORPAY ORDER ID
    // =====================================================

    if (
      razorpayResponse.razorpay_order_id !==
      payment.razorpay_order_id
    ) {
      throw new Error(
        "Razorpay order ID does not match the payment."
      );
    }

    // =====================================================
    // IDEMPOTENCY KEY
    // =====================================================

    const idempotencyKey =
      buildVerificationIdempotencyKey(
        razorpayResponse.razorpay_payment_id
      );

    if (!idempotencyKey) {
      throw new Error(
        "Unable to generate payment verification idempotency key."
      );
    }

    console.log(
      "Verification Idempotency-Key:",
      idempotencyKey
    );

    // =====================================================
    // PAYMENT METHOD
    // =====================================================

    /*
      Razorpay checkout response normally does not return
      payment_method directly in the handler response.

      We send "razorpay" to the backend.

      The backend should ideally obtain the actual method
      (UPI/card/netbanking/wallet/etc.) from Razorpay
      after verification.
    */

    const verifyPayload = {
      razorpay_order_id:
        razorpayResponse.razorpay_order_id,

      razorpay_payment_id:
        razorpayResponse.razorpay_payment_id,

      razorpay_signature:
        razorpayResponse.razorpay_signature,

      payment_method: "razorpay",
    };

    console.log("=================================");
    console.log("VERIFY PAYLOAD");
    console.log("=================================");

    console.log(
      JSON.stringify(
        {
          ...verifyPayload,

          // Never expose the actual signature in logs
          razorpay_signature:
            verifyPayload.razorpay_signature
              ? "[PRESENT]"
              : "[MISSING]",
        },
        null,
        2
      )
    );

    // =====================================================
    // VERIFY URL
    // =====================================================

    const verifyUrl =
      `${API_URL}/payments/${payment.id}/verify`;

    console.log(
      "VERIFY URL:",
      verifyUrl
    );

    // =====================================================
    // BACKEND REQUEST
    // =====================================================

    const verifyResponse =
      await fetch(
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

          body:
            JSON.stringify(
              verifyPayload
            ),
        }
      );

    // =====================================================
    // READ RESPONSE
    // =====================================================

    const responseText =
      await verifyResponse.text();

    let result = null;

    try {
      result = responseText
        ? JSON.parse(responseText)
        : null;
    } catch {
      result = responseText;
    }

    console.log("=================================");
    console.log(
      "BACKEND VERIFY RESPONSE"
    );
    console.log("=================================");

    console.log(
      "HTTP STATUS:",
      verifyResponse.status
    );

    console.log(
      "RESPONSE:",
      result
    );

    // =====================================================
    // ERROR
    // =====================================================

    if (!verifyResponse.ok) {
      console.error(
        "PAYMENT VERIFICATION FAILED"
      );

      console.error(
        "HTTP STATUS:",
        verifyResponse.status
      );

      console.error(
        "BACKEND RESPONSE:",
        result
      );

      if (
        Array.isArray(
          result?.detail
        )
      ) {
        console.error(
          "FASTAPI VALIDATION ERRORS"
        );

        result.detail.forEach(
          (item, index) => {
            console.error(
              `Validation Error #${index + 1}`
            );

            console.error(
              "Location:",
              item.loc
            );

            console.error(
              "Message:",
              item.msg
            );

            console.error(
              "Type:",
              item.type
            );
          }
        );
      }

      throw new Error(
        getBackendErrorMessage(
          result
        )
      );
    }

    // =====================================================
    // SUCCESS
    // =====================================================

    console.log("=================================");
    console.log(
      "PAYMENT VERIFIED SUCCESSFULLY"
    );
    console.log("=================================");

    console.log(
      "VERIFIED PAYMENT:",
      result
    );

    return result;
  }

  // =======================================================
  // HANDLE PAYMENT
  // =======================================================

  async function handlePayment() {
    try {
      setError("");
      setProcessing(true);

      // ===================================================
      // PAYMENT CHECK
      // ===================================================

      if (!payment) {
        throw new Error(
          "Payment information is missing."
        );
      }

      // ===================================================
      // ALREADY CAPTURED
      // ===================================================

      if (
        String(payment.status).toUpperCase() ===
        "CAPTURED"
      ) {
        setSuccess(true);
        setProcessing(false);

        return;
      }

      // ===================================================
      // RAZORPAY ORDER CHECK
      // ===================================================

      if (
        !payment.razorpay_order_id
      ) {
        throw new Error(
          "Razorpay Order ID is missing."
        );
      }

      // ===================================================
      // RAZORPAY KEY CHECK
      // ===================================================

      if (!RAZORPAY_KEY_ID) {
        throw new Error(
          "VITE_RAZORPAY_KEY_ID is missing from the frontend .env file."
        );
      }

      // ===================================================
      // LOAD RAZORPAY
      // ===================================================

      console.log("=================================");
      console.log(
        "STARTING RAZORPAY CHECKOUT"
      );
      console.log("=================================");

      const loaded =
        await loadRazorpayScript();

      if (!loaded) {
        throw new Error(
          "Razorpay Checkout failed to load."
        );
      }

      if (!window.Razorpay) {
        throw new Error(
          "Razorpay SDK is not available."
        );
      }

      // ===================================================
      // RAZORPAY OPTIONS
      // ===================================================

      const options = {
        key:
          RAZORPAY_KEY_ID,

        order_id:
          payment.razorpay_order_id,

        currency:
          payment.currency || "INR",

        name:
          "PayPilot AI",

        description:
          `Payment for Order #${payment.order_id}`,

        prefill: {
          name:
            "PayPilot Customer",

          email:
            "customer@example.com",

          contact:
            "9999999999",
        },

        theme: {
          color:
            "#2563eb",
        },

        // =================================================
        // PAYMENT SUCCESS
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
              "Razorpay Order ID:",
              razorpayResponse?.razorpay_order_id
            );

            console.log(
              "Razorpay Payment ID:",
              razorpayResponse?.razorpay_payment_id
            );

            console.log(
              "Signature:",
              razorpayResponse?.razorpay_signature
                ? "[PRESENT]"
                : "[MISSING]"
            );

            try {
              const verifiedPayment =
                await verifyPayment(
                  razorpayResponse
                );

              // =========================================
              // UPDATE PAYMENT
              // =========================================

              setPayment(
                verifiedPayment
              );

              setSuccess(true);

              setProcessing(false);

            } catch (err) {
              console.error(
                "================================="
              );

              console.error(
                "PAYMENT VERIFICATION ERROR"
              );

              console.error(
                "================================="
              );

              console.error(err);

              setError(
                err?.message ||
                  "Payment verification failed."
              );

              setProcessing(false);
            }
          },

        // =================================================
        // MODAL
        // =================================================

        modal: {
          confirm_close:
            true,

          escape:
            true,

          backdropclose:
            false,

          ondismiss:
            function () {
              console.log(
                "Razorpay Checkout closed"
              );

              setProcessing(false);
            },
        },

        // =================================================
        // RETRY
        // =================================================

        retry: {
          enabled:
            true,
        },
      };

      console.log("=================================");
      console.log(
        "RAZORPAY OPTIONS"
      );
      console.log("=================================");

      console.log({
        ...options,
        key: "[CONFIGURED]",
      });

      // ===================================================
      // CREATE RAZORPAY INSTANCE
      // ===================================================

      const razorpay =
        new window.Razorpay(
          options
        );

      // ===================================================
      // PAYMENT FAILED
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
            "Failure response:",
            response
          );

          const reason =
            response?.error?.description ||
            response?.error?.reason ||
            "Payment failed.";

          setError(reason);

          setProcessing(false);
        }
      );

      // ===================================================
      // OPEN CHECKOUT
      // ===================================================

      console.log(
        "Opening Razorpay Checkout..."
      );

      razorpay.open();

    } catch (err) {
      console.error(
        "================================="
      );

      console.error(
        "RAZORPAY ERROR"
      );

      console.error(
        "================================="
      );

      console.error(err);

      setError(
        err?.message ||
          "Unable to start payment."
      );

      setProcessing(false);
    }
  }

  // =======================================================
  // LOADING
  // =======================================================

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl border bg-white p-8 shadow-sm">
          <p className="text-lg font-semibold">
            Loading payment...
          </p>
        </div>
      </div>
    );
  }

  // =======================================================
  // ERROR WITHOUT PAYMENT
  // =======================================================

  if (error && !payment) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="w-full max-w-md rounded-2xl border bg-white p-8 shadow-sm">

          <h2 className="mb-4 text-xl font-bold text-red-600">
            Payment Error
          </h2>

          <p className="mb-6 break-words text-slate-600">
            {error}
          </p>

          <button
            onClick={fetchPayment}
            className="rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Retry
          </button>

        </div>
      </div>
    );
  }

  // =======================================================
  // NO PAYMENT
  // =======================================================

  if (!payment) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="w-full max-w-md rounded-2xl border bg-white p-8 text-center shadow-sm">

          <h2 className="mb-4 text-xl font-bold">
            Payment Not Found
          </h2>

          <p className="mb-6 text-slate-600">
            The requested payment could not be found.
          </p>

          <button
            onClick={() =>
              navigate("/orders")
            }
            className="rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Back to Orders
          </button>

        </div>
      </div>
    );
  }

  // =======================================================
  // SUCCESS
  // =======================================================

  if (
    success ||
    String(payment.status).toUpperCase() ===
      "CAPTURED"
  ) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">

        <div className="w-full max-w-md rounded-2xl border bg-white p-8 text-center shadow-sm">

          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-3xl text-green-600">
            ✓
          </div>

          <h1 className="mb-2 text-2xl font-bold text-green-600">
            Payment Successful
          </h1>

          <p className="mb-6 text-slate-600">
            Your payment has been verified successfully.
          </p>

          <div className="mb-6 rounded-xl bg-slate-50 p-4 text-left">

            <p className="mb-2">
              <strong>
                Payment ID:
              </strong>{" "}
              {payment.id}
            </p>

            <p className="mb-2">
              <strong>
                Order ID:
              </strong>{" "}
              #{payment.order_id}
            </p>

            <p className="mb-2">
              <strong>
                Amount:
              </strong>{" "}
              {payment.currency}{" "}
              {Number(payment.amount).toFixed(2)}
            </p>

            <p className="mb-2">
              <strong>
                Status:
              </strong>{" "}
              {payment.status}
            </p>

            {payment.payment_method && (
              <p className="mb-2">
                <strong>
                  Payment Method:
                </strong>{" "}
                {payment.payment_method}
              </p>
            )}

            {payment.razorpay_payment_id && (
              <p className="break-all">
                <strong>
                  Razorpay Payment ID:
                </strong>{" "}
                {payment.razorpay_payment_id}
              </p>
            )}

          </div>

          <button
            onClick={() =>
              navigate("/orders")
            }
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Back to Orders
          </button>

        </div>

      </div>
    );
  }

  // =======================================================
  // MAIN PAYMENT SCREEN
  // =======================================================

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">

      <div className="w-full max-w-md rounded-2xl border bg-white p-8 shadow-sm">

        {/* HEADER */}

        <h1 className="mb-2 text-2xl font-bold">
          Pay with Razorpay
        </h1>

        <p className="mb-6 text-slate-500">
          Secure payment powered by Razorpay
        </p>

        {/* PAYMENT INFORMATION */}

        <div className="mb-6 rounded-xl bg-slate-50 p-5">

          <div className="mb-3 flex justify-between">
            <span className="text-slate-500">
              Payment ID
            </span>

            <span className="font-semibold">
              {payment.id}
            </span>
          </div>

          <div className="mb-3 flex justify-between">
            <span className="text-slate-500">
              Order ID
            </span>

            <span className="font-semibold">
              #{payment.order_id}
            </span>
          </div>

          <div className="mb-3 flex justify-between">
            <span className="text-slate-500">
              Amount
            </span>

            <span className="text-lg font-bold">
              {payment.currency}{" "}
              {Number(payment.amount).toFixed(2)}
            </span>
          </div>

          <div className="mb-3 flex justify-between">
            <span className="text-slate-500">
              Status
            </span>

            <span className="font-semibold">
              {payment.status}
            </span>
          </div>

          <div className="flex justify-between gap-4">
            <span className="text-slate-500">
              Razorpay Order
            </span>

            <span className="break-all text-right text-sm font-medium">
              {payment.razorpay_order_id}
            </span>
          </div>

        </div>

        {/* ERROR */}

        {error && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">

            <p className="font-semibold">
              Payment Error
            </p>

            <p className="mt-1 break-words">
              {error}
            </p>

          </div>
        )}

        {/* PAY BUTTON */}

        <button
          onClick={handlePayment}
          disabled={processing}
          className="w-full rounded-xl bg-blue-600 px-6 py-4 font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {processing
            ? "Processing..."
            : `Pay ${payment.currency} ${Number(
                payment.amount
              ).toFixed(2)}`}
        </button>

        {/* SECURITY */}

        <p className="mt-4 text-center text-xs text-slate-400">
          Your payment is securely processed by Razorpay.
        </p>

      </div>

    </div>
  );
}

export default Payment;