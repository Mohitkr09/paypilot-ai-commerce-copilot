import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  DollarSign,
  Package,
  RefreshCw,
  Search,
  ShieldAlert,
  ShoppingCart,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";

import { getAnalyticsDashboard } from "../services/api";

// =============================================================
// API BASE URL
// =============================================================

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

// =============================================================
// DASHBOARD
// =============================================================

function Dashboard() {
  // -----------------------------------------------------------
  // Dashboard analytics response
  // -----------------------------------------------------------

  const [dashboard, setDashboard] = useState(null);

  // -----------------------------------------------------------
  // UI state
  // -----------------------------------------------------------

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sseConnected, setSseConnected] = useState(false);

  // ===========================================================
  // LOAD DASHBOARD
  // ===========================================================

  const loadDashboard = useCallback(
    async (showRefresh = false) => {
      try {
        if (showRefresh) {
          setRefreshing(true);
        } else if (!dashboard) {
          setLoading(true);
        }

        setError("");

        const data = await getAnalyticsDashboard(30);

        console.log(
          "Dashboard analytics response:",
          data
        );

        setDashboard(data || {});
      } catch (err) {
        console.error(
          "Dashboard analytics API error:",
          err
        );

        const backendError =
          err?.response?.data?.detail;

        if (typeof backendError === "string") {
          setError(backendError);
        } else if (
          backendError &&
          typeof backendError === "object"
        ) {
          setError(
            backendError.message ||
              "Unable to load dashboard analytics."
          );
        } else {
          setError(
            "Unable to connect to PayPilot analytics API."
          );
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [dashboard]
  );

  // ===========================================================
  // INITIAL LOAD
  // ===========================================================

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // ===========================================================
  // SSE REAL-TIME CONNECTION
  // ===========================================================

  useEffect(() => {
    const url =
      `${API_BASE_URL}/events/orders`;

    console.log(
      "Connecting Dashboard SSE:",
      url
    );

    const eventSource =
      new EventSource(url);

    // ---------------------------------------------------------
    // CONNECTED
    // ---------------------------------------------------------

    const handleConnected = (event) => {
      console.log(
        "SSE connected:",
        event.data
      );

      setSseConnected(true);
    };

    // ---------------------------------------------------------
    // ORDER EVENT
    // ---------------------------------------------------------

    const handleOrderEvent = (event) => {
      console.log(
        "SSE ORDER EVENT:",
        event.type,
        event.data
      );

      setTimeout(() => {
        loadDashboard();
      }, 200);
    };

    // ---------------------------------------------------------
    // MANUAL REVIEW EVENT
    // ---------------------------------------------------------

    const handleManualReview = (event) => {
      console.log(
        "SSE MANUAL REVIEW EVENT:",
        event.type,
        event.data
      );

      setTimeout(() => {
        loadDashboard();
      }, 200);
    };

    // ---------------------------------------------------------
    // EVENT LISTENERS
    // ---------------------------------------------------------

    eventSource.addEventListener(
      "connected",
      handleConnected
    );

    eventSource.addEventListener(
      "order_created",
      handleOrderEvent
    );

    eventSource.addEventListener(
      "order_updated",
      handleOrderEvent
    );

    eventSource.addEventListener(
      "order_approved",
      handleOrderEvent
    );

    eventSource.addEventListener(
      "order_rejected",
      handleOrderEvent
    );

    eventSource.addEventListener(
      "manual_review_created",
      handleManualReview
    );

    eventSource.addEventListener(
      "manual_review_updated",
      handleManualReview
    );

    // ---------------------------------------------------------
    // GENERIC SSE MESSAGE
    // ---------------------------------------------------------

    eventSource.onmessage = (event) => {
      console.log(
        "SSE generic event:",
        event.data
      );

      setTimeout(() => {
        loadDashboard();
      }, 200);
    };

    // ---------------------------------------------------------
    // SSE ERROR
    // ---------------------------------------------------------

    eventSource.onerror = (event) => {
      console.warn(
        "Dashboard SSE connection error:",
        event
      );

      setSseConnected(false);
    };

    // ---------------------------------------------------------
    // CLEANUP
    // ---------------------------------------------------------

    return () => {
      console.log(
        "Closing Dashboard SSE"
      );

      eventSource.close();

      setSseConnected(false);
    };
  }, [loadDashboard]);

  // ===========================================================
  // FALLBACK AUTO REFRESH
  // ===========================================================

  useEffect(() => {
    const interval =
      setInterval(() => {
        loadDashboard();
      }, 15000);

    return () => {
      clearInterval(interval);
    };
  }, [loadDashboard]);

  // ===========================================================
  // NORMALIZED DATA
  // ===========================================================

  const summary =
    dashboard?.summary || {};

  const riskData =
    normalizeRiskData(
      dashboard?.risk
    );

  const statusData =
    normalizeStatusData(
      dashboard?.order_status
    );

  const orderTrend =
    normalizeTrendData(
      dashboard?.order_trend
    );

  const revenueTrend =
    normalizeTrendData(
      dashboard?.revenue_trend
    );

  const merchantPerformance =
    normalizeMerchantData(
      dashboard?.merchant_performance
    );

  const manualReviews =
    dashboard?.manual_reviews || {};

  const recentActivity =
    Array.isArray(
      dashboard?.recent_activity
    )
      ? dashboard.recent_activity
      : [];

  // ===========================================================
  // ORDERS FOR SEARCH
  // ===========================================================
  //
  // The dashboard endpoint may not contain raw orders.
  // Therefore the recent activity list is used as the
  // searchable transaction source.
  //
  // ===========================================================

  const recentOrders =
    useMemo(() => {
      if (
        Array.isArray(
          dashboard?.recent_activity
        )
      ) {
        return dashboard.recent_activity;
      }

      return [];
    }, [dashboard]);

  const filteredOrders =
    useMemo(() => {
      const query =
        search.trim().toLowerCase();

      const source =
        recentOrders || [];

      if (!query) {
        return source
          .slice()
          .reverse()
          .slice(0, 8);
      }

      return source
        .filter((order) => {
          return (
            String(
              order.id ??
                order.order_id ??
                ""
            )
              .toLowerCase()
              .includes(query) ||
            String(
              order.product_id ??
                ""
            )
              .toLowerCase()
              .includes(query) ||
            String(
              order.status ??
                ""
            )
              .toLowerCase()
              .includes(query) ||
            String(
              order.risk_level ??
                order.riskLevel ??
                ""
            )
              .toLowerCase()
              .includes(query)
          );
        })
        .slice()
        .reverse();
    }, [
      recentOrders,
      search,
    ]);

  // ===========================================================
  // KPI VALUES
  // ===========================================================

  const totalOrders =
    getNumber(
      summary?.orders?.total,
      summary?.total_orders,
      summary?.orders,
      statusData.reduce(
        (sum, item) =>
          sum + item.value,
        0
      )
    );

  const approved =
    getNumber(
      summary?.orders?.approved,
      summary?.approved,
      findStatusValue(
        statusData,
        "APPROVED"
      )
    );

  const rejected =
    getNumber(
      summary?.orders?.rejected,
      summary?.rejected,
      findStatusValue(
        statusData,
        "REJECTED"
      )
    );

  const manualReviewCount =
    getNumber(
      summary?.orders?.manual_review,
      summary?.orders?.manual_review_required,
      summary?.manual_review,
      summary?.manual_reviews,
      findStatusValue(
        statusData,
        "MANUAL_REVIEW_REQUIRED"
      )
    );

  const pendingReviews =
    getNumber(
      manualReviews?.pending,
      manualReviews?.pending_reviews,
      manualReviews?.pending_count
    );

  const revenue =
    getNumber(
      summary?.revenue?.total,
      summary?.revenue?.total_revenue,
      summary?.total_revenue
    );

  const averageRiskScore =
    getNumber(
      summary?.risk?.average_score,
      summary?.risk?.average_risk_score,
      summary?.average_risk_score
    );

  // ===========================================================
  // RISK VALUES
  // ===========================================================

  const lowRisk =
    findRiskValue(
      riskData,
      "LOW"
    );

  const mediumRisk =
    findRiskValue(
      riskData,
      "MEDIUM"
    );

  const highRisk =
    findRiskValue(
      riskData,
      "HIGH"
    );

  // ===========================================================
  // PROCESSING RATE
  // ===========================================================

  const processingRate =
    totalOrders > 0
      ? Math.round(
          (approved /
            totalOrders) *
            100
        )
      : 0;

  // ===========================================================
  // LOADING
  // ===========================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 lg:p-8">
        <div className="mx-auto max-w-[1500px]">
          <div className="animate-pulse space-y-8">

            <div className="h-8 w-64 rounded-lg bg-slate-200" />

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-5">
              {Array.from({
                length: 5,
              }).map((_, index) => (
                <div
                  key={index}
                  className="h-36 rounded-2xl bg-white shadow-sm"
                />
              ))}
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
              <div className="h-96 rounded-2xl bg-white xl:col-span-2" />
              <div className="h-96 rounded-2xl bg-white" />
            </div>

          </div>
        </div>
      </div>
    );
  }

  // ===========================================================
  // DASHBOARD UI
  // ===========================================================

  return (
    <div className="min-h-screen bg-slate-50">

      <div className="mx-auto w-full max-w-[1500px] px-4 py-6 sm:px-6 lg:px-8">

        {/* =====================================================
            HEADER
        ===================================================== */}

        <header className="mb-8">

          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">

            <div>

              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-500">
                <span>Admin</span>
                <span>/</span>
                <span>Overview</span>
              </div>

              <h1 className="text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
                Dashboard
              </h1>

              <p className="mt-2 text-sm text-slate-500 sm:text-base">
                Monitor orders, payments and AI-powered risk decisions.
              </p>

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

                <span
                  className={`h-2 w-2 rounded-full ${
                    sseConnected
                      ? "animate-pulse bg-emerald-500"
                      : "bg-amber-500"
                  }`}
                />

                {sseConnected
                  ? "Live Updates"
                  : "Reconnecting..."}

              </div>

              {/* REFRESH */}

              <button
                onClick={() =>
                  loadDashboard(true)
                }
                disabled={refreshing}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
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

        </header>

        {/* =====================================================
            ERROR
        ===================================================== */}

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">

            <ShieldAlert
              size={20}
              className="mt-0.5 shrink-0"
            />

            <div>

              <p className="font-semibold">
                Analytics API Error
              </p>

              <p className="mt-1 text-sm">
                {error}
              </p>

            </div>

          </div>
        )}

        {/* =====================================================
            KPI CARDS
        ===================================================== */}

        <section className="mb-8">

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">

            <StatCard
              title="Total Orders"
              value={totalOrders}
              subtitle="All orders"
              icon={ShoppingCart}
              iconClass="bg-blue-50 text-blue-600"
            />

            <StatCard
              title="Approved"
              value={approved}
              subtitle={`${processingRate}% processing rate`}
              icon={CheckCircle2}
              iconClass="bg-emerald-50 text-emerald-600"
              valueClass="text-emerald-700"
            />

            <StatCard
              title="Rejected"
              value={rejected}
              subtitle="Risk rejected"
              icon={XCircle}
              iconClass="bg-red-50 text-red-600"
              valueClass="text-red-700"
            />

            <StatCard
              title="Manual Reviews"
              value={manualReviewCount}
              subtitle={`${pendingReviews} pending`}
              icon={AlertTriangle}
              iconClass="bg-amber-50 text-amber-600"
              valueClass="text-amber-700"
            />

            <StatCard
              title="Revenue"
              value={formatCurrency(
                revenue
              )}
              subtitle="Approved orders"
              icon={DollarSign}
              iconClass="bg-violet-50 text-violet-600"
              valueClass="text-violet-700"
            />

          </div>

        </section>

        {/* =====================================================
            TREND CHARTS
        ===================================================== */}

        <section className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-2">

          {/* ORDER TREND */}

          <ChartCard
            title="Order Trend"
            subtitle="Daily order volume"
            icon={ShoppingCart}
          >
            <LineChart
              data={orderTrend}
              valueKey="value"
              valueFormatter={(value) =>
                Number(value).toLocaleString(
                  "en-IN"
                )
              }
            />
          </ChartCard>

          {/* REVENUE TREND */}

          <ChartCard
            title="Revenue Trend"
            subtitle="Daily revenue performance"
            icon={DollarSign}
          >
            <LineChart
              data={revenueTrend}
              valueKey="value"
              valueFormatter={(value) =>
                formatCurrency(value)
              }
            />
          </ChartCard>

        </section>

        {/* =====================================================
            MAIN CONTENT
        ===================================================== */}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">

          {/* ===================================================
              RECENT ORDERS / ACTIVITY
          =================================================== */}

          <section className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:col-span-2">

            <div className="flex flex-col gap-4 border-b border-slate-200 p-5 sm:flex-row sm:items-center sm:justify-between">

              <div>

                <div className="flex items-center gap-2">

                  <Package
                    size={19}
                    className="text-blue-600"
                  />

                  <h2 className="text-lg font-bold text-slate-900">
                    Recent Activity
                  </h2>

                </div>

                <p className="mt-1 text-sm text-slate-500">
                  Latest payment and risk activity
                </p>

              </div>

              <div className="relative w-full sm:w-64">

                <Search
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />

                <input
                  type="text"
                  placeholder="Search activity..."
                  value={search}
                  onChange={(e) =>
                    setSearch(
                      e.target.value
                    )
                  }
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
                />

              </div>

            </div>

            <div className="overflow-x-auto">

              <table className="w-full min-w-[800px]">

                <thead>

                  <tr className="border-b border-slate-200 bg-slate-50/80">

                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Order
                    </th>

                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Activity
                    </th>

                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Amount
                    </th>

                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Risk
                    </th>

                    <th className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Status
                    </th>

                  </tr>

                </thead>

                <tbody className="divide-y divide-slate-100">

                  {filteredOrders.length === 0 ? (

                    <tr>

                      <td
                        colSpan="5"
                        className="px-5 py-14 text-center"
                      >

                        <Package
                          size={34}
                          className="mx-auto mb-3 text-slate-300"
                        />

                        <p className="font-semibold text-slate-700">
                          No recent activity
                        </p>

                        <p className="mt-1 text-sm text-slate-400">
                          Activity will appear here when orders are processed.
                        </p>

                      </td>

                    </tr>

                  ) : (

                    filteredOrders.map(
                      (activity, index) => (
                        <ActivityRow
                          key={
                            activity.id ??
                            activity.order_id ??
                            index
                          }
                          activity={
                            activity
                          }
                        />
                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

            <div className="border-t border-slate-200 bg-slate-50/50 px-5 py-3">

              <p className="text-xs text-slate-500">

                Showing{" "}

                <span className="font-semibold text-slate-700">
                  {filteredOrders.length}
                </span>{" "}

                recent activities

              </p>

            </div>

          </section>

          {/* =================================================
              RISK OVERVIEW
          ================================================= */}

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

            <div className="border-b border-slate-200 p-5">

              <div className="flex items-center gap-2">

                <Activity
                  size={19}
                  className="text-blue-600"
                />

                <h2 className="text-lg font-bold text-slate-900">
                  Risk Overview
                </h2>

              </div>

              <p className="mt-1 text-sm text-slate-500">
                Current payment risk distribution
              </p>

            </div>

            <div className="space-y-6 p-5">

              <RiskRow
                label="Low Risk"
                count={lowRisk}
                percentage={getPercentage(
                  lowRisk,
                  totalOrders
                )}
                icon={CheckCircle2}
                iconClass="bg-emerald-50 text-emerald-600"
                barClass="bg-emerald-500"
              />

              <RiskRow
                label="Medium Risk"
                count={mediumRisk}
                percentage={getPercentage(
                  mediumRisk,
                  totalOrders
                )}
                icon={AlertTriangle}
                iconClass="bg-amber-50 text-amber-600"
                barClass="bg-amber-500"
              />

              <RiskRow
                label="High Risk"
                count={highRisk}
                percentage={getPercentage(
                  highRisk,
                  totalOrders
                )}
                icon={ShieldAlert}
                iconClass="bg-red-50 text-red-600"
                barClass="bg-red-500"
              />

              {/* Average Risk */}

              <div className="rounded-xl bg-slate-50 p-4">

                <div className="flex items-center justify-between">

                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">

                    <ShieldAlert size={16} />

                    Average Risk Score

                  </div>

                  <span className="text-lg font-bold text-slate-900">
                    {averageRiskScore.toFixed(
                      2
                    )}
                  </span>

                </div>

              </div>

              {/* Processing Rate */}

              <div className="rounded-xl bg-slate-50 p-4">

                <div className="flex items-center justify-between">

                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">

                    <TrendingUp size={16} />

                    Processing Rate

                  </div>

                  <span className="text-sm font-bold text-slate-900">
                    {processingRate}%
                  </span>

                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">

                  <div
                    className="h-full rounded-full bg-blue-600 transition-all duration-500"
                    style={{
                      width: `${processingRate}%`,
                    }}
                  />

                </div>

              </div>

            </div>

          </section>

        </div>

        {/* =====================================================
            ORDER STATUS + MERCHANT PERFORMANCE
        ===================================================== */}

        <section className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">

          {/* ORDER STATUS */}

          <ChartCard
            title="Order Status"
            subtitle="Current order distribution"
            icon={Activity}
          >

            <BarChart
              data={statusData}
            />

          </ChartCard>

          {/* MERCHANT PERFORMANCE */}

          <MerchantPerformance
            data={
              merchantPerformance
            }
          />

        </section>

        {/* =====================================================
            MANUAL REVIEW + RECENT ACTIVITY
        ===================================================== */}

        <section className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-2">

          {/* MANUAL REVIEWS */}

          <ManualReviewCard
            data={manualReviews}
          />

          {/* RECENT ACTIVITY */}

          <RecentActivityCard
            activities={
              recentActivity
            }
          />

        </section>

        {/* =====================================================
            SYSTEM STATUS
        ===================================================== */}

        <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">

          <SystemCard
            icon={ShieldAlert}
            title="AI Risk Engine"
            value="Operational"
            description="Risk decisions are being processed."
            iconClass="bg-blue-50 text-blue-600"
          />

          <SystemCard
            icon={Clock3}
            title="Manual Reviews"
            value={`${pendingReviews} Pending`}
            description="Reviews requiring administrator attention."
            iconClass="bg-amber-50 text-amber-600"
          />

          <SystemCard
            icon={Activity}
            title="Real-Time API"
            value={
              sseConnected
                ? "Connected"
                : "Reconnecting"
            }
            description={
              sseConnected
                ? "Live order events are being received."
                : "Waiting for the event stream."
            }
            iconClass={
              sseConnected
                ? "bg-emerald-50 text-emerald-600"
                : "bg-amber-50 text-amber-600"
            }
          />

        </section>

        {/* =====================================================
            FOOTER
        ===================================================== */}

        <footer className="mt-8 border-t border-slate-200 py-5 text-center text-xs text-slate-400">
          PayPilot AI • Payment Risk Management System
        </footer>

      </div>

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
  icon: Icon,
  iconClass,
  valueClass = "text-slate-950",
}) {
  return (
    <div className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md">

      <div className="flex items-start justify-between">

        <div>

          <p className="text-sm font-medium text-slate-500">
            {title}
          </p>

          <p
            className={`mt-3 text-2xl font-bold tracking-tight ${valueClass}`}
          >
            {value}
          </p>

        </div>

        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconClass}`}
        >
          <Icon size={21} />
        </div>

      </div>

      <p className="mt-4 text-xs font-medium text-slate-500">
        {subtitle}
      </p>

    </div>
  );
}

// =============================================================
// CHART CARD
// =============================================================

function ChartCard({
  title,
  subtitle,
  icon: Icon,
  children,
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

      <div className="border-b border-slate-200 p-5">

        <div className="flex items-center gap-2">

          <Icon
            size={19}
            className="text-blue-600"
          />

          <h2 className="text-lg font-bold text-slate-900">
            {title}
          </h2>

        </div>

        <p className="mt-1 text-sm text-slate-500">
          {subtitle}
        </p>

      </div>

      <div className="p-5">
        {children}
      </div>

    </section>
  );
}

// =============================================================
// LINE CHART
// =============================================================

function LineChart({
  data,
  valueKey = "value",
  valueFormatter = (value) =>
    value,
}) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">

        <div className="text-center">

          <TrendingUp
            size={34}
            className="mx-auto mb-3 text-slate-300"
          />

          <p className="font-semibold text-slate-600">
            No trend data
          </p>

          <p className="mt-1 text-xs text-slate-400">
            Analytics will appear here as data is collected.
          </p>

        </div>

      </div>
    );
  }

  const width = 700;
  const height = 250;

  const paddingX = 45;
  const paddingY = 25;

  const values = data.map(
    (item) =>
      Number(
        item[valueKey] || 0
      )
  );

  const maxValue =
    Math.max(
      ...values,
      1
    );

  const points = data.map(
    (item, index) => {
      const x =
        paddingX +
        (index /
          Math.max(
            data.length - 1,
            1
          )) *
          (width -
            paddingX * 2);

      const y =
        height -
        paddingY -
        (Number(
          item[valueKey] || 0
        ) /
          maxValue) *
          (height -
            paddingY * 2);

      return {
        x,
        y,
        value:
          Number(
            item[valueKey] || 0
          ),
        label:
          item.label ??
          item.date ??
          item.day ??
          "",
      };
    }
  );

  const polyline =
    points
      .map(
        (point) =>
          `${point.x},${point.y}`
      )
      .join(" ");

  const areaPoints = [
    `${paddingX},${height - paddingY}`,
    polyline,
    `${
      width - paddingX
    },${height - paddingY}`,
  ].join(" ");

  return (
    <div className="w-full">

      <div className="mb-3 flex items-center justify-between">

        <span className="text-xs font-medium text-slate-400">
          {data[0]?.label || ""}
        </span>

        <span className="text-xs font-medium text-slate-400">
          {data[data.length - 1]?.label ||
            ""}
        </span>

      </div>

      <div className="h-64 w-full">

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-full w-full"
          preserveAspectRatio="none"
        >

          {/* GRID */}

          {[0, 1, 2, 3, 4].map(
            (line) => {
              const y =
                paddingY +
                (line / 4) *
                  (height -
                    paddingY * 2);

              return (
                <line
                  key={line}
                  x1={paddingX}
                  y1={y}
                  x2={
                    width -
                    paddingX
                  }
                  y2={y}
                  stroke="#e2e8f0"
                  strokeWidth="1"
                />
              );
            }
          )}

          {/* AREA */}

          <polygon
            points={areaPoints}
            fill="rgba(37, 99, 235, 0.08)"
          />

          {/* LINE */}

          <polyline
            points={polyline}
            fill="none"
            stroke="#2563eb"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* POINTS */}

          {points.map(
            (point, index) => (
              <circle
                key={index}
                cx={point.x}
                cy={point.y}
                r="4"
                fill="#ffffff"
                stroke="#2563eb"
                strokeWidth="2"
              >
                <title>
                  {point.label}:{" "}
                  {valueFormatter(
                    point.value
                  )}
                </title>
              </circle>
            )
          )}

        </svg>

      </div>

      <div className="mt-3 flex justify-between">

        <span className="text-xs text-slate-400">
          Min:{" "}
          {valueFormatter(
            Math.min(...values)
          )}
        </span>

        <span className="text-xs font-semibold text-slate-700">
          Max:{" "}
          {valueFormatter(
            Math.max(...values)
          )}
        </span>

      </div>

    </div>
  );
}

// =============================================================
// BAR CHART
// =============================================================

function BarChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">

        <div className="text-center">

          <Activity
            size={34}
            className="mx-auto mb-3 text-slate-300"
          />

          <p className="font-semibold text-slate-600">
            No status data
          </p>

        </div>

      </div>
    );
  }

  const maxValue =
    Math.max(
      ...data.map(
        (item) =>
          Number(
            item.value || 0
          )
      ),
      1
    );

  return (
    <div className="space-y-5">

      {data.map(
        (item, index) => {
          const value =
            Number(
              item.value || 0
            );

          const percentage =
            Math.round(
              (value /
                maxValue) *
                100
            );

          return (
            <div key={index}>

              <div className="mb-2 flex items-center justify-between">

                <span className="text-sm font-semibold text-slate-700">
                  {formatLabel(
                    item.label
                  )}
                </span>

                <span className="text-sm font-bold text-slate-900">
                  {value}
                </span>

              </div>

              <div className="h-3 overflow-hidden rounded-full bg-slate-100">

                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    getStatusBarClass(
                      item.label
                    )
                  }`}
                  style={{
                    width: `${percentage}%`,
                  }}
                />

              </div>

            </div>
          );
        }
      )}

    </div>
  );
}

