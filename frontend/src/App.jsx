import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";

import { useEffect, useState } from "react";
import axios from "axios";

import {
  LayoutDashboard,
  ShoppingCart,
  ShieldCheck,
  Package,
  Activity,
  Settings as SettingsIcon,
  FileText,
  Bot,
  LogOut,
  User,
  LockKeyhole,
  AlertCircle,
} from "lucide-react";
import { Megaphone } from "lucide-react";

// =========================================================
// PAGES
// =========================================================

import Dashboard from "./pages/Dashboard";
import Orders from "./pages/Orders";
import ManualReviews from "./pages/ManualReviews";
import RiskAnalytics from "./pages/RiskAnalytics";
import Products from "./pages/Products";
import Settings from "./pages/Settings";
import AuditLogs from "./pages/AuditLogs";
import Agent from "./pages/Agent";
import Campaigns from "./pages/Campaigns";

// =========================================================
// COMPONENTS
// =========================================================

import RazorpayPayment from "./components/RazorpayPayment";

// =========================================================
// API
// =========================================================

import api from "./services/api";

// =========================================================
// API CONFIGURATION
// =========================================================

export const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

// =========================================================
// STORAGE KEYS
// =========================================================

const TOKEN_KEY = "paypilot_access_token";
const MERCHANT_ID_KEY = "paypilot_merchant_id";
const ROLE_KEY = "paypilot_role";
const EXPIRES_AT_KEY = "paypilot_token_expires_at";

// =========================================================
// AUTH STORAGE HELPERS
// =========================================================

const getStoredToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

const getStoredMerchantId = () => {
  const value = localStorage.getItem(MERCHANT_ID_KEY);

  if (!value) {
    return null;
  }

  const numericValue = Number(value);

  return Number.isInteger(numericValue)
    ? numericValue
    : null;
};

const getStoredRole = () => {
  return (
    localStorage.getItem(ROLE_KEY) || ""
  ).toLowerCase();
};

const getStoredExpiresAt = () => {
  const value = localStorage.getItem(EXPIRES_AT_KEY);

  if (!value) {
    return null;
  }

  const numericValue = Number(value);

  return Number.isFinite(numericValue)
    ? numericValue
    : null;
};

// =========================================================
// SAVE AUTH
// =========================================================

const saveAuth = ({
  access_token,
  merchant_id,
  role,
  expires_in,
}) => {
  if (!access_token) {
    throw new Error(
      "Login response did not contain an access token."
    );
  }

  localStorage.setItem(
    TOKEN_KEY,
    access_token
  );

  if (
    merchant_id !== undefined &&
    merchant_id !== null
  ) {
    localStorage.setItem(
      MERCHANT_ID_KEY,
      String(merchant_id)
    );
  }

  if (role) {
    localStorage.setItem(
      ROLE_KEY,
      String(role).toLowerCase()
    );
  }

  if (
    expires_in !== undefined &&
    expires_in !== null
  ) {
    const expiresAt =
      Date.now() + Number(expires_in) * 1000;

    localStorage.setItem(
      EXPIRES_AT_KEY,
      String(expiresAt)
    );
  }
};

// =========================================================
// CLEAR AUTH
// =========================================================

export const clearAuth = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(MERCHANT_ID_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
};

// =========================================================
// AUTH VALIDITY
// =========================================================

const isTokenExpired = () => {
  const expiresAt = getStoredExpiresAt();

  if (!expiresAt) {
    return false;
  }

  return Date.now() >= expiresAt;
};

// =========================================================
// API REQUEST AUTHENTICATION
// =========================================================
//
// Merchant/dashboard API calls use JWT.
//
// Buyer pages themselves do NOT require authentication.
//
// The interceptor only attaches a token when one exists.
// =========================================================

let authInterceptorInitialized = false;

const initializeApiAuthentication = () => {
  if (authInterceptorInitialized) {
    return;
  }

  authInterceptorInitialized = true;

  api.interceptors.request.use(
    (config) => {
      const token = getStoredToken();

      if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization =
          `Bearer ${token}`;
      }

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
};

initializeApiAuthentication();

// =========================================================
// API RESPONSE AUTHENTICATION
// =========================================================

let responseInterceptorInitialized = false;

const initializeApiResponseAuthentication = () => {
  if (responseInterceptorInitialized) {
    return;
  }

  responseInterceptorInitialized = true;

  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error?.response?.status === 401) {
        clearAuth();

        window.dispatchEvent(
          new Event("paypilot:unauthorized")
        );
      }

      return Promise.reject(error);
    }
  );
};

