// ============================================================
// SSE EVENT SERVICE
// ============================================================

const EVENT_URL =
  import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/events/orders`
    : "http://127.0.0.1:8000/events/orders";

let eventSource = null;


// ============================================================
// CONNECT
// ============================================================

export function connectToOrderEvents({
  onConnected,
  onOrderCreated,
  onOrderProcessed,
  onOrderUpdated,
  onOrderApproved,
  onOrderRejected,
  onManualReviewCreated,
  onManualReviewProcessed,
  onManualReviewCompleted,
  onError,
} = {}) {

  // ----------------------------------------------------------
  // PREVENT DUPLICATE CONNECTION
  // ----------------------------------------------------------

  if (
    eventSource &&
    eventSource.readyState !== EventSource.CLOSED
  ) {
    console.log("Order SSE already connected");
    return eventSource;
  }

  console.log(
    "Connecting to order SSE:",
    EVENT_URL
  );

  eventSource = new EventSource(EVENT_URL);


  // ==========================================================
  // CONNECTED
  // ==========================================================

  eventSource.addEventListener(
    "connected",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "SSE connected:",
          data
        );

        if (onConnected) {
          onConnected(data);
        }

      } catch (error) {

        console.error(
          "Invalid connected SSE event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // ORDER CREATED
  // ==========================================================

  eventSource.addEventListener(
    "order_created",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Order created:",
          data
        );

        if (onOrderCreated) {
          onOrderCreated(data);
        }

      } catch (error) {

        console.error(
          "Invalid order_created event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // ORDER PROCESSED
  // ==========================================================

  eventSource.addEventListener(
    "order_processed",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Order processed:",
          data
        );

        if (onOrderProcessed) {
          onOrderProcessed(data);
        }

      } catch (error) {

        console.error(
          "Invalid order_processed event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // ORDER UPDATED
  // ==========================================================

  eventSource.addEventListener(
    "order_updated",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Order updated:",
          data
        );

        if (onOrderUpdated) {
          onOrderUpdated(data);
        }

      } catch (error) {

        console.error(
          "Invalid order_updated event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // ORDER APPROVED
  // ==========================================================

  eventSource.addEventListener(
    "order_approved",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Order approved:",
          data
        );

        if (onOrderApproved) {
          onOrderApproved(data);
        }

      } catch (error) {

        console.error(
          "Invalid order_approved event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // ORDER REJECTED
  // ==========================================================

  eventSource.addEventListener(
    "order_rejected",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Order rejected:",
          data
        );

        if (onOrderRejected) {
          onOrderRejected(data);
        }

      } catch (error) {

        console.error(
          "Invalid order_rejected event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // MANUAL REVIEW CREATED
  // ==========================================================

  eventSource.addEventListener(
    "manual_review_created",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Manual review created:",
          data
        );

        if (onManualReviewCreated) {
          onManualReviewCreated(data);
        }

      } catch (error) {

        console.error(
          "Invalid manual_review_created event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // MANUAL REVIEW PROCESSED
  // ==========================================================

  eventSource.addEventListener(
    "manual_review_processed",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Manual review processed:",
          data
        );

        if (onManualReviewProcessed) {
          onManualReviewProcessed(data);
        }

      } catch (error) {

        console.error(
          "Invalid manual_review_processed event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // MANUAL REVIEW COMPLETED
  // ==========================================================

  eventSource.addEventListener(
    "manual_review_completed",
    (event) => {

      try {

        const data =
          JSON.parse(event.data);

        console.log(
          "Manual review completed:",
          data
        );

        if (onManualReviewCompleted) {
          onManualReviewCompleted(data);
        }

      } catch (error) {

        console.error(
          "Invalid manual_review_completed event:",
          error
        );

      }
    }
  );


  // ==========================================================
  // GENERIC MESSAGE
  // ==========================================================

  eventSource.onmessage =
    (event) => {

      console.log(
        "Generic SSE message:",
        event.data
      );

    };


  // ==========================================================
  // ERROR
  // ==========================================================

  eventSource.onerror =
    (error) => {

      console.error(
        "SSE connection error:",
        error
      );

      if (onError) {
        onError(error);
      }

    };


  return eventSource;
}


// ============================================================
// DISCONNECT
// ============================================================

export function disconnectFromOrderEvents() {

  if (eventSource) {

    console.log(
      "Closing order SSE connection..."
    );

    eventSource.close();

    eventSource = null;

  }

}