// =============================================================
// RISK ROW
// =============================================================

function RiskRow({
  label,
  count,
  percentage,
  icon: Icon,
  iconClass,
  barClass,
}) {
  return (
    <div>

      <div className="mb-3 flex items-center justify-between">

        <div className="flex items-center gap-3">

          <div
            className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconClass}`}
          >
            <Icon size={17} />
          </div>

          <span className="text-sm font-semibold text-slate-700">
            {label}
          </span>

        </div>

        <span className="text-sm font-bold text-slate-900">
          {count}
        </span>

      </div>

      <div className="h-2 overflow-hidden rounded-full bg-slate-100">

        <div
          className={`h-full rounded-full transition-all duration-500 ${barClass}`}
          style={{
            width: `${percentage}%`,
          }}
        />

      </div>

      <div className="mt-2 text-right text-xs text-slate-400">
        {percentage}% of orders
      </div>

    </div>
  );
}

// =============================================================
// ACTIVITY ROW
// =============================================================

function ActivityRow({
  activity,
}) {
  const status =
    String(
      activity.status ||
        activity.new_status ||
        activity.event ||
        ""
    ).toUpperCase();

  const risk =
    String(
      activity.risk_level ??
        activity.riskLevel ??
        ""
    ).toUpperCase();

  const amount =
    Number(
      activity.final_amount ??
        activity.amount ??
        0
    );

  const orderId =
    activity.order_id ??
    activity.id ??
    "-";

  const productId =
    activity.product_id ??
    "-";

  const statusConfig =
    getStatusConfig(
      status
    );

  const riskConfig =
    getRiskConfig(
      risk
    );

  return (
    <tr className="transition hover:bg-slate-50/80">

      {/* ORDER */}

      <td className="px-5 py-4">

        <div className="font-semibold text-slate-900">
          #{orderId}
        </div>

        <div className="mt-1 text-xs text-slate-400">
          Product #{productId}
        </div>

      </td>

      {/* ACTIVITY */}

      <td className="px-5 py-4">

        <div className="flex items-center gap-3">

          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <Activity size={17} />
          </div>

          <div>

            <p className="font-semibold text-slate-800">
              {formatLabel(
                activity.event ||
                  activity.action ||
                  activity.activity ||
                  status ||
                  "Order Activity"
              )}
            </p>

            <p className="text-xs text-slate-400">
              {formatDate(
                activity.created_at ||
                  activity.timestamp ||
                  activity.date
              )}
            </p>

          </div>

        </div>

      </td>

      {/* AMOUNT */}

      <td className="px-5 py-4">

        <p className="font-semibold text-slate-900">
          {formatCurrency(
            amount
          )}
        </p>

      </td>

      {/* RISK */}

      <td className="px-5 py-4">

        {risk ? (
          <span
            className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold ${riskConfig.className}`}
          >
            {riskConfig.icon}

            {riskConfig.label}
          </span>
        ) : (
          <span className="text-xs text-slate-400">
            N/A
          </span>
        )}

      </td>

      {/* STATUS */}

      <td className="px-5 py-4">

        <span
          className={`inline-flex whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold ${statusConfig.className}`}
        >
          {statusConfig.label}
        </span>

      </td>

    </tr>
  );
}

