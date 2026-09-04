import axios from "axios";

// =========================================================
// CONFIG
// =========================================================

const RAW_API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

export const API_BASE_URL =
  String(RAW_API_BASE_URL).trim().replace(/\/+$/, "");

const DEFAULT_TIMEOUT = 30000;
const AGENT_TIMEOUT = 60000;
const CAMPAIGN_TIMEOUT = 60000;

// =========================================================
// AUTH STORAGE
// =========================================================

export const AUTH_STORAGE_KEYS = {
  TOKEN: "paypilot_access_token",
  ROLE: "paypilot_role",
  MERCHANT_ID: "paypilot_merchant_id",
  EXPIRES_AT: "paypilot_expires_at",
};

// =========================================================
// AUTH HELPERS
// =========================================================

export const getAccessToken = () => {
  return localStorage.getItem(
    AUTH_STORAGE_KEYS.TOKEN
  );
};

export const getStoredRole = () => {
  return (
    localStorage.getItem(
      AUTH_STORAGE_KEYS.ROLE
    ) || ""
  ).toLowerCase();
};

export const getStoredMerchantId = () => {
  const value = localStorage.getItem(
    AUTH_STORAGE_KEYS.MERCHANT_ID
  );

  if (!value) {
    return null;
  }

  const id = Number(value);

  return Number.isInteger(id) && id > 0
    ? id
    : null;
};

export const getStoredExpiresAt = () => {
  const value = localStorage.getItem(
    AUTH_STORAGE_KEYS.EXPIRES_AT
  );

  if (!value) {
    return null;
  }

  const expiry = Number(value);

  return Number.isFinite(expiry)
    ? expiry
    : null;
};

export const isAuthenticated = () => {
  const token = getAccessToken();

  if (!token) {
    return false;
  }

  const expiresAt = getStoredExpiresAt();

  if (
    expiresAt &&
    Date.now() >= expiresAt
  ) {
    clearAuth();
    return false;
  }

  return true;
};

export const isMerchantAuthenticated = () => {
  if (!isAuthenticated()) {
    return false;
  }

  const role = getStoredRole();

  return (
    role === "merchant" ||
    role === "admin" ||
    role === "administrator"
  );
};

export const getAuthHeaders = () => {
  const token = getAccessToken();

  if (!token) {
    throw new Error(
      "Merchant authentication is required. Please sign in before approving a manual review."
    );
  }

  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
};

// =========================================================
// SAVE AUTH
// =========================================================

export const saveAuth = ({
  access_token,
  expires_in,
  merchant_id,
  role,
}) => {
  if (!access_token) {
    throw new Error(
      "Authentication response did not contain an access token."
    );
  }

  localStorage.setItem(
    AUTH_STORAGE_KEYS.TOKEN,
    access_token
  );

  if (
    merchant_id !== null &&
    merchant_id !== undefined
  ) {
    localStorage.setItem(
      AUTH_STORAGE_KEYS.MERCHANT_ID,
      String(merchant_id)
    );
  }

  if (role) {
    localStorage.setItem(
      AUTH_STORAGE_KEYS.ROLE,
      String(role).toLowerCase()
    );
  }

  if (
    expires_in !== null &&
    expires_in !== undefined
  ) {
    const numericExpiry = Number(expires_in);

    if (
      Number.isFinite(numericExpiry) &&
      numericExpiry > 0
    ) {
      localStorage.setItem(
        AUTH_STORAGE_KEYS.EXPIRES_AT,
        String(
          Date.now() +
            numericExpiry * 1000
        )
      );
    }
  }
};

// =========================================================
// CLEAR AUTH
// =========================================================

export const clearAuth = () => {
  localStorage.removeItem(
    AUTH_STORAGE_KEYS.TOKEN
  );

  localStorage.removeItem(
    AUTH_STORAGE_KEYS.ROLE
  );

  localStorage.removeItem(
    AUTH_STORAGE_KEYS.MERCHANT_ID
  );

  localStorage.removeItem(
    AUTH_STORAGE_KEYS.EXPIRES_AT
  );
};

// =========================================================
// LOGIN
// =========================================================

export const login = async (
  email,
  password
) => {
  if (!email || !password) {
    throw new Error(
      "Email and password are required."
    );
  }

  const response = await axios.post(
    `${API_BASE_URL}/auth/login`,
    {
      email: String(email).trim(),
      password: String(password),
    },
    {
      headers: {
        "Content-Type":
          "application/json",
      },
      timeout: DEFAULT_TIMEOUT,
    }
  );

  saveAuth(response.data);

  return response.data;
};

// =========================================================
// LOGOUT
// =========================================================

export const logout = () => {
  clearAuth();

  window.dispatchEvent(
    new CustomEvent(
      "paypilot:logout"
    )
  );
};

// =========================================================
// AXIOS INSTANCES
// =========================================================

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type":
      "application/json",
  },
  timeout: DEFAULT_TIMEOUT,
});

const publicApi = axios.create({
  baseURL: API_BASE_URL,

  // IMPORTANT:
  // Do not set Content-Type globally for public GET requests.
  //
  // A JSON Content-Type on a cross-origin GET can trigger
  // a CORS preflight request.
  headers: {
    Accept: "application/json",
  },

  timeout: DEFAULT_TIMEOUT,
});

// =========================================================
// AUTH REQUEST INTERCEPTOR
// =========================================================

api.interceptors.request.use(
  (config) => {
    const token = getAccessToken();

    if (token) {
      config.headers =
        config.headers || {};

      config.headers.Authorization =
        `Bearer ${token}`;
    }

    return config;
  },
  (error) =>
    Promise.reject(error)
);

