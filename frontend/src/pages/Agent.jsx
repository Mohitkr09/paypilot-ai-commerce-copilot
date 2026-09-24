import { useEffect, useRef, useState } from "react";

import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bot,
  Boxes,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  CreditCard,
  DollarSign,
  Hash,
  Loader2,
  LockKeyhole,
  Package,
  Send,
  ShieldAlert,
  ShieldCheck,
  ShoppingCart,
  Store,
  User,
  UserCheck,
  XCircle,
} from "lucide-react";

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const PUBLIC_CATALOG_ENDPOINT =
  `${API_URL}/products/public-catalog`;

import {
  sendAgentChat,
  getStoredMerchantId,
  getManualReviews,
  approveOrderManualReview,
  rejectOrderManualReview,
  getApiErrorMessage as getSharedApiErrorMessage,
  createPayment,
  verifyPayment,
} from "../services/api";


// =========================================================
// PAYPILOT AGENT
// =========================================================
//
// PHASE 8C:
//
// User
//   ↓
// PayPilot Agent
//   ↓
// Catalog / Intent Detection
//   ↓
// Order Creation
//   ↓
// Policy Agent
//   ↓
// Risk Agent
//   ↓
// Payment Gate
//   ↓
// Agent Decision
//   ↓
// HUMAN CONFIRMATION
//   ↓
// Razorpay Checkout
//   ↓
// Backend Verification
//   ↓
// PAID
//
// IMPORTANT:
//
// The AI is never allowed to authorize money movement.
//
// =========================================================


const STORED_MERCHANT_ID = Number(getStoredMerchantId());

const MERCHANT_ID =
  Number.isInteger(STORED_MERCHANT_ID) && STORED_MERCHANT_ID > 0
    ? STORED_MERCHANT_ID
    : 1;


// =========================================================
// RAZORPAY
// =========================================================

const RAZORPAY_KEY_ID =
  import.meta.env.VITE_RAZORPAY_KEY_ID;


// =========================================================
// SAFE STRING
// =========================================================

const safeString = (value, fallback = "") => {
  if (
    value === null ||
    value === undefined
  ) {
    return fallback;
  }

  if (typeof value === "string") {
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
};


// =========================================================
// FORMAT CURRENCY
// =========================================================

const formatCurrency = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return safeString(value, "—");
  }

  return `₹${number.toLocaleString(
    "en-IN",
    {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  )}`;
};


// =========================================================
// FORMAT PERCENT
// =========================================================

const formatPercent = (value) => {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return safeString(value, "—");
  }

  return `${number.toFixed(2)}%`;
};


// =========================================================
// NORMALIZE STATUS
// =========================================================

const normalizeStatus = (value) =>
  safeString(value, "")
    .trim()
    .toUpperCase();


// =========================================================
// API ERROR
// =========================================================
//
// Handles:
//
// {
//   detail: "error"
// }
//
// {
//   detail: {
//      message: "...",
//      error: "..."
//   }
// }
//
// FastAPI validation arrays.
//
// =========================================================

const getApiErrorMessage = (
  data,
  fallback = "Request failed."
) => {
  if (!data) {
    return fallback;
  }

  if (typeof data === "string") {
    return data;
  }

  const detail = data.detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (
          !item ||
          typeof item !== "object"
        ) {
          return null;
        }

        const location = Array.isArray(
          item.loc
        )
          ? item.loc
              .filter(
                (part) =>
                  part !== "body" &&
                  part !== "query" &&
                  part !== "path"
              )
              .join(" → ")
          : "";

        const message =
          item.msg ||
          "Validation error";

        return location
          ? `${location}: ${message}`
          : message;
      })
      .filter(Boolean);

    return messages.length
      ? messages.join(" | ")
      : fallback;
  }

  if (
    detail &&
    typeof detail === "object"
  ) {
    // Show the actual Python/backend exception first.
    if (
      typeof detail.error === "string" &&
      detail.error.trim()
    ) {
      return detail.error;
    }

    if (
      typeof detail.message === "string" &&
      detail.message.trim()
    ) {
      return detail.message;
    }

    if (
      typeof detail.msg === "string" &&
      detail.msg.trim()
    ) {
      return detail.msg;
    }

    return safeString(
      detail,
      fallback
    );
  }

  if (
    typeof detail === "string" &&
    detail.trim()
  ) {
    return detail;
  }

  if (
    typeof data.error === "string" &&
    data.error.trim()
  ) {
    return data.error;
  }

  if (
    typeof data.message === "string" &&
    data.message.trim()
  ) {
    return data.message;
  }

  return fallback;
};


// =========================================================
// LOAD RAZORPAY
// =========================================================

const loadRazorpay = () =>
  new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }

    const existing =
      document.querySelector(
        'script[src="https://checkout.razorpay.com/v1/checkout.js"]'
      );

    if (existing) {
      existing.addEventListener(
        "load",
        () => resolve(true),
        { once: true }
      );

      existing.addEventListener(
        "error",
        () =>
          reject(
            new Error(
              "Unable to load Razorpay Checkout."
            )
          ),
        { once: true }
      );

      return;
    }

    const script =
      document.createElement("script");

    script.src =
      "https://checkout.razorpay.com/v1/checkout.js";

    script.async = true;

    script.onload = () => {
      if (window.Razorpay) {
        resolve(true);
      } else {
        reject(
          new Error(
            "Razorpay Checkout loaded but Razorpay was not initialized."
          )
        );
      }
    };

    script.onerror = () => {
      reject(
        new Error(
          "Unable to load Razorpay Checkout."
        )
      );
    };

    document.body.appendChild(script);
  });


// =========================================================
// RESPONSE BODY READER
// =========================================================

const readResponseBody = async (
  response
) => {
  const contentType =
    response.headers.get(
      "content-type"
    ) || "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  const text =
    await response.text();

  return {
    message: text,
  };
};


// =========================================================
// DETAIL ITEM
// =========================================================

function DetailItem({
  icon: Icon,
  label,
  value,
  muted = false,
}) {
  return (
    <div className="group rounded-xl border border-slate-200/80 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition hover:border-slate-300 hover:shadow-sm">
      <div className="flex items-center gap-2">
        <Icon
          size={15}
          className="text-slate-400 transition group-hover:text-blue-500"
        />

        <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
          {label}
        </span>
      </div>

      <p
        className={`mt-1.5 break-words text-sm font-semibold ${
          muted
            ? "text-slate-400"
            : "text-slate-800"
        }`}
      >
        {safeString(value, "—")}
      </p>
    </div>
  );
}


// =========================================================
// SECTION
// =========================================================

function Section({
  title,
  icon: Icon,
  children,
}) {
  return (
    <div className="mt-5">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm">
          <Icon size={15} />
        </div>

        <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
          {title}
        </h3>
      </div>

      {children}
    </div>
  );
}


// =========================================================
// BUYER CATALOG HELPERS
// =========================================================

const normalizePublicProduct = (product) => {
  if (!product || typeof product !== "object") {
    return null;
  }

  const id = Number(
    product.product_id ??
      product.id
  );

  const merchantId = Number(
    product.merchant_id ??
      product.merchantId
  );

  const stock = Number(
    product.stock_quantity ??
      product.stock ??
      0
  );

  const price = Number(
    product.price ?? 0
  );

  if (
    !Number.isInteger(id) ||
    id <= 0 ||
    !Number.isInteger(merchantId) ||
    merchantId <= 0 ||
    !String(product.name || "").trim()
  ) {
    return null;
  }

  return {
    id,
    product_id: id,
    merchant_id: merchantId,
    name: String(product.name).trim(),
    category: String(product.category || "General").trim(),
    description: String(product.description || "").trim(),
    sku: String(product.sku || "").trim(),
    price: Number.isFinite(price) ? price : 0,
    stock: Number.isFinite(stock) ? stock : 0,
    stock_quantity: Number.isFinite(stock) ? stock : 0,
    status: String(
      product.stock_status ||
        (stock > 5 ? "IN_STOCK" : stock > 0 ? "LOW_STOCK" : "OUT_OF_STOCK")
    ).toUpperCase(),
    is_active: product.is_active !== false,
  };
};

const fetchPublicCatalog = async () => {
  // The buyer catalog is a public read-only endpoint.
  // Never send this request through /agent/chat.
  // We try both FastAPI URL variants because deployments can
  // expose the route with or without a trailing slash.
  const endpoints = [
    PUBLIC_CATALOG_ENDPOINT,
    `${PUBLIC_CATALOG_ENDPOINT}/`,
  ];

  let lastError = null;

  for (const endpoint of endpoints) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      8000
    );

    try {
      const response = await fetch(endpoint, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
        signal: controller.signal,
      });

      const payload = await readResponseBody(response);

      if (!response.ok) {
        const message = getApiErrorMessage(
          payload,
          `Unable to load marketplace catalog (${response.status}).`
        );

        // Try the second URL variant for 404/405 only.
        if (
          (response.status === 404 ||
            response.status === 405) &&
          endpoint !== endpoints[endpoints.length - 1]
        ) {
          lastError = new Error(message);
          continue;
        }

        throw new Error(message);
      }

      const products =
        normalizePublicCatalogResponse(payload);

      return products;
    } catch (error) {
      lastError = error;

      if (error?.name === "AbortError") {
        lastError = new Error(
          `Marketplace catalog request timed out at ${endpoint}.`
        );
      }

      // Continue to the trailing-slash variant.
      if (endpoint !== endpoints[endpoints.length - 1]) {
        continue;
      }
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  throw new Error(
    `${lastError?.message || "Unable to load marketplace catalog."} ` +
    `Check that FastAPI is running and that GET /products/public-catalog is registered.`
  );
};

const normalizePublicCatalogResponse = (payload) => {
  // Support every response shape currently used by the PayPilot
  // backend, while preserving merchant_id for every product.
  // The frontend intentionally NEVER filters by the logged-in
  // merchant. The public catalog is the marketplace catalog.
  const raw = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.catalog)
      ? payload.catalog
      : Array.isArray(payload?.products)
        ? payload.products
        : Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload?.data?.catalog)
            ? payload.data.catalog
            : Array.isArray(payload?.data?.products)
              ? payload.data.products
              : [];

  const normalized = raw
    .map(normalizePublicProduct)
    .filter(Boolean)
    .filter(
      (product) =>
        product.is_active &&
        product.stock > 0
    );

  // A product belongs to a merchant, so de-duplicate only identical
  // product/merchant records. Never de-duplicate by product name; two
  // different merchants may legitimately sell the same product.
  const unique = new Map();

  for (const product of normalized) {
    const key = `${product.id}::${product.merchant_id}`;

    if (!unique.has(key)) {
      unique.set(key, product);
    }
  }

  return [...unique.values()].sort((a, b) => {
    const merchantCompare =
      Number(a.merchant_id) - Number(b.merchant_id);

    if (merchantCompare !== 0) {
      return merchantCompare;
    }

    return String(a.name).localeCompare(
      String(b.name)
    );
  });
};