// =============================================================
// MERCHANT PERFORMANCE
// =============================================================

function MerchantPerformance({
  data,
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

      <div className="border-b border-slate-200 p-5">

        <div className="flex items-center gap-2">

          <TrendingUp
            size={19}
            className="text-blue-600"
          />

          <h2 className="text-lg font-bold text-slate-900">
            Merchant Performance
          </h2>

        </div>

        <p className="mt-1 text-sm text-slate-500">
          Merchant-level payment performance
        </p>

      </div>

      <div className="overflow-x-auto">

        <table className="w-full min-w-[500px]">

          <thead>

            <tr className="border-b border-slate-200 bg-slate-50/80">

              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Merchant
              </th>

              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Orders
              </th>

              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Approved
              </th>

              <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                Revenue
              </th>

            </tr>

          </thead>

          <tbody className="divide-y divide-slate-100">

            {data.length === 0 ? (

              <tr>

                <td
                  colSpan="4"
                  className="px-5 py-10 text-center text-sm text-slate-400"
                >
                  No merchant performance data.
                </td>

              </tr>

            ) : (

              data.slice(
                0,
                8
              ).map(
                (
                  merchant,
                  index
                ) => (
                  <tr
                    key={
                      merchant.id ??
                      merchant.merchant_id ??
                      index
                    }
                    className="hover:bg-slate-50"
                  >

                    <td className="px-5 py-4 font-semibold text-slate-800">
                      {merchant.name ||
                        `Merchant #${
                          merchant.merchant_id ??
                          merchant.id ??
                          "-"
                        }`}
                    </td>

                    <td className="px-5 py-4 text-sm text-slate-600">
                      {getNumber(
                        merchant.orders,
                        merchant.total_orders
                      )}
                    </td>

                    <td className="px-5 py-4 text-sm font-semibold text-emerald-600">
                      {getNumber(
                        merchant.approved,
                        merchant.approved_orders
                      )}
                    </td>

                    <td className="px-5 py-4 text-sm font-semibold text-slate-800">
                      {formatCurrency(
                        getNumber(
                          merchant.revenue,
                          merchant.total_revenue
                        )
                      )}
                    </td>

                  </tr>
                )
              )

            )}

          </tbody>

        </table>

      </div>

    </section>
  );
}