initializeApiResponseAuthentication();

// =========================================================
// SSE CONFIGURATION
// =========================================================

const EVENT_URL =
  `${API_URL}/events/orders`;

// =========================================================
// AUTH HOOK
// =========================================================

function useAuth() {
  const [auth, setAuth] = useState(() => {
    const token = getStoredToken();
    const merchantId = getStoredMerchantId();
    const role = getStoredRole();

    return {
      token,
      merchantId,
      role,
      isAuthenticated:
        Boolean(token) && !isTokenExpired(),
    };
  });

  useEffect(() => {
    const handleUnauthorized = () => {
      setAuth({
        token: null,
        merchantId: null,
        role: "",
        isAuthenticated: false,
      });
    };

    const handleAuthenticated = () => {
      const token = getStoredToken();

      setAuth({
        token,
        merchantId: getStoredMerchantId(),
        role: getStoredRole(),
        isAuthenticated:
          Boolean(token) && !isTokenExpired(),
      });
    };

    window.addEventListener(
      "paypilot:unauthorized",
      handleUnauthorized
    );

    window.addEventListener(
      "paypilot:authenticated",
      handleAuthenticated
    );

    return () => {
      window.removeEventListener(
        "paypilot:unauthorized",
        handleUnauthorized
      );

      window.removeEventListener(
        "paypilot:authenticated",
        handleAuthenticated
      );
    };
  }, []);

  const login = (loginResponse) => {
    saveAuth(loginResponse);

    const newAuth = {
      token: loginResponse.access_token,
      merchantId: loginResponse.merchant_id,
      role: String(
        loginResponse.role || ""
      ).toLowerCase(),
      isAuthenticated: true,
    };

    setAuth(newAuth);

    return newAuth;
  };

  const logout = () => {
    clearAuth();

    setAuth({
      token: null,
      merchantId: null,
      role: "",
      isAuthenticated: false,
    });
  };

  return {
    ...auth,
    login,
    logout,
  };
}

// =========================================================
// LOGIN PAGE
// =========================================================

