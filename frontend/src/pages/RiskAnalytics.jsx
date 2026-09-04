import { useEffect, useMemo, useRef, useState } from "react";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  XCircle,
  Activity,
  BarChart3,
  Wifi,
  WifiOff,
  IndianRupee,
} from "lucide-react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  LineChart,
  Line,
} from "recharts";

import {
  getRiskAnalyticsSummary,
  getRiskDistribution,
  getStatusDistribution,
  getRecentRiskActivity,
  getRiskScoreDistribution,
  getRiskReasons,
  getOrderTrend,
} from "../services/api";

import {
  connectToOrderEvents,
  disconnectFromOrderEvents,
} from "../services/eventService";

// ============================================================
// CONSTANTS
// ============================================================

const RISK_COLORS = {
  LOW: "#10b981",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
  CRITICAL: "#7c3aed",
};

const STATUS_COLORS = {
  APPROVED: "#10b981",
  APPROVE: "#10b981",
  REJECTED: "#ef4444",
  REJECT: "#ef4444",
  MANUAL_REVIEW_REQUIRED: "#f59e0b",
  MANUAL_REVIEW: "#f59e0b",
  DISCOUNT_ADJUSTED: "#6366f1",
};

const EMPTY_RISK_SCORE_DATA = [
  {
    range: "0-20",
    count: 0,
  },
  {
    range: "21-40",
    count: 0,
  },
  {
    range: "41-60",
    count: 0,
  },
  {
    range: "61-80",
    count: 0,
  },
  {
    range: "81-100",
    count: 0,
  },
];

// ============================================================
// HELPERS
// ============================================================