const isGlobalCatalogRequest = (message) => {
  const text = String(message || "")
    .trim()
    .toLowerCase()
    .replace(/[?!.]/g, " ");

  if (!text) {
    return false;
  }

  // Buyer-only browsing intent. These requests must never
  // enter the order/policy/risk/payment agent.
  const browseVerb =
    /\b(show|display|list|give|tell|see|view|browse|find|get|what|which)\b/.test(
      text
    );

  const allScope =
    /\b(all|every|entire|available|everything|whole|any)\b/.test(
      text
    );

  const productWord =
    /\b(product|products|catalog|inventory|items|merchandise)\b/.test(
      text
    );

  const marketplaceScope =
    /\b(all\s+merchants|every\s+merchant|across\s+merchants|marketplace|from\s+all\s+merchants)\b/.test(
      text
    );

  return (
    (browseVerb && allScope && productWord) ||
    (browseVerb && productWord && marketplaceScope) ||
    /\ball\s+available\s+products\b/.test(text) ||
    /\bavailable\s+products\b/.test(text) ||
    /\bproducts\s+from\s+all\s+merchants\b/.test(text) ||
    /\ball\s+products\b/.test(text)
  );
};

const findUniqueProductFromMessage = (
  message,
  products
) => {
  const text = String(message || "")
    .trim()
    .toLowerCase();

  if (!text || !Array.isArray(products) || !products.length) {
    return null;
  }

  const exactMatches = products.filter((product) => {
    const name = String(product?.name || "")
      .trim()
      .toLowerCase();

    return name && text.includes(name);
  });

  if (!exactMatches.length) {
    return null;
  }

  const uniqueMerchantMatches = new Map();

  for (const product of exactMatches) {
    uniqueMerchantMatches.set(
      `${product.name.toLowerCase()}::${product.merchant_id}`,
      product
    );
  }

  // Prefer the current merchant when the same product name exists
  // at more than one merchant. Otherwise use the unique match.
  const currentMerchantMatch = [...uniqueMerchantMatches.values()].find(
    (product) =>
      Number(product.merchant_id) === Number(MERCHANT_ID)
  );

  if (currentMerchantMatch) {
    return currentMerchantMatch;
  }

  const distinctNames = new Set(
    [...uniqueMerchantMatches.values()].map(
      (product) => product.name.toLowerCase()
    )
  );

  if (distinctNames.size === 1) {
    return [...uniqueMerchantMatches.values()][0];
  }

  return null;
};


// =========================================================
// PARSE CATALOG
// =========================================================
//
// Backend format:
//
// Available products:
// Mechanical Keyboard (₹50000.00) - IN_STOCK, stock: 22
//
// Parse each line independently.
//
// =========================================================

const parseCatalogProducts = (
  message
) => {
  if (
    typeof message !== "string"
  ) {
    return [];
  }

  const products = [];

  const lines =
    message
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

  const regex =
    /^(.+?)\s+\(₹([\d,.]+)\)\s*-\s*([A-Z_]+),\s*stock:\s*(\d+)$/i;

  for (const line of lines) {
    const match =
      line.match(regex);

    if (!match) {
      continue;
    }

    products.push({
      name: match[1].trim(),

      price: Number(
        match[2].replace(/,/g, "")
      ),

      status:
        match[3]
          .trim()
          .toUpperCase(),

      stock: Number(
        match[4]
      ),
    });
  }

  return products;
};


// =========================================================
// STOCK STATUS
// =========================================================

const getStockStatus = (
  product
) => {
  const stock =
    Number(product.stock || 0);

  if (stock <= 0) {
    return {
      label: "OUT OF STOCK",

      className:
        "border-red-200 bg-red-50 text-red-600",

      dotClass:
        "bg-red-500",
    };
  }

  if (stock <= 5) {
    return {
      label: "LOW STOCK",

      className:
        "border-amber-200 bg-amber-50 text-amber-600",

      dotClass:
        "bg-amber-500",
    };
  }

  return {
    label: "IN STOCK",

    className:
      "border-emerald-200 bg-emerald-50 text-emerald-600",

    dotClass:
      "bg-emerald-500",
  };
};


// =========================================================
// COMMERCE DETAILS
// =========================================================

function CommerceDetails({
  data,
}) {
  return (
    <Section
      title="Commerce Details"
      icon={ShoppingCart}
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <DetailItem
          icon={Package}
          label="Product"
          value={
            data.product_name ||
            "—"
          }
          muted={
            !data.product_name
          }
        />

        <DetailItem
          icon={Hash}
          label="Product ID"
          value={
            data.product_id ??
            "—"
          }
          muted={
            data.product_id ==
            null
          }
        />

        <DetailItem
          icon={Boxes}
          label="Quantity"
          value={
            data.quantity ??
            "—"
          }
          muted={
            data.quantity ==
            null
          }
        />

        <DetailItem
          icon={Hash}
          label="Order ID"
          value={
            data.order_id ??
            "Not created"
          }
          muted={
            data.order_id ==
            null
          }
        />

        <DetailItem
          icon={Clock3}
          label="Order Status"
          value={
            data.order_status ||
            "—"
          }
          muted={
            !data.order_status
          }
        />

        <DetailItem
          icon={Store}
          label="Merchant ID"
          value={
            data.merchant_id ??
            MERCHANT_ID
          }
        />
      </div>
    </Section>
  );
}


// =========================================================
// GOVERNANCE DETAILS
// =========================================================

function GovernanceDetails({
  data,
}) {
  const riskLevel =
    normalizeStatus(
      data.risk_level
    );

  return (
    <Section
      title="Risk & Governance"
      icon={ShieldCheck}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <DetailItem
          icon={Activity}
          label="Risk Score"
          value={
            data.risk_score ??
            "—"
          }
          muted={
            data.risk_score ==
            null
          }
        />

        <DetailItem
          icon={ShieldAlert}
          label="Risk Level"
          value={
            riskLevel || "—"
          }
          muted={
            !riskLevel
          }
        />

        <DetailItem
          icon={
            data.manual_review_required
              ? ShieldAlert
              : ShieldCheck
          }
          label="Manual Review"
          value={
            data.manual_review_required
              ? "Required"
              : "Not Required"
          }
        />
      </div>
    </Section>
  );
}


// =========================================================
// PHASE 8C NOTICE
// =========================================================

function Phase8CNotice() {
  return (
    <div className="mt-5 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
      <LockKeyhole
        size={17}
        className="mt-0.5 shrink-0 text-blue-600"
      />

      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-blue-800">
          Phase 8C Agentic Commerce
        </p>

        <p className="mt-1 text-xs leading-5 text-blue-700">
          PayPilot AI can evaluate the order and
          prepare payment, but it cannot approve a
          manual-review exception. Once an authorized
          merchant approves the review, the agent
          automatically continues to Razorpay. The
          buyer still completes the actual payment inside
          Razorpay.
        </p>
      </div>
    </div>
  );
}


// =========================================================
// CATALOG RESPONSE
// =========================================================

function CatalogResponse({
  data,
  onRecommend,
  recommendationLoadingId = null,
  recommendationError = "",
  growthRecommendation = null,
  onChooseRecommendation,
  onChooseProduct,
}) {
  const products =
    Array.isArray(data?.products)
      ? data.products
      : parseCatalogProducts(data.message);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
            <Boxes size={19} />
          </div>

          <div>
            <p className="text-sm font-bold text-blue-900">
              Catalog Query
            </p>

            <p className="mt-1 text-xs leading-5 text-blue-700">
              PayPilot is showing live buyer inventory
              across all active merchants.
              Only in-stock products are displayed.
            </p>
          </div>
        </div>
      </div>

      <Section
        title={`Available Products${
          products.length
            ? ` • ${products.length}`
            : ""
        }`}
        icon={Package}
      >
        {products.length ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {products.map(
              (product, index) => {
                const stockStatus =
                  getStockStatus(
                    product
                  );

                return (
                  <div
                    key={`${product.name}-${index}`}
                    className="rounded-xl border border-slate-200 bg-white p-4 transition hover:border-blue-200 hover:shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h4 className="text-sm font-bold text-slate-800">
                          {product.name}
                        </h4>

                        <p className="mt-1 text-lg font-black text-slate-900">
                          {formatCurrency(product.price)}
                        </p>

                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold text-slate-600">
                            <Store size={11} />
                            Merchant #{product.merchant_id || "—"}
                          </span>

                          {product.category && (
                            <span className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-bold text-blue-700">
                              {product.category}
                            </span>
                          )}
                        </div>
                      </div>

                      <span
                        className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] font-bold ${stockStatus.className}`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${stockStatus.dotClass}`}
                        />

                        {
                          stockStatus.label
                        }
                      </span>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                      <span className="flex items-center gap-1.5 text-xs text-slate-400">
                        <Package size={13} />
                        Available stock
                      </span>

                      <span className="text-sm font-extrabold text-slate-700">
                        {product.stock}
                      </span>
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => onChooseProduct?.(product)}
                        className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-blue-700"
                      >
                        <ShoppingCart size={14} />
                        Buy now
                      </button>

                      <button
                        type="button"
                        onClick={() => onRecommend?.(product.name)}
                        disabled={recommendationLoadingId === product.name}
                        className="flex items-center justify-center gap-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2.5 text-xs font-bold text-violet-700 transition hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {recommendationLoadingId === product.name ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <CircleDollarSign size={14} />
                        )}
                        AI recommend
                      </button>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        ) : (
          <div className="whitespace-pre-line rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            {safeString(
              data.message,
              "No products found."
            )}
          </div>
        )}
      </Section>

      {recommendationError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle size={17} className="mt-0.5 shrink-0 text-red-600" />
            <div>
              <p className="text-sm font-bold text-red-700">
                Recommendation Failed
              </p>
              <p className="mt-1 text-xs leading-5 text-red-600">
                {recommendationError}
              </p>
            </div>
          </div>
        </div>
      )}

      {growthRecommendation && (
        <GrowthRecommendationPanel
          recommendation={growthRecommendation}
          onChoose={onChooseRecommendation}
        />
      )}

      <CommerceDetails
        data={data}
      />

      <GovernanceDetails
        data={data}
      />

      <Phase8CNotice />
    </div>
  );
}


