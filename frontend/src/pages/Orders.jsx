import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Search,
  RefreshCw,
  ShoppingCart,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  Package,
  User,
  IndianRupee,
  Percent,
  Hash,
  Clock3,
  Wifi,
  WifiOff,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import { getOrders } from "../services/api";

// =========================================================
// API / SSE CONFIGURATION
// =========================================================

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const EVENTS_URL =
  `${API_BASE_URL}/events/orders`;


// =========================================================
// ORDERS PAGE
// =========================================================

function Orders() {
  // =======================================================
  // STATE
  // =======================================================

  const [orders, setOrders] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState("");

  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] =
    useState("ALL");

  const [riskFilter, setRiskFilter] =
    useState("ALL");

  const [selectedOrder, setSelectedOrder] =
    useState(null);

  const [currentPage, setCurrentPage] =
    useState(1);

  const [sseConnected, setSseConnected] =
    useState(false);

  const [lastUpdated, setLastUpdated] =
    useState(null);

  const ordersPerPage = 8;

  // =======================================================
  // SSE REFS
  // =======================================================

  const eventSourceRef = useRef(null);

  const reloadTimerRef = useRef(null);


  // =======================================================
  // LOAD ORDERS
  // =======================================================

  const loadOrders = useCallback(
    async (showRefresh = false) => {
      try {
        if (showRefresh) {
          setRefreshing(true);
        } else if (orders.length === 0) {
          setLoading(true);
        }

        setError("");

        const data = await getOrders();

        const normalizedOrders =
          Array.isArray(data)
            ? data
            : [];

        setOrders(normalizedOrders);

        setLastUpdated(new Date());
      } catch (err) {
        console.error(
          "Failed to load orders:",
          err
        );

        const backendError =
          err?.response?.data?.detail;

        if (
          typeof backendError === "object" &&
          backendError !== null
        ) {
          setError(
            backendError.message ||
              "Unable to load orders."
          );
        } else {
          setError(
            backendError ||
              err?.message ||
              "Unable to load orders from PayPilot API."
          );
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [orders.length]
  );


  // =======================================================
  // INITIAL LOAD
  // =======================================================

  useEffect(() => {
    loadOrders();
  }, [loadOrders]);


  // =======================================================
  // REAL-TIME SSE
  // =======================================================

  useEffect(() => {
    let isMounted = true;

    // -----------------------------------------------------
    // DEBOUNCED RELOAD
    // -----------------------------------------------------

    const scheduleOrdersReload = () => {
      if (reloadTimerRef.current) {
        clearTimeout(
          reloadTimerRef.current
        );
      }

      reloadTimerRef.current =
        setTimeout(() => {
          if (!isMounted) {
            return;
          }

          loadOrders(false);
        }, 300);
    };


    // -----------------------------------------------------
    // CONNECT SSE
    // -----------------------------------------------------

    const connectSSE = () => {
      if (!isMounted) {
        return;
      }

      console.log(
        "Connecting to PayPilot SSE:",
        EVENTS_URL
      );

      const eventSource =
        new EventSource(EVENTS_URL);

      eventSourceRef.current =
        eventSource;


      // ---------------------------------------------------
      // CONNECTED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "connected",
        () => {
          if (!isMounted) {
            return;
          }

          console.log(
            "PayPilot SSE connected."
          );

          setSseConnected(true);
        }
      );


      // ---------------------------------------------------
      // ORDER CREATED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "order_created",
        (event) => {
          if (!isMounted) {
            return;
          }

          console.log(
            "SSE order_created:",
            event.data
          );

          scheduleOrdersReload();
        }
      );


      // ---------------------------------------------------
      // ORDER UPDATED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "order_updated",
        (event) => {
          if (!isMounted) {
            return;
          }

          console.log(
            "SSE order_updated:",
            event.data
          );

          scheduleOrdersReload();
        }
      );


      // ---------------------------------------------------
      // ORDER PROCESSED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "order_processed",
        (event) => {
          if (!isMounted) {
            return;
          }

          console.log(
            "SSE order_processed:",
            event.data
          );

          scheduleOrdersReload();
        }
      );


      // ---------------------------------------------------
      // ORDER APPROVED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "order_approved",
        (event) => {
          if (!isMounted) {
            return;
          }

          console.log(
            "SSE order_approved:",
            event.data
          );

          scheduleOrdersReload();
        }
      );


      // ---------------------------------------------------
      // ORDER REJECTED
      // ---------------------------------------------------

      eventSource.addEventListener(
        "order_rejected",
        (event) => {
          if (!isMounted) {
            return;
          }

          console.log(
            "SSE order_rejected:",
            event.data
          );

          scheduleOrdersReload();
        }
      );


      // ---------------------------------------------------
      // GENERIC MESSAGE
      // ---------------------------------------------------

      eventSource.onmessage = (event) => {
        console.log(
          "SSE generic message:",
          event.data
        );
      };


      // ---------------------------------------------------
      // SSE ERROR
      // ---------------------------------------------------

      eventSource.onerror = () => {
        if (!isMounted) {
          return;
        }

        console.warn(
          "PayPilot SSE connection lost."
        );

        setSseConnected(false);

        // EventSource automatically reconnects.
      };
    };


    connectSSE();


    // -----------------------------------------------------
    // CLEANUP
    // -----------------------------------------------------

    return () => {
      isMounted = false;

      if (reloadTimerRef.current) {
        clearTimeout(
          reloadTimerRef.current
        );

        reloadTimerRef.current = null;
      }

      if (eventSourceRef.current) {
        eventSourceRef.current.close();

        eventSourceRef.current = null;
      }

      setSseConnected(false);
    };
  }, [loadOrders]);


  // =======================================================
  // FILTER ORDERS
  // =======================================================

  const filteredOrders = useMemo(() => {
    const query =
      search
        .trim()
        .toLowerCase();

    return orders.filter((order) => {
      const status =
        String(
          order.status || ""
        ).toUpperCase();

      const riskLevel =
        String(
          order.risk_level ??
            order.riskLevel ??
            ""
        ).toUpperCase();


      // ---------------------------------------------------
      // STATUS
      // ---------------------------------------------------

      const matchesStatus =
        statusFilter === "ALL" ||
        status === statusFilter;


      // ---------------------------------------------------
      // RISK
      // ---------------------------------------------------

      const matchesRisk =
        riskFilter === "ALL" ||
        riskLevel === riskFilter;


      // ---------------------------------------------------
      // SEARCH
      // ---------------------------------------------------

      const searchableValues = [
        order.id,
        order.product_id,
        order.merchant_id,
        order.quantity,
        order.status,
        order.risk_level,
        order.riskLevel,
        order.risk_score,
        order.riskScore,
      ];


      const matchesSearch =
        !query ||
        searchableValues.some(
          (value) =>
            String(value ?? "")
              .toLowerCase()
              .includes(query)
        );


      return (
        matchesStatus &&
        matchesRisk &&
        matchesSearch
      );
    });
  }, [
    orders,
    search,
    statusFilter,
    riskFilter,
  ]);


  // =======================================================
  // PAGINATION
  // =======================================================

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        filteredOrders.length /
          ordersPerPage
      )
    );


  const safeCurrentPage =
    Math.min(
      currentPage,
      totalPages
    );


  const startIndex =
    (safeCurrentPage - 1) *
    ordersPerPage;


  const visibleOrders =
    filteredOrders.slice(
      startIndex,
      startIndex +
        ordersPerPage
    );


  // -------------------------------------------------------
  // RESET PAGE
  // -------------------------------------------------------

  useEffect(() => {
    setCurrentPage(1);
  }, [
    search,
    statusFilter,
    riskFilter,
  ]);


  // =======================================================
  // STATISTICS
  // =======================================================

  const statistics = useMemo(() => {
    const total =
      orders.length;

    const approved =
      orders.filter(
        (order) =>
          String(order.status)
            .toUpperCase() ===
          "APPROVED"
      ).length;


    const rejected =
      orders.filter(
        (order) =>
          String(order.status)
            .toUpperCase() ===
          "REJECTED"
      ).length;


    const manualReview =
      orders.filter(
        (order) =>
          String(order.status)
            .toUpperCase() ===
          "MANUAL_REVIEW_REQUIRED"
      ).length;


    const lowRisk =
      orders.filter(
        (order) =>
          String(
            order.risk_level ??
              order.riskLevel ??
              ""
          ).toUpperCase() ===
          "LOW"
      ).length;


    const mediumRisk =
      orders.filter(
        (order) =>
          String(
            order.risk_level ??
              order.riskLevel ??
              ""
          ).toUpperCase() ===
          "MEDIUM"
      ).length;


    const highRisk =
      orders.filter(
        (order) =>
          String(
            order.risk_level ??
              order.riskLevel ??
              ""
          ).toUpperCase() ===
          "HIGH"
      ).length;


    const totalRevenue =
      orders
        .filter(
          (order) =>
            String(order.status)
              .toUpperCase() ===
            "APPROVED"
        )
        .reduce(
          (total, order) =>
            total +
            Number(
              order.final_amount ??
                order.finalAmount ??
                0
            ),
          0
        );


    const averageRiskScore =
      total === 0
        ? 0
        : orders.reduce(
            (sum, order) =>
              sum +
              Number(
                order.risk_score ??
                  order.riskScore ??
                  0
              ),
            0
          ) / total;


    return {
      total,
      approved,
      rejected,
      manualReview,
      lowRisk,
      mediumRisk,
      highRisk,
      totalRevenue,
      averageRiskScore,
    };
  }, [orders]);


  // =======================================================
  // HELPERS
  // =======================================================

  const formatCurrency =
    (value) =>
      `₹${Number(
        value || 0
      ).toLocaleString(
        "en-IN",
        {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }
      )}`;


  const formatLastUpdated =
    () => {
      if (!lastUpdated) {
        return "Not updated yet";
      }

      return lastUpdated.toLocaleTimeString(
        "en-IN",
        {
          hour: "numeric",
          minute: "2-digit",
          second: "2-digit",
        }
      );
    };


  // =======================================================
  // STATUS CONFIG
  // =======================================================

  const getStatusConfig =
    (status) => {
      const normalized =
        String(
          status || ""
        ).toUpperCase();


      switch (normalized) {
        case "APPROVED":
          return {
            label: "Approved",
            className:
              "bg-emerald-50 text-emerald-700 border-emerald-200",
            icon:
              CheckCircle2,
          };


        case "REJECTED":
          return {
            label: "Rejected",
            className:
              "bg-red-50 text-red-700 border-red-200",
            icon:
              XCircle,
          };


        case "MANUAL_REVIEW_REQUIRED":
          return {
            label: "Manual Review",
            className:
              "bg-amber-50 text-amber-700 border-amber-200",
            icon:
              AlertTriangle,
          };


        case "DISCOUNT_ADJUSTED":
          return {
            label: "Discount Adjusted",
            className:
              "bg-blue-50 text-blue-700 border-blue-200",
            icon:
              Percent,
          };


        case "PENDING":
          return {
            label: "Pending",
            className:
              "bg-slate-50 text-slate-700 border-slate-200",
            icon:
              Clock3,
          };


        default:
          return {
            label:
              status ||
              "Unknown",
            className:
              "bg-slate-50 text-slate-600 border-slate-200",
            icon:
              Clock3,
          };
      }
    };


  // =======================================================
  // RISK CONFIG
  // =======================================================

  const getRiskConfig =
    (riskLevel) => {
      const normalized =
        String(
          riskLevel || ""
        ).toUpperCase();


      switch (normalized) {
        case "LOW":
          return {
            label: "Low",
            className:
              "bg-emerald-50 text-emerald-700 border-emerald-200",
            iconClass:
              "text-emerald-600",
          };


        case "MEDIUM":
          return {
            label: "Medium",
            className:
              "bg-amber-50 text-amber-700 border-amber-200",
            iconClass:
              "text-amber-600",
          };


        case "HIGH":
          return {
            label: "High",
            className:
              "bg-red-50 text-red-700 border-red-200",
            iconClass:
              "text-red-600",
          };


        default:
          return {
            label:
              riskLevel ||
              "Unknown",
            className:
              "bg-slate-50 text-slate-600 border-slate-200",
            iconClass:
              "text-slate-500",
          };
      }
    };


  // =======================================================
  // LOADING
  // =======================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-6 lg:p-8">
        <div className="mx-auto max-w-[1500px]">

          <div className="mb-8">
            <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />

            <div className="mt-3 h-9 w-52 animate-pulse rounded bg-slate-200" />

            <div className="mt-3 h-4 w-80 animate-pulse rounded bg-slate-200" />
          </div>


          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map(
              (item) => (
                <div
                  key={item}
                  className="h-32 animate-pulse rounded-2xl bg-white shadow-sm ring-1 ring-slate-200"
                />
              )
            )}
          </div>


          <div className="mt-6 h-[500px] animate-pulse rounded-2xl bg-white shadow-sm ring-1 ring-slate-200" />
        </div>
      </div>
    );
  }


  // =======================================================
  // PAGE
  // =======================================================

  return (
    <div className="min-h-screen bg-slate-50">

      <div className="mx-auto max-w-[1500px] px-5 py-6 lg:px-8 lg:py-8">

        {/* =================================================
            HEADER
        ================================================= */}

        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">

          <div>

            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-500">
              <span>Admin</span>
              <span>/</span>
              <span>Orders</span>
            </div>


            <h1 className="text-3xl font-bold tracking-tight text-slate-950">
              Orders
            </h1>


            <p className="mt-2 text-sm text-slate-500">
              Monitor and manage PayPilot payment transactions.
            </p>

          </div>


          <div className="flex items-center gap-3">

            {/* SSE STATUS */}

            <div
              className={`hidden items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium sm:flex ${
                sseConnected
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
            >

              {sseConnected ? (
                <>
                  <Wifi size={15} />

                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />

                  Live
                </>
              ) : (
                <>
                  <WifiOff size={15} />

                  <span className="h-2 w-2 rounded-full bg-amber-500" />

                  Reconnecting...
                </>
              )}

            </div>


            {/* LAST UPDATED */}

            <div className="hidden text-right lg:block">

              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                Last Updated
              </p>

              <p className="text-xs font-semibold text-slate-600">
                {formatLastUpdated()}
              </p>

            </div>


            {/* REFRESH */}

            <button
              onClick={() =>
                loadOrders(true)
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


        {/* =================================================
            ERROR
        ================================================= */}

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">

            <XCircle
              size={20}
              className="mt-0.5 shrink-0"
            />

            <div>

              <p className="font-semibold">
                Unable to load orders
              </p>

              <p className="mt-1">
                {error}
              </p>

            </div>

          </div>
        )}


        {/* =================================================
            REAL-TIME STATUS
        ================================================= */}

        {sseConnected && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">

            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600">
              <Wifi size={17} />
            </div>

            <div>

              <p className="text-sm font-semibold text-emerald-800">
                Real-time monitoring active
              </p>

              <p className="text-xs text-emerald-700">
                New and processed orders will appear automatically.
              </p>

            </div>

          </div>
        )}


        {/* =================================================
            STATISTICS
        ================================================= */}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <StatCard
            title="Total Orders"
            value={statistics.total}
            subtitle="All transactions"
            icon={ShoppingCart}
            iconClass="bg-blue-50 text-blue-600"
          />


          <StatCard
            title="Approved"
            value={statistics.approved}
            subtitle="Successfully processed"
            icon={CheckCircle2}
            iconClass="bg-emerald-50 text-emerald-600"
            valueClass="text-emerald-700"
          />


          <StatCard
            title="Rejected"
            value={statistics.rejected}
            subtitle="Risk rejected"
            icon={XCircle}
            iconClass="bg-red-50 text-red-600"
            valueClass="text-red-700"
          />


          <StatCard
            title="Manual Review"
            value={statistics.manualReview}
            subtitle="Requires attention"
            icon={AlertTriangle}
            iconClass="bg-amber-50 text-amber-600"
            valueClass="text-amber-700"
          />

        </div>


        {/* =================================================
            ANALYTICS STRIP
        ================================================= */}

        <div className="mt-4 grid gap-4 md:grid-cols-3">

          <MiniMetric
            title="Approved Revenue"
            value={formatCurrency(
              statistics.totalRevenue
            )}
            subtitle="From approved orders"
            icon={IndianRupee}
            iconClass="bg-violet-50 text-violet-600"
          />


          <MiniMetric
            title="High Risk Orders"
            value={statistics.highRisk}
            subtitle={`${statistics.mediumRisk} medium-risk orders`}
            icon={ShieldAlert}
            iconClass="bg-red-50 text-red-600"
          />


          <MiniMetric
            title="Average Risk Score"
            value={
              Number(
                statistics.averageRiskScore
              ).toFixed(1)
            }
            subtitle={`${statistics.lowRisk} low-risk orders`}
            icon={TrendingUp}
            iconClass="bg-blue-50 text-blue-600"
          />

        </div>


        {/* =================================================
            ORDERS PANEL
        ================================================= */}

        <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          {/* PANEL HEADER */}

          <div className="border-b border-slate-200 p-5 lg:p-6">

            <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">

              <div>

                <h2 className="text-lg font-bold text-slate-950">
                  All Orders
                </h2>

                <p className="mt-1 text-sm text-slate-500">

                  {filteredOrders.length}

                  {" "}
                  transaction
                  {filteredOrders.length !== 1
                    ? "s"
                    : ""}

                  {" "}
                  found

                </p>

              </div>


              <div className="flex flex-col gap-3 sm:flex-row">

                {/* SEARCH */}

                <div className="relative">

                  <Search
                    size={18}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />

                  <input
                    type="text"
                    value={search}
                    onChange={(e) =>
                      setSearch(
                        e.target.value
                      )
                    }
                    placeholder="Search orders..."
                    className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 sm:w-64"
                  />

                </div>


                {/* STATUS */}

                <select
                  value={statusFilter}
                  onChange={(e) =>
                    setStatusFilter(
                      e.target.value
                    )
                  }
                  className="h-11 rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
                >

                  <option value="ALL">
                    All Status
                  </option>

                  <option value="APPROVED">
                    Approved
                  </option>

                  <option value="REJECTED">
                    Rejected
                  </option>

                  <option value="MANUAL_REVIEW_REQUIRED">
                    Manual Review
                  </option>

                  <option value="DISCOUNT_ADJUSTED">
                    Discount Adjusted
                  </option>

                  <option value="PENDING">
                    Pending
                  </option>

                </select>


                {/* RISK */}

                <select
                  value={riskFilter}
                  onChange={(e) =>
                    setRiskFilter(
                      e.target.value
                    )
                  }
                  className="h-11 rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-slate-700 outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
                >

                  <option value="ALL">
                    All Risk
                  </option>

                  <option value="LOW">
                    Low Risk
                  </option>

                  <option value="MEDIUM">
                    Medium Risk
                  </option>

                  <option value="HIGH">
                    High Risk
                  </option>

                </select>

              </div>

            </div>

          </div>


          {/* =================================================
              TABLE
          ================================================= */}

          {visibleOrders.length === 0 ? (

            <div className="flex min-h-[350px] flex-col items-center justify-center px-6 text-center">

              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                <ShoppingCart size={28} />
              </div>

              <h3 className="mt-4 text-base font-semibold text-slate-900">
                No orders found
              </h3>

              <p className="mt-1 max-w-sm text-sm text-slate-500">
                Try changing your search, status, or risk filter.
              </p>

            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full min-w-[1200px]">

                <thead>

                  <tr className="border-b border-slate-200 bg-slate-50/80">

                    <TableHeader>
                      Order
                    </TableHeader>

                    <TableHeader>
                      Merchant
                    </TableHeader>

                    <TableHeader>
                      Product
                    </TableHeader>

                    <TableHeader>
                      Quantity
                    </TableHeader>

                    <TableHeader>
                      Amount
                    </TableHeader>

                    <TableHeader>
                      Discount
                    </TableHeader>

                    <TableHeader>
                      Risk
                    </TableHeader>

                    <TableHeader>
                      Status
                    </TableHeader>

                    <TableHeader align="right">
                      Action
                    </TableHeader>

                  </tr>

                </thead>


                <tbody className="divide-y divide-slate-100">

                  {visibleOrders.map(
                    (order) => {

                      const status =
                        getStatusConfig(
                          order.status
                        );

                      const StatusIcon =
                        status.icon;


                      const riskLevel =
                        String(
                          order.risk_level ??
                            order.riskLevel ??
                            ""
                        ).toUpperCase();


                      const risk =
                        getRiskConfig(
                          riskLevel
                        );


                      const RiskIcon =
                        riskLevel === "HIGH"
                          ? ShieldAlert
                          : TrendingUp;


                      const riskScore =
                        Number(
                          order.risk_score ??
                            order.riskScore ??
                            0
                        );


                      return (
                        <tr
                          key={order.id}
                          className="group transition hover:bg-slate-50/70"
                        >

                          {/* ORDER */}

                          <td className="px-6 py-5">

                            <div className="flex items-center gap-3">

                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                                <Hash size={18} />
                              </div>

                              <div>

                                <p className="font-bold text-slate-900">
                                  #{order.id}
                                </p>

                                <p className="mt-0.5 text-xs text-slate-400">
                                  Transaction
                                </p>

                              </div>

                            </div>

                          </td>


                          {/* MERCHANT */}

                          <td className="px-6 py-5">

                            <div className="flex items-center gap-2">

                              <User
                                size={16}
                                className="text-slate-400"
                              />

                              <span className="text-sm font-medium text-slate-700">
                                Merchant #{order.merchant_id}
                              </span>

                            </div>

                          </td>


                          {/* PRODUCT */}

                          <td className="px-6 py-5">

                            <div className="flex items-center gap-3">

                              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                                <Package size={18} />
                              </div>

                              <div>

                                <p className="text-sm font-semibold text-slate-900">
                                  Product #{order.product_id}
                                </p>

                                <p className="text-xs text-slate-400">
                                  ID {order.product_id}
                                </p>

                              </div>

                            </div>

                          </td>


                          {/* QUANTITY */}

                          <td className="px-6 py-5">

                            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-sm font-semibold text-slate-700">
                              {order.quantity ?? 0}
                            </span>

                          </td>


                          {/* AMOUNT */}

                          <td className="px-6 py-5">

                            <div>

                              <p className="text-sm font-bold text-slate-900">
                                {formatCurrency(
                                  order.final_amount ??
                                    order.finalAmount
                                )}
                              </p>

                              <p className="mt-1 text-xs text-slate-400">
                                Original{" "}
                                {formatCurrency(
                                  order.original_amount ??
                                    order.originalAmount
                                )}
                              </p>

                            </div>

                          </td>


                          {/* DISCOUNT */}

                          <td className="px-6 py-5">

                            <div>

                              <p className="text-sm font-semibold text-slate-700">

                                {Number(
                                  order.discount_percent ??
                                    order.discountPercent ??
                                    0
                                ).toFixed(2)}

                                %

                              </p>

                              <p className="mt-1 text-xs text-slate-400">

                                -

                                {formatCurrency(
                                  order.discount_amount ??
                                    order.discountAmount
                                )}

                              </p>

                            </div>

                          </td>


                          {/* RISK */}

                          <td className="px-6 py-5">

                            <div className="flex flex-col items-start gap-1.5">

                              <span
                                className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-xs font-bold ${risk.className}`}
                              >

                                <RiskIcon
                                  size={13}
                                  className={risk.iconClass}
                                />

                                {risk.label}

                              </span>

                              <span className="text-xs font-medium text-slate-400">
                                Score: {riskScore}
                              </span>

                            </div>

                          </td>


                          {/* STATUS */}

                          <td className="px-6 py-5">

                            <span
                              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold ${status.className}`}
                            >

                              <StatusIcon
                                size={14}
                              />

                              {status.label}

                            </span>

                          </td>


                          {/* ACTION */}

                          <td className="px-6 py-5 text-right">

                            <button
                              onClick={() =>
                                setSelectedOrder(
                                  order
                                )
                              }
                              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 opacity-0 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 group-hover:opacity-100"
                            >

                              <Eye size={15} />

                              View

                            </button>

                          </td>

                        </tr>
                      );
                    }
                  )}

                </tbody>

              </table>

            </div>

          )}


          {/* =================================================
              PAGINATION
          ================================================= */}

          {filteredOrders.length > 0 && (

            <div className="flex flex-col gap-4 border-t border-slate-200 px-5 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">

              <p className="text-sm text-slate-500">

                Showing{" "}

                <span className="font-semibold text-slate-700">
                  {startIndex + 1}
                </span>

                {" "}to{" "}

                <span className="font-semibold text-slate-700">
                  {Math.min(
                    startIndex +
                      visibleOrders.length,
                    filteredOrders.length
                  )}
                </span>

                {" "}of{" "}

                <span className="font-semibold text-slate-700">
                  {filteredOrders.length}
                </span>

              </p>


              <div className="flex items-center gap-2">

                <button
                  disabled={
                    safeCurrentPage === 1
                  }
                  onClick={() =>
                    setCurrentPage(
                      (page) =>
                        Math.max(
                          1,
                          page - 1
                        )
                    )
                  }
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft
                    size={17}
                  />
                </button>


                <div className="flex h-9 min-w-9 items-center justify-center rounded-lg bg-blue-600 px-3 text-sm font-semibold text-white">
                  {safeCurrentPage}
                </div>


                <span className="px-1 text-sm text-slate-400">
                  of {totalPages}
                </span>


                <button
                  disabled={
                    safeCurrentPage >=
                    totalPages
                  }
                  onClick={() =>
                    setCurrentPage(
                      (page) =>
                        Math.min(
                          totalPages,
                          page + 1
                        )
                    )
                  }
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronRight
                    size={17}
                  />
                </button>

              </div>

            </div>

          )}

        </div>

      </div>


      {/* =====================================================
          ORDER DETAILS MODAL
      ===================================================== */}

      {selectedOrder && (
        <OrderDetailsModal
          order={selectedOrder}
          onClose={() =>
            setSelectedOrder(null)
          }
          formatCurrency={
            formatCurrency
          }
        />
      )}

    </div>
  );
}


// =============================================================
// TABLE HEADER
// =============================================================

function TableHeader({
  children,
  align = "left",
}) {
  return (
    <th
      className={`px-6 py-4 text-${align} text-xs font-bold uppercase tracking-wider text-slate-500`}
    >
      {children}
    </th>
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
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">

      <div className="flex items-start justify-between">

        <div>

          <p className="text-sm font-medium text-slate-500">
            {title}
          </p>

          <p
            className={`mt-2 text-2xl font-bold tracking-tight ${valueClass}`}
          >
            {value}
          </p>

        </div>


        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl ${iconClass}`}
        >
          <Icon size={21} />
        </div>

      </div>


      <p className="mt-4 text-xs font-medium text-slate-400">
        {subtitle}
      </p>

    </div>
  );
}