// =============================================================
// MANUAL REVIEW CARD
// =============================================================

function ManualReviewCard({
  data,
}) {
  const pending =
    getNumber(
      data?.pending,
      data?.pending_reviews,
      data?.pending_count
    );

  const approved =
    getNumber(
      data?.approved,
      data?.approved_reviews,
      data?.approved_count
    );

  const rejected =
    getNumber(
      data?.rejected,
      data?.rejected_reviews,
      data?.rejected_count
    );

  const total =
    getNumber(
      data?.total,
      data?.total_reviews,
      pending +
        approved +
        rejected
    );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div className="flex items-center gap-2">

        <Clock3
          size={19}
          className="text-amber-600"
        />

        <h2 className="text-lg font-bold text-slate-900">
          Manual Reviews
        </h2>

      </div>

      <p className="mt-1 text-sm text-slate-500">
        Review queue performance
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4">

        <MiniMetric
          title="Total"
          value={total}
          icon={Activity}
          iconClass="bg-blue-50 text-blue-600"
        />

        <MiniMetric
          title="Pending"
          value={pending}
          icon={Clock3}
          iconClass="bg-amber-50 text-amber-600"
        />

        <MiniMetric
          title="Approved"
          value={approved}
          icon={CheckCircle2}
          iconClass="bg-emerald-50 text-emerald-600"
        />

        <MiniMetric
          title="Rejected"
          value={rejected}
          icon={XCircle}
          iconClass="bg-red-50 text-red-600"
        />

      </div>

    </section>
  );
}

