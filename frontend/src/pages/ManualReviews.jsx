import { useEffect, useMemo, useState } from "react";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  RefreshCw,
  Search,
  ShieldAlert,
  X,
  XCircle,
  Wifi,
  WifiOff,
} from "lucide-react";

import {
  getManualReviews,
  getOrder,
  decideManualReview,
} from "../services/api";

import {
  connectToOrderEvents,
  disconnectFromOrderEvents,
} from "../services/eventService";

// =============================================================
// CONSTANTS
// =============================================================

const DECISIONS = {
  APPROVE: "APPROVED",
  REJECT: "REJECTED",
};

const DEFAULT_APPROVE_COMMENT =
  "Approved from PayPilot dashboard";

const DEFAULT_REJECT_COMMENT =
  "Rejected after manual risk review";

// =============================================================
// MANUAL REVIEWS
// =============================================================

function ManualReviews() {
  const [reviews, setReviews] = useState([]);

  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");

  const [selectedReview, setSelectedReview] = useState(null);

  /*
   * IMPORTANT:
   *
   * We keep the UI decision as:
   *
   * APPROVED
   * REJECTED
   *
   * instead of:
   *
   * APPROVE
   * REJECT
   *
   * because the backend decision endpoint normally expects
   * the resulting review/order status.
   */
  const [decision, setDecision] = useState(null);

  const [comment, setComment] = useState("");

  const [sseConnected, setSseConnected] = useState(false);

  // ===========================================================
  // LOAD REVIEWS
  // ===========================================================

  const loadReviews = async (showRefresh = false) => {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const data = await getManualReviews();

      if (Array.isArray(data)) {
        setReviews(data);
      } else {
        console.warn(
          "Manual reviews API returned non-array:",
          data
        );

        setReviews([]);
      }
    } catch (err) {
      console.error(
        "Manual reviews loading error:",
        err
      );

      const message = extractApiError(
        err,
        "Unable to load manual reviews."
      );

      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // ===========================================================
  // INITIAL LOAD
  // ===========================================================

  useEffect(() => {
    loadReviews(false);
  }, []);

  // ===========================================================
  // REAL-TIME SSE
  // ===========================================================

  useEffect(() => {
    console.log(
      "Starting Manual Reviews SSE connection..."
    );

    let refreshTimer = null;

    const refreshFromSSE = () => {
      console.log(
        "Manual Reviews: refreshing after SSE event..."
      );

      /*
       * Give the backend a small amount of time to commit
       * the transaction before requesting the latest list.
       */
      if (refreshTimer) {
        clearTimeout(refreshTimer);
      }

      refreshTimer = setTimeout(() => {
        loadReviews(false);
      }, 300);
    };

    const eventSource = connectToOrderEvents({
      // -------------------------------------------------------
      // CONNECTED
      // -------------------------------------------------------

      onConnected: (data) => {
        console.log(
          "Manual Reviews SSE connected:",
          data
        );

        setSseConnected(true);
      },

      // -------------------------------------------------------
      // ORDER CREATED
      // -------------------------------------------------------

      onOrderCreated: (data) => {
        console.log(
          "Manual Reviews - order created:",
          data
        );

        refreshFromSSE();
      },

      // -------------------------------------------------------
      // ORDER PROCESSED
      // -------------------------------------------------------

      onOrderProcessed: (data) => {
        console.log(
          "Manual Reviews - order processed:",
          data
        );

        refreshFromSSE();
      },

      // -------------------------------------------------------
      // MANUAL REVIEW CREATED
      // -------------------------------------------------------

      onManualReviewCreated: (data) => {
        console.log(
          "Manual review created:",
          data
        );

        refreshFromSSE();
      },

      // -------------------------------------------------------
      // MANUAL REVIEW PROCESSED
      // -------------------------------------------------------

      onManualReviewProcessed: (data) => {
        console.log(
          "Manual review processed:",
          data
        );

        refreshFromSSE();
      },

      // -------------------------------------------------------
      // MANUAL REVIEW COMPLETED
      // -------------------------------------------------------

      onManualReviewCompleted: (data) => {
        console.log(
          "Manual review completed:",
          data
        );

        refreshFromSSE();
      },

      // -------------------------------------------------------
      // ERROR
      // -------------------------------------------------------

      onError: (error) => {
        console.warn(
          "Manual Reviews SSE error:",
          error
        );

        setSseConnected(false);
      },
    });

    // ---------------------------------------------------------
    // CLEANUP
    // ---------------------------------------------------------

    return () => {
      console.log(
        "Closing Manual Reviews SSE connection..."
      );

      if (refreshTimer) {
        clearTimeout(refreshTimer);
      }

      /*
       * eventSource is intentionally referenced here so that
       * custom eventService implementations can be cleaned up.
       */
      if (
        eventSource &&
        typeof eventSource.close === "function"
      ) {
        try {
          eventSource.close();
        } catch (err) {
          console.warn(
            "Unable to close SSE EventSource:",
            err
          );
        }
      }

      disconnectFromOrderEvents();

      setSseConnected(false);
    };
  }, []);

  // ===========================================================
  // STATISTICS
  // ===========================================================

  const statistics = useMemo(() => {
    const pending = reviews.filter(
      (review) =>
        normalizeValue(review.status) ===
        "PENDING"
    ).length;

    const approved = reviews.filter(
      (review) =>
        normalizeValue(review.status) ===
        "APPROVED"
    ).length;

    const rejected = reviews.filter(
      (review) =>
        normalizeValue(review.status) ===
        "REJECTED"
    ).length;

    const highRisk = reviews.filter(
      (review) =>
        normalizeValue(review.risk_level) ===
        "HIGH"
    ).length;

    const criticalRisk = reviews.filter(
      (review) =>
        normalizeValue(review.risk_level) ===
        "CRITICAL"
    ).length;

    return {
      total: reviews.length,
      pending,
      approved,
      rejected,
      highRisk,
      criticalRisk,
    };
  }, [reviews]);

  // ===========================================================
  // FILTER REVIEWS
  // ===========================================================

  const filteredReviews = useMemo(() => {
    const query = search.trim().toLowerCase();

    return reviews
      .filter((review) => {
        const matchesSearch =
          !query ||
          String(review.id ?? "")
            .toLowerCase()
            .includes(query) ||
          String(review.order_id ?? "")
            .toLowerCase()
            .includes(query) ||
          String(review.reason ?? "")
            .toLowerCase()
            .includes(query) ||
          String(review.reviewed_by ?? "")
            .toLowerCase()
            .includes(query);

        const reviewStatus =
          normalizeValue(review.status);

        const reviewRisk =
          normalizeValue(review.risk_level);

        const matchesStatus =
          statusFilter === "ALL" ||
          reviewStatus === statusFilter;

        const matchesRisk =
          riskFilter === "ALL" ||
          reviewRisk === riskFilter;

        return (
          matchesSearch &&
          matchesStatus &&
          matchesRisk
        );
      })
      .sort((a, b) => {
        return (
          Number(b.id || 0) -
          Number(a.id || 0)
        );
      });
  }, [
    reviews,
    search,
    statusFilter,
    riskFilter,
  ]);

  // ===========================================================
  // OPEN DECISION MODAL
  // ===========================================================

  const openDecisionModal = (
    review,
    action
  ) => {
    if (
      normalizeValue(review.status) !==
      "PENDING"
    ) {
      setError(
        "This manual review has already been processed."
      );

      return;
    }

    setSelectedReview(review);
    setDecision(action);

    setComment(
      action === DECISIONS.APPROVE
        ? DEFAULT_APPROVE_COMMENT
        : DEFAULT_REJECT_COMMENT
    );

    setError("");
  };

  // ===========================================================
  // CLOSE MODAL
  // ===========================================================

  const closeModal = () => {
    if (processing) {
      return;
    }

    setSelectedReview(null);
    setDecision(null);
    setComment("");
  };

  // ===========================================================
  // SUBMIT DECISION
  // ===========================================================

  const handleDecision = async () => {
    if (!selectedReview || !decision) {
      return;
    }

    if (
      normalizeValue(selectedReview.status) !==
      "PENDING"
    ) {
      setError(
        "This manual review is no longer pending."
      );

      closeModal();

      return;
    }

    try {
      setProcessing(true);
      setError("");

      const finalComment =
        comment.trim() ||
        (decision === DECISIONS.APPROVE
          ? DEFAULT_APPROVE_COMMENT
          : DEFAULT_REJECT_COMMENT);

      console.log(
        "Submitting manual review decision:",
        {
          reviewId: selectedReview.id,
          decision,
          reviewedBy: "admin",
          comment: finalComment,
        }
      );

      /*
       * IMPORTANT:
       *
       * decision is now:
       *
       * APPROVED
       * REJECTED
       *
       * instead of:
       *
       * APPROVE
       * REJECT
       */
      const decisionData = await decideManualReview(
        selectedReview.id,
        decision,
        "admin",
        finalComment
      );

      console.log(
        "Manual review decision response:",
        decisionData
      );

      /*
       * The decision endpoint is responsible for changing both:
       *
       *   ManualReview.status
       *   Order.status
       *
       * Do not assume that a successful HTTP response alone means
       * the order reached APPROVED. Verify the authoritative order
       * state before closing an approval operation.
       *
       * Different backend versions may expose the decision under
       * different response keys, so accept all known variants.
       */
      const returnedReviewStatus = normalizeValue(
        decisionData?.status ??
          decisionData?.review_status ??
          decisionData?.new_status ??
          decisionData?.order_status
      );

      if (
        decision === DECISIONS.APPROVE &&
        returnedReviewStatus &&
        returnedReviewStatus !== "APPROVED"
      ) {
        throw new Error(
          `Manual review was not approved. Backend returned status: ${returnedReviewStatus}`
        );
      }

      /*
       * For APPROVE, verify the associated order as well.
       *
       * This prevents the merchant dashboard from showing a
       * successful approval when the order is still stuck at
       * MANUAL_REVIEW_REQUIRED.
       *
       * The backend should normally update the order in the same
       * transaction, so this is only a short consistency check.
       */
      if (decision === DECISIONS.APPROVE) {
        const orderId = selectedReview.order_id;

        if (orderId) {
          let latestOrder = null;
          let approved = false;

          for (let attempt = 1; attempt <= 5; attempt += 1) {
            try {
              latestOrder = await getOrder(orderId);

              const latestOrderStatus = normalizeValue(
                latestOrder?.status ??
                  latestOrder?.order_status
              );

              console.log(
                `Manual review approval order verification ${attempt}/5:`,
                {
                  orderId,
                  status: latestOrderStatus,
                  order: latestOrder,
                }
              );

              if (latestOrderStatus === "APPROVED") {
                approved = true;
                break;
              }

              if (latestOrderStatus === "REJECTED") {
                throw new Error(
                  "The manual review response succeeded, but the associated order is REJECTED."
                );
              }
            } catch (orderError) {
              /*
               * If the decision endpoint itself succeeded but the
               * immediate order read is temporarily unavailable,
               * retry briefly. On the final attempt surface the
               * actual error instead of hiding it.
               */
              if (attempt === 5) {
                throw orderError;
              }

              console.warn(
                `Unable to verify approved order on attempt ${attempt}/5:`,
                orderError
              );
            }

            await new Promise((resolve) =>
              setTimeout(resolve, 400)
            );
          }

          if (!approved) {
            throw new Error(
              `Manual review was approved, but order #${orderId} is not APPROVED yet. Please refresh and verify the order before starting payment.`
            );
          }
        }
      }

      console.log(
        "Manual review decision successful:",
        selectedReview.id,
        decision
      );

      // -------------------------------------------------------
      // CLOSE MODAL
      // -------------------------------------------------------

      setSelectedReview(null);
      setDecision(null);
      setComment("");

      // -------------------------------------------------------
      // REFRESH DATA
      // -------------------------------------------------------

      await loadReviews(true);
    } catch (err) {
      console.error(
        "Manual review decision error:",
        err
      );

      const message = extractApiError(
        err,
        "Manual review decision failed."
      );

      setError(message);
    } finally {
      setProcessing(false);
    }
  };

  // ===========================================================
  // LOADING STATE
  // ===========================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">

          <div className="mb-8">
            <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-200" />

            <div className="mt-3 h-4 w-96 animate-pulse rounded bg-slate-200" />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-32 animate-pulse rounded-2xl bg-white shadow-sm"
              />
            ))}
          </div>

          <div className="mt-6 h-96 animate-pulse rounded-2xl bg-white shadow-sm" />

        </div>
      </div>
    );
  }

  // ===========================================================
  // MAIN UI
  // ===========================================================

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">

      <div className="mx-auto max-w-7xl">

        {/* =====================================================
            HEADER
        ====================================================== */}

        <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">

          <div>
            <div className="flex items-center gap-3">

              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm">
                <ShieldAlert size={22} />
              </div>

              <div>

                <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                  Manual Reviews
                </h1>

                <p className="mt-1 text-sm text-slate-500">
                  Review AI-flagged payment transactions
                </p>

              </div>

            </div>
          </div>

          <div className="flex items-center gap-3">

            {/* SSE STATUS */}

            <div
              className={`hidden items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold sm:flex ${
                sseConnected
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >

              {sseConnected ? (
                <Wifi
                  size={15}
                  className="animate-pulse"
                />
              ) : (
                <WifiOff size={15} />
              )}

              {sseConnected
                ? "Live Updates"
                : "Reconnecting..."}

            </div>

            {/* REFRESH */}

            <button
              type="button"
              onClick={() => loadReviews(true)}
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >

              <RefreshCw
                size={17}
                className={
                  refreshing
                    ? "animate-spin"
                    : ""
                }
              />

              {refreshing
                ? "Refreshing..."
                : "Refresh"}

            </button>

          </div>

        </div>

        {/* =====================================================
            ERROR
        ====================================================== */}

        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">

            <AlertTriangle
              size={18}
              className="shrink-0"
            />

            <span className="leading-5">
              {error}
            </span>

            <button
              type="button"
              onClick={() => setError("")}
              className="ml-auto shrink-0 rounded-lg p-1 hover:bg-red-100"
            >
              <X size={16} />
            </button>

          </div>
        )}

        {/* =====================================================
            STAT CARDS
        ====================================================== */}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <StatCard
            title="Pending Reviews"
            value={statistics.pending}
            subtitle="Requires attention"
            icon={<Clock3 size={20} />}
            iconClass="bg-amber-50 text-amber-600"
          />

          <StatCard
            title="Approved"
            value={statistics.approved}
            subtitle="Manually approved"
            icon={<CheckCircle2 size={20} />}
            iconClass="bg-emerald-50 text-emerald-600"
          />

          <StatCard
            title="Rejected"
            value={statistics.rejected}
            subtitle="Manually rejected"
            icon={<XCircle size={20} />}
            iconClass="bg-red-50 text-red-600"
          />

          <StatCard
            title="High Risk"
            value={
              statistics.highRisk +
              statistics.criticalRisk
            }
            subtitle="High / critical transactions"
            icon={<ShieldAlert size={20} />}
            iconClass="bg-violet-50 text-violet-600"
          />

        </div>

        {/* =====================================================
            REVIEW QUEUE
        ====================================================== */}

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          {/* FILTER HEADER */}

          <div className="border-b border-slate-200 p-5">

            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">

              <div>

                <h2 className="text-base font-bold text-slate-900">
                  Review Queue
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  {filteredReviews.length} review
                  {filteredReviews.length !== 1
                    ? "s"
                    : ""}{" "}
                  found
                </p>

              </div>

              <div className="flex flex-col gap-3 sm:flex-row">

                {/* SEARCH */}

                <div className="relative">

                  <Search
                    size={17}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />

                  <input
                    type="text"
                    value={search}
                    onChange={(e) =>
                      setSearch(e.target.value)
                    }
                    placeholder="Search reviews..."
                    className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:bg-white sm:w-56"
                  />

                </div>

                {/* STATUS */}

                <select
                  value={statusFilter}
                  onChange={(e) =>
                    setStatusFilter(e.target.value)
                  }
                  className="h-10 rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 outline-none focus:border-slate-400"
                >

                  <option value="ALL">
                    All Status
                  </option>

                  <option value="PENDING">
                    Pending
                  </option>

                  <option value="APPROVED">
                    Approved
                  </option>

                  <option value="REJECTED">
                    Rejected
                  </option>

                </select>

                {/* RISK */}

                <select
                  value={riskFilter}
                  onChange={(e) =>
                    setRiskFilter(e.target.value)
                  }
                  className="h-10 rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 outline-none focus:border-slate-400"
                >

                  <option value="ALL">
                    All Risk
                  </option>

                  <option value="LOW">
                    Low
                  </option>

                  <option value="MEDIUM">
                    Medium
                  </option>

                  <option value="HIGH">
                    High
                  </option>

                  <option value="CRITICAL">
                    Critical
                  </option>

                </select>

              </div>

            </div>

          </div>

          {/* ===================================================
              TABLE
          ==================================================== */}

          <div className="overflow-x-auto">

            <table className="w-full min-w-[1050px] text-left">

              <thead className="bg-slate-50">

                <tr className="border-b border-slate-200">

                  <TableHeader>
                    Review
                  </TableHeader>

                  <TableHeader>
                    Order
                  </TableHeader>

                  <TableHeader>
                    Risk
                  </TableHeader>

                  <TableHeader>
                    Reason
                  </TableHeader>

                  <TableHeader>
                    Status
                  </TableHeader>

                  <TableHeader>
                    Reviewed By
                  </TableHeader>

                  <TableHeader>
                    Action
                  </TableHeader>

                </tr>

              </thead>

              <tbody className="divide-y divide-slate-100">

                {filteredReviews.map(
                  (review) => {

                    const isPending =
                      normalizeValue(
                        review.status
                      ) === "PENDING";

                    return (
                      <tr
                        key={review.id}
                        className="transition hover:bg-slate-50/80"
                      >

                        {/* REVIEW */}

                        <td className="px-5 py-4">

                          <div className="font-semibold text-slate-900">
                            #{review.id}
                          </div>

                          {review.created_at && (
                            <div className="mt-1 text-xs text-slate-400">
                              {formatDate(
                                review.created_at
                              )}
                            </div>
                          )}

                        </td>

                        {/* ORDER */}

                        <td className="px-5 py-4">

                          <span className="font-semibold text-slate-700">
                            #{review.order_id}
                          </span>

                        </td>

                        {/* RISK */}

                        <td className="px-5 py-4">

                          <div className="flex items-center gap-3">

                            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-sm font-bold text-slate-700">
                              {review.risk_score ?? 0}
                            </div>

                            <RiskBadge
                              level={
                                review.risk_level
                              }
                            />

                          </div>

                        </td>

                        {/* REASON */}

                        <td className="max-w-xs px-5 py-4">

                          <div className="flex items-start gap-2">

                            <AlertTriangle
                              size={16}
                              className="mt-0.5 shrink-0 text-amber-500"
                            />

                            <span className="text-sm leading-5 text-slate-600">
                              {review.reason ||
                                "No reason provided"}
                            </span>

                          </div>

                        </td>

                        {/* STATUS */}

                        <td className="px-5 py-4">

                          <StatusBadge
                            status={
                              review.status
                            }
                          />

                        </td>

                        {/* REVIEWED BY */}

                        <td className="px-5 py-4">

                          <span className="text-sm text-slate-600">
                            {review.reviewed_by ||
                              "—"}
                          </span>

                        </td>

                        {/* ACTION */}

                        <td className="px-5 py-4">

                          {isPending ? (
                            <div className="flex items-center gap-2">

                              <button
                                type="button"
                                onClick={() =>
                                  openDecisionModal(
                                    review,
                                    DECISIONS.APPROVE
                                  )
                                }
                                disabled={processing}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                              >

                                <CheckCircle2
                                  size={14}
                                />

                                Approve

                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  openDecisionModal(
                                    review,
                                    DECISIONS.REJECT
                                  )
                                }
                                disabled={processing}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                              >

                                <XCircle
                                  size={14}
                                />

                                Reject

                              </button>

                            </div>
                          ) : (
                            <span className="text-xs font-medium text-slate-400">
                              Completed
                            </span>
                          )}

                        </td>

                      </tr>
                    );
                  }
                )}

                {/* EMPTY */}

                {filteredReviews.length === 0 && (

                  <tr>

                    <td
                      colSpan={7}
                      className="px-6 py-16 text-center"
                    >

                      <div className="mx-auto flex max-w-sm flex-col items-center">

                        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                          <ShieldAlert
                            size={25}
                          />
                        </div>

                        <h3 className="mt-4 text-sm font-semibold text-slate-900">
                          No reviews found
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                          Try changing your search
                          or filters.
                        </p>

                      </div>

                    </td>

                  </tr>

                )}

              </tbody>

            </table>

          </div>

        </div>

      </div>

      {/* =======================================================
          DECISION MODAL
      ======================================================== */}

      {selectedReview && (

        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm"
          onMouseDown={(e) => {
            if (
              e.target === e.currentTarget &&
              !processing
            ) {
              closeModal();
            }
          }}
        >

          <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">

            {/* HEADER */}

            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">

              <div>

                <h3 className="text-lg font-bold text-slate-900">

                  {decision ===
                  DECISIONS.APPROVE
                    ? "Approve Review"
                    : "Reject Review"}

                </h3>

                <p className="mt-1 text-sm text-slate-500">
                  Review #{selectedReview.id}
                </p>

              </div>

              <button
                type="button"
                onClick={closeModal}
                disabled={processing}
                className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <X size={20} />
              </button>

            </div>

            {/* CONTENT */}

            <div className="space-y-5 p-6">

              {/* RISK SUMMARY */}

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

                <div className="flex items-center justify-between">

                  <div>

                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Order
                    </p>

                    <p className="mt-1 font-bold text-slate-900">
                      #{selectedReview.order_id}
                    </p>

                  </div>

                  <div className="text-right">

                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Risk Score
                    </p>

                    <p className="mt-1 text-xl font-bold text-slate-900">
                      {selectedReview.risk_score ??
                        0}
                    </p>

                  </div>

                </div>

                <div className="mt-4">

                  <RiskBadge
                    level={
                      selectedReview.risk_level
                    }
                  />

                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {selectedReview.reason ||
                      "No reason provided"}
                  </p>

                </div>

              </div>

              {/* COMMENT */}

              <div>

                <label className="mb-2 block text-sm font-semibold text-slate-700">
                  Review Comment
                </label>

                <textarea
                  value={comment}
                  onChange={(e) =>
                    setComment(
                      e.target.value
                    )
                  }
                  rows={4}
                  placeholder="Enter review comment..."
                  disabled={processing}
                  className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-100 disabled:bg-slate-50"
                />

              </div>

              {/* WARNING */}

              <div
                className={
                  decision ===
                  DECISIONS.APPROVE
                    ? "flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
                    : "flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
                }
              >

                {decision ===
                DECISIONS.APPROVE ? (
                  <CheckCircle2
                    size={18}
                    className="mt-0.5 shrink-0"
                  />
                ) : (
                  <AlertTriangle
                    size={18}
                    className="mt-0.5 shrink-0"
                  />
                )}

                <p>

                  {decision ===
                  DECISIONS.APPROVE
                    ? "Approving this review will mark the associated order as APPROVED. Reserved stock will remain consumed."
                    : "Rejecting this review will mark the associated order as REJECTED and return the reserved quantity to inventory."}

                </p>

              </div>

            </div>

            {/* FOOTER */}

            <div className="flex justify-end gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">

              <button
                type="button"
                onClick={closeModal}
                disabled={processing}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleDecision}
                disabled={processing}
                className={
                  decision ===
                  DECISIONS.APPROVE
                    ? "inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                    : "inline-flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                }
              >

                {processing ? (
                  <>
                    <RefreshCw
                      size={16}
                      className="animate-spin"
                    />

                    Processing...
                  </>
                ) : decision ===
                  DECISIONS.APPROVE ? (
                  <>
                    <CheckCircle2
                      size={16}
                    />

                    Confirm Approval
                  </>
                ) : (
                  <>
                    <XCircle size={16} />

                    Confirm Rejection
                  </>
                )}

              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}

// =============================================================
// STAT CARD
// =============================================================

function StatCard({
  title,
  value,
  subtitle,
  icon,
  iconClass,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">

      <div className="flex items-start justify-between">

        <div>

          <p className="text-sm font-medium text-slate-500">
            {title}
          </p>

          <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {value}
          </p>

          <p className="mt-1 text-xs text-slate-400">
            {subtitle}
          </p>

        </div>

        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
        >
          {icon}
        </div>

      </div>

    </div>
  );
}

// =============================================================
// TABLE HEADER
// =============================================================

function TableHeader({ children }) {
  return (
    <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
      {children}
    </th>
  );
}

// =============================================================
// STATUS BADGE
// =============================================================

function StatusBadge({ status }) {
  const normalized =
    normalizeValue(status);

  const styles = {
    PENDING:
      "border-amber-200 bg-amber-50 text-amber-700",

    APPROVED:
      "border-emerald-200 bg-emerald-50 text-emerald-700",

    REJECTED:
      "border-red-200 bg-red-50 text-red-700",

    MANUAL_REVIEW_REQUIRED:
      "border-violet-200 bg-violet-50 text-violet-700",
  };

  const labels = {
    PENDING: "Pending",

    APPROVED: "Approved",

    REJECTED: "Rejected",

    MANUAL_REVIEW_REQUIRED:
      "Manual Review",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${
        styles[normalized] ||
        "border-slate-200 bg-slate-50 text-slate-600"
      }`}
    >
      {labels[normalized] ||
        status ||
        "Unknown"}
    </span>
  );
}