function safeNumber(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function normalizeRiskLevel(value) {
  if (!value) {
    return null;
  }

  return String(value)
    .trim()
    .toUpperCase();
}

function normalizeStatus(value) {
  if (!value) {
    return null;
  }

  const normalized = String(value)
    .trim()
    .toUpperCase();

  if (normalized === "APPROVE") {
    return "APPROVED";
  }

  if (normalized === "REJECT") {
    return "REJECTED";
  }

  if (
    normalized === "MANUAL_REVIEW" ||
    normalized === "REVIEW"
  ) {
    return "MANUAL_REVIEW_REQUIRED";
  }

  return normalized;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

function RiskAnalytics() {
  // ==========================================================
  // STATE
  // ==========================================================

  const [summary, setSummary] = useState(null);

  const [
    riskDistributionData,
    setRiskDistributionData,
  ] = useState(null);

  const [
    statusDistributionData,
    setStatusDistributionData,
  ] = useState(null);

  const [
    riskScoreDistributionData,
    setRiskScoreDistributionData,
  ] = useState([]);

  const [
    riskReasonsData,
    setRiskReasonsData,
  ] = useState([]);

  const [
    orderTrendData,
    setOrderTrendData,
  ] = useState([]);

  const [
    recentActivity,
    setRecentActivity,
  ] = useState([]);

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] = useState("");

  const [lastUpdated, setLastUpdated] =
    useState(null);

  const [isLive, setIsLive] =
    useState(false);

  // ==========================================================
  // REFS
  // ==========================================================

  const refreshInProgressRef =
    useRef(false);

  const refreshTimerRef =
    useRef(null);

  const isMountedRef =
    useRef(false);

  const sseConnectedRef =
    useRef(false);

  // ==========================================================
  // LOAD ANALYTICS
  // ==========================================================

  const loadAnalytics = async (
    silent = false
  ) => {
    if (refreshInProgressRef.current) {
      return;
    }

    refreshInProgressRef.current = true;

    try {
      if (!silent) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError("");

      const [
        summaryResponse,
        riskResponse,
        statusResponse,
        recentResponse,
        riskScoreResponse,
        reasonsResponse,
        trendResponse,
      ] = await Promise.all([
        getRiskAnalyticsSummary(),
        getRiskDistribution(),
        getStatusDistribution(),
        getRecentRiskActivity(20),
        getRiskScoreDistribution(),
        getRiskReasons(5),
        getOrderTrend(),
      ]);

      if (!isMountedRef.current) {
        return;
      }

      // ======================================================
      // SUMMARY
      // ======================================================

      setSummary(
        summaryResponse || {}
      );

      // ======================================================
      // RISK DISTRIBUTION
      // ======================================================

      setRiskDistributionData(
        riskResponse?.distribution ||
          {}
      );

      // ======================================================
      // STATUS DISTRIBUTION
      // ======================================================

      setStatusDistributionData(
        statusResponse?.distribution ||
          {}
      );

      // ======================================================
      // RECENT ACTIVITY
      // ======================================================

      const activities =
        Array.isArray(
          recentResponse?.activities
        )
          ? recentResponse.activities
          : [];

      setRecentActivity(activities);

      // ======================================================
      // RISK SCORE DISTRIBUTION
      // ======================================================

      const scoreDistribution =
        Array.isArray(
          riskScoreResponse?.distribution
        )
          ? riskScoreResponse.distribution
          : [];

      setRiskScoreDistributionData(
        scoreDistribution
      );

      // ======================================================
      // RISK REASONS
      // ======================================================

      const reasons =
        Array.isArray(
          reasonsResponse?.reasons
        )
          ? reasonsResponse.reasons
          : [];

      setRiskReasonsData(reasons);

      // ======================================================
      // ORDER TREND
      // ======================================================

      const trend =
        Array.isArray(
          trendResponse?.trend
        )
          ? trendResponse.trend
          : [];

      setOrderTrendData(trend);

      // ======================================================
      // TIMESTAMP
      // ======================================================

      setLastUpdated(
        new Date()
      );
    } catch (err) {
      console.error(
        "Risk analytics error:",
        err
      );

      if (!isMountedRef.current) {
        return;
      }

      const backendMessage =
        err?.response?.data?.detail;

      setError(
        backendMessage ||
          err?.message ||
          "Unable to load risk analytics."
      );
    } finally {
      refreshInProgressRef.current =
        false;

      if (isMountedRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  };

  // ==========================================================
  // DEBOUNCED LIVE REFRESH
  //
  // If several SSE events arrive together, don't make
  // several API requests.
  // ==========================================================

  const scheduleAnalyticsRefresh =
    () => {
      if (
        refreshTimerRef.current
      ) {
        clearTimeout(
          refreshTimerRef.current
        );
      }

      refreshTimerRef.current =
        setTimeout(() => {
          if (
            isMountedRef.current
          ) {
            loadAnalytics(true);
          }
        }, 500);
    };

  // ==========================================================
  // SSE HANDLERS
  // ==========================================================

  const handleConnected = (
    data
  ) => {
    console.log(
      "Risk Analytics SSE connected:",
      data
    );

    sseConnectedRef.current =
      true;

    if (isMountedRef.current) {
      setIsLive(true);
    }
  };

  const handleOrderCreated = (
    data
  ) => {
    console.log(
      "Risk Analytics - order created:",
      data
    );

    scheduleAnalyticsRefresh();
  };

  const handleOrderProcessed = (
    data
  ) => {
    console.log(
      "Risk Analytics - order processed:",
      data
    );

    scheduleAnalyticsRefresh();
  };

  const handleManualReviewCompleted =
    (data) => {
      console.log(
        "Risk Analytics - manual review completed:",
        data
      );

      scheduleAnalyticsRefresh();
    };

  const handleSSEError = (
    error
  ) => {
    console.error(
      "Risk Analytics SSE error:",
      error
    );

    sseConnectedRef.current =
      false;

    if (isMountedRef.current) {
      setIsLive(false);
    }
  };

  // ==========================================================
  // SSE CONNECT
  // ==========================================================

  const connectSSE = () => {
    if (
      !isMountedRef.current
    ) {
      return;
    }

    console.log(
      "Connecting to global order event stream..."
    );

    // IMPORTANT:
    // Disconnect first so visibility changes don't
    // create duplicate EventSource connections.

    try {
      disconnectFromOrderEvents();
    } catch (error) {
      console.warn(
        "SSE disconnect warning:",
        error
      );
    }

    sseConnectedRef.current =
      false;

    connectToOrderEvents({
      onConnected:
        handleConnected,

      onOrderCreated:
        handleOrderCreated,

      onOrderProcessed:
        handleOrderProcessed,

      onManualReviewCompleted:
        handleManualReviewCompleted,

      onError:
        handleSSEError,
    });
  };

  // ==========================================================
  // INITIAL LOAD + SSE
  // ==========================================================

  useEffect(() => {
    isMountedRef.current = true;

    // Initial analytics request
    loadAnalytics(false);

    // Connect SSE
    connectSSE();

    // ========================================================
    // TAB VISIBILITY
    // ========================================================

    const handleVisibilityChange =
      () => {
        if (
          document.visibilityState ===
          "visible"
        ) {
          console.log(
            "User returned to Risk Analytics."
          );

          // Refresh analytics
          loadAnalytics(true);

          // Reconnect SSE cleanly
          connectSSE();
        }
      };

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange
    );

    // ========================================================
    // CLEANUP
    // ========================================================

    return () => {
      isMountedRef.current =
        false;

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
      );

      if (
        refreshTimerRef.current
      ) {
        clearTimeout(
          refreshTimerRef.current
        );
      }

      try {
        disconnectFromOrderEvents();
      } catch (error) {
        console.warn(
          "SSE cleanup warning:",
          error
        );
      }

      sseConnectedRef.current =
        false;
    };
  }, []);

  // ==========================================================
  // SAFE BACKEND DATA
  // ==========================================================

  const orders =
    summary?.orders || {};

  const rates =
    summary?.rates || {};

  const risk =
    summary?.risk || {};

  const financial =
    summary?.financial || {};

  const reviews =
    summary?.reviews || {};

  // ==========================================================
  // BASIC METRICS
  // ==========================================================

  const totalOrders =
    safeNumber(
      orders.total
    );

  const approvedOrders =
    safeNumber(
      orders.approved
    );

  const rejectedOrders =
    safeNumber(
      orders.rejected
    );

  const manualReviewOrders =
    safeNumber(
      orders.manual_review
    );

  const discountAdjustedOrders =
    safeNumber(
      orders.discount_adjusted
    );

  // ==========================================================
  // RATES
  // ==========================================================

  const approvalRate =
    safeNumber(
      rates.approval_rate
    );

  const rejectionRate =
    safeNumber(
      rates.rejection_rate
    );

  const manualReviewRate =
    rates.manual_review_rate !==
      undefined &&
    rates.manual_review_rate !==
      null
      ? safeNumber(
          rates.manual_review_rate
        )
      : totalOrders > 0
      ? (
          manualReviewOrders /
          totalOrders
        ) * 100
      : 0;

  // ==========================================================
  // RISK METRICS
  // ==========================================================

  const pendingReviews =
    safeNumber(
      reviews.pending,
      manualReviewOrders
    );

  const lowRisk =
    safeNumber(
      risk.low
    );

  const mediumRisk =
    safeNumber(
      risk.medium
    );

  const highRisk =
    safeNumber(
      risk.high
    );

  const criticalRisk =
    safeNumber(
      risk.critical
    );

  const highRiskReviews =
    risk.high_risk_total !==
      undefined &&
    risk.high_risk_total !==
      null
      ? safeNumber(
          risk.high_risk_total
        )
      : highRisk +
        criticalRisk;

  const averageRiskScore =
    safeNumber(
      risk.average_score
    );

  const totalRiskReviews =
    reviews.total !==
      undefined &&
    reviews.total !== null
      ? safeNumber(
          reviews.total
        )
      : lowRisk +
        mediumRisk +
        highRisk +
        criticalRisk;

  // ==========================================================
  // RISK DISTRIBUTION
  // ==========================================================

  const riskDistribution =
    useMemo(() => {
      const distribution =
        riskDistributionData ||
        {};

      return [
        {
          name: "Low",
          value: safeNumber(
            distribution.LOW ??
              distribution.low ??
              lowRisk
          ),
          key: "LOW",
        },

        {
          name: "Medium",
          value: safeNumber(
            distribution.MEDIUM ??
              distribution.medium ??
              mediumRisk
          ),
          key: "MEDIUM",
        },

        {
          name: "High",
          value: safeNumber(
            distribution.HIGH ??
              distribution.high ??
              highRisk
          ),
          key: "HIGH",
        },

        {
          name: "Critical",
          value: safeNumber(
            distribution.CRITICAL ??
              distribution.critical ??
              criticalRisk
          ),
          key: "CRITICAL",
        },
      ].filter(
        (item) =>
          item.value > 0
      );
    }, [
      riskDistributionData,
      lowRisk,
      mediumRisk,
      highRisk,
      criticalRisk,
    ]);

  // ==========================================================
  // STATUS DISTRIBUTION
  // ==========================================================

  const orderStatusData =
    useMemo(() => {
      const distribution =
        statusDistributionData ||
        {};

      const approved =
        safeNumber(
          distribution.APPROVED ??
            distribution.approve ??
            distribution.APPROVE ??
            approvedOrders
        );

      const rejected =
        safeNumber(
          distribution.REJECTED ??
            distribution.reject ??
            distribution.REJECT ??
            rejectedOrders
        );

      const manualReview =
        safeNumber(
          distribution.MANUAL_REVIEW_REQUIRED ??
            distribution.MANUAL_REVIEW ??
            manualReviewOrders
        );

      const discountAdjusted =
        safeNumber(
          distribution.DISCOUNT_ADJUSTED ??
            discountAdjustedOrders
        );

      return [
        {
          name: "Approved",
          value: approved,
          key: "APPROVED",
        },

        {
          name: "Rejected",
          value: rejected,
          key: "REJECTED",
        },

        {
          name: "Manual Review",
          value: manualReview,
          key: "MANUAL_REVIEW_REQUIRED",
        },

        {
          name: "Discount Adjusted",
          value: discountAdjusted,
          key: "DISCOUNT_ADJUSTED",
        },
      ].filter(
        (item) =>
          item.value > 0
      );
    }, [
      statusDistributionData,
      approvedOrders,
      rejectedOrders,
      manualReviewOrders,
      discountAdjustedOrders,
    ]);

  // ==========================================================
  // RISK SCORE DISTRIBUTION
  // ==========================================================

  const riskScoreData =
    useMemo(() => {
      const backendData =
        riskScoreDistributionData ||
        [];

      if (
        backendData.length > 0
      ) {
        return backendData.map(
          (item) => ({
            range:
              item.range ||
              "Unknown",

            count: safeNumber(
              item.count
            ),
          })
        );
      }

      return EMPTY_RISK_SCORE_DATA;
    }, [
      riskScoreDistributionData,
    ]);

  // ==========================================================
  // RISK REASONS
  // ==========================================================

  const riskReasons =
    useMemo(() => {
      return (
        riskReasonsData || []
      )
        .map(
          (item) => ({
            reason:
              item?.reason ||
              "Unknown reason",

            count: safeNumber(
              item?.count
            ),
          })
        )
        .filter(
          (item) =>
            item.count > 0
        )
        .sort(
          (a, b) =>
            b.count -
            a.count
        )
        .slice(0, 5);
    }, [
      riskReasonsData,
    ]);

  // ==========================================================
  // RISK SCORE TREND
  //
  // Uses ORDER_DECISION events from recent activity.
  // ==========================================================

  const riskTrend =
    useMemo(() => {
      const dateMap = {};

      (
        recentActivity || []
      ).forEach(
        (activity) => {
          if (
            String(
              activity?.event_type
            ).toUpperCase() !==
            "ORDER_DECISION"
          ) {
            return;
          }

          if (
            !activity?.created_at
          ) {
            return;
          }

          if (
            activity.risk_score ===
              null ||
            activity.risk_score ===
              undefined
          ) {
            return;
          }

          const date =
            new Date(
              activity.created_at
            );

          if (
            Number.isNaN(
              date.getTime()
            )
          ) {
            return;
          }

          const key =
            date.toLocaleDateString(
              "en-IN",
              {
                day: "2-digit",
                month: "short",
              }
            );

          if (!dateMap[key]) {
            dateMap[key] = {
              date: key,
              timestamp:
                date.getTime(),
              scoreTotal: 0,
              count: 0,
            };
          }

          dateMap[
            key
          ].scoreTotal +=
            safeNumber(
              activity.risk_score
            );

          dateMap[
            key
          ].count++;
        }
      );

      return Object.values(
        dateMap
      )
        .sort(
          (a, b) =>
            a.timestamp -
            b.timestamp
        )
        .map(
          (item) => ({
            date: item.date,

            averageScore:
              item.count > 0
                ? Number(
                    (
                      item.scoreTotal /
                      item.count
                    ).toFixed(2)
                  )
                : 0,
          })
        );
    }, [
      recentActivity,
    ]);

  // ==========================================================
  // ORDER TREND
  // ==========================================================

  const orderTrend =
    useMemo(() => {
      return (
        orderTrendData || []
      )
        .map(
          (item) => ({
            date:
              item.date,

            orders:
              safeNumber(
                item.orders
              ),

            approved:
              safeNumber(
                item.approved
              ),

            rejected:
              safeNumber(
                item.rejected
              ),

            review:
              safeNumber(
                item.review
              ),

            discount_adjusted:
              safeNumber(
                item.discount_adjusted
              ),
          })
        )
        .sort(
          (a, b) =>
            new Date(
              a.date
            ) -
            new Date(
              b.date
            )
        );
    }, [
      orderTrendData,
    ]);

  // ==========================================================
  // LOADING SCREEN
  // ==========================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 lg:p-8">
        <div className="mx-auto max-w-7xl">

          <div className="mb-8">
            <div className="h-9 w-72 animate-pulse rounded-lg bg-slate-200" />

            <div className="mt-3 h-4 w-96 animate-pulse rounded bg-slate-200" />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map(
              (item) => (
                <div
                  key={item}
                  className="h-32 animate-pulse rounded-2xl bg-white shadow-sm"
                />
              )
            )}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            {[1, 2].map(
              (item) => (
                <div
                  key={item}
                  className="h-96 animate-pulse rounded-2xl bg-white shadow-sm"
                />
              )
            )}
          </div>

        </div>
      </div>
    );
  }

  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">

      <div className="mx-auto max-w-7xl">

        {/* ====================================================
            HEADER
        ==================================================== */}

        <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">

          <div className="flex items-center gap-3">

            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-900 text-white shadow-sm">
              <TrendingUp size={23} />
            </div>

            <div>

              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                Risk Analytics
              </h1>

              <p className="mt-1 text-sm text-slate-500">
                Monitor AI-powered payment risk and transaction performance
              </p>

            </div>

          </div>

          <div className="flex items-center gap-3">

            {/* LIVE STATUS */}

            <div
              className={`hidden items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold sm:flex ${
                isLive
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-red-200 bg-red-50 text-red-700"
              }`}
            >

              {isLive ? (
                <>
                  <span className="relative flex h-2 w-2">

                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />

                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />

                  </span>

                  Live
                </>
              ) : (
                <>
                  <WifiOff size={14} />

                  Reconnecting...
                </>
              )}

            </div>

            {/* REFRESH */}

            <button
              onClick={() =>
                loadAnalytics(true)
              }
              disabled={refreshing}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
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
                ? "Updating..."
                : "Refresh"}

            </button>

          </div>

        </div>

        {/* ====================================================
            LIVE BAR
        ==================================================== */}

        <div className="mb-6 flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">

          <div className="flex items-center gap-3">

            {isLive ? (
              <Wifi
                size={17}
                className="text-emerald-600"
              />
            ) : (
              <WifiOff
                size={17}
                className="text-red-500"
              />
            )}

            <div>

              <p className="text-sm font-semibold text-slate-800">

                {isLive
                  ? "Real-time monitoring active"
                  : "Real-time connection unavailable"}

              </p>

              <p className="text-xs text-slate-500">

                {isLive
                  ? "Analytics update automatically when orders or reviews change."
                  : "Analytics still works. Trying to reconnect to the global order event stream..."}

              </p>

            </div>

          </div>

          <div className="hidden text-right sm:block">

            <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
              Last updated
            </p>

            <p className="mt-1 text-xs font-semibold text-slate-600">

              {lastUpdated
                ? lastUpdated.toLocaleTimeString(
                    "en-IN",
                    {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    }
                  )
                : "--"}

            </p>

          </div>

        </div>

        {/* ====================================================
            ERROR
        ==================================================== */}

        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">

            <AlertTriangle
              size={18}
            />

            <span>
              {error}
            </span>

          </div>
        )}

        {/* ====================================================
            KPI CARDS
        ==================================================== */}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <MetricCard
            title="Approval Rate"
            value={`${approvalRate.toFixed(
              1
            )}%`}
            description={`${approvedOrders} approved orders`}
            icon={
              <CheckCircle2 size={20} />
            }
            iconClass="bg-emerald-50 text-emerald-600"
          />

          <MetricCard
            title="Rejection Rate"
            value={`${rejectionRate.toFixed(
              1
            )}%`}
            description={`${rejectedOrders} rejected orders`}
            icon={
              <XCircle size={20} />
            }
            iconClass="bg-red-50 text-red-600"
          />

          <MetricCard
            title="Manual Review Rate"
            value={`${manualReviewRate.toFixed(
              1
            )}%`}
            description={`${pendingReviews} pending reviews`}
            icon={
              <Clock3 size={20} />
            }
            iconClass="bg-amber-50 text-amber-600"
          />

          <MetricCard
            title="Average Risk Score"
            value={averageRiskScore.toFixed(
              1
            )}
            description={`${highRiskReviews} high-risk reviews`}
            icon={
              <ShieldAlert size={20} />
            }
            iconClass="bg-violet-50 text-violet-600"
          />

        </div>

        {/* ====================================================
            SUMMARY
        ==================================================== */}

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-4">

          <SummaryItem
            icon={
              <Activity size={19} />
            }
            label="Total Orders"
            value={totalOrders}
          />

          <SummaryItem
            icon={
              <BarChart3 size={19} />
            }
            label="Risk Decisions"
            value={totalRiskReviews}
          />

          <SummaryItem
            icon={
              <ShieldAlert size={19} />
            }
            label="High Risk"
            value={highRiskReviews}
          />

          <SummaryItem
            icon={
              <IndianRupee size={19} />
            }
            label="Total Order Value"
            value={`₹${safeNumber(
              financial.total_order_value
            ).toLocaleString(
              "en-IN",
              {
                maximumFractionDigits: 2,
              }
            )}`}
          />

        </div>

        {/* ====================================================
            CHART ROW 1
        ==================================================== */}

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* RISK DISTRIBUTION */}

          <ChartCard
            title="Risk Distribution"
            description="Transactions grouped by AI risk level"
          >

            {riskDistribution.length ===
            0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer
                width="100%"
                height={320}
              >

                <PieChart>

                  <Pie
                    data={
                      riskDistribution
                    }
                    cx="50%"
                    cy="50%"
                    innerRadius={75}
                    outerRadius={110}
                    paddingAngle={4}
                    dataKey="value"
                  >

                    {riskDistribution.map(
                      (entry) => (
                        <Cell
                          key={
                            entry.key
                          }
                          fill={
                            RISK_COLORS[
                              entry.key
                            ] ||
                            "#6366f1"
                          }
                        />
                      )
                    )}

                  </Pie>

                  <Tooltip />

                  <Legend />

                </PieChart>

              </ResponsiveContainer>
            )}

          </ChartCard>

          {/* DECISION DISTRIBUTION */}

          <ChartCard
            title="Decision Distribution"
            description="Current transaction decision breakdown"
          >

            {orderStatusData.length ===
            0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer
                width="100%"
                height={320}
              >

                <PieChart>

                  <Pie
                    data={
                      orderStatusData
                    }
                    cx="50%"
                    cy="50%"
                    outerRadius={110}
                    dataKey="value"
                    paddingAngle={3}
                  >

                    {orderStatusData.map(
                      (entry) => (
                        <Cell
                          key={
                            entry.key
                          }
                          fill={
                            STATUS_COLORS[
                              entry.key
                            ] ||
                            "#6366f1"
                          }
                        />
                      )
                    )}

                  </Pie>

                  <Tooltip />

                  <Legend />

                </PieChart>

              </ResponsiveContainer>
            )}

          </ChartCard>

        </div>

        {/* ====================================================
            CHART ROW 2
        ==================================================== */}

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* RISK SCORE DISTRIBUTION */}

          <ChartCard
            title="Risk Score Distribution"
            description="Risk decisions grouped by AI risk score"
          >

            <ResponsiveContainer
              width="100%"
              height={320}
            >

              <BarChart
                data={
                  riskScoreData
                }
                margin={{
                  top: 10,
                  right: 10,
                  left: -20,
                  bottom: 0,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                />

                <XAxis
                  dataKey="range"
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                />

                <Tooltip />

                <Bar
                  dataKey="count"
                  name="Risk Decisions"
                  fill="#6366f1"
                  radius={[
                    6,
                    6,
                    0,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          </ChartCard>

          {/* TRANSACTION TREND */}

          <ChartCard
            title="Transaction Trend"
            description="Daily approved, rejected and manual review decisions"
          >

            {orderTrend.length ===
            0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer
                width="100%"
                height={320}
              >

                <LineChart
                  data={
                    orderTrend
                  }
                  margin={{
                    top: 10,
                    right: 10,
                    left: -20,
                    bottom: 0,
                  }}
                >

                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                  />

                  <YAxis
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={false}
                  />

                  <Tooltip />

                  <Legend />

                  <Line
                    type="monotone"
                    dataKey="approved"
                    name="Approved"
                    stroke="#10b981"
                    strokeWidth={3}
                    dot={false}
                  />

                  <Line
                    type="monotone"
                    dataKey="rejected"
                    name="Rejected"
                    stroke="#ef4444"
                    strokeWidth={3}
                    dot={false}
                  />

                  <Line
                    type="monotone"
                    dataKey="review"
                    name="Manual Review"
                    stroke="#f59e0b"
                    strokeWidth={3}
                    dot={false}
                  />

                </LineChart>

              </ResponsiveContainer>
            )}

          </ChartCard>

        </div>

        {/* ====================================================
            RISK SCORE TREND
        ==================================================== */}

        {riskTrend.length > 0 && (
          <div className="mt-6">

            <ChartCard
              title="Average Risk Score Trend"
              description="Average AI risk score from recent order decisions"
            >

              <ResponsiveContainer
                width="100%"
                height={300}
              >

                <LineChart
                  data={riskTrend}
                  margin={{
                    top: 10,
                    right: 10,
                    left: -20,
                    bottom: 0,
                  }}
                >

                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                  />

                  <YAxis
                    domain={[0, 100]}
                    tickLine={false}
                    axisLine={false}
                  />

                  <Tooltip />

                  <Line
                    type="monotone"
                    dataKey="averageScore"
                    name="Average Risk Score"
                    stroke="#7c3aed"
                    strokeWidth={3}
                    dot
                  />

                </LineChart>

              </ResponsiveContainer>

            </ChartCard>

          </div>
        )}

        {/* ====================================================
            TOP RISK REASONS
        ==================================================== */}

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 px-6 py-5">

            <h2 className="text-base font-bold text-slate-900">
              Top Risk Signals
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Most frequently detected signals from risk decisions
            </p>

          </div>

          <div className="divide-y divide-slate-100">

            {riskReasons.length ===
            0 ? (
              <div className="p-10 text-center text-sm text-slate-500">
                No risk signals available.
              </div>
            ) : (
              riskReasons.map(
                (
                  item,
                  index
                ) => (
                  <div
                    key={`${item.reason}-${index}`}
                    className="flex items-center gap-4 px-6 py-4"
                  >

                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-bold text-slate-600">
                      {index + 1}
                    </div>

                    <div className="min-w-0 flex-1">

                      <p className="truncate text-sm font-semibold text-slate-800">
                        {item.reason}
                      </p>

                    </div>

                    <div className="flex items-center gap-3">

                      <div className="hidden h-2 w-32 overflow-hidden rounded-full bg-slate-100 sm:block">

                        <div
                          className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                          style={{
                            width: `${
                              totalRiskReviews >
                              0
                                ? Math.min(
                                    100,
                                    (item.count /
                                      totalRiskReviews) *
                                      100
                                  )
                                : 0
                            }%`,
                          }}
                        />

                      </div>

                      <span className="min-w-8 text-right text-sm font-bold text-slate-700">
                        {item.count}
                      </span>

                    </div>

                  </div>
                )
              )
            )}

          </div>

        </div>

        {/* ====================================================
            RECENT ACTIVITY
        ==================================================== */}

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 px-6 py-5">

            <h2 className="text-base font-bold text-slate-900">
              Recent Risk Activity
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Latest audit and risk decision events
            </p>

          </div>

          {recentActivity.length ===
          0 ? (
            <div className="p-10 text-center text-sm text-slate-500">
              No recent activity available.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">

              {recentActivity.map(
                (activity) => {

                  const riskLevel =
                    normalizeRiskLevel(
                      activity.risk_level
                    );

                  const status =
                    normalizeStatus(
                      activity.new_status ||
                        activity.status
                    );

                  return (
                    <div
                      key={
                        activity.id
                      }
                      className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center sm:justify-between"
                    >

                      <div className="min-w-0 flex-1">

                        <div className="flex flex-wrap items-center gap-2">

                          <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600">
                            {activity.event_type ||
                              "EVENT"}
                          </span>

                          {status && (
                            <span
                              className="rounded-md px-2 py-1 text-[11px] font-bold"
                              style={{
                                backgroundColor:
                                  `${
                                    STATUS_COLORS[
                                      status
                                    ] ||
                                    "#6366f1"
                                  }20`,

                                color:
                                  STATUS_COLORS[
                                    status
                                  ] ||
                                  "#6366f1",
                              }}
                            >
                              {status}
                            </span>
                          )}

                          {riskLevel && (
                            <span
                              className="rounded-md px-2 py-1 text-[11px] font-bold"
                              style={{
                                backgroundColor:
                                  `${
                                    RISK_COLORS[
                                      riskLevel
                                    ] ||
                                    "#6366f1"
                                  }20`,

                                color:
                                  RISK_COLORS[
                                    riskLevel
                                  ] ||
                                  "#6366f1",
                              }}
                            >
                              {riskLevel}
                            </span>
                          )}

                        </div>

                        <p className="mt-2 truncate text-sm font-semibold text-slate-800">
                          {activity.message ||
                            "Risk activity recorded"}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">

                          Order #
                          {activity.order_id ??
                            "--"}

                          {" • "}

                          {activity.created_at
                            ? new Date(
                                activity.created_at
                              ).toLocaleString(
                                "en-IN"
                              )
                            : "--"}

                        </p>

                      </div>

                      <div className="flex items-center gap-4">

                        {activity.risk_score !==
                          null &&
                          activity.risk_score !==
                            undefined && (
                            <div className="text-right">

                              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                                Risk Score
                              </p>

                              <p className="mt-1 text-lg font-bold text-slate-900">

                                {safeNumber(
                                  activity.risk_score
                                ).toFixed(
                                  1
                                )}

                              </p>

                            </div>
                          )}

                      </div>

                    </div>
                  );
                }
              )}

            </div>
          )}

        </div>

        {/* ====================================================
            FOOTER
        ==================================================== */}

        <div className="mt-6 flex flex-col items-center justify-between gap-2 pb-4 text-xs text-slate-400 sm:flex-row">

          <span>
            PayPilot AI Risk Engine
          </span>

          <span>
            Real-time risk monitoring
          </span>

        </div>

      </div>

    </div>
  );
}

// ============================================================
// METRIC CARD
// ============================================================

function MetricCard({
  title,
  value,
  description,
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

          <p className="mt-2 text-xs font-medium text-slate-500">
            {description}
          </p>

        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconClass}`}
        >
          {icon}
        </div>

      </div>

    </div>
  );
}

// ============================================================
// SUMMARY ITEM
// ============================================================

function SummaryItem({
  icon,
  label,
  value,
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
        {icon}
      </div>

      <div>

        <p className="text-xs font-medium text-slate-500">
          {label}
        </p>

        <p className="mt-1 text-2xl font-bold text-slate-900">
          {value}
        </p>

      </div>

    </div>
  );
}

// ============================================================
// CHART CARD
// ============================================================

function ChartCard({
  title,
  description,
  children,
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

      <div className="border-b border-slate-200 px-6 py-5">

        <h2 className="text-base font-bold text-slate-900">
          {title}
        </h2>

        <p className="mt-1 text-sm text-slate-500">
          {description}
        </p>

      </div>

      <div className="p-5">
        {children}
      </div>

    </div>
  );
}

// ============================================================
// EMPTY CHART
// ============================================================

function EmptyChart() {
  return (
    <div className="flex h-[320px] flex-col items-center justify-center text-center">

      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
        <BarChart3 size={22} />
      </div>

      <p className="mt-3 text-sm font-semibold text-slate-600">
        No data available
      </p>

      <p className="mt-1 text-xs text-slate-400">
        Analytics will appear when transactions are processed.
      </p>

    </div>
  );
}

export default RiskAnalytics;