// =============================================================
// RECENT ACTIVITY CARD
// =============================================================

function RecentActivityCard({
  activities,
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div className="flex items-center gap-2">

        <Activity
          size={19}
          className="text-blue-600"
        />

        <h2 className="text-lg font-bold text-slate-900">
          Activity Feed
        </h2>

      </div>

      <p className="mt-1 text-sm text-slate-500">
        Latest system events
      </p>

      <div className="mt-5 space-y-3">

        {activities.length === 0 ? (

          <div className="rounded-xl bg-slate-50 p-6 text-center">

            <p className="text-sm font-semibold text-slate-600">
              No recent activity
            </p>

          </div>

        ) : (

          activities
            .slice(
              0,
              6
            )
            .map(
              (
                activity,
                index
              ) => {

                const event =
                  activity.event ||
                  activity.action ||
                  activity.activity ||
                  activity.status ||
                  "Activity";

                return (
                  <div
                    key={
                      activity.id ??
                      activity.order_id ??
                      index
                    }
                    className="flex items-center gap-3 rounded-xl border border-slate-100 p-3"
                  >

                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                      <Activity size={16} />
                    </div>

                    <div className="min-w-0 flex-1">

                      <p className="truncate text-sm font-semibold text-slate-700">
                        {formatLabel(
                          event
                        )}
                      </p>

                      <p className="mt-0.5 text-xs text-slate-400">
                        Order #
                        {activity.order_id ??
                          activity.id ??
                          "-"}
                      </p>

                    </div>

                    <div className="text-right text-xs text-slate-400">
                      {formatDate(
                        activity.created_at ||
                          activity.timestamp ||
                          activity.date
                      )}
                    </div>

                  </div>
                );
              }
            )

        )}

      </div>

    </section>
  );
}

