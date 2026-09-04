import { useEffect, useMemo, useState } from "react";

import {
  Search,
  ShieldCheck,
  FileText,
  CheckCircle2,
  XCircle,
  Clock3,
  ChevronDown,
  Activity,
  Radio,
} from "lucide-react";

import { API_URL } from "../App";

// =========================================================
// HELPERS
// =========================================================

const formatEventType = (eventType) => {
  if (!eventType) return "Unknown";

  return eventType
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const formatStatus = (status) => {
  if (!status) return "—";

  return status
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const formatDate = (dateString) => {
  if (!dateString) return "—";

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
};

// =========================================================
// RISK BADGE
// =========================================================

function RiskBadge({ level }) {
  const normalized = String(level || "").toUpperCase();

  let classes =
    "border-slate-200 bg-slate-50 text-slate-600";

  if (normalized === "LOW") {
    classes =
      "border-emerald-200 bg-emerald-50 text-emerald-600";
  }

  if (normalized === "MEDIUM") {
    classes =
      "border-amber-200 bg-amber-50 text-amber-600";
  }

  if (normalized === "HIGH") {
    classes =
      "border-orange-200 bg-orange-50 text-orange-600";
  }

  if (normalized === "CRITICAL") {
    classes =
      "border-red-200 bg-red-50 text-red-600";
  }

  return (
    <span
      className={`
        inline-flex
        items-center
        rounded-full
        border
        px-3
        py-1
        text-xs
        font-semibold
        ${classes}
      `}
    >
      {normalized || "UNKNOWN"}
    </span>
  );
}

// =========================================================
// STATUS BADGE
// =========================================================

function StatusBadge({ status }) {
  const normalized = String(status || "").toUpperCase();

  let classes =
    "border-slate-200 bg-slate-50 text-slate-600";

  if (normalized === "APPROVED") {
    classes =
      "border-emerald-200 bg-emerald-50 text-emerald-600";
  }

  if (normalized === "REJECTED") {
    classes =
      "border-red-200 bg-red-50 text-red-600";
  }

  if (normalized === "MANUAL_REVIEW_REQUIRED") {
    classes =
      "border-amber-200 bg-amber-50 text-amber-600";
  }

  if (normalized === "DISCOUNT_ADJUSTED") {
    classes =
      "border-purple-200 bg-purple-50 text-purple-600";
  }

  if (normalized === "NEW") {
    classes =
      "border-slate-200 bg-slate-50 text-slate-600";
  }

  return (
    <span
      className={`
        inline-flex
        max-w-[145px]
        items-center
        rounded-full
        border
        px-3
        py-1
        text-xs
        font-semibold
        leading-tight
        ${classes}
      `}
    >
      {formatStatus(status)}
    </span>
  );
}

// =========================================================
// EVENT ICON
// =========================================================

function EventIcon({ eventType }) {
  const isManual =
    eventType === "MANUAL_REVIEW_DECISION";

  return (
    <div
      className={`
        flex
        h-9
        w-9
        shrink-0
        items-center
        justify-center
        rounded-xl
        ${
          isManual
            ? "bg-purple-50 text-purple-600"
            : "bg-blue-50 text-blue-600"
        }
      `}
    >
      {isManual ? (
        <ShieldCheck size={19} />
      ) : (
        <FileText size={19} />
      )}
    </div>
  );
}

// =========================================================
// STAT CARD
// =========================================================

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  iconClass,
}) {
  return (
    <div
      className="
        rounded-2xl
        border
        border-slate-200
        bg-white
        p-5
        shadow-sm
      "
    >
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
          className={`
            flex
            h-11
            w-11
            items-center
            justify-center
            rounded-xl
            ${iconClass}
          `}
        >
          <Icon size={21} />
        </div>
      </div>
    </div>
  );
}