// =========================================================
// AI GROWTH RECOMMENDATIONS
// =========================================================

function RecommendationCard({
  product,
  type,
  onChoose,
}) {
  if (!product) {
    return null;
  }

  const isUpsell = type === "UPSELL";

  return (
    <div
      className={`rounded-xl border p-4 ${
        isUpsell
          ? "border-violet-200 bg-violet-50/70"
          : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2 py-1 text-[10px] font-bold ${
                isUpsell
                  ? "bg-violet-100 text-violet-700"
                  : "bg-blue-50 text-blue-700"
              }`}
            >
              {isUpsell ? "UPSELL" : "CROSS-SELL"}
            </span>

            {product.stock_quantity > 0 && (
              <span className="text-[10px] font-semibold text-emerald-600">
                In stock
              </span>
            )}
          </div>

          <h4 className="mt-2 text-sm font-bold text-slate-800">
            {product.name}
          </h4>

          <p className="mt-1 text-base font-bold text-slate-900">
            {formatCurrency(product.price)}
          </p>
        </div>

        <Package
          size={19}
          className={
            isUpsell
              ? "shrink-0 text-violet-500"
              : "shrink-0 text-blue-500"
          }
        />
      </div>

      {product.description && (
        <p className="mt-2 text-xs leading-5 text-slate-500">
          {product.description}
        </p>
      )}

      {product.reason && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
            Why PayPilot recommends this
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {product.reason}
          </p>
        </div>
      )}

      <button
        type="button"
        onClick={() => onChoose?.(product)}
        className={`mt-3 flex w-full items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-xs font-bold text-white transition ${
          isUpsell
            ? "bg-violet-600 hover:bg-violet-700"
            : "bg-blue-600 hover:bg-blue-700"
        }`}
      >
        <ShoppingCart size={14} />
        Choose {isUpsell ? "Upgrade" : "Product"}
        <ArrowRight size={14} />
      </button>
    </div>
  );
}

function GrowthRecommendationPanel({
  recommendation,
  onChoose,
}) {
  if (!recommendation) {
    return null;
  }

  const upsell = recommendation.upsell;
  const crossSells = Array.isArray(
    recommendation.cross_sells
  )
    ? recommendation.cross_sells
    : [];

  return (
    <div className="overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm">
      <div className="border-b border-indigo-100 bg-indigo-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <ShoppingCart size={19} />
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold text-indigo-900">
                AI Growth Recommendations
              </p>

              <span className="rounded-full border border-indigo-200 bg-white px-2 py-0.5 text-[10px] font-bold text-indigo-700">
                BOUNDED
              </span>
            </div>

            <p className="mt-1 text-xs leading-5 text-indigo-700">
              PayPilot found explainable upsell and cross-sell options.
              Recommendations do not create orders or move money.
            </p>
          </div>
        </div>
      </div>

      <div className="p-4">
        {recommendation.base_product && (
          <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                  Selected Product
                </p>
                <p className="mt-1 text-sm font-bold text-slate-800">
                  {recommendation.base_product.name}
                </p>
              </div>

              <p className="text-sm font-bold text-slate-900">
                {formatCurrency(
                  recommendation.base_product.price
                )}
              </p>
            </div>
          </div>
        )}

        {upsell && (
          <Section
            title="Recommended Upgrade"
            icon={ArrowRight}
          >
            <RecommendationCard
              product={upsell}
              type="UPSELL"
              onChoose={onChoose}
            />
          </Section>
        )}

        {crossSells.length > 0 && (
          <Section
            title={`Recommended Accessories • ${crossSells.length}`}
            icon={Package}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              {crossSells.map((product) => (
                <RecommendationCard
                  key={`${product.product_id}-${product.recommendation_type}`}
                  product={product}
                  type="CROSS_SELL"
                  onChoose={onChoose}
                />
              ))}
            </div>
          </Section>
        )}

        {!upsell && crossSells.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            No suitable upsell or cross-sell was found for this product.
          </div>
        )}

        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
            <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-700">
              Money Action
            </p>
            <p className="mt-1 text-xs font-bold text-emerald-800">
              {recommendation.money_action ? "Yes" : "No"}
            </p>
          </div>

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-center">
            <p className="text-[10px] font-bold uppercase tracking-wide text-blue-700">
              User Confirmation
            </p>
            <p className="mt-1 text-xs font-bold text-blue-800">
              {recommendation.requires_user_confirmation
                ? "Required"
                : "Not required"}
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
            <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
              Recommendation Type
            </p>
            <p className="mt-1 text-xs font-bold text-slate-700">
              AI Growth
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}


// =========================================================
// GENERAL QUERY
// =========================================================

function GeneralQueryResponse({
  data,
}) {
  return (
    <div>
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-600">
            <Bot size={19} />
          </div>

          <div className="min-w-0">
            <p className="text-sm font-bold text-slate-800">
              General Query
            </p>

            <p className="mt-1 text-xs text-slate-400">
              PayPilot returned information
              for your request.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-lg border border-white bg-white p-4">
          <p className="whitespace-pre-line text-sm leading-6 text-slate-600">
            {safeString(
              data.message,
              "The agent returned a response."
            )}
          </p>
        </div>
      </div>

      <CommerceDetails
        data={data}
      />

      <GovernanceDetails
        data={data}
      />

      <Phase8CNotice />
    </div>
  );
}


// =========================================================
// PAYMENT CONFIRMATION
// =========================================================

function PaymentConfirmation({
  data,
  onPay,
  paymentLoading,
}) {
  return (
    <div className="mt-5 overflow-hidden rounded-2xl border border-blue-200 bg-white shadow-sm">
      <div className="border-b border-blue-100 bg-blue-50 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
            <UserCheck size={19} />
          </div>

          <div>
            <p className="text-sm font-bold text-blue-900">
              Payment Checkout
            </p>

            <p className="mt-1 text-xs leading-5 text-blue-700">
              The payment gate has passed. PayPilot will
              automatically continue to secure Razorpay
              checkout. If the browser blocks the
              automatic checkout window, use the button
              below to open checkout with your click.
            </p>
          </div>
        </div>
      </div>

      <div className="p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailItem
            icon={Package}
            label="Product"
            value={
              data.product_name ||
              "Order"
            }
          />

          <DetailItem
            icon={Boxes}
            label="Quantity"
            value={
              data.quantity ??
              "—"
            }
          />

          <DetailItem
            icon={Hash}
            label="Order ID"
            value={
              data.order_id ??
              "—"
            }
          />

          <DetailItem
            icon={CircleDollarSign}
            label="Amount"
            value={formatCurrency(
              data.final_amount
            )}
          />
        </div>

        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck
              size={18}
              className="mt-0.5 shrink-0 text-emerald-600"
            />

            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-emerald-800">
                Payment Gate Passed
              </p>

              <p className="mt-1 text-xs leading-5 text-emerald-700">
                Merchant approval passed the
                payment gate. The agent can now
                prepare the Razorpay checkout.
                Completing payment still happens
                inside Razorpay.
              </p>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onPay}
          disabled={paymentLoading}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {paymentLoading ? (
            <>
              <Loader2
                size={17}
                className="animate-spin"
              />

              Preparing secure payment...
            </>
          ) : (
            <>
              <LockKeyhole
                size={17}
              />

              Open Secure Checkout{" "}
              {formatCurrency(
                data.final_amount
              )}

              <ArrowRight
                size={17}
              />
            </>
          )}
        </button>

        <p className="mt-3 text-center text-[11px] leading-5 text-slate-400">
          The payment gate has passed. This button is a
          safe user-gesture fallback if automatic Razorpay
          opening was blocked or checkout was cancelled.
        </p>
      </div>
    </div>
  );
}


// =========================================================
// ORDER RESPONSE
// =========================================================