function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] =
    useState(false);

  const handleLogin = async (event) => {
    event.preventDefault();

    setError("");

    const normalizedEmail = email.trim();

    if (!normalizedEmail) {
      setError("Email is required.");
      return;
    }

    if (!password) {
      setError("Password is required.");
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/auth/login`,
        {
          email: normalizedEmail,
          password,
        },
        {
          headers: {
            "Content-Type":
              "application/json",
          },
          timeout: 30000,
        }
      );

      const data = response.data;

      if (!data?.access_token) {
        throw new Error(
          "Login succeeded but no access token was returned."
        );
      }

      saveAuth(data);

      window.dispatchEvent(
        new CustomEvent(
          "paypilot:authenticated",
          {
            detail: data,
          }
        )
      );

      navigate("/", {
        replace: true,
      });
    } catch (loginError) {
      console.error(
        "Login failed:",
        loginError
      );

      const detail =
        loginError?.response?.data?.detail;

      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(
          detail
            .map(
              (item) =>
                item?.msg ||
                "Validation error"
            )
            .join(", ")
        );
      } else if (
        loginError?.response?.status === 401
      ) {
        setError(
          "Invalid email or password."
        );
      } else if (!loginError?.response) {
        setError(
          "Unable to connect to the PayPilot backend."
        );
      } else {
        setError(
          "Login failed. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="
        flex
        min-h-screen
        items-center
        justify-center
        bg-[#020817]
        px-4
      "
    >
      <div
        className="
          w-full
          max-w-md
          rounded-2xl
          border
          border-slate-800
          bg-slate-900
          p-8
          shadow-2xl
        "
      >
        <div className="mb-8 text-center">
          <div
            className="
              mx-auto
              mb-4
              flex
              h-14
              w-14
              items-center
              justify-center
              rounded-2xl
              bg-blue-600
              text-white
              shadow-lg
              shadow-blue-600/30
            "
          >
            <ShieldCheck size={30} />
          </div>

          <h1 className="text-2xl font-bold text-white">
            PayPilot
          </h1>

          <p className="mt-1 text-sm text-slate-400">
            AI Risk Engine
          </p>
        </div>

        <div className="mb-6">
          <h2 className="text-xl font-bold text-white">
            Merchant Sign in
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Access your PayPilot merchant account.
          </p>
        </div>

        {error && (
          <div
            className="
              mb-5
              flex
              gap-3
              rounded-xl
              border
              border-red-500/30
              bg-red-500/10
              p-4
              text-sm
              text-red-300
            "
          >
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <span>{error}</span>
          </div>
        )}

        <form
          onSubmit={handleLogin}
          className="space-y-5"
        >
          <div>
            <label
              className="
                mb-2
                block
                text-sm
                font-semibold
                text-slate-300
              "
            >
              Email
            </label>

            <div className="relative">
              <User
                size={18}
                className="
                  absolute
                  left-3
                  top-1/2
                  -translate-y-1/2
                  text-slate-500
                "
              />

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="you@example.com"
                autoComplete="email"
                disabled={loading}
                className="
                  w-full
                  rounded-xl
                  border
                  border-slate-700
                  bg-slate-950
                  py-3
                  pl-10
                  pr-4
                  text-white
                  outline-none
                  transition
                  placeholder:text-slate-600
                  focus:border-blue-500
                  focus:ring-2
                  focus:ring-blue-500/20
                "
              />
            </div>
          </div>

          <div>
            <label
              className="
                mb-2
                block
                text-sm
                font-semibold
                text-slate-300
              "
            >
              Password
            </label>

            <div className="relative">
              <LockKeyhole
                size={18}
                className="
                  absolute
                  left-3
                  top-1/2
                  -translate-y-1/2
                  text-slate-500
                "
              />

              <input
                type={
                  showPassword
                    ? "text"
                    : "password"
                }
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                placeholder="Enter your password"
                autoComplete="current-password"
                disabled={loading}
                className="
                  w-full
                  rounded-xl
                  border
                  border-slate-700
                  bg-slate-950
                  py-3
                  pl-10
                  pr-20
                  text-white
                  outline-none
                  transition
                  placeholder:text-slate-600
                  focus:border-blue-500
                  focus:ring-2
                  focus:ring-blue-500/20
                "
              />

              <button
                type="button"
                onClick={() =>
                  setShowPassword(
                    (value) => !value
                  )
                }
                className="
                  absolute
                  right-3
                  top-1/2
                  -translate-y-1/2
                  text-xs
                  font-semibold
                  text-blue-400
                  hover:text-blue-300
                "
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="
              flex
              w-full
              items-center
              justify-center
              rounded-xl
              bg-blue-600
              px-4
              py-3
              font-bold
              text-white
              shadow-lg
              shadow-blue-600/20
              transition
              hover:bg-blue-500
              disabled:cursor-not-allowed
              disabled:opacity-60
            "
          >
            {loading
              ? "Signing in..."
              : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

// =========================================================
// PROTECTED MERCHANT ROUTE
// =========================================================

function ProtectedRoute({ children }) {
  const token = getStoredToken();

  if (!token) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  if (isTokenExpired()) {
    clearAuth();

    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}

// =========================================================
// ROLE PROTECTED ROUTE
// =========================================================
//
// Both ADMIN and MERCHANT can access every merchant page.
//
// Buyer/public users never enter these routes because all
// merchant routes are wrapped with ProtectedRoute.
//
// This keeps role handling simple and matches the requested
// authorization model.
// =========================================================

function RoleProtectedRoute({
  children,
  allowedRoles = ["admin", "merchant"],
}) {
  const role = getStoredRole();

  if (!allowedRoles.includes(role)) {
    return <UnauthorizedPage />;
  }

  return children;
}

// =========================================================
// UNAUTHORIZED PAGE
// =========================================================

function UnauthorizedPage() {
  const navigate = useNavigate();

  return (
    <div
      className="
        flex
        min-h-screen
        items-center
        justify-center
        bg-slate-50
        p-8
      "
    >
      <div
        className="
          max-w-md
          rounded-2xl
          border
          border-slate-200
          bg-white
          p-8
          text-center
          shadow-lg
        "
      >
        <div
          className="
            mx-auto
            mb-4
            flex
            h-14
            w-14
            items-center
            justify-center
            rounded-full
            bg-red-100
            text-red-600
          "
        >
          <ShieldCheck size={28} />
        </div>

        <h2 className="text-xl font-bold text-slate-900">
          Access Denied
        </h2>

        <p className="mt-2 text-sm text-slate-500">
          Your account does not have permission
          to access this page.
        </p>

        <button
          onClick={() => navigate("/")}
          className="
            mt-6
            rounded-xl
            bg-blue-600
            px-5
            py-3
            font-semibold
            text-white
            hover:bg-blue-500
          "
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}

// =========================================================
// GLOBAL REAL-TIME EVENTS
// =========================================================
//
// SSE is only required for merchant/admin monitoring.
// Buyer/public mode does not create an SSE connection.
// =========================================================

function useOrderEvents(isAuthenticated) {
  useEffect(() => {
    if (!isAuthenticated) {
      console.log(
        "SSE skipped: buyer/public mode."
      );

      return undefined;
    }

    const token = getStoredToken();

    if (!token) {
      return undefined;
    }

    console.log(
      "Connecting to PayPilot authenticated SSE..."
    );

    const authenticatedEventUrl =
      `${EVENT_URL}?token=${encodeURIComponent(
        token
      )}`;

    const eventSource =
      new EventSource(
        authenticatedEventUrl
      );

    eventSource.addEventListener(
      "connected",
      (event) => {
        try {
          const data = JSON.parse(
            event.data
          );

          window.dispatchEvent(
            new CustomEvent(
              "paypilot:connected",
              { detail: data }
            )
          );
        } catch (error) {
          console.error(
            "Error parsing connected event:",
            error
          );
        }
      }
    );

    eventSource.addEventListener(
      "order_created",
      (event) => {
        try {
          const data = JSON.parse(
            event.data
          );

          window.dispatchEvent(
            new CustomEvent(
              "paypilot:order_created",
              { detail: data }
            )
          );
        } catch (error) {
          console.error(
            "Error parsing order_created:",
            error
          );
        }
      }
    );

    eventSource.addEventListener(
      "order_processed",
      (event) => {
        try {
          const data = JSON.parse(
            event.data
          );

          window.dispatchEvent(
            new CustomEvent(
              "paypilot:order_processed",
              { detail: data }
            )
          );
        } catch (error) {
          console.error(
            "Error parsing order_processed:",
            error
          );
        }
      }
    );

    eventSource.addEventListener(
      "manual_review_completed",
      (event) => {
        try {
          const data = JSON.parse(
            event.data
          );

          window.dispatchEvent(
            new CustomEvent(
              "paypilot:manual_review_completed",
              { detail: data }
            )
          );
        } catch (error) {
          console.error(
            "Error parsing manual_review_completed:",
            error
          );
        }
      }
    );

    eventSource.onerror = (error) => {
      console.error(
        "PayPilot SSE connection error:",
        error
      );
    };

    return () => {
      eventSource.close();
    };
  }, [isAuthenticated]);
}

// =========================================================
// MERCHANT NAVIGATION
// =========================================================
//
// IMPORTANT:
// Both ADMIN and MERCHANT see all merchant pages.
//
// Buyer never renders this navigation.
// =========================================================

function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();

  const [auth, setAuth] = useState(() => ({
    merchantId: getStoredMerchantId(),
    role: getStoredRole(),
  }));

  const isActive = (path) => {
    return location.pathname === path;
  };

  useEffect(() => {
    const updateAuth = () => {
      setAuth({
        merchantId: getStoredMerchantId(),
        role: getStoredRole(),
      });
    };

    window.addEventListener(
      "paypilot:authenticated",
      updateAuth
    );

    window.addEventListener(
      "paypilot:unauthorized",
      updateAuth
    );

    return () => {
      window.removeEventListener(
        "paypilot:authenticated",
        updateAuth
      );

      window.removeEventListener(
        "paypilot:unauthorized",
        updateAuth
      );
    };
  }, []);

  const handleLogout = () => {
    clearAuth();

    window.dispatchEvent(
      new Event("paypilot:unauthorized")
    );

    navigate("/login", {
      replace: true,
    });
  };

  const role = auth.role || "merchant";

  const isAdmin = role === "admin";

  const displayName = isAdmin
    ? "Admin"
    : "Merchant";

  const displayRole = isAdmin
    ? "Risk Manager"
    : "Merchant";

  return (
    <aside
      className="
        fixed
        left-0
        top-0
        z-40
        flex
        h-screen
        w-[270px]
        flex-col
        border-r
        border-slate-800
        bg-[#020817]
        text-white
      "
    >
      <div
        className="
          flex
          h-[138px]
          shrink-0
          items-center
          border-b
          border-slate-800
          px-6
        "
      >
        <div className="flex items-center gap-3">
          <div
            className="
              flex
              h-11
              w-11
              items-center
              justify-center
              rounded-xl
              bg-blue-600
              shadow-lg
              shadow-blue-600/20
            "
          >
            <ShieldCheck size={24} />
          </div>

          <div>
            <h1 className="text-lg font-bold tracking-tight">
              PayPilot
            </h1>

            <p className="text-xs text-slate-400">
              AI Risk Engine
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-7">
        <p
          className="
            mb-3
            px-3
            text-[11px]
            font-bold
            uppercase
            tracking-widest
            text-slate-500
          "
        >
          Overview
        </p>

        <nav className="space-y-1">
          <NavItem
            to="/"
            icon={LayoutDashboard}
            label="Dashboard"
            active={isActive("/")}
          />

          <NavItem
            to="/orders"
            icon={ShoppingCart}
            label="Orders"
            active={isActive("/orders")}
          />

          <NavItem
            to="/manual-reviews"
            icon={ShieldCheck}
            label="Manual Reviews"
            active={isActive(
              "/manual-reviews"
            )}
          />

          <NavItem
            to="/products"
            icon={Package}
            label="Products"
            active={isActive("/products")}
          />

          <NavItem
            to="/risk-analytics"
            icon={Activity}
            label="Risk Analytics"
            active={isActive(
              "/risk-analytics"
            )}
          />

          <NavItem
            to="/audit-logs"
            icon={FileText}
            label="Audit Logs"
            active={isActive(
              "/audit-logs"
            )}
          />

          {/* <NavItem
            to="/merchant-agent"
            icon={Bot}
            label="AI Commerce Agent"
            active={isActive(
              "/merchant-agent"
            )}
          /> */}

          <NavItem
  to="/campaigns"
  icon={Megaphone}
  label="Campaigns"
  active={isActive("/campaigns")}
/>

        </nav>

        <p
          className="
            mb-3
            mt-9
            px-3
            text-[11px]
            font-bold
            uppercase
            tracking-widest
            text-slate-500
          "
        >
          System
        </p>

        <NavItem
          to="/settings"
          icon={SettingsIcon}
          label="Settings"
          active={isActive("/settings")}
        />
      </div>

      <div className="shrink-0 border-t border-slate-800 p-4">
        <div
          className="
            rounded-xl
            bg-slate-900/80
            p-3
          "
        >
          <div className="flex items-center gap-3">
            <div
              className="
                flex
                h-10
                w-10
                shrink-0
                items-center
                justify-center
                rounded-full
                bg-blue-600
                font-bold
                text-white
              "
            >
              {isAdmin ? "A" : "M"}
            </div>

            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-white">
                {displayName}
              </p>

              <p className="text-xs text-slate-500">
                {displayRole}
              </p>

              {auth.merchantId && (
                <p className="text-[10px] text-slate-600">
                  Merchant #{auth.merchantId}
                </p>
              )}
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="
              mt-3
              flex
              w-full
              items-center
              justify-center
              gap-2
              rounded-lg
              border
              border-slate-700
              px-3
              py-2
              text-xs
              font-semibold
              text-slate-400
              transition
              hover:border-red-500/40
              hover:bg-red-500/10
              hover:text-red-400
            "
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}

// =========================================================
// NAV ITEM
// =========================================================

function NavItem({
  to,
  icon: Icon,
  label,
  active,
}) {
  return (
    <Link
      to={to}
      className={`
        flex
        items-center
        gap-3
        rounded-xl
        px-3
        py-3
        text-sm
        font-semibold
        transition-all
        duration-200
        ${
          active
            ? `
              bg-blue-600
              text-white
              shadow-lg
              shadow-blue-600/20
            `
            : `
              text-slate-400
              hover:bg-slate-900
              hover:text-white
            `
        }
      `}
    >
      <Icon size={19} />
      <span>{label}</span>
    </Link>
  );
}

// =========================================================
// PAYMENT PAGE
// =========================================================
//
// Frontend route is public so a buyer does not need a
// merchant login just to reach the checkout page.
//
// IMPORTANT:
// The backend payment endpoint must still enforce a secure
// buyer checkout/session mechanism. Do not remove backend
// authorization blindly.
// =========================================================

function PaymentPage() {
  const { paymentId } = useParams();

  const numericPaymentId = Number(paymentId);

  if (
    !paymentId ||
    Number.isNaN(numericPaymentId)
  ) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl border bg-white p-8 shadow">
          <h2 className="text-xl font-bold text-red-600">
            Invalid Payment ID
          </h2>

          <p className="mt-2 text-slate-500">
            Payment ID must be a valid number.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="
        flex
        min-h-screen
        items-center
        justify-center
        bg-slate-50
        p-8
      "
    >
      <RazorpayPayment
        paymentId={numericPaymentId}
      />
    </div>
  );
}

// =========================================================
// MERCHANT LAYOUT
// =========================================================
//
// Every route inside this layout is merchant/admin only.
//
// Both roles are allowed:
//   admin
//   merchant
//
// Buyer never enters this layout.
// =========================================================

function MerchantLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navigation />

      <main className="min-h-screen pl-[270px]">
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <Dashboard />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/orders"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <Orders />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/manual-reviews"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <ManualReviews />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/products"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <Products />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/risk-analytics"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <RiskAnalytics />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/audit-logs"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <AuditLogs />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="/merchant-agent"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <Agent />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />
     

     <Route
  path="/campaigns"
  element={
    <ProtectedRoute>
      <RoleProtectedRoute>
        <Campaigns />
      </RoleProtectedRoute>
    </ProtectedRoute>
  }
/>

          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <RoleProtectedRoute>
                  <Settings />
                </RoleProtectedRoute>
              </ProtectedRoute>
            }
          />

          <Route
            path="*"
            element={
              <Navigate
                to="/"
                replace
              />
            }
          />
        </Routes>
      </main>
    </div>
  );
}

// =========================================================
// PUBLIC BUYER AGENT
// =========================================================
//
// NO AUTHENTICATION.
//
// / and /agent are buyer-facing when there is no merchant
// session. There is no merchant sidebar.
// =========================================================

function BuyerAgentPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Agent />
    </div>
  );
}

// =========================================================
// PUBLIC BUYER PAYMENT
// =========================================================

function BuyerPaymentPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <PaymentPage />
    </div>
  );
}

// =========================================================
// ROOT ROUTER
// =========================================================
//
// Root behavior:
//
// 1. Merchant/admin logged in:
//       /  -> Merchant dashboard
//
// 2. Buyer/not logged in:
//       /  -> Buyer AI Commerce Agent
//
// This avoids sending an unauthenticated buyer to /login.
// =========================================================

function RootRoute() {
  const token = getStoredToken();

  const authenticated =
    Boolean(token) && !isTokenExpired();

  if (authenticated) {
    return (
      <MerchantLayout />
    );
  }

  return (
    <BuyerAgentPage />
  );
}

// =========================================================
// APP
// =========================================================

function App() {
  const { isAuthenticated } = useAuth();

  // Only authenticated merchant/admin sessions establish SSE.
  useOrderEvents(isAuthenticated);

  return (
    <BrowserRouter>
      <Routes>
        {/* =================================================
            MERCHANT LOGIN
        ================================================= */}

        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate
                to="/"
                replace
              />
            ) : (
              <Login />
            )
          }
        />

        {/* =================================================
            PUBLIC BUYER ROOT
        =================================================

        Buyer without authentication:
            localhost:5173/
              -> AI Commerce Agent

        Authenticated merchant/admin:
            localhost:5173/
              -> Merchant Dashboard
        ================================================= */}

        <Route
          path="/"
          element={<RootRoute />}
        />

        {/* =================================================
            PUBLIC BUYER AI AGENT
        ================================================= */}

        <Route
          path="/agent"
          element={<BuyerAgentPage />}
        />

        {/* =================================================
            PUBLIC BUYER PAYMENT PAGE
        ================================================= */}

        <Route
          path="/payment/:paymentId"
          element={<BuyerPaymentPage />}
        />

        {/* =================================================
            ALL OTHER PATHS -> MERCHANT APPLICATION
        ================================================= */}

        <Route
          path="/*"
          element={<MerchantLayout />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
