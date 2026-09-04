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
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center gap-2">
        <Icon
          size={15}
          className="text-slate-400"
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
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
          <Icon size={15} />
        </div>

        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
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
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-[1200px]">

        {/* =================================================
            PAGE HEADER
        ================================================= */}

        <div className="mb-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Bot size={25} />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                  AI Commerce Agent
                </h1>

                <span className="rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-bold text-blue-600 sm:text-xs">
                  PHASE 8C
                </span>
              </div>

              <p className="mt-1 text-sm text-slate-500">
                Agentic commerce decisions with
                policy gates, risk controls, and
                human-authorized payments.
              </p>
            </div>
          </div>
        </div>


        {/* =================================================
            GOVERNANCE
        ================================================= */}

        <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <ShieldCheck
            size={19}
            className="mt-0.5 shrink-0 text-amber-600"
          />

          <div>
            <p className="text-sm font-semibold text-amber-800">
              Human confirmation required
            </p>

            <p className="mt-1 text-xs leading-5 text-amber-700">
              PayPilot may evaluate and approve
              an order according to merchant
              policy, but the AI cannot authorize
              money movement. Razorpay opens only
              after explicit human confirmation.
            </p>
          </div>
        </div>


        {/* =================================================
            CHAT PANEL
        ================================================= */}

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          {/* HEADER */}

          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <Bot size={18} />
              </div>

              <div>
                <p className="text-sm font-bold text-slate-800">
                  PayPilot Commerce Copilot
                </p>

                <p className="text-xs text-slate-400">
                  AI commerce • marketplace catalog • policy-gated checkout
                </p>
              </div>
            </div>

            <span className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-600">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />

              Ready
            </span>
          </div>


          {/* =================================================
              MESSAGES
          ================================================= */}

          <div className="min-h-[520px] max-h-[720px] space-y-6 overflow-y-auto bg-slate-50/60 p-4 sm:p-6">

            {/* EMPTY */}

            {messages.length === 0 && (
              <div className="flex min-h-[450px] items-center justify-center">
                <div className="max-w-lg text-center">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                    <Bot size={30} />
                  </div>

                  <h2 className="mt-5 text-xl font-bold text-slate-800">
                    Ask the Commerce Agent
                  </h2>

                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    Ask about products,
                    inventory, discounts, or ask
                    PayPilot to create an order
                    decision.
                  </p>

                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {quickQuestions.map(
                      (question) => (
                        <button
                          key={
                            question
                          }
                          type="button"
                          onClick={() =>
                            setMessage(
                              question
                            )
                          }
                          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
                        >
                          {question}
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>
            )}


            {/* MESSAGE LIST */}

            {messages.map(
              (item, index) => {
                const isUser =
                  item.role ===
                  "user";

                return (
                  <div
                    key={index}
                    className={`flex gap-3 ${
                      isUser
                        ? "justify-end"
                        : "justify-start"
                    }`}
                  >
                    {!isUser && (
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
                        <Bot size={18} />
                      </div>
                    )}

                    <div
                      className={
                        isUser
                          ? "max-w-[80%]"
                          : "w-full max-w-[900px]"
                      }
                    >
                      {isUser ? (
                        <div className="flex justify-end gap-3">
                          <div className="rounded-2xl rounded-br-md bg-blue-600 px-4 py-3 text-white shadow-sm">
                            <p className="whitespace-pre-line text-sm leading-6">
                              {safeString(
                                item.content
                              )}
                            </p>
                          </div>

                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-600">
                            <User
                              size={18}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="rounded-2xl rounded-tl-md border border-slate-200 bg-white p-5 shadow-sm">
                          <AgentResponse
                            data={
                              item.content
                            }
                            onRecommend={
                              handleRecommendProduct
                            }
                            recommendationLoadingId={
                              recommendationLoadingId
                            }
                            recommendationError={
                              recommendationError
                            }
                            growthRecommendation={
                              growthRecommendation
                            }
                            onChooseRecommendation={
                              handleChooseRecommendation
                            }
                            onChooseProduct={
                              handleChooseProduct
                            }
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            )}


            {/* LOADING */}

            {loading && (
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white">
                  <Bot size={18} />
                </div>

                <div className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  <Loader2
                    size={17}
                    className="animate-spin text-blue-600"
                  />

                  <span className="text-sm text-slate-500">
                    Agent is evaluating the request...
                  </span>
                </div>
              </div>
            )}

            <div
              ref={
                messagesEndRef
              }
            />
          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (
            <div className="border-t border-red-100 bg-red-50 px-5 py-4 sm:px-6">
              <div className="flex items-start gap-3">
                <AlertCircle
                  size={18}
                  className="mt-0.5 shrink-0 text-red-500"
                />

                <div>
                  <p className="text-sm font-bold text-red-700">
                    Agent Request Failed
                  </p>

                  <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-5 text-red-600">
                    {safeString(
                      error,
                      "Unable to communicate with PayPilot."
                    )}
                  </p>
                </div>
              </div>
            </div>
          )}


          {/* =================================================
              INPUT
          ================================================= */}

          <form
            onSubmit={
              sendMessage
            }
            className="border-t border-slate-200 bg-white p-4"
          >
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={message}
                onChange={(e) =>
                  setMessage(
                    e.target.value
                  )
                }
                disabled={loading}
                placeholder="Example: I want to buy 1 Mechanical Keyboard"
                className="h-12 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-700 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
              />

              <button
                type="submit"
                disabled={
                  loading ||
                  !message.trim()
                }
                className="flex h-12 items-center gap-2 rounded-xl bg-blue-600 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <Loader2
                    size={18}
                    className="animate-spin"
                  />
                ) : (
                  <Send size={18} />
                )}

                <span className="hidden sm:inline">
                  Send
                </span>
              </button>
            </div>

            <div className="mt-2 flex items-center justify-between px-1">
              <p className="text-[11px] text-slate-400">
                Agent decision → Policy/Risk Gate
                → Human Confirmation → Razorpay
                → Backend Verification
              </p>

              <p className="hidden text-[11px] text-slate-400 sm:block">
                Merchant ID{" "}
                {MERCHANT_ID}
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}