// =============================================================
// MINI METRIC
// =============================================================

function MiniMetric({
  title,
  value,
  icon: Icon,
  iconClass,
}) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-xs font-medium text-slate-500">
            {title}
          </p>

          <p className="mt-1 text-xl font-bold text-slate-900">
            {value}
          </p>

        </div>

        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconClass}`}
        >
          <Icon size={17} />
        </div>

      </div>

    </div>
  );
}

// =============================================================
// SYSTEM CARD
// =============================================================

function SystemCard({
  icon: Icon,
  title,
  value,
  description,
  iconClass,
}) {
  return (
    <div className="flex items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${iconClass}`}
      >
        <Icon size={20} />
      </div>

      <div className="min-w-0">

        <p className="text-sm font-medium text-slate-500">
          {title}
        </p>

        <p className="mt-1 font-bold text-slate-900">
          {value}
        </p>

        <p className="mt-1 text-xs leading-5 text-slate-400">
          {description}
        </p>

      </div>

    </div>
  );
}

// =============================================================
// NORMALIZE RISK DATA
// =============================================================

function normalizeRiskData(data) {
  if (!data) {
    return [];
  }

  if (Array.isArray(data)) {
    return data.map(
      normalizeAnalyticsItem
    );
  }

  if (
    typeof data === "object"
  ) {
    return Object.entries(
      data
    ).map(
      ([label, value]) => ({
        label,
        value:
          typeof value === "object"
            ? getNumber(
                value?.count,
                value?.value,
                value?.total
              )
            : Number(value || 0),
      })
    );
  }

  return [];
}