function OrderResponse({
  data,
}) {
  const initialStatus =
    normalizeStatus(data.order_status);

  const [
    orderData,
    setOrderData,
  ] = useState(data);

  const [
    reviewLoading,
    setReviewLoading,
  ] = useState(false);

  const [
    reviewError,
    setReviewError,
  ] = useState("");

  const [
    reviewInfo,
    setReviewInfo,
  ] = useState(null);

  const [
    paymentLoading,
    setPaymentLoading,
  ] = useState(false);

  const [
    paymentResult,
    setPaymentResult,
  ] = useState(null);

  // Prevent duplicate payment creation when approval is detected
  // by both the local decision flow and the polling flow.
  const paymentInFlightRef = useRef(false);
  const paymentCompletedRef = useRef(false);
  const razorpayInstanceRef = useRef(null);

  // Keeps the Razorpay callback after checkout succeeds but backend
  // verification fails. This lets us retry verification without
  // creating another payment or another Razorpay checkout.
  const pendingVerificationRef = useRef(null);

  useEffect(() => {
    setOrderData(data);
    setReviewError("");
    setReviewInfo(null);
    setPaymentResult(null);
    paymentInFlightRef.current = false;
    paymentCompletedRef.current = false;
    razorpayInstanceRef.current = null;
    pendingVerificationRef.current = null;
  }, [
    data,
  ]);

  const status =
    normalizeStatus(
      orderData.order_status
    );

  const approved =
    status === "APPROVED";

  const manualReview =
    status ===
    "MANUAL_REVIEW_REQUIRED";

  const rejected =
    status === "REJECTED";

  const blocked =
    status === "BLOCKED";

  const noOrder =
    !orderData.order_id;

  // =======================================================
  // FIND MANUAL REVIEW
  // =======================================================
  //
  // The current /agent/chat response may contain only
  // order_id and MANUAL_REVIEW_REQUIRED. Therefore we
  // resolve the review record from GET /manual-reviews/.
  //
  // If your backend later adds manual_review_id to
  // /agent/chat, this code will use it directly.
  // =======================================================

  const findManualReview = async () => {
    if (!orderData.order_id) {
      throw new Error(
        "Order ID is missing. Manual review cannot be resolved."
      );
    }

    const directReviewId =
      orderData.manual_review_id ??
      orderData.review_id ??
      orderData.manualReviewId;

    if (directReviewId) {
      return {
        id: directReviewId,
      };
    }

    // Use the authenticated API client. The Axios interceptor in
    // services/api.js attaches the merchant JWT automatically.
    const responseData =
      await getManualReviews();

    const reviews =
      Array.isArray(responseData)
        ? responseData
        : Array.isArray(
            responseData?.reviews
          )
          ? responseData.reviews
          : [];

    const matchingReview =
      reviews.find(
        (review) =>
          Number(
            review?.order_id
          ) ===
          Number(
            orderData.order_id
          ) &&
          normalizeStatus(
            review?.status
          ) === "PENDING"
      );

    if (!matchingReview) {
      throw new Error(
        `No pending manual review was found for Order #${orderData.order_id}.`
      );
    }

    return matchingReview;
  };

  // =======================================================
  // EXTERNAL MERCHANT APPROVAL SYNC
  // =======================================================
  // The merchant may approve/reject the order from the merchant
  // dashboard in a different browser tab. The buyer Agent must
  // detect that decision without requiring merchant credentials.
  //
  // IMPORTANT:
  // GET /manual-reviews/order-status/{order_id} is a READ-ONLY
  // buyer endpoint. It does NOT allow approval/rejection. The
  // merchant decision itself is still made through the protected
  // manual-review decision endpoint.
  //
  // When the backend reports that the merchant approved the order:
  //   1. Mark the local order APPROVED.
  //   2. Clear manual_review_required.
  //   3. Treat the manual-review approval as the payment-gate authorization.
  //   4. Automatically create/open the payment checkout.
  //
  // IMPORTANT: do not require payment_approved to be present in the
  // polling response. The manual-review decision endpoint already sets
  // payment_approved=true on the Order. Some deployments may serialize
  // that field differently or omit it from a lightweight status response.
  // APPROVED is therefore the authoritative transition for this flow.
  // =======================================================

  useEffect(() => {
    // Only poll the merchant decision endpoint while this order
    // actually requires manual review. Normal orders do not have a
    // manual-review record, so calling /manual-reviews/order-status/{id}
    // for them produces a misleading 404 in the backend logs.
    if (
      !orderData.order_id ||
      !manualReview ||
      approved ||
      rejected ||
      blocked
    ) {
      return undefined;
    }

    let cancelled = false;
    let timerId = null;

    const refreshMerchantDecision = async () => {
      try {
        const orderId = Number(
          orderData.order_id
        );

        const response = await fetch(
          `${API_URL}/manual-reviews/order-status/${orderId}`,
          {
            method: "GET",
            headers: {
              Accept: "application/json",
            },
            cache: "no-store",
          }
        );

        const serverOrder =
          await readResponseBody(response);

        if (cancelled) {
          return;
        }

        if (!response.ok) {
          // Background polling is intentionally silent. The next
          // poll will retry without interrupting the Agent UI.
          return;
        }

        const serverStatus = normalizeStatus(
          serverOrder?.order_status ??
            serverOrder?.status
        );

        const paymentApproved =
          serverOrder?.payment_approved === true ||
          serverOrder?.paymentApproved === true ||
          String(
            serverOrder?.payment_approved ??
              serverOrder?.paymentApproved ??
              ""
          ).toLowerCase() === "true" ||
          Number(
            serverOrder?.payment_approved ??
              serverOrder?.paymentApproved
          ) === 1;

        const paymentGateStatus = normalizeStatus(
          serverOrder?.payment_gate_status
        );

        // ---------------------------------------------------
        // MERCHANT APPROVED
        // ---------------------------------------------------
        // APPROVED is the authoritative order transition.
        // payment_approved is accepted when present, but it must not
        // block continuation because this endpoint is a lightweight
        // buyer-status endpoint.
        const merchantApproved =
          serverStatus === "APPROVED" ||
          paymentGateStatus === "APPROVED_BY_MANUAL_REVIEW" ||
          (serverStatus === "APPROVED" && paymentApproved);

        console.log(
          "PAYPILOT MANUAL REVIEW STATUS:",
          {
            orderId,
            serverStatus,
            paymentApproved,
            paymentGateStatus,
            merchantApproved,
          }
        );

        if (merchantApproved) {
          const approvedOrder = {
            ...orderData,
            ...serverOrder,

            order_id:
              serverOrder?.order_id ??
              orderData.order_id,

            order_status: "APPROVED",
            status: "APPROVED",

            manual_review_required: false,
            payment_approved: true,

            message:
              `${orderData.product_name || "Order"} was approved by the merchant. ` +
              `The manual-review gate is passed and the payment gate is now approved. ` +
              `PayPilot is automatically continuing to secure payment checkout.`,
          };

          setOrderData(approvedOrder);

          setReviewInfo({
            type: "APPROVED",
            message:
              `Merchant approved Order #${orderId}. Payment gate passed. PayPilot is automatically continuing to secure payment checkout.`,
          });

          setReviewError("");

          // -------------------------------------------------
          // FULL AGENTIC CONTINUATION
          // -------------------------------------------------
          // Do not wait for another user click. The merchant's
          // approval is the authorization required to pass the
          // manual-review exception gate. The buyer still performs
          // the actual payment inside Razorpay.
          void handleConfirmPayment(
            approvedOrder
          );

          return;
        }

        // ---------------------------------------------------
        // MERCHANT REJECTED
        // ---------------------------------------------------
        if (serverStatus === "REJECTED") {
          const rejectedOrder = {
            ...orderData,
            ...serverOrder,

            order_id:
              serverOrder?.order_id ??
              orderData.order_id,

            order_status: "REJECTED",
            status: "REJECTED",

            manual_review_required: false,
            payment_approved: false,

            message:
              `${orderData.product_name || "Order"} was rejected by the merchant. ` +
              `Payment is not allowed.`,
          };

          setOrderData(rejectedOrder);

          setReviewInfo({
            type: "REJECTED",
            message:
              `Merchant rejected Order #${orderId}. Payment has been stopped.`,
          });

          setReviewError("");
          return;
        }
      } catch (error) {
        // Never turn a temporary polling failure into a manual-review
        // failure. Keep polling until the merchant decides.
        console.debug(
          "MERCHANT APPROVAL STATUS POLL RETRY:",
          error?.message || error
        );
      } finally {
        if (!cancelled) {
          timerId = window.setTimeout(
            refreshMerchantDecision,
            3000
          );
        }
      }
    };

    refreshMerchantDecision();

    return () => {
      cancelled = true;

      if (timerId !== null) {
        window.clearTimeout(timerId);
      }
    };
  }, [
    manualReview,
    orderData.order_id,
  ]);

  // =======================================================
  // MANUAL REVIEW DECISION
  // =======================================================

  const handleManualReviewDecision =
    async (
      action
    ) => {
      if (
        !manualReview ||
        !orderData.order_id
      ) {
        return;
      }

      const normalizedAction =
        safeString(
          action
        )
          .trim()
          .toUpperCase();

      if (
        normalizedAction !==
          "APPROVE" &&
        normalizedAction !==
          "REJECT"
      ) {
        return;
      }

      setReviewLoading(true);
      setReviewError("");
      setReviewInfo(null);
      setPaymentResult(null);

      try {
        const review =
          await findManualReview();

        const reviewId =
          review?.id;

        if (!reviewId) {
          throw new Error(
            "Manual review ID is missing."
          );
        }

        // -------------------------------------------------
        // HUMAN IDENTITY
        // -------------------------------------------------
        //
        // Replace this with the authenticated admin/reviewer
        // name when your auth system exposes it.
        // -------------------------------------------------

        const reviewedBy =
          localStorage.getItem(
            "user_email"
          ) ||
          localStorage.getItem(
            "username"
          ) ||
          localStorage.getItem(
            "user_name"
          ) ||
          "ADMIN";

        // Use the authenticated API helpers instead of raw fetch().
        // This guarantees the merchant JWT is attached to the decision
        // request and prevents the 401 Unauthorized error.
        const decisionData =
          normalizedAction === "APPROVE"
            ? await approveOrderManualReview(
                reviewId,
                reviewedBy,
                "Approved by human reviewer from PayPilot Agent."
              )
            : await rejectOrderManualReview(
                reviewId,
                reviewedBy,
                "Rejected by human reviewer from PayPilot Agent."
              );

        const decisionStatus =
          normalizeStatus(
            decisionData?.status
          );

        if (
          normalizedAction ===
            "APPROVE" &&
          decisionStatus !==
            "APPROVED"
        ) {
          throw new Error(
            `Backend did not approve the review. Current review status: ${decisionData?.status || "UNKNOWN"}`
          );
        }

        if (
          normalizedAction ===
            "REJECT" &&
          decisionStatus !==
            "REJECTED"
        ) {
          throw new Error(
            `Backend did not reject the review. Current review status: ${decisionData?.status || "UNKNOWN"}`
          );
        }

        // -------------------------------------------------
        // UPDATE THE LOCAL ORDER STATE
        // -------------------------------------------------

        if (
          normalizedAction ===
          "APPROVE"
        ) {
          const approvedOrder = {
            ...orderData,

            order_status:
              "APPROVED",

            status:
              "APPROVED",

            manual_review_required:
              false,

            payment_approved:
              true,

            manual_review_id:
              reviewId,

            message:
              `${orderData.product_name || "Order"} order was approved by a human reviewer. Quantity: ${orderData.quantity}. Final amount: ${formatCurrency(orderData.final_amount)}. Risk: ${orderData.risk_level || "—"} (${orderData.risk_score ?? "—"}). Order ID: ${orderData.order_id}. Merchant approval passed the manual-review gate, so PayPilot is automatically continuing to Razorpay.`,
          };

          setOrderData(approvedOrder);

          setReviewInfo({
            type: "APPROVED",
            message:
              `Manual review approved successfully for Order #${orderData.order_id}. PayPilot is automatically continuing to secure payment checkout.`,
          });

          // This was the missing continuation in the previous flow.
          void handleConfirmPayment(approvedOrder);
        } else {
          setOrderData(
            (previous) => ({
              ...previous,

              order_status:
                "REJECTED",

              status:
                "REJECTED",

              manual_review_required:
                false,

              payment_approved:
                false,

              manual_review_id:
                reviewId,

              message:
                `${previous.product_name || "Order"} order was rejected by the human reviewer. Payment is not allowed.`,
            })
          );

          setReviewInfo({
            type: "REJECTED",
            message:
              `Manual review rejected for Order #${orderData.order_id}. Payment has been stopped.`,
          });
        }
      } catch (error) {
        console.error(
          "MANUAL REVIEW DECISION ERROR:",
          error
        );

        setReviewError(
          safeString(
            error?.message,
            "Unable to process manual review."
          )
        );
      } finally {
        setReviewLoading(
          false
        );
      }
    };

  // =======================================================
  // PAYMENT
  // =======================================================

  // Extract the real backend verification error instead of only showing
  // "Request failed with status code 400".
  const getPaymentVerificationErrorMessage = (error) => {
    const backendData =
      error?.backendData ||
      error?.response?.data ||
      null;

    const backendMessage =
      getSharedApiErrorMessage(
        backendData,
        ""
      );

    if (backendMessage) {
      return backendMessage;
    }

    if (
      typeof error?.message === "string" &&
      error.message.trim()
    ) {
      return error.message;
    }

    return "Payment verification failed. Please contact support before retrying payment.";
  };

  // Verify a Razorpay payment that has already completed checkout.
  // This is deliberately separate from createPayment(): if verification
  // fails, we retry ONLY verification and never create a second payment.
  const verifyCompletedPayment = async (
    paymentRecord,
    razorpayResponse
  ) => {
    if (!paymentRecord?.id) {
      throw new Error(
        "Backend payment ID is missing. Payment cannot be verified."
      );
    }

    if (
      !razorpayResponse?.razorpay_order_id ||
      !razorpayResponse?.razorpay_payment_id ||
      !razorpayResponse?.razorpay_signature
    ) {
      throw new Error(
        "Razorpay did not return all required verification values."
      );
    }

    console.log(
      "========================================"
    );
    console.log(
      "PAYPILOT PAYMENT VERIFICATION"
    );
    console.log({
      backendPaymentId: paymentRecord.id,
      razorpayOrderId:
        razorpayResponse.razorpay_order_id,
      razorpayPaymentId:
        razorpayResponse.razorpay_payment_id,
      signatureReceived: Boolean(
        razorpayResponse.razorpay_signature
      ),
    });
    console.log(
      "========================================"
    );

    return await verifyPayment(
      paymentRecord.id,
      {
        razorpay_order_id:
          razorpayResponse.razorpay_order_id,
        razorpay_payment_id:
          razorpayResponse.razorpay_payment_id,
        razorpay_signature:
          razorpayResponse.razorpay_signature,
      }
    );
  };

  const handleConfirmPayment =
    async (approvedOrderOverride = null, paymentOptions = {}) => {
      const paymentOrder =
        approvedOrderOverride || orderData;

      const paymentOrderStatus =
        normalizeStatus(
          paymentOrder?.order_status
        );

      const paymentGatePassed =
        paymentOrderStatus === "APPROVED" ||
        paymentOrder?.payment_approved === true;

      if (!paymentGatePassed) {
        return;
      }

      if (!paymentOrder?.order_id) {
        setPaymentResult({
          success: false,

          message:
            "Order ID is missing. Payment cannot be started.",
        });

        return;
      }

      if (!RAZORPAY_KEY_ID) {
        setPaymentResult({
          success: false,

          message:
            "Razorpay key is not configured. Add VITE_RAZORPAY_KEY_ID to frontend/.env.",
        });

        return;
      }

      if (paymentCompletedRef.current) {
        return;
      }

      const manualRetry =
        paymentOptions?.manualRetry === true;

      // If automatic checkout already created a Razorpay instance but
      // the browser blocked its first open() call, a real user click on
      // "Open Secure Checkout" should reopen THAT SAME instance.
      if (
        manualRetry &&
        razorpayInstanceRef.current
      ) {
        try {
          paymentInFlightRef.current = true;
          setPaymentLoading(true);
          setPaymentResult(null);
          razorpayInstanceRef.current.open();
          return;
        } catch (reopenError) {
          console.warn(
            "RAZORPAY REOPEN FAILED; CREATING A FRESH CHECKOUT:",
            reopenError
          );
          razorpayInstanceRef.current = null;
          paymentInFlightRef.current = false;
          setPaymentLoading(false);
        }
      }

      // A previous automatic attempt can leave the in-flight flag set
      // when the browser blocks the first checkout opening. A manual
      // button click is an explicit user gesture, so it is allowed to
      // retry safely. The stable idempotency key prevents duplicate
      // backend payment records.
      if (paymentInFlightRef.current && !manualRetry) {
        return;
      }

      if (manualRetry) {
        paymentInFlightRef.current = false;
      }

      paymentInFlightRef.current = true;

      setPaymentLoading(true);
      setPaymentResult(null);

      try {
        // -------------------------------------------------
        // CREATE PAYMENT
        // -------------------------------------------------
        // Stable idempotency key: retries cannot create a second
        // payment record for the same approved order.
        const paymentData =
          await createPayment(
            {
              order_id:
                paymentOrder.order_id,

              currency: "INR",
            },
            {
              idempotencyKey:
                `paypilot-order-${paymentOrder.order_id}`,
            }
          );

        if (
          !paymentData
            ?.razorpay_order_id
        ) {
          throw new Error(
            "Backend did not return a Razorpay order ID."
          );
        }

        // -------------------------------------------------
        // LOAD RAZORPAY
        // -------------------------------------------------

        await loadRazorpay();

        // -------------------------------------------------
        // CHECKOUT
        // -------------------------------------------------

        const options = {
          key:
            RAZORPAY_KEY_ID,

          amount:
            Math.round(
              Number(
                paymentData.amount
              ) * 100
            ),

          currency:
            paymentData.currency ||
            "INR",

          name:
            "PayPilot",

          description:
            paymentOrder.product_name
              ? `Order for ${paymentOrder.product_name}`
              : `PayPilot Order #${paymentOrder.order_id}`,

          order_id:
            paymentData
              .razorpay_order_id,

          handler:
            async (
              razorpayResponse
            ) => {
              // Razorpay checkout has completed. Keep the callback payload
              // so verification can be retried safely if the backend
              // temporarily rejects the verification request.
              pendingVerificationRef.current = {
                paymentData,
                razorpayResponse,
              };

              try {
                const verifyData =
                  await verifyCompletedPayment(
                    paymentData,
                    razorpayResponse
                  );

                pendingVerificationRef.current =
                  null;

                paymentCompletedRef.current =
                  true;

                paymentInFlightRef.current =
                  false;

                razorpayInstanceRef.current =
                  null;

                setPaymentResult({
                  success: true,

                  message:
                    "Payment completed and verified successfully. The order is now paid.",

                  payment:
                    verifyData,
                });
              } catch (
                verifyError
              ) {
                console.error(
                  "PAYMENT VERIFY ERROR:",
                  verifyError
                );

                // The buyer may already have paid. Never create another
                // payment/order here. Keep the callback for verification retry.
                paymentInFlightRef.current =
                  false;

                razorpayInstanceRef.current =
                  null;

                setPaymentResult({
                  success: false,

                  verificationFailed: true,

                  message:
                    getPaymentVerificationErrorMessage(
                      verifyError
                    ),
                });
              } finally {
                setPaymentLoading(
                  false
                );
              }
            },

          modal: {
            ondismiss() {
              paymentInFlightRef.current =
                false;

              razorpayInstanceRef.current =
                null;

              setPaymentLoading(
                false
              );

              setPaymentResult({
                success: false,

                cancelled: true,

                message:
                  "Payment checkout was cancelled. The order remains approved, so you can reopen secure checkout below.",
              });
            },
          },

          theme: {
            color:
              "#2563eb",
          },
        };

        const razorpay =
          new window.Razorpay(
            options
          );

        razorpayInstanceRef.current =
          razorpay;

        razorpay.on(
          "payment.failed",
          (response) => {
            paymentInFlightRef.current =
              false;

            razorpayInstanceRef.current =
              null;

            setPaymentLoading(
              false
            );

            setPaymentResult({
              success: false,

              message:
                response
                  ?.error
                  ?.description ||
                "Razorpay payment failed.",
            });
          }
        );

        razorpay.open();
      } catch (paymentError) {
        console.error(
          "PAYMENT START ERROR:",
          paymentError
        );

        paymentInFlightRef.current =
          false;

        razorpayInstanceRef.current =
          null;

        setPaymentLoading(false);

        setPaymentResult({
          success: false,

          message:
            paymentError?.message ||
            "Unable to start payment.",
        });
      }
    };

  // Retry ONLY backend verification for a Razorpay payment that has
  // already completed. It does not create a new payment.
  const handleRetryPaymentVerification = async () => {
    const pending =
      pendingVerificationRef.current;

    if (
      !pending?.paymentData ||
      !pending?.razorpayResponse
    ) {
      setPaymentResult({
        success: false,
        message:
          "There is no pending Razorpay payment verification to retry.",
      });
      return;
    }

    if (paymentCompletedRef.current) {
      return;
    }

    setPaymentLoading(true);
    setPaymentResult(null);

    try {
      const verifyData =
        await verifyCompletedPayment(
          pending.paymentData,
          pending.razorpayResponse
        );

      pendingVerificationRef.current =
        null;

      paymentCompletedRef.current =
        true;

      paymentInFlightRef.current =
        false;

      setPaymentResult({
        success: true,
        message:
          "Payment completed and verified successfully. The order is now paid.",
        payment: verifyData,
      });
    } catch (verifyError) {
      console.error(
        "PAYMENT VERIFY RETRY ERROR:",
        verifyError
      );

      paymentInFlightRef.current =
        false;

      setPaymentResult({
        success: false,
        verificationFailed: true,
        message:
          getPaymentVerificationErrorMessage(
            verifyError
          ),
      });
    } finally {
      setPaymentLoading(false);
    }
  };


  // =======================================================
  // STATUS UI
  // =======================================================

  let heading =
    "Order Decision";

  let label =
    status || "NOT CREATED";

  let headerClass =
    "border-slate-200 bg-slate-50";

  let iconClass =
    "bg-slate-500";

  let textClass =
    "text-slate-800";

  let HeaderIcon =
    Clock3;

  if (approved) {
    heading =
      "Order Approved";

    headerClass =
      "border-emerald-200 bg-emerald-50";

    iconClass =
      "bg-emerald-600";

    textClass =
      "text-emerald-900";

    HeaderIcon =
      CheckCircle2;
  } else if (manualReview) {
    heading =
      "Manual Review Required";

    headerClass =
      "border-amber-200 bg-amber-50";

    iconClass =
      "bg-amber-500";

    textClass =
      "text-amber-900";

    HeaderIcon =
      UserCheck;
  } else if (
    rejected ||
    blocked
  ) {
    heading =
      blocked
        ? "Order Blocked"
        : "Order Rejected";

    headerClass =
      "border-red-200 bg-red-50";

    iconClass =
      "bg-red-600";

    textClass =
      "text-red-900";

    HeaderIcon =
      XCircle;
  } else if (noOrder) {
    heading =
      "Order Not Created";

    label =
      "STOPPED";

    headerClass =
      "border-amber-200 bg-amber-50";

    iconClass =
      "bg-amber-500";

    textClass =
      "text-amber-900";

    HeaderIcon =
      AlertCircle;
  }

  return (
    <div className="space-y-4">
      <div
        className={`rounded-xl border p-4 ${headerClass}`}
      >
        <div className="flex items-start gap-3">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white ${iconClass}`}
          >
            <HeaderIcon
              size={20}
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p
                className={`text-sm font-bold ${textClass}`}
              >
                Agent Decision
              </p>

              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-bold text-white ${iconClass}`}
              >
                {label}
              </span>
            </div>

            <h3
              className={`mt-2 text-base font-bold ${textClass}`}
            >
              {heading}
            </h3>

            <p
              className={`mt-1 whitespace-pre-line text-sm leading-6 ${textClass}`}
            >
              {safeString(
                orderData.message,
                "PayPilot processed the request."
              )}
            </p>
          </div>
        </div>
      </div>

      <CommerceDetails
        data={orderData}
      />

      <Section
        title="Policy & Pricing"
        icon={DollarSign}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <DetailItem
            icon={DollarSign}
            label="Requested Discount"
            value={formatPercent(
              orderData
                .requested_discount_percent ??
              orderData.discount_percent
            )}
          />

          <DetailItem
            icon={DollarSign}
            label="Approved Discount"
            value={formatPercent(
              orderData
                .approved_discount_percent ??
              orderData.discount_percent
            )}
          />

          <DetailItem
            icon={CircleDollarSign}
            label="Original Amount"
            value={formatCurrency(
              orderData.original_amount
            )}
          />

          <DetailItem
            icon={CircleDollarSign}
            label="Final Amount"
            value={formatCurrency(
              orderData.final_amount
            )}
          />
        </div>
      </Section>

      <GovernanceDetails
        data={orderData}
      />

      {manualReview && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <UserCheck
              size={18}
              className="mt-0.5 shrink-0 text-amber-600"
            />

            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-amber-800">
                Human Review Required
              </p>

              <p className="mt-1 text-xs leading-5 text-amber-700">
                This order exceeded the automatic
                PayPilot payment/risk policy. An
                authorized human reviewer must approve
                or reject it before payment can continue.
              </p>

              {orderData.risk_reason && (
                <div className="mt-3 rounded-lg border border-amber-200 bg-white p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-amber-700">
                    Risk Reason
                  </p>

                  <p className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">
                    {safeString(
                      orderData.risk_reason
                    )}
                  </p>
                </div>
              )}

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() =>
                    handleManualReviewDecision(
                      "APPROVE"
                    )
                  }
                  disabled={
                    reviewLoading
                  }
                  className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {reviewLoading ? (
                    <Loader2
                      size={17}
                      className="animate-spin"
                    />
                  ) : (
                    <CheckCircle2
                      size={17}
                    />
                  )}

                  {reviewLoading
                    ? "Processing..."
                    : "Approve Order"}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    handleManualReviewDecision(
                      "REJECT"
                    )
                  }
                  disabled={
                    reviewLoading
                  }
                  className="flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-4 py-3 text-sm font-bold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {reviewLoading ? (
                    <Loader2
                      size={17}
                      className="animate-spin"
                    />
                  ) : (
                    <XCircle
                      size={17}
                    />
                  )}

                  {reviewLoading
                    ? "Processing..."
                    : "Reject Order"}
                </button>
              </div>

              <p className="mt-3 text-center text-[11px] leading-5 text-amber-700">
                This is the human authorization step for a
                manual-review exception. After approval,
                PayPilot automatically continues to payment checkout.
              </p>
            </div>
          </div>
        </div>
      )}

      {reviewError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0 text-red-600"
            />

            <div>
              <p className="text-sm font-bold text-red-700">
                Manual Review Failed
              </p>

              <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-red-600">
                {reviewError}
              </p>
            </div>
          </div>
        </div>
      )}

      {reviewInfo && (
        <div
          className={`rounded-xl border p-4 ${
            reviewInfo.type ===
            "APPROVED"
              ? "border-emerald-200 bg-emerald-50"
              : "border-red-200 bg-red-50"
          }`}
        >
          <div className="flex items-start gap-3">
            {reviewInfo.type ===
            "APPROVED" ? (
              <CheckCircle2
                size={18}
                className="mt-0.5 shrink-0 text-emerald-600"
              />
            ) : (
              <XCircle
                size={18}
                className="mt-0.5 shrink-0 text-red-600"
              />
            )}

            <div>
              <p className="text-sm font-bold text-slate-800">
                {reviewInfo.type ===
                "APPROVED"
                  ? "Human Review Approved"
                  : "Human Review Rejected"}
              </p>

              <p className="mt-1 text-xs leading-5 text-slate-600">
                {reviewInfo.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {approved && (
        <PaymentConfirmation
          data={orderData}
          onPay={() =>
            handleConfirmPayment(
              null,
              { manualRetry: true }
            )
          }
          paymentLoading={
            paymentLoading
          }
        />
      )}

      {(
        blocked ||
        rejected ||
        noOrder
      ) && !approved && (
        <div className="flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-xs font-medium leading-5 text-red-700">
          <ShieldAlert
            size={16}
            className="mt-0.5 shrink-0"
          />

          <span>
            Payment execution stopped. PayPilot
            did not authorize this request to
            proceed to Razorpay.
          </span>
        </div>
      )}

      {paymentResult && (
        <div
          className={`rounded-xl border p-4 ${
            paymentResult.success
              ? "border-emerald-200 bg-emerald-50"
              : paymentResult.cancelled
                ? "border-amber-200 bg-amber-50"
                : "border-red-200 bg-red-50"
          }`}
        >
          <div className="flex items-start gap-3">
            {paymentResult.success ? (
              <CheckCircle2
                size={19}
                className="mt-0.5 shrink-0 text-emerald-600"
              />
            ) : (
              <AlertCircle
                size={19}
                className={`mt-0.5 shrink-0 ${
                  paymentResult.cancelled
                    ? "text-amber-600"
                    : "text-red-600"
                }`}
              />
            )}

            <div>
              <p className="text-sm font-bold text-slate-800">
                {paymentResult.success
                  ? "Payment Verified"
                  : paymentResult.cancelled
                    ? "Checkout Cancelled"
                    : "Payment Not Completed"}
              </p>

              <p className="mt-1 whitespace-pre-line text-xs leading-5 text-slate-600">
                {safeString(
                  paymentResult.message
                )}
              </p>

              {paymentResult.verificationFailed &&
                !paymentResult.success && (
                  <button
                    type="button"
                    onClick={
                      handleRetryPaymentVerification
                    }
                    disabled={paymentLoading}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {paymentLoading ? (
                      <>
                        <Loader2
                          size={14}
                          className="animate-spin"
                        />
                        Verifying Payment...
                      </>
                    ) : (
                      <>
                        <ShieldCheck
                          size={14}
                        />
                        Retry Payment Verification
                      </>
                    )}
                  </button>
                )}

              {paymentResult.success &&
                paymentResult.payment
                  ?.razorpay_payment_id && (
                  <p className="mt-2 text-[11px] font-medium text-emerald-700">
                    Razorpay Payment ID:{" "}
                    {paymentResult.payment
                      .razorpay_payment_id}
                  </p>
                )}
            </div>
          </div>
        </div>
      )}

      <Phase8CNotice />
    </div>
  );
}

// =========================================================
// RESPONSE ROUTER
// =========================================================

function AgentResponse({
  data,
  onRecommend,
  recommendationLoadingId,
  recommendationError,
  growthRecommendation,
  onChooseRecommendation,
  onChooseProduct,
}) {
  if (
    !data ||
    typeof data !== "object"
  ) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        {safeString(
          data,
          "No response."
        )}
      </div>
    );
  }

  const intent =
    normalizeStatus(
      data.intent
    );

  switch (intent) {
    case "CATALOG_QUERY":
      return (
        <CatalogResponse
          data={data}
          onRecommend={onRecommend}
          recommendationLoadingId={recommendationLoadingId}
          recommendationError={recommendationError}
          growthRecommendation={growthRecommendation}
          onChooseRecommendation={onChooseRecommendation}
          onChooseProduct={onChooseProduct}
        />
      );

    case "CREATE_ORDER":
      return (
        <OrderResponse
          data={data}
        />
      );

    case "GENERAL_QUERY":
      return (
        <GeneralQueryResponse
          data={data}
        />
      );

    default:
      return (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-semibold text-slate-800">
            Agent Response
          </p>

          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
            {safeString(
              data.message,
              "The agent returned a response."
            )}
          </p>
        </div>
      );
  }
}