// =============================================================
// RISK BADGE
// =============================================================

function RiskBadge({ level }) {
  const normalized =
    normalizeValue(level);

  const styles = {
    LOW:
      "border-emerald-200 bg-emerald-50 text-emerald-700",

    MEDIUM:
      "border-amber-200 bg-amber-50 text-amber-700",

    HIGH:
      "border-red-200 bg-red-50 text-red-700",

    CRITICAL:
      "border-red-300 bg-red-100 text-red-800",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${
        styles[normalized] ||
        "border-slate-200 bg-slate-50 text-slate-600"
      }`}
    >
      {level || "Unknown"}
    </span>
  );
}

// =============================================================
// NORMALIZE VALUE
// =============================================================

function normalizeValue(value) {
  return String(value || "")
    .trim()
    .toUpperCase();
}

// =============================================================
// API ERROR EXTRACTION
// =============================================================

function extractApiError(
  err,
  fallback
) {
  const detail =
    err?.response?.data?.detail;

  // FastAPI commonly returns:
  //
  // { "detail": "some message" }
  //
  if (typeof detail === "string") {
    return detail;
  }

  // Sometimes detail can be an array/object.
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item?.msg) {
          return item.msg;
        }

        return JSON.stringify(item);
      })
      .join(", ");
  }

  if (
    detail &&
    typeof detail === "object"
  ) {
    if (detail.message) {
      return String(detail.message);
    }

    if (detail.error) {
      return String(detail.error);
    }

    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  if (
    typeof err?.response?.data ===
    "string"
  ) {
    return err.response.data;
  }

  if (err?.message) {
    return err.message;
  }

  return fallback;
}

// =============================================================
// DATE FORMAT
// =============================================================

function formatDate(date) {
  if (!date) {
    return "—";
  }

  try {
    const parsedDate = new Date(date);

    if (
      Number.isNaN(
        parsedDate.getTime()
      )
    ) {
      return String(date);
    }

    return parsedDate.toLocaleString(
      "en-IN",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }
    );
  } catch {
    return String(date);
  }
}

// =============================================================
// EXPORT
// =============================================================

export default ManualReviews;