// =============================================================
// MINI METRIC
// =============================================================

function MiniMetric({
  title,
  value,
  subtitle,
  icon: Icon,
  iconClass,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

      <div className="flex items-center gap-3">

        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
        >
          <Icon size={19} />
        </div>


        <div className="min-w-0">

          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {title}
          </p>

          <p className="mt-1 truncate text-lg font-bold text-slate-950">
            {value}
          </p>

        </div>

      </div>


      <p className="mt-3 text-xs text-slate-500">
        {subtitle}
      </p>

    </div>
  );
}


// =============================================================
// ORDER DETAILS MODAL
// =============================================================

function OrderDetailsModal({
  order,
  onClose,
  formatCurrency,
}) {
  const statusConfig =
    (() => {
      switch (
        String(
          order.status || ""
        ).toUpperCase()
      ) {
        case "APPROVED":
          return {
            label: "Approved",
            className:
              "bg-emerald-50 text-emerald-700 border-emerald-200",
          };

        case "REJECTED":
          return {
            label: "Rejected",
            className:
              "bg-red-50 text-red-700 border-red-200",
          };

        case "MANUAL_REVIEW_REQUIRED":
          return {
            label: "Manual Review",
            className:
              "bg-amber-50 text-amber-700 border-amber-200",
          };

        case "DISCOUNT_ADJUSTED":
          return {
            label: "Discount Adjusted",
            className:
              "bg-blue-50 text-blue-700 border-blue-200",
          };

        default:
          return {
            label:
              order.status ||
              "Unknown",
            className:
              "bg-slate-50 text-slate-700 border-slate-200",
          };
      }
    })();


  const riskLevel =
    String(
      order.risk_level ??
        order.riskLevel ??
        "UNKNOWN"
    ).toUpperCase();


  const riskConfig =
    (() => {
      switch (riskLevel) {
        case "LOW":
          return {
            label: "Low",
            className:
              "bg-emerald-50 text-emerald-700 border-emerald-200",
          };

        case "MEDIUM":
          return {
            label: "Medium",
            className:
              "bg-amber-50 text-amber-700 border-amber-200",
          };

        case "HIGH":
          return {
            label: "High",
            className:
              "bg-red-50 text-red-700 border-red-200",
          };

        default:
          return {
            label: riskLevel,
            className:
              "bg-slate-50 text-slate-700 border-slate-200",
          };
      }
    })();


  const riskScore =
    Number(
      order.risk_score ??
        order.riskScore ??
        0
    );


  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (
          event.target ===
          event.currentTarget
        ) {
          onClose();
        }
      }}
    >

      <div className="w-full max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">

        {/* HEADER */}

        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">

          <div>

            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Transaction
            </p>

            <h2 className="mt-1 text-xl font-bold text-slate-950">
              Order #{order.id}
            </h2>

          </div>


          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          >
            <X size={20} />
          </button>

        </div>


        {/* BODY */}

        <div className="max-h-[75vh] overflow-y-auto p-6">

          {/* STATUS / RISK */}

          <div className="mb-6 grid gap-4 sm:grid-cols-2">

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

              <p className="text-xs font-medium text-slate-500">
                Current Status
              </p>

              <span
                className={`mt-2 inline-flex rounded-full border px-3 py-1.5 text-xs font-bold ${statusConfig.className}`}
              >
                {statusConfig.label}
              </span>

            </div>


            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">

              <p className="text-xs font-medium text-slate-500">
                Risk
              </p>

              <div className="mt-2 flex items-center gap-2">

                <span
                  className={`inline-flex rounded-full border px-3 py-1.5 text-xs font-bold ${riskConfig.className}`}
                >
                  {riskConfig.label}
                </span>

                <span className="text-xs font-semibold text-slate-500">
                  Score: {riskScore}
                </span>

              </div>

            </div>

          </div>


          {/* AMOUNT */}

          <div className="mb-6 rounded-xl border border-violet-100 bg-violet-50 p-5">

            <p className="text-xs font-semibold uppercase tracking-wider text-violet-600">
              Final Amount
            </p>

            <p className="mt-1 text-3xl font-bold text-slate-950">
              {formatCurrency(
                order.final_amount ??
                  order.finalAmount
              )}
            </p>

          </div>


          {/* DETAILS */}

          <div className="grid gap-4 sm:grid-cols-2">

            <DetailItem
              icon={Hash}
              label="Order ID"
              value={`#${order.id}`}
            />


            <DetailItem
              icon={User}
              label="Merchant"
              value={`Merchant #${order.merchant_id}`}
            />


            <DetailItem
              icon={Package}
              label="Product"
              value={`Product #${order.product_id}`}
            />


            <DetailItem
              icon={ShoppingCart}
              label="Quantity"
              value={
                order.quantity ??
                0
              }
            />


            <DetailItem
              icon={IndianRupee}
              label="Original Amount"
              value={formatCurrency(
                order.original_amount ??
                  order.originalAmount
              )}
            />


            <DetailItem
              icon={Percent}
              label="Discount"
              value={`${Number(
                order.discount_percent ??
                  order.discountPercent ??
                  0
              ).toFixed(2)}%`}
            />


            <DetailItem
              icon={IndianRupee}
              label="Discount Amount"
              value={formatCurrency(
                order.discount_amount ??
                  order.discountAmount
              )}
            />


            <DetailItem
              icon={IndianRupee}
              label="Final Amount"
              value={formatCurrency(
                order.final_amount ??
                  order.finalAmount
              )}
              highlight
            />

          </div>


          {/* EXTRA INFORMATION */}

          {(order.risk_reason ||
            order.riskReason ||
            order.ai_reason ||
            order.aiReason) && (

            <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5">

              <div className="flex items-center gap-2">

                <ShieldAlert
                  size={18}
                  className="text-blue-600"
                />

                <h3 className="font-semibold text-slate-900">
                  Risk Decision
                </h3>

              </div>


              <p className="mt-3 text-sm leading-6 text-slate-600">
                {order.risk_reason ||
                  order.riskReason ||
                  order.ai_reason ||
                  order.aiReason}
              </p>

            </div>
          )}

        </div>


        {/* FOOTER */}

        <div className="flex justify-end border-t border-slate-200 bg-slate-50 px-6 py-4">

          <button
            onClick={onClose}
            className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Close
          </button>

        </div>

      </div>

    </div>
  );
}


// =============================================================
// DETAIL ITEM
// =============================================================

function DetailItem({
  icon: Icon,
  label,
  value,
  highlight = false,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">

      <div className="flex items-center gap-3">

        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
          <Icon size={17} />
        </div>


        <div className="min-w-0">

          <p className="text-xs font-medium text-slate-400">
            {label}
          </p>

          <p
            className={`mt-1 truncate text-sm font-bold ${
              highlight
                ? "text-blue-600"
                : "text-slate-900"
            }`}
          >
            {value}
          </p>

        </div>

      </div>

    </div>
  );
}


// =============================================================
// EXPORT
// =============================================================

export default Orders;