// =========================================================
// MAIN AGENT PAGE
// =========================================================

export default function Agent() {
  const [
    message,
    setMessage,
  ] = useState("");

  const [
    messages,
    setMessages,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const messagesEndRef =
    useRef(null);

  const [catalogProducts, setCatalogProducts] =
    useState([]);

  const [catalogLoading, setCatalogLoading] =
    useState(false);

  const [catalogError, setCatalogError] =
    useState("");


  const [selectedMerchantId, setSelectedMerchantId] =
    useState(MERCHANT_ID);

  const [recommendationLoadingId, setRecommendationLoadingId] =
    useState(null);

  const [recommendationError, setRecommendationError] =
    useState("");

  const [growthRecommendation, setGrowthRecommendation] =
    useState(null);


  // =======================================================
  // AUTO SCROLL
  // =======================================================

  useEffect(() => {
    messagesEndRef
      .current
      ?.scrollIntoView({
        behavior: "smooth",
      });
  }, [
    messages,
    loading,
    error,
  ]);


  // =======================================================
  // PUBLIC CATALOG
  // =======================================================
  //
  // Do NOT automatically call the catalog endpoint on page load.
  // A buyer opening the Agent page should not see a timeout just
  // because the marketplace endpoint is temporarily unavailable.
  //
  // The catalog is fetched:
  //   1. when the buyer asks to show/browse available products
  //   2. when the buyer clicks the storefront retry action
  //   3. when AI recommendations need product lookup
  // =======================================================

  const loadPublicCatalog = async () => {
    setCatalogLoading(true);
    setCatalogError("");

    try {
      const products = await fetchPublicCatalog();

      setCatalogProducts(products);
      setCatalogError("");

      return products;
    } catch (error) {
      console.warn(
        "Unable to load public buyer catalog:",
        error
      );

      setCatalogError(
        safeString(
          error?.message,
          "Unable to load products from all merchants."
        )
      );

      throw error;
    } finally {
      setCatalogLoading(false);
    }
  };

  // =======================================================
  // GENERATE AI GROWTH RECOMMENDATIONS
  // =======================================================

  const handleRecommendProduct = async (
    productName
  ) => {
    const normalizedName = String(
      productName || ""
    )
      .trim()
      .toLowerCase();

    if (!normalizedName) {
      return;
    }

    setRecommendationError("");
    setGrowthRecommendation(null);
    setRecommendationLoadingId(productName);

    try {
      let products = catalogProducts;

      if (!products.length) {
        products = await loadPublicCatalog();
      }

      const matchedProduct = products.find(
        (product) =>
          String(product?.name || "")
            .trim()
            .toLowerCase() === normalizedName
      );

      if (!matchedProduct?.id) {
        throw new Error(
          `Product ID could not be resolved for ${productName}.`
        );
      }

      // Buyer recommendations must use the public recommendation
      // endpoint directly. Do NOT call api.js getGrowthRecommendations
      // here because that helper first calls GET /products/, which is
      // merchant-authenticated and causes a 401 for public buyers.
      const recommendationResponse = await fetch(
        `${API_URL}/agent/recommendations`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            product_id: Number(matchedProduct.id),
            merchant_id: Number(matchedProduct.merchant_id),
          }),
        }
      );

      let recommendationPayload = null;
      try {
        recommendationPayload = await recommendationResponse.json();
      } catch {
        recommendationPayload = null;
      }

      if (!recommendationResponse.ok) {
        throw new Error(
          recommendationPayload?.detail ||
            recommendationPayload?.message ||
            `Recommendation request failed (${recommendationResponse.status}).`
        );
      }

      const result = recommendationPayload;

      if (!result || typeof result !== "object") {
        throw new Error(
          "The growth recommendation service returned an invalid response."
        );
      }

      setGrowthRecommendation(result);
    } catch (error) {
      console.error(
        "AI GROWTH RECOMMENDATION ERROR:",
        error
      );

      setRecommendationError(
        safeString(
          getSharedApiErrorMessage(error),
          "Unable to generate AI growth recommendations."
        )
      );
    } finally {
      setRecommendationLoadingId(null);
    }
  };

  // =======================================================
  // CHOOSE RECOMMENDATION
  // =======================================================
  //
  // IMPORTANT:
  // Selecting a recommendation does NOT create an order.
  // It only prepares a natural-language purchase request.
  // The user must still press Send, after which the existing
  // policy -> risk -> merchant approval -> payment
  // workflow continues automatically.
  // =======================================================

  const handleChooseRecommendation = (
    product
  ) => {
    if (!product?.name) {
      return;
    }

    setMessage(
      `I want to buy 1 ${product.name}`
    );

    setRecommendationError("");
  };

  // =======================================================
  // BUY PRODUCT FROM MARKETPLACE
  // =======================================================

  const handleChooseProduct = (product) => {
    if (!product?.name) {
      return;
    }

    setMessage(`I want to buy 1 ${product.name}`);
    setRecommendationError("");

    // Keep the merchant context in the next request by storing it
    // on the component. The actual order is still authorized by
    // the backend policy/risk/payment gates.
    setSelectedMerchantId(Number(product.merchant_id) || MERCHANT_ID);
  };

  // =======================================================
  // SEND MESSAGE
  // =======================================================

  const sendMessage =
    async (e) => {
      e?.preventDefault();

      const trimmed =
        message.trim();

      if (
        !trimmed ||
        loading
      ) {
        return;
      }

      setError("");

      setMessages(
        (previous) => [
          ...previous,
          {
            role: "user",

            content:
              trimmed,
          },
        ]
      );

      setMessage("");
      setLoading(true);

      const globalCatalogRequest =
        isGlobalCatalogRequest(trimmed);

      // -------------------------------------------------
      // GLOBAL BUYER CATALOG REQUEST
      // -------------------------------------------------
      // Do NOT call /agent/chat for this request.
      // The buyer is only asking to browse products, so
      // sending it through the order agent can unnecessarily
      // invoke policy/risk/order processing and cause a long
      // timeout. The public catalog endpoint is sufficient.
      // -------------------------------------------------
      if (globalCatalogRequest) {
        try {
          let products = catalogProducts;

          if (!products.length) {
            products = await loadPublicCatalog();
          }

          if (!products.length) {
            throw new Error(
              "The marketplace catalog is reachable, but no active, in-stock products are available across the marketplace."
            );
          }

          setMessages((previous) => [
            ...previous,
            {
              role: "agent",
              content: {
                intent: "CATALOG_QUERY",
                catalog_scope: "ALL_MERCHANTS",
                products,
                total_products: products.length,
                message: `Showing ${products.length} available products across the PayPilot marketplace (all active merchants).`,
                manual_review_required: false,
              },
            },
          ]);

          setCatalogProducts(products);
          setCatalogError("");
        } catch (catalogRequestError) {
          console.error(
            "PUBLIC MARKETPLACE CATALOG ERROR:",
            catalogRequestError
          );

          setMessages((previous) => [
            ...previous,
            {
              role: "agent",
              content: {
                intent: "GENERAL_QUERY",
                message:
                  `I could not load the marketplace catalog right now. ${safeString(
                    catalogRequestError?.message,
                    "Please make sure the public catalog API is available."
                  )}`,
              },
            },
          ]);
        } finally {
          setLoading(false);
        }

        return;
      }

      // Resolve a product against the GLOBAL buyer catalog before
      // sending a purchase request to /agent/chat. This prevents a
      // product owned by another merchant from being accidentally
      // routed to the currently logged-in merchant.
      let buyerCatalog = catalogProducts;

      if (!buyerCatalog.length) {
        try {
          buyerCatalog = await loadPublicCatalog();
        } catch (catalogError) {
          console.warn(
            "GLOBAL CATALOG LOOKUP BEFORE PURCHASE FAILED:",
            catalogError
          );
        }
      }

      const matchedBuyerProduct =
        findUniqueProductFromMessage(
          trimmed,
          buyerCatalog
        );

      const requestMerchantId =
        Number(
          matchedBuyerProduct?.merchant_id ||
            selectedMerchantId ||
            MERCHANT_ID
        );

      try {
        console.log(
          "========================================"
        );

        console.log(
          "PAYPILOT AGENT REQUEST"
        );

        console.log({
          merchant_id:
            requestMerchantId,

          message:
            trimmed,
        });

        console.log(
          "========================================"
        );

        // -------------------------------------------------
        // Uses centralized api.js.
        //
        // api.js guarantees:
        //
        // {
        //   merchant_id: 1,
        //   message: "..."
        // }
        //
        // -------------------------------------------------

        const data =
          await sendAgentChat({
            merchant_id:
              requestMerchantId,

            message:
              trimmed,
          });

        console.log(
          "========================================"
        );

        console.log(
          "PAYPILOT AGENT RESPONSE"
        );

        console.log(data);

        console.log(
          "========================================"
        );

        if (
          !data ||
          typeof data !== "object"
        ) {
          throw new Error(
            "The PayPilot backend returned an invalid agent response."
          );
        }

        const responseData = data;

        setMessages(
          (previous) => [
            ...previous,
            {
              role:
                "agent",

              content:
                responseData,
            },
          ]
        );

      } catch (requestError) {
        console.error(
          "========================================"
        );

        console.error(
          "PAYPILOT AGENT REQUEST ERROR"
        );

        console.error(
          requestError
        );

        console.error(
          "BACKEND RESPONSE:",
          requestError
            ?.response
            ?.data
        );

        console.error(
          "========================================"
        );

        // -------------------------------------------------
        // First try to expose the true nested backend error.
        // -------------------------------------------------

        const backendData =
          requestError
            ?.response
            ?.data;

        let messageText =
          "";

        if (backendData) {
          messageText =
            getApiErrorMessage(
              backendData,
              ""
            );
        }

        // -------------------------------------------------
        // Fallback to shared axios formatter.
        // -------------------------------------------------

        if (!messageText) {
          messageText =
            getSharedApiErrorMessage(
              requestError
            );
        }

        // Absolutely ensure React gets a STRING.
        setError(
          safeString(
            messageText,
            "Unable to communicate with the AI agent."
          )
        );
      } finally {
        setLoading(false);
      }
    };


  // =======================================================
  // QUICK QUESTIONS
  // =======================================================

  const quickQuestions = [
    "Show me all available products from all merchants",

    "Tell me about Mechanical Keyboard",

    "Show me AI growth recommendations for Laptop",

    "I want to buy 1 Mechanical Keyboard",

    "I want to buy 2 Premium AI Laptops with 10% discount",
  ];


  // =======================================================
  // UI
  // =======================================================

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-[#eef2ff] via-[#f8f7ff] to-[#ecfeff] px-3 py-4 text-slate-900 sm:px-6 sm:py-6 lg:px-8">
      {/* Soft ambient background — UI only */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-blue-400/20 blur-3xl" />
        <div className="absolute right-[-90px] top-24 h-80 w-80 rounded-full bg-violet-400/20 blur-3xl" />
        <div className="absolute bottom-[-120px] left-1/3 h-96 w-96 rounded-full bg-cyan-300/15 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.035)_1px,transparent_1px)] bg-[size:32px_32px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-[1380px]">

        {/* =================================================
            AGENT HEADER
        ================================================= */}
        <div className="mb-5 overflow-hidden rounded-3xl border border-slate-200/80 bg-white shadow-[0_12px_40px_rgba(15,23,42,0.06)]">
          <div className="relative overflow-hidden px-5 py-5 sm:px-7 sm:py-6">
            <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-blue-100/50 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-24 left-1/3 h-48 w-48 rounded-full bg-violet-100/40 blur-3xl" />

            <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-start gap-4">
                <div className="relative flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-xl shadow-slate-900/15">
                  <Bot size={28} />
                  <span className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full border-[3px] border-white bg-emerald-500" />
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h1 className="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
                      PayPilot AI
                    </h1>

                    <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-[10px] font-extrabold tracking-wide text-violet-700">
                      AGENTIC COMMERCE
                    </span>

                    <span className="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                      ONLINE
                    </span>
                  </div>

                  <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-500">
                    Autonomous commerce orchestration across catalog, policy,
                    risk and payment gates — with a human-controlled money boundary.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap lg:justify-end">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <p className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-slate-400">
                    Agent
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <Activity size={13} className="text-blue-500" />
                    Orchestrating
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <p className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-slate-400">
                    Governance
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <LockKeyhole size={13} className="text-amber-500" />
                    Human gated
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* AGENT WORKFLOW */}
          <div className="border-t border-indigo-100/70 bg-gradient-to-r from-indigo-50/80 via-white/70 to-cyan-50/70 px-5 py-4 sm:px-7">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-extrabold uppercase tracking-[0.16em] text-slate-400">
                  Agent workflow
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  Every transaction passes through bounded decision gates.
                </p>
              </div>

              <span className="hidden items-center gap-1.5 text-[10px] font-bold text-slate-400 sm:flex">
                <ShieldCheck size={13} />
                Policy-controlled
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              {[
                ["01", "Intent", Bot],
                ["02", "Catalog", Store],
                ["03", "Policy", CheckCircle2],
                ["04", "Risk", ShieldCheck],
                ["05", "Human Gate", UserCheck],
                ["06", "Payment", LockKeyhole],
              ].map(([step, label, Icon], index) => (
                <div key={label} className="relative flex items-center gap-2.5 rounded-xl border border-indigo-100/80 bg-white/90 px-3 py-2.5 shadow-sm backdrop-blur transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
                    <Icon size={13} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[9px] font-bold text-slate-400">{step}</p>
                    <p className="truncate text-[11px] font-bold text-slate-700">{label}</p>
                  </div>
                  {index < 5 && (
                    <ArrowRight size={12} className="absolute -right-2.5 z-10 hidden text-slate-300 lg:block" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* =================================================
            GOVERNANCE
        ================================================= */}
        <div className="mb-5 overflow-hidden rounded-2xl border border-amber-200/80 bg-gradient-to-r from-amber-50 to-orange-50 shadow-sm">
          <div className="flex items-start gap-3 px-4 py-3.5 sm:px-5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-200 bg-white text-amber-600 shadow-sm">
              <ShieldCheck size={18} />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-extrabold text-amber-900">
                  Human confirmation required
                </p>
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[9px] font-extrabold uppercase tracking-wide text-amber-700">
                  Safety Boundary
                </span>
              </div>

              <p className="mt-1 text-xs leading-5 text-amber-800/80">
                PayPilot can evaluate orders and continue approved workflows, but
                the AI cannot authorize money movement. Razorpay opens only after
                the required human-controlled gate.
              </p>
            </div>
          </div>
        </div>

        {/* =================================================
            CHAT PANEL
        ================================================= */}
        <div className="overflow-hidden rounded-3xl border border-white/70 bg-white/90 shadow-[0_24px_70px_rgba(79,70,229,0.14)] backdrop-blur-xl">

          {/* HEADER */}
          <div className="flex flex-col gap-3 border-b border-indigo-100 bg-gradient-to-r from-white via-indigo-50/50 to-cyan-50/50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div className="flex items-center gap-3">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-white shadow-md">
                <Bot size={19} />
                <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-500" />
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-extrabold text-slate-900">
                    PayPilot Commerce Copilot
                  </p>
                  <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[9px] font-extrabold text-violet-700">
                    AGENT
                  </span>
                </div>

                <p className="mt-0.5 text-[11px] text-slate-400">
                  Marketplace intelligence · policy reasoning · risk controls · secure checkout
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-[10px] font-bold text-slate-500 sm:inline-flex">
                Merchant #{MERCHANT_ID}
              </span>

              <span className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[10px] font-extrabold text-emerald-700">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                Ready
              </span>
            </div>
          </div>

          {/* =================================================
              MESSAGES
          ================================================= */}
          <div className="min-h-[560px] max-h-[760px] space-y-7 overflow-y-auto bg-[radial-gradient(circle_at_15%_10%,_rgba(99,102,241,0.14),_transparent_30%),radial-gradient(circle_at_85%_20%,_rgba(6,182,212,0.10),_transparent_28%),linear-gradient(135deg,#f8faff,#f5f3ff_50%,#f0fdff)] p-3 sm:p-6">

            {/* EMPTY */}
            {messages.length === 0 && (
              <div className="flex min-h-[500px] items-center justify-center">
                <div className="w-full max-w-3xl text-center">
                  <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl border border-indigo-100 bg-gradient-to-br from-indigo-600 via-violet-600 to-cyan-500 text-white shadow-[0_16px_40px_rgba(79,70,229,0.25)]">
                    <div className="relative">
                      <Bot size={36} />
                      <span className="absolute -bottom-1 -right-2 h-3.5 w-3.5 rounded-full border-[3px] border-white bg-emerald-500" />
                    </div>
                  </div>

                  <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-blue-600">
                    AI Commerce Orchestrator
                  </p>

                  <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
                    What can I execute for you?
                  </h2>

                  <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-500">
                    Ask about products, inventory, recommendations, discounts,
                    or start a purchase workflow. PayPilot will route the request
                    through the appropriate agentic gates.
                  </p>

                  <div className="mt-7 grid gap-2 text-left sm:grid-cols-2">
                    {quickQuestions.map((question, index) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => setMessage(question)}
                        className="group flex items-center gap-3 rounded-2xl border border-indigo-100 bg-white/90 p-3.5 text-left shadow-sm backdrop-blur transition hover:-translate-y-1 hover:border-indigo-300 hover:bg-white hover:shadow-lg"
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-[10px] font-extrabold text-blue-600 transition group-hover:bg-blue-600 group-hover:text-white">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="min-w-0 flex-1 text-xs font-semibold leading-5 text-slate-600 group-hover:text-slate-900">
                          {question}
                        </span>
                        <ArrowRight size={14} className="shrink-0 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-blue-500" />
                      </button>
                    ))}
                  </div>

                  <div className="mt-6 flex flex-wrap justify-center gap-x-4 gap-y-2 text-[10px] font-semibold text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 size={12} className="text-emerald-500" />
                      Policy controlled
                    </span>
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck size={12} className="text-blue-500" />
                      Risk evaluated
                    </span>
                    <span className="flex items-center gap-1.5">
                      <LockKeyhole size={12} className="text-amber-500" />
                      Human gated
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* MESSAGE LIST */}
            {messages.map((item, index) => {
              const isUser = item.role === "user";

              return (
                <div
                  key={index}
                  className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                >
                  {!isUser && (
                    <div className="relative mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white shadow-md">
                      <Bot size={17} />
                      <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-50 bg-emerald-500" />
                    </div>
                  )}

                  <div className={isUser ? "max-w-[88%] sm:max-w-[75%]" : "w-full max-w-[980px]"}>
                    {isUser ? (
                      <div className="flex items-end justify-end gap-2.5">
                        <div>
                          <p className="mb-1.5 mr-1 text-right text-[9px] font-bold uppercase tracking-wider text-slate-400">
                            You
                          </p>
                          <div className="rounded-2xl rounded-br-md bg-slate-950 px-4 py-3.5 text-white shadow-lg shadow-slate-900/10">
                            <p className="whitespace-pre-line text-sm leading-6">
                              {safeString(item.content)}
                            </p>
                          </div>
                        </div>

                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm">
                          <User size={15} />
                        </div>
                      </div>
                    ) : (
                      <div className="overflow-hidden rounded-2xl rounded-tl-md border border-slate-200 bg-white shadow-[0_5px_20px_rgba(15,23,42,0.05)]">
                        <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50/80 px-4 py-2.5">
                          <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          <span className="text-[9px] font-extrabold uppercase tracking-[0.16em] text-slate-400">
                            PayPilot Agent Response
                          </span>
                          <span className="ml-auto text-[9px] font-semibold text-slate-300">
                            Decision engine
                          </span>
                        </div>

                        <div className="p-4 sm:p-5">
                          <AgentResponse
                            data={item.content}
                            onRecommend={handleRecommendProduct}
                            recommendationLoadingId={recommendationLoadingId}
                            recommendationError={recommendationError}
                            growthRecommendation={growthRecommendation}
                            onChooseRecommendation={handleChooseRecommendation}
                            onChooseProduct={handleChooseProduct}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* LOADING */}
            {loading && (
              <div className="flex items-start gap-3">
                <div className="relative mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white shadow-md">
                  <Bot size={17} />
                  <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-slate-50 bg-blue-500" />
                </div>

                <div className="w-full max-w-[680px] overflow-hidden rounded-2xl rounded-tl-md border border-slate-200 bg-white shadow-sm">
                  <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50/80 px-4 py-3">
                    <Loader2 size={16} className="animate-spin text-blue-600" />
                    <div>
                      <p className="text-xs font-bold text-slate-700">
                        Agent is evaluating the request
                      </p>
                      <p className="text-[10px] text-slate-400">
                        Routing intent → policy → risk → authorization gates
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-4">
                    {["Intent", "Policy", "Risk", "Gate"].map((stage, index) => (
                      <div key={stage} className="flex items-center gap-2 rounded-xl bg-slate-50 px-3 py-2">
                        <span className={`h-1.5 w-1.5 rounded-full ${index === 0 ? "animate-pulse bg-blue-500" : "bg-slate-200"}`} />
                        <span className="text-[10px] font-bold text-slate-400">{stage}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ERROR */}
          {error && (
            <div className="border-t border-red-100 bg-red-50/80 px-4 py-3.5 sm:px-6">
              <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white text-red-500 shadow-sm">
                  <AlertCircle size={17} />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-extrabold uppercase tracking-wide text-red-700">
                    Agent request failed
                  </p>
                  <p className="mt-1 whitespace-pre-wrap break-words text-xs leading-5 text-red-600">
                    {safeString(error, "Unable to communicate with PayPilot.")}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* INPUT */}
          <form onSubmit={sendMessage} className="border-t border-indigo-100 bg-gradient-to-r from-white via-indigo-50/30 to-cyan-50/30 p-3 sm:p-4">
            <div className="rounded-2xl border border-indigo-100 bg-white/90 p-2 shadow-[0_8px_25px_rgba(79,70,229,0.08)] backdrop-blur">
              <div className="flex items-center gap-2">
                <div className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white text-slate-500 shadow-sm sm:flex">
                  <Bot size={17} />
                </div>

                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  disabled={loading}
                  placeholder="Ask PayPilot to browse, recommend, or start a purchase..."
                  className="h-11 min-w-0 flex-1 rounded-xl border-0 bg-transparent px-2 text-sm text-slate-700 outline-none placeholder:text-slate-400 focus:ring-0 disabled:cursor-not-allowed disabled:opacity-60"
                />

                <button
                  type="submit"
                  disabled={loading || !message.trim()}
                  className="flex h-11 shrink-0 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white shadow-lg shadow-slate-900/10 transition hover:-translate-y-0.5 hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:translate-y-0"
                >
                  {loading ? (
                    <Loader2 size={17} className="animate-spin" />
                  ) : (
                    <Send size={17} />
                  )}
                  <span className="hidden sm:inline">
                    {loading ? "Thinking" : "Send"}
                  </span>
                </button>
              </div>
            </div>

            <div className="mt-2.5 flex flex-col gap-1 px-1 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
                <LockKeyhole size={11} />
                Agent decision → Policy/Risk Gate → Human Confirmation → Razorpay → Verification
              </p>

              <p className="text-[10px] font-semibold text-slate-400">
                Merchant #{MERCHANT_ID}
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}