// =============================================================
// NORMALIZE STATUS DATA
// =============================================================

function normalizeStatusData(data) {
  if (!data) {
    return [];
  }

  if (Array.isArray(data)) {
    return data.map(
      normalizeAnalyticsItem
    );
  }

  if (
    typeof data === "object"
  ) {
    return Object.entries(
      data
    ).map(
      ([label, value]) => ({
        label,
        value:
          typeof value === "object"
            ? getNumber(
                value?.count,
                value?.value,
                value?.total
              )
            : Number(value || 0),
      })
    );
  }

  return [];
}

// =============================================================
// NORMALIZE TREND DATA
// =============================================================

function normalizeTrendData(data) {
  if (!data) {
    return [];
  }

  const source =
    Array.isArray(data)
      ? data
      : Array.isArray(data?.data)
      ? data.data
      : [];

  return source.map(
    (item) => ({
      label:
        item.label ??
        item.date ??
        item.day ??
        item.period ??
        "",
      value:
        Number(
          item.value ??
            item.count ??
            item.amount ??
            item.revenue ??
            0
        ),
    })
  );
}

// =============================================================
// NORMALIZE MERCHANT DATA
// =============================================================

function normalizeMerchantData(
  data
) {
  if (
    Array.isArray(data)
  ) {
    return data;
  }

  if (
    Array.isArray(
      data?.data
    )
  ) {
    return data.data;
  }

  if (
    typeof data ===
      "object" &&
    data !== null
  ) {
    return Object.entries(
      data
    ).map(
      ([merchantId, value]) => ({
        merchant_id:
          merchantId,
        ...(typeof value ===
        "object"
          ? value
          : {
              orders: Number(
                value || 0
              ),
            }),
      })
    );
  }

  return [];
}