// =========================================================
// AUDIT LOGS PAGE
// =========================================================

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [eventFilter, setEventFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // =======================================================
  // REAL-TIME STATE
  // =======================================================

  const [isLive, setIsLive] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // =======================================================
  // FETCH AUDIT LOGS
  // =======================================================

  const fetchLogs = async (showRefreshing = false) => {
    try {
      if (showRefreshing) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const response = await fetch(
        `${API_URL}/audit-logs?skip=0&limit=500`
      );

      if (!response.ok) {
        throw new Error(
          `Failed to load audit logs (${response.status})`
        );
      }

      const data = await response.json();

      setLogs(data.logs || []);
      setLastUpdated(new Date());

    } catch (err) {
      console.error("Audit logs error:", err);

      setError(
        err.message || "Unable to load audit logs."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // =======================================================
  // INITIAL LOAD
  // =======================================================

  useEffect(() => {
    fetchLogs();
  }, []);

  // =======================================================
  // REAL-TIME SSE INTEGRATION
  //
  // App.jsx already owns the EventSource.
  // We listen to the CustomEvents dispatched by App.jsx.
  // =======================================================

  useEffect(() => {
    const handleConnected = () => {
      console.log(
        "AuditLogs: SSE connection detected."
      );

      setIsLive(true);
    };

    const handleOrderCreated = (event) => {
      console.log(
        "AuditLogs: order created event received:",
        event.detail
      );

      fetchLogs(true);
    };

    const handleOrderProcessed = (event) => {
      console.log(
        "AuditLogs: order processed event received:",
        event.detail
      );

      fetchLogs(true);
    };

    const handleManualReviewCompleted = (event) => {
      console.log(
        "AuditLogs: manual review completed event received:",
        event.detail
      );

      fetchLogs(true);
    };

    window.addEventListener(
      "paypilot:connected",
      handleConnected
    );

    window.addEventListener(
      "paypilot:order_created",
      handleOrderCreated
    );

    window.addEventListener(
      "paypilot:order_processed",
      handleOrderProcessed
    );

    window.addEventListener(
      "paypilot:manual_review_completed",
      handleManualReviewCompleted
    );

    return () => {
      window.removeEventListener(
        "paypilot:connected",
        handleConnected
      );

      window.removeEventListener(
        "paypilot:order_created",
        handleOrderCreated
      );

      window.removeEventListener(
        "paypilot:order_processed",
        handleOrderProcessed
      );

      window.removeEventListener(
        "paypilot:manual_review_completed",
        handleManualReviewCompleted
      );
    };
  }, []);

  // =======================================================
  // FILTERED LOGS
  // =======================================================

  const filteredLogs = useMemo(() => {
    const query = search.trim().toLowerCase();

    return logs.filter((log) => {
      const matchesSearch =
        !query ||
        String(log.id || "")
          .toLowerCase()
          .includes(query) ||
        String(log.order_id || "")
          .toLowerCase()
          .includes(query) ||
        String(log.event_type || "")
          .toLowerCase()
          .includes(query) ||
        String(log.message || "")
          .toLowerCase()
          .includes(query) ||
        String(log.performed_by || "")
          .toLowerCase()
          .includes(query);

      const matchesEvent =
        eventFilter === "ALL" ||
        log.event_type === eventFilter;

      const matchesRisk =
        riskFilter === "ALL" ||
        String(log.risk_level || "").toUpperCase() ===
          riskFilter;

      const matchesStatus =
        statusFilter === "ALL" ||
        String(log.new_status || "").toUpperCase() ===
          statusFilter;

      return (
        matchesSearch &&
        matchesEvent &&
        matchesRisk &&
        matchesStatus
      );
    });
  }, [
    logs,
    search,
    eventFilter,
    riskFilter,
    statusFilter,
  ]);

  // =======================================================
  // STATISTICS
  // =======================================================

  const totalEvents = logs.length;

  const manualReviews = logs.filter(
    (log) =>
      log.event_type === "MANUAL_REVIEW_DECISION"
  ).length;

  const approved = logs.filter(
    (log) =>
      String(log.new_status || "").toUpperCase() ===
      "APPROVED"
  ).length;

  const rejected = logs.filter(
    (log) =>
      String(log.new_status || "").toUpperCase() ===
      "REJECTED"
  ).length;

  // =======================================================
  // LOADING
  // =======================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-[1400px]">

          <div className="mb-8">
            <div className="h-8 w-52 animate-pulse rounded-lg bg-slate-200" />
            <div className="mt-3 h-4 w-72 animate-pulse rounded bg-slate-200" />
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="
                  h-32
                  animate-pulse
                  rounded-2xl
                  bg-white
                  shadow-sm
                "
              />
            ))}
          </div>

          <div
            className="
              mt-7
              h-[500px]
              animate-pulse
              rounded-2xl
              bg-white
              shadow-sm
            "
          />
        </div>
      </div>
    );
  }

  // =======================================================
  // ERROR
  // =======================================================

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-[1400px]">

          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <div className="flex items-center gap-3">

              <XCircle
                className="text-red-500"
                size={24}
              />

              <div>
                <h2 className="font-semibold text-red-700">
                  Failed to load audit logs
                </h2>

                <p className="mt-1 text-sm text-red-600">
                  {error}
                </p>
              </div>

            </div>

            <button
              onClick={() => fetchLogs(true)}
              className="
                mt-5
                rounded-lg
                bg-red-600
                px-4
                py-2
                text-sm
                font-semibold
                text-white
                transition
                hover:bg-red-700
              "
            >
              Try Again
            </button>

          </div>

        </div>
      </div>
    );
  }

  // =======================================================
  // PAGE
  // =======================================================

  return (
    <div className="min-h-screen bg-slate-50 p-8">

      <div className="mx-auto max-w-[1400px]">

        {/* =================================================
            HEADER
        ================================================= */}

        <div className="mb-7 flex items-start justify-between">

          <div>
            <div className="flex items-center gap-3">

              <div
                className="
                  flex
                  h-12
                  w-12
                  items-center
                  justify-center
                  rounded-xl
                  bg-[#020817]
                  text-white
                  shadow-sm
                "
              >
                <FileText size={24} />
              </div>

              <div>
                <div className="flex items-center gap-3">

                  <h1
                    className="
                      text-3xl
                      font-bold
                      tracking-tight
                      text-slate-900
                    "
                  >
                    Audit Logs
                  </h1>

                  {/* LIVE INDICATOR */}

                  <div
                    className={`
                      inline-flex
                      items-center
                      gap-1.5
                      rounded-full
                      border
                      px-2.5
                      py-1
                      text-xs
                      font-semibold
                      ${
                        isLive
                          ? "border-emerald-200 bg-emerald-50 text-emerald-600"
                          : "border-slate-200 bg-slate-50 text-slate-500"
                      }
                    `}
                  >
                    <span
                      className={`
                        h-2
                        w-2
                        rounded-full
                        ${
                          isLive
                            ? "animate-pulse bg-emerald-500"
                            : "bg-slate-400"
                        }
                      `}
                    />

                    {isLive ? "LIVE" : "CONNECTING"}
                  </div>

                </div>

                <p className="mt-1 text-sm text-slate-500">
                  Complete history of AI and manual risk decisions
                </p>

                {lastUpdated && (
                  <p className="mt-1 text-xs text-slate-400">
                    Last updated{" "}
                    {lastUpdated.toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </p>
                )}

              </div>

            </div>
          </div>

          <button
            onClick={() => fetchLogs(true)}
            disabled={refreshing}
            className="
              flex
              items-center
              gap-2
              rounded-xl
              border
              border-slate-200
              bg-white
              px-4
              py-2.5
              text-sm
              font-semibold
              text-slate-700
              shadow-sm
              transition
              hover:bg-slate-50
              disabled:cursor-not-allowed
              disabled:opacity-60
            "
          >
            <Activity
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

        {/* =================================================
            STAT CARDS
        ================================================= */}

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">

          <StatCard
            title="Total Events"
            value={totalEvents}
            subtitle="All recorded activities"
            icon={Activity}
            iconClass="bg-blue-50 text-blue-600"
          />

          <StatCard
            title="Manual Reviews"
            value={manualReviews}
            subtitle="Human review decisions"
            icon={ShieldCheck}
            iconClass="bg-purple-50 text-purple-600"
          />

          <StatCard
            title="Approved"
            value={approved}
            subtitle="Successful decisions"
            icon={CheckCircle2}
            iconClass="bg-emerald-50 text-emerald-600"
          />

          <StatCard
            title="Rejected"
            value={rejected}
            subtitle="Rejected decisions"
            icon={XCircle}
            iconClass="bg-red-50 text-red-600"
          />

        </div>

        {/* =================================================
            FILTER BAR
        ================================================= */}

        <div
          className="
            mt-7
            rounded-2xl
            border
            border-slate-200
            bg-white
            p-4
            shadow-sm
          "
        >

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1.8fr_1fr_1fr_1fr]">

            {/* SEARCH */}

            <div className="relative">

              <Search
                size={19}
                className="
                  absolute
                  left-4
                  top-1/2
                  -translate-y-1/2
                  text-slate-400
                "
              />

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search logs, order ID, event, message..."
                className="
                  h-12
                  w-full
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  pl-11
                  pr-4
                  text-sm
                  text-slate-700
                  outline-none
                  transition
                  placeholder:text-slate-400
                  focus:border-blue-400
                  focus:bg-white
                  focus:ring-2
                  focus:ring-blue-100
                "
              />

            </div>

            {/* EVENT FILTER */}

            <div className="relative">

              <select
                value={eventFilter}
                onChange={(e) =>
                  setEventFilter(e.target.value)
                }
                className="
                  h-12
                  w-full
                  appearance-none
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  px-4
                  pr-10
                  text-sm
                  font-medium
                  text-slate-700
                  outline-none
                  focus:border-blue-400
                  focus:ring-2
                  focus:ring-blue-100
                "
              >
                <option value="ALL">
                  All Events
                </option>

                <option value="ORDER_DECISION">
                  Order Decision
                </option>

                <option value="MANUAL_REVIEW_DECISION">
                  Manual Review
                </option>

              </select>

              <ChevronDown
                size={17}
                className="
                  pointer-events-none
                  absolute
                  right-4
                  top-1/2
                  -translate-y-1/2
                  text-slate-400
                "
              />

            </div>

            {/* RISK FILTER */}

            <div className="relative">

              <select
                value={riskFilter}
                onChange={(e) =>
                  setRiskFilter(e.target.value)
                }
                className="
                  h-12
                  w-full
                  appearance-none
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  px-4
                  pr-10
                  text-sm
                  font-medium
                  text-slate-700
                  outline-none
                  focus:border-blue-400
                  focus:ring-2
                  focus:ring-blue-100
                "
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

              <ChevronDown
                size={17}
                className="
                  pointer-events-none
                  absolute
                  right-4
                  top-1/2
                  -translate-y-1/2
                  text-slate-400
                "
              />

            </div>

            {/* STATUS FILTER */}

            <div className="relative">

              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value)
                }
                className="
                  h-12
                  w-full
                  appearance-none
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  px-4
                  pr-10
                  text-sm
                  font-medium
                  text-slate-700
                  outline-none
                  focus:border-blue-400
                  focus:ring-2
                  focus:ring-blue-100
                "
              >
                <option value="ALL">
                  All Status
                </option>

                <option value="NEW">
                  New
                </option>

                <option value="MANUAL_REVIEW_REQUIRED">
                  Manual Review Required
                </option>

                <option value="APPROVED">
                  Approved
                </option>

                <option value="REJECTED">
                  Rejected
                </option>

                <option value="DISCOUNT_ADJUSTED">
                  Discount Adjusted
                </option>

              </select>

              <ChevronDown
                size={17}
                className="
                  pointer-events-none
                  absolute
                  right-4
                  top-1/2
                  -translate-y-1/2
                  text-slate-400
                "
              />

            </div>

          </div>

        </div>

        {/* =================================================
            ACTIVITY HISTORY
        ================================================= */}

        <div
          className="
            mt-7
            overflow-hidden
            rounded-2xl
            border
            border-slate-200
            bg-white
            shadow-sm
          "
        >

          {/* TABLE HEADER */}

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-slate-200
              px-7
              py-5
            "
          >

            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Activity History
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                {filteredLogs.length} of {totalEvents} events shown
              </p>
            </div>

            <div className="flex items-center gap-2 text-sm text-slate-500">

              <Clock3 size={17} />

              Latest first

              {isLive && (
                <>
                  <span className="mx-1 text-slate-300">
                    •
                  </span>

                  <Radio
                    size={15}
                    className="text-emerald-500"
                  />

                  <span className="text-emerald-600">
                    Live
                  </span>
                </>
              )}

            </div>

          </div>

          {/* =================================================
              EMPTY
          ================================================= */}

          {filteredLogs.length === 0 ? (

            <div className="px-6 py-20 text-center">

              <div
                className="
                  mx-auto
                  flex
                  h-14
                  w-14
                  items-center
                  justify-center
                  rounded-full
                  bg-slate-100
                  text-slate-400
                "
              >
                <Search size={24} />
              </div>

              <h3 className="mt-4 font-semibold text-slate-800">
                No audit logs found
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Try changing your search or filters.
              </p>

            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full min-w-[1150px]">

                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">

                    <th className="px-7 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Event
                    </th>

                    <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Order
                    </th>

                    <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Status Change
                    </th>

                    <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Risk
                    </th>

                    <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Performed By
                    </th>

                    <th className="px-5 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Message
                    </th>

                    <th className="px-7 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Time
                    </th>

                  </tr>
                </thead>

                <tbody>

                  {filteredLogs.map((log) => (

                    <tr
                      key={log.id}
                      className="
                        border-b
                        border-slate-100
                        transition
                        hover:bg-slate-50
                      "
                    >

                      {/* EVENT */}

                      <td className="px-7 py-5">

                        <div className="flex items-center gap-3">

                          <EventIcon
                            eventType={log.event_type}
                          />

                          <div className="min-w-0">

                            <p className="max-w-[160px] text-sm font-semibold uppercase leading-5 text-slate-800">
                              {formatEventType(
                                log.event_type
                              )}
                            </p>

                            <p className="mt-1 text-xs text-slate-400">
                              #{log.id}
                            </p>

                          </div>

                        </div>

                      </td>

                      {/* ORDER */}

                      <td className="px-5 py-5">

                        <p className="text-sm font-bold text-slate-800">
                          #{log.order_id ?? "—"}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          Merchant #{log.merchant_id ?? "—"}
                        </p>

                      </td>

                      {/* STATUS CHANGE */}

                      <td className="px-5 py-5">

                        <div className="flex items-center gap-2">

                          <StatusBadge
                            status={log.old_status}
                          />

                          <span className="text-slate-400">
                            →
                          </span>

                          <StatusBadge
                            status={log.new_status}
                          />

                        </div>

                      </td>

                      {/* RISK */}

                      <td className="px-5 py-5">

                        <div className="flex items-center gap-3">

                          <span className="text-sm font-bold text-slate-800">
                            {log.risk_score ?? 0}
                          </span>

                          <RiskBadge
                            level={log.risk_level}
                          />

                        </div>

                      </td>

                      {/* PERFORMED BY */}

                      <td className="px-5 py-5">

                        <div className="flex items-center gap-3">

                          <div
                            className="
                              flex
                              h-9
                              w-9
                              shrink-0
                              items-center
                              justify-center
                              rounded-full
                              bg-slate-100
                              text-xs
                              font-bold
                              text-slate-600
                            "
                          >
                            {String(
                              log.performed_by || "?"
                            )
                              .charAt(0)
                              .toUpperCase()}
                          </div>

                          <span className="whitespace-nowrap text-sm font-medium text-slate-700">
                            {log.performed_by || "—"}
                          </span>

                        </div>

                      </td>

                      {/* MESSAGE */}

                      <td className="px-5 py-5">

                        <div
                          className="max-w-[220px] truncate text-sm text-slate-600"
                          title={log.message}
                        >
                          {log.message || "—"}
                        </div>

                      </td>

                      {/* TIME */}

                      <td className="whitespace-nowrap px-7 py-5">

                        <span className="text-sm font-medium text-slate-700">
                          {formatDate(log.created_at)}
                        </span>

                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </div>

      </div>

    </div>
  );
}