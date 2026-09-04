import { useEffect, useMemo, useState } from "react";

import {
  Package,
  Plus,
  Search,
  Edit3,
  Trash2,
  X,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Boxes,
  DollarSign,
  Minus,
} from "lucide-react";

import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
  updateProductStock,
  updateProductActiveStatus,
} from "../services/api";

// =========================================================
// PRODUCTS PAGE
// =========================================================

function Products() {
  const [products, setProducts] = useState([]);

  const [loading, setLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");

  const [search, setSearch] = useState("");

  const [showModal, setShowModal] = useState(false);

  const [editingProduct, setEditingProduct] = useState(null);

  const [showStockModal, setShowStockModal] = useState(false);

  const [stockProduct, setStockProduct] = useState(null);

  const [stockValue, setStockValue] = useState("");

  const [stockMode, setStockMode] = useState("SET");

  // =========================================================
  // LOAD PRODUCTS
  // =========================================================

  const loadProducts = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getProducts();

      setProducts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Products load error:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to load products."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  // =========================================================
  // REAL-TIME PRODUCT EVENTS
  //
  // App.jsx owns the SINGLE SSE connection.
  // Products.jsx only listens to the custom window events.
  // =========================================================

  useEffect(() => {
    // -------------------------------------------------------
    // PRODUCT CREATED
    // -------------------------------------------------------

    const handleProductCreated = (event) => {
      try {
        const product = event.detail;

        if (!product) {
          return;
        }

        console.log(
          "REAL-TIME PRODUCT CREATED:",
          product
        );

        setProducts((current) => {
          const alreadyExists = current.some(
            (item) => item.id === product.id
          );

          if (alreadyExists) {
            return current;
          }

          return [product, ...current];
        });

        setSuccess(
          `Product "${product.name || "Product"}" was created.`
        );
      } catch (err) {
        console.error(
          "Product created event error:",
          err
        );
      }
    };

    // -------------------------------------------------------
    // PRODUCT UPDATED
    // -------------------------------------------------------

    const handleProductUpdated = (event) => {
      try {
        const product = event.detail;

        if (!product) {
          return;
        }

        console.log(
          "REAL-TIME PRODUCT UPDATED:",
          product
        );

        setProducts((current) => {
          const exists = current.some(
            (item) => item.id === product.id
          );

          if (!exists) {
            return [product, ...current];
          }

          return current.map((item) =>
            item.id === product.id
              ? {
                  ...item,
                  ...product,
                }
              : item
          );
        });

        setEditingProduct((current) => {
          if (
            current &&
            current.id === product.id
          ) {
            return {
              ...current,
              ...product,
            };
          }

          return current;
        });

        setStockProduct((current) => {
          if (
            current &&
            current.id === product.id
          ) {
            return {
              ...current,
              ...product,
            };
          }

          return current;
        });
      } catch (err) {
        console.error(
          "Product updated event error:",
          err
        );
      }
    };

    // -------------------------------------------------------
    // PRODUCT DELETED
    // -------------------------------------------------------

    const handleProductDeleted = (event) => {
      try {
        const data = event.detail;

        if (!data) {
          return;
        }

        console.log(
          "REAL-TIME PRODUCT DELETED:",
          data
        );

        const productId =
          typeof data === "object"
            ? data.id ??
              data.product_id
            : data;

        if (
          productId === undefined ||
          productId === null
        ) {
          return;
        }

        setProducts((current) =>
          current.filter(
            (product) =>
              String(product.id) !==
              String(productId)
          )
        );

        setStockProduct((current) => {
          if (
            current &&
            String(current.id) ===
              String(productId)
          ) {
            return null;
          }

          return current;
        });
      } catch (err) {
        console.error(
          "Product deleted event error:",
          err
        );
      }
    };

    // -------------------------------------------------------
    // PRODUCT STOCK UPDATED
    // -------------------------------------------------------

    const handleProductStockUpdated = (event) => {
      try {
        const data = event.detail;

        if (!data) {
          return;
        }

        console.log(
          "REAL-TIME PRODUCT STOCK UPDATED:",
          data
        );

        const product =
          data.product || data;

        const productId =
          product.id ??
          product.product_id;

        if (
          productId === undefined ||
          productId === null
        ) {
          return;
        }

        const newStock =
          product.stock_quantity ??
          data.stock_quantity ??
          data.new_stock;

        setProducts((current) =>
          current.map((item) => {
            if (
              String(item.id) !==
              String(productId)
            ) {
              return item;
            }

            return {
              ...item,
              ...(product.id
                ? product
                : {}),
              stock_quantity:
                newStock ??
                item.stock_quantity,
            };
          })
        );

        setStockProduct((current) => {
          if (
            !current ||
            String(current.id) !==
              String(productId)
          ) {
            return current;
          }

          return {
            ...current,
            ...(product.id
              ? product
              : {}),
            stock_quantity:
              newStock ??
              current.stock_quantity,
          };
        });
      } catch (err) {
        console.error(
          "Product stock event error:",
          err
        );
      }
    };

    // -------------------------------------------------------
    // PRODUCT ACTIVE STATUS UPDATED
    // -------------------------------------------------------

    const handleProductActiveStatusUpdated = (
      event
    ) => {
      try {
        const data = event.detail;

        if (!data) {
          return;
        }

        console.log(
          "REAL-TIME PRODUCT STATUS UPDATED:",
          data
        );

        const product =
          data.product || data;

        const productId =
          product.id ??
          product.product_id;

        if (
          productId === undefined ||
          productId === null
        ) {
          return;
        }

        const isActive =
          product.is_active ??
          data.is_active ??
          data.active;

        setProducts((current) =>
          current.map((item) => {
            if (
              String(item.id) !==
              String(productId)
            ) {
              return item;
            }

            return {
              ...item,
              ...(product.id
                ? product
                : {}),
              is_active:
                isActive ??
                item.is_active,
            };
          })
        );
      } catch (err) {
        console.error(
          "Product status event error:",
          err
        );
      }
    };

    // -------------------------------------------------------
    // REGISTER LISTENERS
    // -------------------------------------------------------

    window.addEventListener(
      "paypilot:product_created",
      handleProductCreated
    );

    window.addEventListener(
      "paypilot:product_updated",
      handleProductUpdated
    );

    window.addEventListener(
      "paypilot:product_deleted",
      handleProductDeleted
    );

    window.addEventListener(
      "paypilot:product_stock_updated",
      handleProductStockUpdated
    );

    window.addEventListener(
      "paypilot:product_active_status_updated",
      handleProductActiveStatusUpdated
    );

    // -------------------------------------------------------
    // CLEANUP
    // -------------------------------------------------------

    return () => {
      window.removeEventListener(
        "paypilot:product_created",
        handleProductCreated
      );

      window.removeEventListener(
        "paypilot:product_updated",
        handleProductUpdated
      );

      window.removeEventListener(
        "paypilot:product_deleted",
        handleProductDeleted
      );

      window.removeEventListener(
        "paypilot:product_stock_updated",
        handleProductStockUpdated
      );

      window.removeEventListener(
        "paypilot:product_active_status_updated",
        handleProductActiveStatusUpdated
      );
    };
  }, []);

  // =========================================================
  // FILTER
  // =========================================================

  const filteredProducts = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return products;
    }

    return products.filter((product) => {
      return (
        String(product.id)
          .toLowerCase()
          .includes(query) ||
        product.name
          ?.toLowerCase()
          .includes(query) ||
        product.sku
          ?.toLowerCase()
          .includes(query) ||
        product.category
          ?.toLowerCase()
          .includes(query)
      );
    });
  }, [products, search]);

  // =========================================================
  // OPEN ADD
  // =========================================================

  const handleAddProduct = () => {
    setEditingProduct(null);
    setShowModal(true);
    setError("");
    setSuccess("");
  };

  // =========================================================
  // OPEN EDIT
  // =========================================================

  const handleEditProduct = (product) => {
    setEditingProduct(product);
    setShowModal(true);
    setError("");
    setSuccess("");
  };

  // =========================================================
  // SAVE PRODUCT
  // =========================================================

  const handleSaveProduct = async (formData) => {
    try {
      setSaving(true);
      setError("");
      setSuccess("");

      let updatedProduct;

      if (editingProduct) {
        updatedProduct = await updateProduct(
          editingProduct.id,
          formData
        );

        setProducts((current) =>
          current.map((product) =>
            product.id === updatedProduct.id
              ? updatedProduct
              : product
          )
        );

        setSuccess(
          "Product updated successfully."
        );
      } else {
        updatedProduct =
          await createProduct(formData);

        setProducts((current) => {
          const exists = current.some(
            (product) =>
              product.id === updatedProduct.id
          );

          if (exists) {
            return current;
          }

          return [
            updatedProduct,
            ...current,
          ];
        });

        setSuccess(
          "Product created successfully."
        );
      }

      setShowModal(false);
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to save product."
      );
    } finally {
      setSaving(false);
    }
  };

  // =========================================================
  // DELETE
  // =========================================================

  const handleDeleteProduct = async (product) => {
    const confirmed = window.confirm(
      `Delete "${product.name}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setSuccess("");

      await deleteProduct(product.id);

      setProducts((current) =>
        current.filter(
          (item) => item.id !== product.id
        )
      );

      setSuccess(
        "Product deleted successfully."
      );
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to delete product."
      );
    }
  };

  // =========================================================
  // OPEN STOCK MODAL
  // =========================================================

  const handleOpenStock = (product) => {
    setStockProduct(product);

    setStockValue(
      String(product.stock_quantity ?? 0)
    );

    setStockMode("SET");

    setShowStockModal(true);

    setError("");
    setSuccess("");
  };

  // =========================================================
  // UPDATE STOCK
  // =========================================================

  const handleStockUpdate = async () => {
    if (!stockProduct) {
      return;
    }

    const enteredValue = Number(stockValue);

    if (
      !Number.isFinite(enteredValue) ||
      enteredValue < 0
    ) {
      setError(
        "Stock quantity must be a valid number greater than or equal to 0."
      );

      return;
    }

    let newStock;

    const currentStock = Number(
      stockProduct.stock_quantity || 0
    );

    if (stockMode === "SET") {
      newStock = enteredValue;
    } else if (stockMode === "INCREASE") {
      newStock =
        currentStock + enteredValue;
    } else {
      newStock =
        currentStock - enteredValue;
    }

    if (newStock < 0) {
      setError(
        "Stock quantity cannot be negative."
      );

      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updatedProduct =
        await updateProduct(
          stockProduct.id,
          {
            stock_quantity: newStock,
          }
        );

      setProducts((current) =>
        current.map((product) =>
          product.id === updatedProduct.id
            ? updatedProduct
            : product
        )
      );

      setStockProduct(updatedProduct);

      setShowStockModal(false);

      setSuccess(
        `Stock updated successfully. New stock: ${newStock}`
      );
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to update stock."
      );
    } finally {
      setSaving(false);
    }
  };

  // =========================================================
  // STATISTICS
  // =========================================================

  const totalProducts = products.length;

  const activeProducts = products.filter(
    (product) => product.is_active
  ).length;

  const lowStockProducts = products.filter(
    (product) =>
      Number(product.stock_quantity) <= 10
  ).length;

  const totalInventoryValue =
    products.reduce(
      (total, product) =>
        total +
        Number(product.price || 0) *
          Number(
            product.stock_quantity || 0
          ),
      0
    );

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex min-h-[500px] items-center justify-center">
            <div className="text-center">
              <RefreshCw
                size={32}
                className="mx-auto animate-spin text-blue-600"
              />

              <p className="mt-4 text-sm font-medium text-slate-500">
                Loading inventory...
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================
  // UI
  // =========================================================

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-[1500px] p-8">

        {/* ===================================================
            HEADER
        =================================================== */}

        <div className="mb-8 flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
                <Package size={24} />
              </div>

              <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                  Products
                </h1>

                <p className="mt-1 text-sm text-slate-500">
                  Manage your product catalog and inventory
                </p>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={loadProducts}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              <RefreshCw size={17} />
              Refresh
            </button>

            <button
              onClick={handleAddProduct}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700"
            >
              <Plus size={18} />
              Add Product
            </button>
          </div>
        </div>

        {/* ===================================================
            ALERTS
        =================================================== */}

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
            <AlertCircle
              size={20}
              className="mt-0.5 shrink-0"
            />

            <p className="text-sm font-medium">
              {error}
            </p>

            <button
              onClick={() => setError("")}
              className="ml-auto"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {success && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-700">
            <CheckCircle2
              size={20}
              className="mt-0.5 shrink-0"
            />

            <p className="text-sm font-medium">
              {success}
            </p>

            <button
              onClick={() => setSuccess("")}
              className="ml-auto"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* ===================================================
            STAT CARDS
        =================================================== */}

        <div className="mb-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={Package}
            label="Total Products"
            value={totalProducts}
            description="Products in catalog"
          />

          <StatCard
            icon={CheckCircle2}
            label="Active Products"
            value={activeProducts}
            description="Currently available"
          />

          <StatCard
            icon={AlertCircle}
            label="Low Stock"
            value={lowStockProducts}
            description="10 units or less"
          />

          <StatCard
            icon={DollarSign}
            label="Inventory Value"
            value={`₹${totalInventoryValue.toLocaleString(
              "en-IN"
            )}`}
            description="Based on selling price"
          />
        </div>

        {/* ===================================================
            TABLE CARD
        =================================================== */}

        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">

          {/* TOOLBAR */}

          <div className="flex flex-col gap-4 border-b border-slate-200 p-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Product Inventory
              </h2>

              <p className="mt-1 text-sm text-slate-500">
                {filteredProducts.length} products displayed
              </p>
            </div>

            <div className="relative w-full lg:w-80">
              <Search
                size={18}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />

              <input
                type="text"
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search products, SKU..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10"
              />
            </div>
          </div>

          {/* TABLE */}

          {filteredProducts.length === 0 ? (
            <div className="flex min-h-[350px] flex-col items-center justify-center p-8 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                <Package size={30} />
              </div>

              <h3 className="mt-5 text-lg font-bold text-slate-900">
                No products found
              </h3>

              <p className="mt-2 max-w-md text-sm text-slate-500">
                Try changing your search or add a new product.
              </p>

              <button
                onClick={handleAddProduct}
                className="mt-5 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Add Product
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1100px]">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Product
                    </th>

                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      SKU
                    </th>

                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Category
                    </th>

                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Price
                    </th>

                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Stock
                    </th>

                    <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wide text-slate-500">
                      Status
                    </th>

                    <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-wide text-slate-500">
                      Actions
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {filteredProducts.map(
                    (product) => (
                      <tr
                        key={product.id}
                        className="transition hover:bg-slate-50/70"
                      >

                        {/* PRODUCT */}

                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 font-bold text-blue-600">
                              {product.name
                                ?.charAt(0)
                                ?.toUpperCase() ||
                                "P"}
                            </div>

                            <div>
                              <p className="font-semibold text-slate-900">
                                {product.name}
                              </p>

                              <p className="mt-0.5 text-xs text-slate-400">
                                ID #{product.id}
                              </p>
                            </div>
                          </div>
                        </td>

                        {/* SKU */}

                        <td className="px-6 py-5">
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 font-mono text-xs font-semibold text-slate-600">
                            {product.sku}
                          </span>
                        </td>

                        {/* CATEGORY */}

                        <td className="px-6 py-5">
                          <span className="text-sm font-medium text-slate-600">
                            {product.category}
                          </span>
                        </td>

                        {/* PRICE */}

                        <td className="px-6 py-5">
                          <p className="font-semibold text-slate-900">
                            ₹
                            {Number(
                              product.price || 0
                            ).toLocaleString(
                              "en-IN"
                            )}
                          </p>

                          <p className="mt-0.5 text-xs text-slate-400">
                            Cost ₹
                            {Number(
                              product.cost_price ||
                                0
                            ).toLocaleString(
                              "en-IN"
                            )}
                          </p>
                        </td>

                        {/* STOCK */}

                        <td className="px-6 py-5">
                          <button
                            onClick={() =>
                              handleOpenStock(
                                product
                              )
                            }
                            className="group flex items-center gap-3"
                          >
                            <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
                              <div
                                className={`h-full rounded-full ${
                                  product.stock_quantity <=
                                  10
                                    ? "bg-red-500"
                                    : product.stock_quantity <=
                                      30
                                    ? "bg-amber-500"
                                    : "bg-emerald-500"
                                }`}
                                style={{
                                  width: `${Math.min(
                                    100,
                                    Math.max(
                                      5,
                                      Number(
                                        product.stock_quantity
                                      ) / 2
                                    )
                                  )}%`,
                                }}
                              />
                            </div>

                            <span className="text-sm font-bold text-slate-700 group-hover:text-blue-600">
                              {
                                product.stock_quantity
                              }
                            </span>
                          </button>
                        </td>

                        {/* STATUS */}

                        <td className="px-6 py-5">
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                              product.is_active
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                product.is_active
                                  ? "bg-emerald-500"
                                  : "bg-slate-400"
                              }`}
                            />

                            {product.is_active
                              ? "Active"
                              : "Inactive"}
                          </span>
                        </td>

                        {/* ACTIONS */}

                        <td className="px-6 py-5">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() =>
                                handleOpenStock(
                                  product
                                )
                              }
                              title="Update stock"
                              className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
                            >
                              <Boxes size={17} />
                            </button>

                            <button
                              onClick={() =>
                                handleEditProduct(
                                  product
                                )
                              }
                              title="Edit product"
                              className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
                            >
                              <Edit3 size={17} />
                            </button>

                            <button
                              onClick={() =>
                                handleDeleteProduct(
                                  product
                                )
                              }
                              title="Delete product"
                              className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 size={17} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* =====================================================
          PRODUCT MODAL
      ===================================================== */}

      {showModal && (
        <ProductModal
          product={editingProduct}
          saving={saving}
          onClose={() =>
            setShowModal(false)
          }
          onSave={handleSaveProduct}
        />
      )}

      {/* =====================================================
          STOCK MODAL
      ===================================================== */}

      {showStockModal && stockProduct && (
        <StockModal
          product={stockProduct}
          mode={stockMode}
          setMode={setStockMode}
          value={stockValue}
          setValue={setStockValue}
          saving={saving}
          onClose={() =>
            setShowStockModal(false)
          }
          onSave={handleStockUpdate}
        />
      )}
    </div>
  );
}