// =============================================================
// NORMALIZE ANALYTICS ITEM
// =============================================================

function normalizeAnalyticsItem(
  item
) {
  if (
    typeof item ===
    "object"
  ) {
    return {
      label:
        item.label ??
        item.name ??
        item.risk_level ??
        item.status ??
        "",
      value:
        Number(
          item.value ??
            item.count ??
            item.total ??
            0
        ),
    };
  }

  return {
    label: "",
    value: Number(
      item || 0
    ),
  };
}

// =============================================================
// FIND RISK VALUE
// =============================================================

function findRiskValue(
  data,
  target
) {
  const item =
    data.find(
      (entry) =>
        String(
          entry.label
        ).toUpperCase() ===
        target
    );

  return item
    ? Number(
        item.value || 0
      )
    : 0;
}

// =============================================================
// FIND STATUS VALUE
// =============================================================

function findStatusValue(
  data,
  target
) {
  const item =
    data.find(
      (entry) =>
        String(
          entry.label
        ).toUpperCase() ===
        target
    );

  return item
    ? Number(
        item.value || 0
      )
    : 0;
}

// =============================================================
// GET NUMBER
// =============================================================

function getNumber(
  ...values
) {
  for (const value of values) {
    if (
      value !==
        undefined &&
      value !== null &&
      value !== ""
    ) {
      const number =
        Number(value);

      if (
        Number.isFinite(
          number
        )
      ) {
        return number;
      }
    }
  }

  return 0;
}

// =============================================================
// PERCENTAGE
// =============================================================

function getPercentage(
  value,
  total
) {
  if (
    !total ||
    total <= 0
  ) {
    return 0;
  }

  return Math.round(
    (value / total) *
      100
  );
}

// =============================================================
// CURRENCY
// =============================================================

function formatCurrency(
  value
) {
  return `₹${Number(
    value || 0
  ).toLocaleString(
    "en-IN",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}`;
}

// =============================================================
// LABEL FORMATTER
// =============================================================

function formatLabel(
  value
) {
  if (
    value ===
      null ||
    value ===
      undefined
  ) {
    return "";
  }

  return String(value)
    .replace(
      /_/g,
      " "
    )
    .replace(
      /\b\w/g,
      (char) =>
        char.toUpperCase()
    );
}

// =============================================================
// DATE FORMATTER
// =============================================================

function formatDate(
  value
) {
  if (!value) {
    return "Recently";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return String(value);
  }

  return date.toLocaleString(
    "en-IN",
    {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }
  );
}

// =============================================================
// STATUS CONFIG
// =============================================================

function getStatusConfig(
  status
) {
  switch (
    String(
      status || ""
    ).toUpperCase()
  ) {
    case "APPROVED":
      return {
        label: "Approved",
        className:
          "border-emerald-200 bg-emerald-50 text-emerald-700",
      };

    case "REJECTED":
      return {
        label: "Rejected",
        className:
          "border-red-200 bg-red-50 text-red-700",
      };

    case "MANUAL_REVIEW_REQUIRED":
      return {
        label: "Manual Review",
        className:
          "border-amber-200 bg-amber-50 text-amber-700",
      };

    case "PENDING":
      return {
        label: "Pending",
        className:
          "border-amber-200 bg-amber-50 text-amber-700",
      };

    default:
      return {
        label:
          formatLabel(
            status ||
              "Unknown"
          ),
        className:
          "border-slate-200 bg-slate-50 text-slate-600",
      };
  }
}

// =============================================================
// RISK CONFIG
// =============================================================

function getRiskConfig(
  risk
) {
  switch (
    String(
      risk || ""
    ).toUpperCase()
  ) {
    case "LOW":
      return {
        label: "Low",
        className:
          "border-emerald-200 bg-emerald-50 text-emerald-700",
        icon: (
          <TrendingUp
            size={13}
            className="text-emerald-600"
          />
        ),
      };

    case "MEDIUM":
      return {
        label: "Medium",
        className:
          "border-amber-200 bg-amber-50 text-amber-700",
        icon: (
          <TrendingUp
            size={13}
            className="text-amber-600"
          />
        ),
      };

    case "HIGH":
      return {
        label: "High",
        className:
          "border-red-200 bg-red-50 text-red-700",
        icon: (
          <TrendingDown
            size={13}
            className="text-red-600"
          />
        ),
      };

    default:
      return {
        label:
          formatLabel(
            risk
          ),
        className:
          "border-slate-200 bg-slate-50 text-slate-600",
        icon: (
          <Activity
            size={13}
          />
        ),
      };
  }
}

// =============================================================
// STATUS BAR COLOR
// =============================================================

function getStatusBarClass(
  status
) {
  const value =
    String(
      status || ""
    ).toUpperCase();

  if (
    value ===
    "APPROVED"
  ) {
    return "bg-emerald-500";
  }

  if (
    value ===
    "REJECTED"
  ) {
    return "bg-red-500";
  }

  if (
    value.includes(
      "MANUAL"
    )
  ) {
    return "bg-amber-500";
  }

  return "bg-blue-500";
}

// =============================================================
// DEFAULT EXPORT
// =============================================================

export default Dashboard;