// =========================================================
// VALIDATION ERROR FORMATTER
// =========================================================

const formatValidationErrors = (
  detail
) => {
  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }

      if (
        item &&
        typeof item === "object"
      ) {
        const message =
          item.msg ||
          "Validation error";

        const location =
          Array.isArray(item.loc)
            ? item.loc
                .filter(
                  (part) =>
                    part !== "body" &&
                    part !== "query" &&
                    part !== "path"
                )
                .join(" → ")
            : "";

        return location
          ? `${location}: ${message}`
          : message;
      }

      return null;
    })
    .filter(Boolean);

  return messages.length
    ? messages.join("\n")
    : null;
};

// =========================================================
// RESPONSE INTERCEPTOR
// =========================================================

api.interceptors.response.use(
  (response) => response,

  (error) => {
    let userMessage =
      "Something went wrong while communicating with the server.";

    if (axios.isCancel(error)) {
      userMessage =
        "The request was canceled.";
    } else if (!error.response) {
      if (
        error.code === "ECONNABORTED" ||
        error.code === "ETIMEDOUT" ||
        error.message
          ?.toLowerCase()
          .includes("timeout")
      ) {
        userMessage =
          "The PayPilot server took too long to respond. Please check the backend logs before trying again.";
      } else {
        userMessage =
          "Unable to connect to the PayPilot backend.";
      }
    } else {
      const status =
        error.response.status;

      const data =
        error.response.data;

      if (status === 401) {
        userMessage =
          "Authentication is required.";

        clearAuth();

        window.dispatchEvent(
          new CustomEvent(
            "paypilot:auth_expired"
          )
        );
      } else if (status === 403) {
        userMessage =
          typeof data?.detail ===
          "string"
            ? data.detail
            : "You are not authorized to perform this action.";
      } else if (status === 422) {
        userMessage =
          formatValidationErrors(
            data?.detail
          ) ||
          (typeof data?.detail ===
          "string"
            ? data.detail
            : "The request data is invalid.");
      } else if (
        typeof data?.detail ===
        "string"
      ) {
        userMessage =
          data.detail;
      } else if (
        typeof data?.message ===
        "string"
      ) {
        userMessage =
          data.message;
      } else if (
        typeof data === "string"
      ) {
        userMessage = data;
      } else if (status === 400) {
        userMessage =
          "The request could not be processed.";
      } else if (status === 404) {
        userMessage =
          "The requested resource was not found.";
      } else if (status === 409) {
        userMessage =
          "This operation conflicts with the current state.";
      } else if (status >= 500) {
        userMessage =
          "The PayPilot backend encountered an internal error.";
      }
    }

    error.userMessage =
      userMessage;

    return Promise.reject(error);
  }
);

// =========================================================
// ERROR MESSAGE
// =========================================================

export const getApiErrorMessage = (
  error
) => {
  if (!error) {
    return "Something went wrong.";
  }

  if (typeof error === "string") {
    return error;
  }

  if (
    typeof error.userMessage ===
    "string"
  ) {
    return error.userMessage;
  }

  const detail =
    error.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return (
      formatValidationErrors(
        detail
      ) ||
      "The request data is invalid."
    );
  }

  if (
    typeof error.response?.data
      ?.message === "string"
  ) {
    return error.response.data.message;
  }

  if (
    error.code === "ECONNABORTED" ||
    error.code === "ETIMEDOUT" ||
    error.message
      ?.toLowerCase()
      .includes("timeout")
  ) {
    return "The PayPilot server took too long to respond. Please check the backend before retrying.";
  }

  return (
    error.message ||
    "Something went wrong."
  );
};

// =========================================================
// ORDERS
// =========================================================

export const getOrders =
  async () => {
    const response =
      await api.get("/orders/");

    return response.data;
  };

export const getOrder =
  async (orderId) => {
    if (
      orderId === null ||
      orderId === undefined ||
      orderId === ""
    ) {
      throw new Error(
        "orderId is required."
      );
    }

    const response =
      await api.get(
        `/orders/${orderId}`
      );

    return response.data;
  };

// =========================================================
// MANUAL REVIEWS
// =========================================================

export const getManualReviews =
  async (params = {}) => {
    const response =
      await api.get(
        "/manual-reviews/",
        {
          params,
        }
      );

    return response.data;
  };

export const getManualReview =
  async (reviewId) => {
    const id = Number(reviewId);

    if (
      !Number.isInteger(id) ||
      id <= 0
    ) {
      throw new Error(
        "A valid reviewId is required."
      );
    }

    const response =
      await api.get(
        `/manual-reviews/${id}`
      );

    return response.data;
  };

// =========================================================
// PUBLIC MANUAL REVIEWS
// =========================================================