// =========================================================
// STAT CARD
// =========================================================

function StatCard({
  icon: Icon,
  label,
  value,
  description,
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">
            {label}
          </p>

          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
            {value}
          </p>

          <p className="mt-1 text-xs text-slate-400">
            {description}
          </p>
        </div>

        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <Icon size={21} />
        </div>
      </div>
    </div>
  );
}

// =========================================================
// PRODUCT MODAL
// =========================================================

function ProductModal({
  product,
  saving,
  onClose,
  onSave,
}) {
  const [form, setForm] = useState({
    merchant_id:
      product?.merchant_id ?? "",

    name:
      product?.name ?? "",

    category:
      product?.category ?? "",

    description:
      product?.description ?? "",

    price:
      product?.price ?? "",

    cost_price:
      product?.cost_price ?? "",

    stock_quantity:
      product?.stock_quantity ?? 0,

    sku:
      product?.sku ?? "",

    is_active:
      product?.is_active ?? true,
  });

  const handleChange = (event) => {
    const {
      name,
      value,
      type,
      checked,
    } = event.target;

    setForm((current) => ({
      ...current,
      [name]:
        type === "checkbox"
          ? checked
          : value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    onSave({
      merchant_id:
        Number(form.merchant_id),

      name:
        form.name.trim(),

      category:
        form.category.trim(),

      description:
        form.description.trim() || null,

      price:
        Number(form.price),

      cost_price:
        Number(form.cost_price),

      stock_quantity:
        Number(form.stock_quantity),

      sku:
        form.sku.trim(),

      is_active:
        Boolean(form.is_active),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">

        {/* HEADER */}

        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              {product
                ? "Edit Product"
                : "Add Product"}
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              {product
                ? "Update product information"
                : "Add a new product to inventory"}
            </p>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X size={20} />
          </button>
        </div>

        {/* FORM */}

        <form
          onSubmit={handleSubmit}
          className="space-y-5 p-6"
        >
          <div className="grid gap-5 md:grid-cols-2">
            <FormField
              label="Merchant ID"
              name="merchant_id"
              type="number"
              value={form.merchant_id}
              onChange={handleChange}
              required
            />

            <FormField
              label="SKU"
              name="sku"
              value={form.sku}
              onChange={handleChange}
              required
            />

            <FormField
              label="Product Name"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
            />

            <FormField
              label="Category"
              name="category"
              value={form.category}
              onChange={handleChange}
              required
            />

            <FormField
              label="Selling Price"
              name="price"
              type="number"
              min="0"
              step="0.01"
              value={form.price}
              onChange={handleChange}
              required
            />

            <FormField
              label="Cost Price"
              name="cost_price"
              type="number"
              min="0"
              step="0.01"
              value={form.cost_price}
              onChange={handleChange}
              required
            />

            <FormField
              label="Initial Stock"
              name="stock_quantity"
              type="number"
              min="0"
              value={form.stock_quantity}
              onChange={handleChange}
              required
            />
          </div>

          {/* DESCRIPTION */}

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
              Description
            </label>

            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              rows={4}
              className="w-full resize-none rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
              placeholder="Product description..."
            />
          </div>

          {/* ACTIVE */}

          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-4">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />

            <div>
              <p className="text-sm font-semibold text-slate-800">
                Product is active
              </p>

              <p className="text-xs text-slate-500">
                Active products can be used in orders.
              </p>
            </div>
          </label>

          {/* ACTIONS */}

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? (
                <RefreshCw
                  size={17}
                  className="animate-spin"
                />
              ) : (
                <Save size={17} />
              )}

              {product
                ? "Save Changes"
                : "Create Product"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =========================================================
// FORM FIELD
// =========================================================

function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  required = false,
  min,
  step,
}) {
  return (
    <div>
      <label className="mb-2 block text-sm font-semibold text-slate-700">
        {label}
      </label>

      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        min={min}
        step={step}
        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
      />
    </div>
  );
}

// =========================================================
// STOCK MODAL
// =========================================================

function StockModal({
  product,
  mode,
  setMode,
  value,
  setValue,
  saving,
  onClose,
  onSave,
}) {
  const currentStock = Number(
    product.stock_quantity || 0
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl">

        {/* HEADER */}

        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              Adjust Stock
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              {product.name}
            </p>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-5 p-6">

          {/* CURRENT STOCK */}

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Current Stock
            </p>

            <p className="mt-1 text-3xl font-bold text-slate-900">
              {currentStock}
            </p>
          </div>

          {/* MODES */}

          <div className="grid grid-cols-3 gap-2">
            <StockModeButton
              active={mode === "SET"}
              icon={Boxes}
              label="Set"
              onClick={() =>
                setMode("SET")
              }
            />

            <StockModeButton
              active={mode === "INCREASE"}
              icon={Plus}
              label="Add"
              onClick={() =>
                setMode("INCREASE")
              }
            />

            <StockModeButton
              active={mode === "DECREASE"}
              icon={Minus}
              label="Remove"
              onClick={() =>
                setMode("DECREASE")
              }
            />
          </div>

          {/* VALUE */}

          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-700">
              {mode === "SET"
                ? "New Stock Quantity"
                : mode === "INCREASE"
                ? "Quantity to Add"
                : "Quantity to Remove"}
            </label>

            <input
              type="number"
              min="0"
              value={value}
              onChange={(e) =>
                setValue(e.target.value)
              }
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-lg font-semibold outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
            />
          </div>

          {/* PREVIEW */}

          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
            <p className="text-xs font-semibold text-blue-600">
              New inventory level
            </p>

            <p className="mt-1 text-2xl font-bold text-blue-900">
              {mode === "SET"
                ? Number(value || 0)
                : mode === "INCREASE"
                ? currentStock +
                  Number(value || 0)
                : Math.max(
                    0,
                    currentStock -
                      Number(value || 0)
                  )}
            </p>
          </div>

          {/* ACTIONS */}

          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={onClose}
              disabled={saving}
              className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>

            <button
              onClick={onSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? (
                <RefreshCw
                  size={17}
                  className="animate-spin"
                />
              ) : (
                <Save size={17} />
              )}

              Update Stock
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =========================================================
// STOCK MODE BUTTON
// =========================================================

function StockModeButton({
  active,
  icon: Icon,
  label,
  onClick,
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1.5 rounded-xl border px-3 py-3 text-xs font-semibold transition ${
        active
          ? "border-blue-600 bg-blue-600 text-white shadow-lg shadow-blue-600/20"
          : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
      }`}
    >
      <Icon size={18} />
      {label}
    </button>
  );
}

export default Products;