export const getPublicManualReviews =
  async (
    params = {},
    options = {}
  ) => {
    const response =
      await publicApi.get(
        "/manual-reviews/",
        {
          params,
          timeout:
            options.timeout ||
            10000,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const getPublicManualReview =
  async (
    reviewId,
    options = {}
  ) => {
    const id = Number(reviewId);

    if (
      !Number.isInteger(id) ||
      id <= 0
    ) {
      throw new Error(
        "A valid reviewId is required."
      );
    }

    const response =
      await publicApi.get(
        `/manual-reviews/${id}`,
        {
          timeout:
            options.timeout ||
            10000,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const findPublicManualReviewByOrder =
  async (
    orderId,
    options = {}
  ) => {
    const numericOrderId =
      Number(orderId);

    if (
      !Number.isInteger(
        numericOrderId
      ) ||
      numericOrderId <= 0
    ) {
      throw new Error(
        "A valid orderId is required."
      );
    }

    const response =
      await getPublicManualReviews(
        {},
        options
      );

    const reviews =
      Array.isArray(response)
        ? response
        : Array.isArray(
            response?.reviews
          )
        ? response.reviews
        : [];

    return (
      reviews.find(
        (review) =>
          Number(
            review?.order_id
          ) === numericOrderId
      ) || null
    );
  };

// =========================================================
// MANUAL REVIEW DECISION
// =========================================================

const normalizeManualReviewAction =
  (action) => {
    const value = String(
      action || ""
    )
      .trim()
      .toUpperCase();

    if (
      value === "APPROVE" ||
      value === "APPROVED"
    ) {
      return "APPROVE";
    }

    if (
      value === "REJECT" ||
      value === "REJECTED"
    ) {
      return "REJECT";
    }

    throw new Error(
      `Invalid manual review action: "${action}". Use APPROVE or REJECT.`
    );
  };

export const decideManualReview =
  async (
    reviewId,
    action,
    reviewedBy = "merchant",
    reviewComment = ""
  ) => {
    const id = Number(reviewId);

    if (
      !Number.isInteger(id) ||
      id <= 0
    ) {
      throw new Error(
        "A valid reviewId is required."
      );
    }

    const normalizedAction =
      normalizeManualReviewAction(
        action
      );

    const token = getAccessToken();

    if (!token) {
      throw new Error(
        "Merchant authentication is required to approve or reject a manual review. Please sign in as the merchant/admin and try again."
      );
    }

    const response =
      await api.post(
        `/manual-reviews/${id}/decision`,
        {
          action:
            normalizedAction,
          reviewed_by:
            String(
              reviewedBy ||
                "merchant"
            ).trim(),
          review_comment:
            String(
              reviewComment || ""
            ).trim(),
        }
      );

    return response.data;
  };

// =========================================================
// APPROVE / REJECT MANUAL REVIEW
// =========================================================

export const approveManualReview =
  async (
    reviewId,
    reviewedBy = "merchant",
    reviewComment = ""
  ) => {
    return decideManualReview(
      reviewId,
      "APPROVE",
      reviewedBy,
      reviewComment
    );
  };

export const rejectManualReview =
  async (
    reviewId,
    reviewedBy = "merchant",
    reviewComment = ""
  ) => {
    return decideManualReview(
      reviewId,
      "REJECT",
      reviewedBy,
      reviewComment
    );
  };

// =========================================================
// AGENT EXPECTED ALIASES
// =========================================================

export const approveOrderManualReview =
  async (
    reviewId,
    reviewedBy = "merchant",
    reviewComment = ""
  ) => {
    return approveManualReview(
      reviewId,
      reviewedBy,
      reviewComment
    );
  };

export const rejectOrderManualReview =
  async (
    reviewId,
    reviewedBy = "merchant",
    reviewComment = ""
  ) => {
    return rejectManualReview(
      reviewId,
      reviewedBy,
      reviewComment
    );
  };

// =========================================================
// PRODUCTS
// =========================================================

export const getProducts =
  async () => {
    const response =
      await api.get("/products/");

    return response.data;
  };

export const getProduct =
  async (productId) => {
    const id = Number(productId);

    if (
      !Number.isInteger(id) ||
      id <= 0
    ) {
      throw new Error(
        "A valid productId is required."
      );
    }

    const response =
      await api.get(
        `/products/${id}`
      );

    return response.data;
  };

export const createProduct =
  async (productData) => {
    const response =
      await api.post(
        "/products/",
        productData
      );

    return response.data;
  };

export const updateProduct =
  async (
    productId,
    productData
  ) => {
    const response =
      await api.put(
        `/products/${productId}`,
        productData
      );

    return response.data;
  };

export const updateProductActiveStatus =
  async (
    productId,
    isActive
  ) => {
    const response =
      await api.put(
        `/products/${productId}`,
        {
          is_active: isActive,
        }
      );

    return response.data;
  };

export const updateProductStock =
  async (
    productId,
    stockQuantity
  ) => {
    const response =
      await api.put(
        `/products/${productId}`,
        {
          stock_quantity:
            Number(stockQuantity),
        }
      );

    return response.data;
  };

export const deleteProduct =
  async (productId) => {
    const response =
      await api.delete(
        `/products/${productId}`
      );

    return response.data;
  };

// =========================================================
// PUBLIC CATALOG
// =========================================================

export const getPublicCatalog =
  async (options = {}) => {
    const timeout =
      Number(options?.timeout) > 0
        ? Number(options.timeout)
        : DEFAULT_TIMEOUT;

    const startedAt = Date.now();

    console.log(
      "PUBLIC CATALOG REQUEST:",
      {
        url: `${API_BASE_URL}/products/public-catalog`,
        timeout,
      }
    );

    try {
      const response =
        await publicApi.get(
          "/products/public-catalog",
          {
            timeout,
            ...(options?.signal
              ? { signal: options.signal }
              : {}),
          }
        );

      console.log(
        "PUBLIC CATALOG SUCCESS:",
        {
          elapsedMs: Date.now() - startedAt,
          totalProducts:
            response?.data?.total_products ??
            response?.data?.products?.length ??
            response?.data?.catalog?.length ??
            0,
        }
      );

      return response.data;
    } catch (error) {
      console.error(
        "PUBLIC CATALOG REQUEST FAILED:",
        {
          url: `${API_BASE_URL}/products/public-catalog`,
          elapsedMs: Date.now() - startedAt,
          code: error?.code,
          message: error?.message,
          responseStatus: error?.response?.status,
          responseData: error?.response?.data,
        }
      );

      throw error;
    }
  };

// =========================================================
// SETTINGS
// =========================================================

export const getSettings =
  async () => {
    const response =
      await api.get("/settings/");

    return response.data;
  };

export const updateSettings =
  async (settingsData) => {
    const response =
      await api.put(
        "/settings/",
        settingsData
      );

    return response.data;
  };

// =========================================================
// ANALYTICS
// =========================================================

const analyticsGet = async (
  endpoint,
  params = {}
) => {
  const response =
    await api.get(
      endpoint,
      { params }
    );

  return response.data;
};

export const getAnalyticsDashboard =
  (days = 30) =>
    analyticsGet(
      "/analytics/dashboard",
      { days: Number(days) }
    );

export const getAnalyticsOverview =
  () =>
    analyticsGet(
      "/analytics/overview"
    );

export const getOrderAnalytics =
  () =>
    analyticsGet(
      "/analytics/orders"
    );

export const getAnalyticsRisk =
  () =>
    analyticsGet(
      "/analytics/risk"
    );

export const getAnalyticsManualReviews =
  () =>
    analyticsGet(
      "/analytics/manual-reviews"
    );

export const getAnalyticsPayments =
  () =>
    analyticsGet(
      "/analytics/payments"
    );

export const getAnalyticsDiscounts =
  () =>
    analyticsGet(
      "/analytics/discounts"
    );

export const getAnalyticsInventory =
  () =>
    analyticsGet(
      "/analytics/inventory"
    );

export const getDailyAnalytics =
  (days = 30) =>
    analyticsGet(
      "/analytics/daily",
      { days: Number(days) }
    );

export const getAnalyticsOrderTrend =
  (days = 30) =>
    analyticsGet(
      "/analytics/order-trend",
      { days: Number(days) }
    );

export const getAnalyticsRevenueTrend =
  (days = 30) =>
    analyticsGet(
      "/analytics/revenue-trend",
      { days: Number(days) }
    );

export const getMerchantPerformance =
  () =>
    analyticsGet(
      "/analytics/merchants"
    );

export const getRecentActivity =
  (limit = 20) =>
    analyticsGet(
      "/analytics/recent-activity",
      { limit: Number(limit) }
    );

// =========================================================
// RISK ANALYTICS
// =========================================================

const riskParams = (
  merchantId,
  extra = {}
) => {
  const params = {
    ...extra,
  };

  if (
    merchantId !== null &&
    merchantId !== undefined
  ) {
    params.merchant_id =
      Number(merchantId);
  }

  return params;
};

export const getRiskAnalyticsSummary =
  async (merchantId = null) =>
    analyticsGet(
      "/risk-analytics/summary",
      riskParams(merchantId)
    );

export const getMerchantRiskAnalytics =
  async (merchantId) => {
    if (
      merchantId === null ||
      merchantId === undefined ||
      merchantId === ""
    ) {
      throw new Error(
        "merchantId is required."
      );
    }

    return analyticsGet(
      `/risk-analytics/merchant/${merchantId}`
    );
  };

export const getRiskDistribution =
  async (merchantId = null) =>
    analyticsGet(
      "/risk-analytics/risk-distribution",
      riskParams(merchantId)
    );

export const getStatusDistribution =
  async (merchantId = null) =>
    analyticsGet(
      "/risk-analytics/status-distribution",
      riskParams(merchantId)
    );

export const getRiskScoreDistribution =
  async (merchantId = null) =>
    analyticsGet(
      "/risk-analytics/risk-score-distribution",
      riskParams(merchantId)
    );

export const getRiskReasons =
  async (
    limit = 5,
    merchantId = null
  ) =>
    analyticsGet(
      "/risk-analytics/risk-reasons",
      riskParams(
        merchantId,
        {
          limit: Number(limit),
        }
      )
    );

export const getRecentRiskActivity =
  async (
    limit = 10,
    merchantId = null
  ) =>
    analyticsGet(
      "/risk-analytics/recent",
      riskParams(
        merchantId,
        {
          limit: Number(limit),
        }
      )
    );

export const getOrderTrend =
  async (merchantId = null) =>
    analyticsGet(
      "/risk-analytics/order-trend",
      riskParams(merchantId)
    );

export const getAllRiskAnalytics =
  async (merchantId = null) => {
    const [
      summary,
      riskDistribution,
      statusDistribution,
      riskScoreDistribution,
      riskReasons,
      recentActivity,
      orderTrend,
    ] = await Promise.all([
      getRiskAnalyticsSummary(
        merchantId
      ),
      getRiskDistribution(
        merchantId
      ),
      getStatusDistribution(
        merchantId
      ),
      getRiskScoreDistribution(
        merchantId
      ),
      getRiskReasons(
        5,
        merchantId
      ),
      getRecentRiskActivity(
        20,
        merchantId
      ),
      getOrderTrend(
        merchantId
      ),
    ]);

    return {
      summary,
      riskDistribution,
      statusDistribution,
      riskScoreDistribution,
      riskReasons,
      recentActivity,
      orderTrend,
    };
  };

// =========================================================
// PAYPILOT AGENT
// =========================================================

const normalizeAgentPayload = (
  payload,
  merchantId = null
) => {
  if (typeof payload === "string") {
    const message =
      payload.trim();

    if (!message) {
      throw new Error(
        "Agent message cannot be empty."
      );
    }

    const resolvedMerchantId =
      merchantId ??
      getStoredMerchantId();

    const numericMerchantId =
      Number(resolvedMerchantId);

    if (
      !Number.isInteger(
        numericMerchantId
      ) ||
      numericMerchantId <= 0
    ) {
      throw new Error(
        "A valid merchant_id is required for the agent."
      );
    }

    return {
      merchant_id:
        numericMerchantId,
      message,
    };
  }

  if (
    !payload ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    throw new Error(
      "Invalid agent request payload."
    );
  }

  const message =
    String(
      payload.message || ""
    ).trim();

  if (!message) {
    throw new Error(
      "Agent message cannot be empty."
    );
  }

  const resolvedMerchantId =
    payload.merchant_id ??
    payload.merchantId ??
    merchantId ??
    getStoredMerchantId();

  const numericMerchantId =
    Number(resolvedMerchantId);

  if (
    !Number.isInteger(
      numericMerchantId
    ) ||
    numericMerchantId <= 0
  ) {
    throw new Error(
      "A valid merchant_id is required for the agent."
    );
  }

  return {
    merchant_id:
      numericMerchantId,
    message,
  };
};

export const sendAgentChat =
  async (
    payload,
    merchantId = null,
    options = {}
  ) => {
    const requestBody =
      normalizeAgentPayload(
        payload,
        merchantId
      );

    try {
      const response =
        await api.post(
          "/agent/chat",
          requestBody,
          {
            timeout:
              AGENT_TIMEOUT,
            signal:
              options?.signal,
          }
        );

      return response.data;
    } catch (error) {
      console.error(
        "PAYPILOT AGENT REQUEST ERROR:",
        error
      );

      if (
        error?.code ===
          "ECONNABORTED" ||
        error?.code ===
          "ETIMEDOUT" ||
        error?.message
          ?.toLowerCase()
          .includes("timeout")
      ) {
        error.userMessage =
          "PayPilot did not respond within 60 seconds. The request was NOT automatically retried because it may already have created an order. Check Orders before trying again.";
      }

      throw error;
    }
  };

export const chatWithAgent =
  async (
    payload,
    merchantId = null,
    options = {}
  ) =>
    sendAgentChat(
      payload,
      merchantId,
      options
    );

export const askAgent =
  async (
    message,
    merchantId = null,
    options = {}
  ) => {
    const normalizedMessage =
      String(
        message || ""
      ).trim();

    if (!normalizedMessage) {
      throw new Error(
        "Agent message is required."
      );
    }

    const resolvedMerchantId =
      merchantId ??
      getStoredMerchantId();

    const numericMerchantId =
      Number(resolvedMerchantId);

    if (
      !Number.isInteger(
        numericMerchantId
      ) ||
      numericMerchantId <= 0
    ) {
      throw new Error(
        "A valid merchant_id is required for the agent."
      );
    }

    return sendAgentChat(
      {
        merchant_id:
          numericMerchantId,
        message:
          normalizedMessage,
      },
      numericMerchantId,
      options
    );
  };

// =========================================================
// GROWTH RECOMMENDATIONS
// =========================================================

export const getGrowthRecommendations =
  async (
    productId,
    merchantId = null,
    options = {}
  ) => {
    const numericProductId =
      Number(productId);

    if (
      !Number.isInteger(
        numericProductId
      ) ||
      numericProductId <= 0
    ) {
      throw new Error(
        "A valid productId is required for growth recommendations."
      );
    }

    const resolvedMerchantId =
      merchantId ??
      getStoredMerchantId();

    const numericMerchantId =
      Number(resolvedMerchantId);

    if (
      !Number.isInteger(
        numericMerchantId
      ) ||
      numericMerchantId <= 0
    ) {
      throw new Error(
        "A valid merchant_id is required for growth recommendations."
      );
    }

    const response =
      await publicApi.post(
        "/agent/recommendations",
        {
          merchant_id:
            numericMerchantId,
          product_id:
            numericProductId,
        },
        {
          timeout:
            AGENT_TIMEOUT,
          signal:
            options?.signal,
        }
      );

    return response.data;
  };

export const getRecommendations =
  (
    productId,
    merchantId = null,
    options = {}
  ) =>
    getGrowthRecommendations(
      productId,
      merchantId,
      options
    );

// =========================================================
// CAMPAIGNS
// =========================================================

const normalizeCampaignId = (
  proposalId,
  fieldName = "proposalId"
) => {
  const id = Number(proposalId);

  if (
    !Number.isInteger(id) ||
    id <= 0
  ) {
    throw new Error(
      `A valid ${fieldName} is required.`
    );
  }

  return id;
};

export const createCampaignProposal =
  async (
    campaignData,
    options = {}
  ) => {
    if (
      !campaignData ||
      typeof campaignData !== "object" ||
      Array.isArray(campaignData)
    ) {
      throw new Error(
        "Campaign proposal data is required."
      );
    }

    const merchantId =
      campaignData.merchant_id ??
      campaignData.merchantId ??
      getStoredMerchantId();

    const numericMerchantId =
      Number(merchantId);

    if (
      !Number.isInteger(
        numericMerchantId
      ) ||
      numericMerchantId <= 0
    ) {
      throw new Error(
        "A valid merchant_id is required for a campaign proposal."
      );
    }

    const response =
      await api.post(
        "/campaigns/proposals",
        {
          ...campaignData,
          merchant_id:
            numericMerchantId,
        },
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const getCampaignProposals =
  async (
    params = {},
    options = {}
  ) => {
    const requestParams = {
      ...params,
    };

    const merchantId =
      getStoredMerchantId();

    if (
      requestParams.merchant_id ===
        undefined &&
      merchantId !== null
    ) {
      requestParams.merchant_id =
        merchantId;
    }

    const response =
      await api.get(
        "/campaigns/proposals",
        {
          params:
            requestParams,
          timeout:
            options.timeout ||
            DEFAULT_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const getCampaignProposal =
  async (
    proposalId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        proposalId
      );

    const response =
      await api.get(
        `/campaigns/proposals/${id}`,
        {
          timeout:
            options.timeout ||
            DEFAULT_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const generateCampaignProposal =
  (
    campaignData,
    options = {}
  ) =>
    createCampaignProposal(
      campaignData,
      options
    );

export const normalizeCampaignProposalStatus =
  (status) => {
    let value = String(
      status || ""
    )
      .trim()
      .toUpperCase();

    if (value.includes(".")) {
      value =
        value.split(".").pop();
    }

    return value;
  };

export const isCampaignProposalDraft =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "DRAFT";

export const isCampaignProposalPolicyApproved =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "POLICY_APPROVED";

export const isCampaignProposalPolicyRejected =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "POLICY_REJECTED";

export const isCampaignProposalMerchantApproved =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "MERCHANT_APPROVED";

export const isCampaignProposalMerchantRejected =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "MERCHANT_REJECTED";

export const isCampaignProposalActive =
  (proposal) =>
    normalizeCampaignProposalStatus(
      proposal?.status
    ) === "ACTIVE";

export const isCampaignProposalApproved =
  (proposal) => {
    const status =
      normalizeCampaignProposalStatus(
        proposal?.status
      );

    return (
      status === "APPROVED" ||
      status === "POLICY_APPROVED" ||
      status === "MERCHANT_APPROVED"
    );
  };

export const isCampaignProposalRejected =
  (proposal) => {
    const status =
      normalizeCampaignProposalStatus(
        proposal?.status
      );

    return (
      status === "REJECTED" ||
      status === "POLICY_REJECTED" ||
      status === "MERCHANT_REJECTED"
    );
  };

// =========================================================
// CAMPAIGN PHASE 2
// =========================================================

export const validateCampaignProposal =
  async (
    proposalId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        proposalId
      );

    const response =
      await api.post(
        `/campaigns/proposals/${id}/validate`,
        null,
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

// =========================================================
// CAMPAIGN PHASE 3
// =========================================================

export const approveCampaignProposal =
  async (
    proposalId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        proposalId
      );

    const response =
      await api.post(
        `/campaigns/proposals/${id}/approve`,
        null,
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const rejectCampaignProposal =
  async (
    proposalId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        proposalId
      );

    const response =
      await api.post(
        `/campaigns/proposals/${id}/reject`,
        null,
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

// =========================================================
// CAMPAIGN PHASE 4
// =========================================================

export const activateCampaignProposal =
  async (
    proposalId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        proposalId
      );

    const response =
      await api.post(
        `/campaigns/proposals/${id}/activate`,
        null,
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const activateCampaign =
  (
    proposalId,
    options = {}
  ) =>
    activateCampaignProposal(
      proposalId,
      options
    );

export const activateProposal =
  (
    proposalId,
    options = {}
  ) =>
    activateCampaignProposal(
      proposalId,
      options
    );

// =========================================================
// CAMPAIGN GOVERNANCE HELPERS
// =========================================================

export const canActivateCampaign =
  (proposal) =>
    proposal?.governance
      ?.can_activate === true;

export const isCampaignActivationPending =
  (proposal) =>
    String(
      proposal?.governance
        ?.activation_status || ""
    )
      .trim()
      .toUpperCase() === "PENDING";

export const isCampaignActivationNotStarted =
  (proposal) =>
    String(
      proposal?.governance
        ?.activation_status || ""
    )
      .trim()
      .toUpperCase() ===
    "NOT_STARTED";

export const isCampaignActive =
  (proposal) => {
    const status =
      normalizeCampaignProposalStatus(
        proposal?.status
      );

    return (
      status === "ACTIVE" ||
      proposal?.governance
        ?.campaign_active === true
    );
  };

export const hasCampaignChangedPrice =
  (proposal) =>
    proposal?.governance
      ?.price_changed === true;

export const hasCampaignChangedInventory =
  (proposal) =>
    proposal?.governance
      ?.inventory_changed === true;

export const hasCampaignChangedOrders =
  (proposal) =>
    proposal?.governance
      ?.orders_changed === true;

export const hasCampaignChangedPayments =
  (proposal) =>
    proposal?.governance
      ?.payments_changed === true;

// =========================================================
// CAMPAIGN PHASE
// =========================================================

export const getCampaignPhase =
  (proposal) => {
    switch (
      normalizeCampaignProposalStatus(
        proposal?.status
      )
    ) {
      case "DRAFT":
        return 1;

      case "POLICY_APPROVED":
      case "POLICY_REJECTED":
        return 2;

      case "MERCHANT_APPROVED":
      case "MERCHANT_REJECTED":
        return 3;

      case "ACTIVE":
        return 4;

      default:
        return 0;
    }
  };

export const getCampaignDisplayStatus =
  (proposal) => {
    const status =
      normalizeCampaignProposalStatus(
        proposal?.status
      );

    const activationStatus =
      String(
        proposal?.governance
          ?.activation_status || ""
      )
        .trim()
        .toUpperCase();

    if (status === "ACTIVE") {
      return "ACTIVE";
    }

    if (
      status ===
        "MERCHANT_APPROVED" &&
      activationStatus ===
        "PENDING"
    ) {
      return "MERCHANT_APPROVED";
    }

    return status || "UNKNOWN";
  };

export const shouldValidateCampaign =
  (proposal) =>
    isCampaignProposalDraft(
      proposal
    ) ||
    isCampaignProposalPolicyRejected(
      proposal
    );

export const shouldApproveCampaign =
  (proposal) =>
    isCampaignProposalPolicyApproved(
      proposal
    ) &&
    proposal?.governance
      ?.validation_passed === true;

export const shouldRejectCampaign =
  (proposal) =>
    isCampaignProposalPolicyApproved(
      proposal
    ) &&
    proposal?.governance
      ?.validation_passed === true;

export const shouldActivateCampaign =
  (proposal) =>
    isCampaignProposalMerchantApproved(
      proposal
    ) &&
    proposal?.governance
      ?.merchant_approved === true &&
    proposal?.governance
      ?.validation_passed === true &&
    proposal?.governance
      ?.can_activate === true &&
    proposal?.governance
      ?.campaign_active !== true;

export const shouldDeleteCampaign =
  (proposal) =>
    isCampaignProposalDraft(
      proposal
    );

export const getCampaignGovernanceSummary =
  (proposal) => {
    const governance =
      proposal?.governance || {};

    return {
      policyApproved:
        governance.policy_validation_status ===
        "PASSED",

      marginApproved:
        governance.margin_validation_status ===
        "PASSED",

      validationPassed:
        governance.validation_passed === true,

      merchantApproved:
        governance.merchant_approved === true,

      merchantApprovalStatus:
        governance.merchant_approval_status ||
        "PENDING",

      canActivate:
        governance.can_activate === true,

      activationStatus:
        governance.activation_status ||
        "NOT_STARTED",

      campaignActive:
        governance.campaign_active === true,

      priceChanged:
        governance.price_changed === true,

      inventoryChanged:
        governance.inventory_changed === true,

      ordersChanged:
        governance.orders_changed === true,

      paymentsChanged:
        governance.payments_changed === true,

      paymentAllowed:
        governance.payment_allowed === true,
    };
  };

export const executeCampaignAction =
  async (
    proposalId,
    action,
    options = {}
  ) => {
    const value = String(
      action || ""
    )
      .trim()
      .toUpperCase();

    switch (value) {
      case "VALIDATE":
        return validateCampaignProposal(
          proposalId,
          options
        );

      case "APPROVE":
        return approveCampaignProposal(
          proposalId,
          options
        );

      case "REJECT":
        return rejectCampaignProposal(
          proposalId,
          options
        );

      case "ACTIVATE":
        return activateCampaignProposal(
          proposalId,
          options
        );

      default:
        throw new Error(
          `Invalid campaign action "${action}". Use VALIDATE, APPROVE, REJECT, or ACTIVATE.`
        );
    }
  };

export const deleteCampaign =
  async (
    campaignId,
    options = {}
  ) => {
    const id =
      normalizeCampaignId(
        campaignId,
        "campaignId"
      );

    const response =
      await api.delete(
        `/campaigns/${id}`,
        {
          timeout:
            options.timeout ||
            DEFAULT_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

// =========================================================
// LEGACY CAMPAIGN API
// =========================================================

export const createCampaignLegacy =
  async (
    campaignData,
    options = {}
  ) => {
    if (
      !campaignData ||
      typeof campaignData !==
        "object" ||
      Array.isArray(campaignData)
    ) {
      throw new Error(
        "Campaign data is required."
      );
    }

    const response =
      await api.post(
        "/campaigns/",
        campaignData,
        {
          timeout:
            options.timeout ||
            CAMPAIGN_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };

export const getCampaigns =
  async (
    params = {},
    options = {}
  ) => {
    const response =
      await api.get(
        "/campaigns/",
        {
          params,
          timeout:
            options.timeout ||
            DEFAULT_TIMEOUT,
          signal:
            options.signal,
        }
      );

    return response.data;
  };


// =========================================================
// PAYMENTS
// =========================================================

// ---------------------------------------------------------
// CREATE PAYMENT
// ---------------------------------------------------------
//
// Used by Agent.jsx after the payment gate has passed.
//
// IMPORTANT:
// This uses the authenticated `api` Axios instance.
// Therefore the request interceptor automatically sends:
//
// Authorization: Bearer <access_token>
//
// The idempotency key prevents duplicate payment creation
// when the same approved order retries checkout.
// ---------------------------------------------------------

export const createPayment = async (
  paymentData,
  options = {}
) => {
  if (
    !paymentData ||
    typeof paymentData !== "object" ||
    Array.isArray(paymentData)
  ) {
    throw new Error(
      "Payment data is required."
    );
  }

  const orderId =
    Number(paymentData.order_id);

  if (
    !Number.isInteger(orderId) ||
    orderId <= 0
  ) {
    throw new Error(
      "A valid order_id is required to create payment."
    );
  }

  const currency =
    String(
      paymentData.currency || "INR"
    )
      .trim()
      .toUpperCase();

  const headers = {};

  if (options.idempotencyKey) {
    headers["Idempotency-Key"] =
      String(
        options.idempotencyKey
      );
  }

  try {
    console.log(
      "========================================"
    );

    console.log(
      "PAYPILOT CREATE PAYMENT"
    );

    console.log({
      order_id: orderId,
      currency,
      idempotency_key:
        options.idempotencyKey ||
        null,
    });

    console.log(
      "========================================"
    );

    const response =
      await api.post(
        "/payments/",
        {
          order_id: orderId,
          currency,
        },
        {
          headers,

          timeout:
            options.timeout ||
            AGENT_TIMEOUT,

          signal:
            options.signal,
        }
      );

    console.log(
      "PAYPILOT PAYMENT CREATED:",
      response.data
    );

    return response.data;
  } catch (error) {
    console.error(
      "PAYPILOT CREATE PAYMENT ERROR:",
      error
    );

    console.error(
      "PAYPILOT CREATE PAYMENT BACKEND RESPONSE:",
      error?.response?.data
    );

    throw error;
  }
};


// ---------------------------------------------------------
// VERIFY PAYMENT
// ---------------------------------------------------------
//
// Called after Razorpay returns:
//
// razorpay_order_id
// razorpay_payment_id
// razorpay_signature
//
// Backend must verify the signature before an order can be
// marked paid.
// ---------------------------------------------------------

export const verifyPayment = async (
  paymentId,
  verificationData = {},
  options = {}
) => {
  if (
    paymentId === null ||
    paymentId === undefined ||
    paymentId === ""
  ) {
    throw new Error("paymentId is required.");
  }

  const numericPaymentId = Number(paymentId);

  if (
    !Number.isInteger(numericPaymentId) ||
    numericPaymentId <= 0
  ) {
    throw new Error("A valid paymentId is required.");
  }

  const razorpayOrderId = String(
    verificationData?.razorpay_order_id || ""
  ).trim();

  const razorpayPaymentId = String(
    verificationData?.razorpay_payment_id || ""
  ).trim();

  const razorpaySignature = String(
    verificationData?.razorpay_signature || ""
  ).trim();

  if (!razorpayOrderId) {
    throw new Error(
      "Razorpay order ID is missing."
    );
  }

  if (!razorpayPaymentId) {
    throw new Error(
      "Razorpay payment ID is missing."
    );
  }

  if (!razorpaySignature) {
    throw new Error(
      "Razorpay signature is missing."
    );
  }

  console.log(
    "========================================"
  );

  console.log(
    "PAYPILOT VERIFY PAYMENT REQUEST"
  );

  console.log({
    paymentId: numericPaymentId,
    razorpayOrderId,
    razorpayPaymentId,
    signatureReceived:
      Boolean(razorpaySignature),
  });

  console.log(
    "========================================"
  );

  try {
    const response = await api.post(
      `/payments/${numericPaymentId}/verify`,
      {
        razorpay_order_id:
          razorpayOrderId,

        razorpay_payment_id:
          razorpayPaymentId,

        razorpay_signature:
          razorpaySignature,
      },
      {
        timeout:
          options.timeout ||
          AGENT_TIMEOUT,
      }
    );

    console.log(
      "PAYPILOT PAYMENT VERIFIED:",
      response.data
    );

    return response.data;
  } catch (error) {
    console.error(
      "========================================"
    );

    console.error(
      "PAYPILOT PAYMENT VERIFICATION FAILED"
    );

    console.error(
      "HTTP STATUS:",
      error?.response?.status
    );

    console.error(
      "BACKEND RESPONSE:",
      error?.response?.data
    );

    console.error(
      "========================================"
    );

    const backendData =
      error?.response?.data;

    let message =
      "Payment verification failed.";

    if (
      typeof backendData?.detail ===
      "string"
    ) {
      message =
        backendData.detail;
    } else if (
      typeof backendData?.detail
        ?.message === "string"
    ) {
      message =
        backendData.detail.message;

      if (
        backendData.detail.error
      ) {
        message +=
          `: ${backendData.detail.error}`;
      }
    } else if (
      typeof backendData?.message ===
      "string"
    ) {
      message =
        backendData.message;
    } else if (
      typeof error?.message ===
      "string"
    ) {
      message =
        error.message;
    }

    const enhancedError =
      new Error(message);

    enhancedError.response =
      error?.response;

    enhancedError.backendData =
      backendData;

    throw enhancedError;
  }
};

// ---------------------------------------------------------
// GET PAYMENT
// ---------------------------------------------------------

export const getPayment = async (
  paymentId,
  options = {}
) => {
  if (
    paymentId === null ||
    paymentId === undefined ||
    paymentId === ""
  ) {
    throw new Error(
      "paymentId is required."
    );
  }

  const numericPaymentId =
    Number(paymentId);

  if (
    !Number.isInteger(
      numericPaymentId
    ) ||
    numericPaymentId <= 0
  ) {
    throw new Error(
      "A valid paymentId is required."
    );
  }

  const response =
    await api.get(
      `/payments/${numericPaymentId}`,
      {
        timeout:
          options.timeout ||
          DEFAULT_TIMEOUT,

        signal:
          options.signal,
      }
    );

  return response.data;
};


// ---------------------------------------------------------
// GET PAYMENTS
// ---------------------------------------------------------

export const getPayments = async (
  params = {},
  options = {}
) => {
  const response =
    await api.get(
      "/payments/",
      {
        params,

        timeout:
          options.timeout ||
          DEFAULT_TIMEOUT,

        signal:
          options.signal,
      }
    );

  return response.data;
};


// =========================================================
// DEFAULT EXPORT
// =========================================================

export default api;