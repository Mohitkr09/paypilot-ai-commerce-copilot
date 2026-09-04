import { useEffect, useState } from "react";

import {
  Settings as SettingsIcon,
  ShieldCheck,
  SlidersHorizontal,
  Percent,
  Save,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Power,
} from "lucide-react";

import {
  getSettings,
  updateSettings,
} from "../services/api";


function Settings() {

  const [settings, setSettings] = useState({
    id: null,

    risk_engine_enabled: true,

    low_risk_threshold: 30,

    high_risk_threshold: 70,

    manual_review_enabled: true,

    manual_review_threshold: 50,

    max_discount: 30,

    require_review_discount: 20,
  });


  const [loading, setLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [error, setError] = useState("");

  const [success, setSuccess] = useState("");


  // =========================================================
  // LOAD SETTINGS
  // =========================================================

  const loadSettings = async () => {

    try {

      setLoading(true);

      setError("");

      setSuccess("");

      const data = await getSettings();

      setSettings(data);

    } catch (err) {

      console.error(
        "Failed to load settings:",
        err
      );

      setError(
        err.response?.data?.detail ||
        "Unable to load settings from PayPilot API."
      );

    } finally {

      setLoading(false);

    }
  };


  useEffect(() => {

    loadSettings();

  }, []);


  // =========================================================
  // INPUT CHANGE
  // =========================================================

  const handleChange = (
    field,
    value
  ) => {

    setSettings((previous) => ({
      ...previous,
      [field]: value,
    }));

    setSuccess("");

    setError("");
  };


  // =========================================================
  // SAVE SETTINGS
  // =========================================================

  const handleSave = async () => {

    setError("");

    setSuccess("");


    // -------------------------------------------------------
    // Validate thresholds
    // -------------------------------------------------------

    if (
      Number(settings.low_risk_threshold) >=
      Number(settings.high_risk_threshold)
    ) {

      setError(
        "Low risk threshold must be lower than high risk threshold."
      );

      return;
    }


    if (
      Number(settings.manual_review_threshold) <
      Number(settings.low_risk_threshold)
    ) {

      setError(
        "Manual review threshold should not be below the low risk threshold."
      );

      return;
    }


    try {

      setSaving(true);


      const payload = {

        risk_engine_enabled:
          Boolean(
            settings.risk_engine_enabled
          ),

        low_risk_threshold:
          Number(
            settings.low_risk_threshold
          ),

        high_risk_threshold:
          Number(
            settings.high_risk_threshold
          ),

        manual_review_enabled:
          Boolean(
            settings.manual_review_enabled
          ),

        manual_review_threshold:
          Number(
            settings.manual_review_threshold
          ),

        max_discount:
          Number(
            settings.max_discount
          ),

        require_review_discount:
          Number(
            settings.require_review_discount
          ),
      };


      const updated =
        await updateSettings(
          payload
        );


      setSettings(updated);

      setSuccess(
        "Settings saved successfully."
      );

    } catch (err) {

      console.error(
        "Failed to save settings:",
        err
      );

      setError(
        err.response?.data?.detail ||
        "Unable to save settings."
      );

    } finally {

      setSaving(false);

    }
  };


  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {

    return (

      <div className="min-h-screen bg-slate-50">

        <div className="mx-auto max-w-7xl px-8 py-10">

          <div className="flex items-center gap-3">

            <RefreshCw
              size={20}
              className="animate-spin text-blue-600"
            />

            <p className="text-sm font-medium text-slate-600">
              Loading PayPilot settings...
            </p>

          </div>

        </div>

      </div>
    );
  }


  // =========================================================
  // PAGE
  // =========================================================

  return (

    <div className="min-h-screen bg-slate-50">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="border-b border-slate-200 bg-white">

        <div className="mx-auto max-w-7xl px-8 py-7">

          <div className="flex items-start justify-between">

            <div>

              <div className="flex items-center gap-3">

                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">

                  <SettingsIcon size={22} />

                </div>

                <div>

                  <h1 className="text-2xl font-bold tracking-tight text-slate-900">

                    Settings

                  </h1>

                  <p className="mt-1 text-sm text-slate-500">

                    Configure PayPilot's risk engine
                    and transaction policies.

                  </p>

                </div>

              </div>

            </div>


            <button
              onClick={handleSave}
              disabled={saving}
              className="
                flex
                items-center
                gap-2
                rounded-xl
                bg-blue-600
                px-5
                py-2.5
                text-sm
                font-semibold
                text-white
                shadow-lg
                shadow-blue-600/20
                transition
                hover:bg-blue-700
                disabled:cursor-not-allowed
                disabled:opacity-60
              "
            >

              {saving ? (

                <RefreshCw
                  size={17}
                  className="animate-spin"
                />

              ) : (

                <Save size={17} />

              )}

              {saving
                ? "Saving..."
                : "Save Changes"}

            </button>

          </div>

        </div>

      </div>


      {/* =====================================================
          CONTENT
      ===================================================== */}

      <div className="mx-auto max-w-7xl px-8 py-8">


        {/* ===================================================
            ALERTS
        =================================================== */}

        {error && (

          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4">

            <AlertCircle
              size={20}
              className="mt-0.5 shrink-0 text-red-600"
            />

            <div>

              <p className="text-sm font-semibold text-red-800">
                Unable to save settings
              </p>

              <p className="mt-1 text-sm text-red-700">
                {error}
              </p>

            </div>

          </div>

        )}


        {success && (

          <div className="mb-6 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">

            <CheckCircle2
              size={20}
              className="mt-0.5 shrink-0 text-emerald-600"
            />

            <div>

              <p className="text-sm font-semibold text-emerald-800">
                Saved
              </p>

              <p className="mt-1 text-sm text-emerald-700">
                {success}
              </p>

            </div>

          </div>

        )}


        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">


          {/* =================================================
              LEFT / MAIN SETTINGS
          ================================================= */}

          <div className="space-y-6 xl:col-span-2">


            {/* =================================================
                RISK ENGINE
            ================================================= */}

            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-100 px-6 py-5">

                <div className="flex items-center gap-3">

                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">

                    <ShieldCheck size={20} />

                  </div>

                  <div>

                    <h2 className="font-bold text-slate-900">
                      Risk Engine
                    </h2>

                    <p className="text-sm text-slate-500">
                      Control automated transaction risk evaluation.
                    </p>

                  </div>

                </div>

              </div>


              <div className="space-y-6 p-6">

                {/* Engine toggle */}

                <ToggleRow
                  icon={Power}
                  title="Risk Engine"
                  description="Enable automated AI risk evaluation for incoming orders."
                  enabled={
                    settings.risk_engine_enabled
                  }
                  onChange={(value) =>
                    handleChange(
                      "risk_engine_enabled",
                      value
                    )
                  }
                />


                <div className="grid grid-cols-1 gap-5 md:grid-cols-2">

                  <NumberInput
                    label="Low Risk Threshold"
                    description="Scores below this value are considered low risk."
                    value={
                      settings.low_risk_threshold
                    }
                    onChange={(value) =>
                      handleChange(
                        "low_risk_threshold",
                        value
                      )
                    }
                  />


                  <NumberInput
                    label="High Risk Threshold"
                    description="Scores at or above this value are considered high risk."
                    value={
                      settings.high_risk_threshold
                    }
                    onChange={(value) =>
                      handleChange(
                        "high_risk_threshold",
                        value
                      )
                    }
                  />

                </div>

              </div>

            </section>


            {/* =================================================
                MANUAL REVIEW
            ================================================= */}

            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-100 px-6 py-5">

                <div className="flex items-center gap-3">

                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">

                    <SlidersHorizontal size={20} />

                  </div>

                  <div>

                    <h2 className="font-bold text-slate-900">
                      Manual Review
                    </h2>

                    <p className="text-sm text-slate-500">
                      Configure when transactions require human review.
                    </p>

                  </div>

                </div>

              </div>


              <div className="space-y-6 p-6">

                <ToggleRow
                  icon={ShieldCheck}
                  title="Manual Review"
                  description="Allow high-risk or suspicious transactions to enter the review queue."
                  enabled={
                    settings.manual_review_enabled
                  }
                  onChange={(value) =>
                    handleChange(
                      "manual_review_enabled",
                      value
                    )
                  }
                />


                <NumberInput
                  label="Manual Review Threshold"
                  description="Transactions at or above this score can require manual review."
                  value={
                    settings.manual_review_threshold
                  }
                  onChange={(value) =>
                    handleChange(
                      "manual_review_threshold",
                      value
                    )
                  }
                />

              </div>

            </section>


            {/* =================================================
                DISCOUNT POLICY
            ================================================= */}

            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-100 px-6 py-5">

                <div className="flex items-center gap-3">

                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-50 text-purple-600">

                    <Percent size={20} />

                  </div>

                  <div>

                    <h2 className="font-bold text-slate-900">
                      Discount Policy
                    </h2>

                    <p className="text-sm text-slate-500">
                      Control promotional discount limits.
                    </p>

                  </div>

                </div>

              </div>


              <div className="grid grid-cols-1 gap-5 p-6 md:grid-cols-2">

                <NumberInput
                  label="Maximum Discount"
                  description="Maximum discount allowed on an order."
                  value={
                    settings.max_discount
                  }
                  onChange={(value) =>
                    handleChange(
                      "max_discount",
                      value
                    )
                  }
                  suffix="%"
                />


                <NumberInput
                  label="Review Discount Threshold"
                  description="Discounts above this value can require additional review."
                  value={
                    settings.require_review_discount
                  }
                  onChange={(value) =>
                    handleChange(
                      "require_review_discount",
                      value
                    )
                  }
                  suffix="%"
                />

              </div>

            </section>

          </div>


          {/* =================================================
              RIGHT SIDEBAR
          ================================================= */}

          <div className="space-y-6">


            {/* =================================================
                CURRENT CONFIGURATION
            ================================================= */}

            <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">

              <div className="border-b border-slate-100 px-5 py-5">

                <h2 className="font-bold text-slate-900">
                  Current Configuration
                </h2>

                <p className="mt-1 text-xs text-slate-500">
                  Values currently loaded from the API.
                </p>

              </div>


              <div className="divide-y divide-slate-100">

                <SummaryRow
                  label="Risk Engine"
                  value={
                    settings.risk_engine_enabled
                      ? "Enabled"
                      : "Disabled"
                  }
                  positive={
                    settings.risk_engine_enabled
                  }
                />

                <SummaryRow
                  label="Low Risk"
                  value={
                    `${settings.low_risk_threshold}`
                  }
                />

                <SummaryRow
                  label="High Risk"
                  value={
                    `${settings.high_risk_threshold}`
                  }
                />

                <SummaryRow
                  label="Manual Review"
                  value={
                    settings.manual_review_enabled
                      ? "Enabled"
                      : "Disabled"
                  }
                  positive={
                    settings.manual_review_enabled
                  }
                />

                <SummaryRow
                  label="Review Threshold"
                  value={
                    `${settings.manual_review_threshold}`
                  }
                />

                <SummaryRow
                  label="Maximum Discount"
                  value={
                    `${settings.max_discount}%`
                  }
                />

                <SummaryRow
                  label="Review Discount"
                  value={
                    `${settings.require_review_discount}%`
                  }
                />

              </div>

            </section>


            {/* =================================================
                RISK SCALE
            ================================================= */}

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">

              <h2 className="font-bold text-slate-900">
                Risk Score Scale
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Current thresholds used by PayPilot.
              </p>


              <div className="mt-5 space-y-3">

                <RiskLevel
                  label="Low Risk"
                  range={`0 - ${settings.low_risk_threshold}`}
                  className="bg-emerald-50 text-emerald-700"
                  dot="bg-emerald-500"
                />


                <RiskLevel
                  label="Review"
                  range={`${settings.low_risk_threshold} - ${settings.high_risk_threshold}`}
                  className="bg-amber-50 text-amber-700"
                  dot="bg-amber-500"
                />


                <RiskLevel
                  label="High Risk"
                  range={`${settings.high_risk_threshold} - 100`}
                  className="bg-red-50 text-red-700"
                  dot="bg-red-500"
                />

              </div>

            </section>


            {/* =================================================
                SAVE REMINDER
            ================================================= */}

            <div className="rounded-2xl border border-blue-100 bg-blue-50 p-5">

              <div className="flex gap-3">

                <div className="mt-0.5 text-blue-600">
                  <ShieldCheck size={19} />
                </div>

                <div>

                  <p className="text-sm font-bold text-blue-900">
                    Configuration is persistent
                  </p>

                  <p className="mt-1 text-xs leading-5 text-blue-700">
                    Changes are saved directly to the
                    PayPilot database through the FastAPI
                    backend.
                  </p>

                </div>

              </div>

            </div>

          </div>

        </div>


        {/* ===================================================
            BOTTOM SAVE
        =================================================== */}

        <div className="mt-8 flex justify-end">

          <button
            onClick={handleSave}
            disabled={saving}
            className="
              flex
              items-center
              gap-2
              rounded-xl
              bg-blue-600
              px-6
              py-3
              text-sm
              font-semibold
              text-white
              shadow-lg
              shadow-blue-600/20
              transition
              hover:bg-blue-700
              disabled:cursor-not-allowed
              disabled:opacity-60
            "
          >

            {saving ? (

              <RefreshCw
                size={17}
                className="animate-spin"
              />

            ) : (

              <Save size={17} />

            )}

            {saving
              ? "Saving..."
              : "Save Settings"}

          </button>

        </div>

      </div>

    </div>
  );
}


// =========================================================
// NUMBER INPUT
// =========================================================

function NumberInput({
  label,
  description,
  value,
  onChange,
  suffix,
}) {

  return (

    <div>

      <label className="text-sm font-semibold text-slate-800">

        {label}

      </label>

      <div className="relative mt-2">

        <input
          type="number"
          min="0"
          max="100"
          value={value ?? ""}
          onChange={(event) =>
            onChange(
              event.target.value
            )
          }
          className="
            w-full
            rounded-xl
            border
            border-slate-200
            bg-white
            px-4
            py-3
            text-sm
            font-medium
            text-slate-900
            outline-none
            transition
            focus:border-blue-500
            focus:ring-4
            focus:ring-blue-500/10
          "
        />

        {suffix && (

          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-400">

            {suffix}

          </span>

        )}

      </div>

      <p className="mt-2 text-xs leading-5 text-slate-500">

        {description}

      </p>

    </div>
  );
}


// =========================================================
// TOGGLE
// =========================================================

function ToggleRow({
  icon: Icon,
  title,
  description,
  enabled,
  onChange,
}) {

  return (

    <div className="flex items-start justify-between gap-5">

      <div className="flex gap-3">

        <div className="mt-0.5 text-slate-400">

          <Icon size={19} />

        </div>

        <div>

          <p className="text-sm font-semibold text-slate-800">
            {title}
          </p>

          <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">
            {description}
          </p>

        </div>

      </div>


      <button
        type="button"
        onClick={() =>
          onChange(!enabled)
        }
        className={`
          relative
          h-7
          w-12
          shrink-0
          rounded-full
          transition
          ${
            enabled
              ? "bg-blue-600"
              : "bg-slate-300"
          }
        `}
      >

        <span
          className={`
            absolute
            top-1
            h-5
            w-5
            rounded-full
            bg-white
            shadow
            transition
            ${
              enabled
                ? "left-6"
                : "left-1"
            }
          `}
        />

      </button>

    </div>
  );
}


// =========================================================
// SUMMARY ROW
// =========================================================

function SummaryRow({
  label,
  value,
  positive,
}) {

  return (

    <div className="flex items-center justify-between px-5 py-3.5">

      <span className="text-sm text-slate-500">
        {label}
      </span>

      <span
        className={`
          text-sm
          font-semibold
          ${
            positive === true
              ? "text-emerald-600"
              : positive === false
                ? "text-slate-400"
                : "text-slate-900"
          }
        `}
      >
        {value}
      </span>

    </div>
  );
}


// =========================================================
// RISK LEVEL
// =========================================================

function RiskLevel({
  label,
  range,
  className,
  dot,
}) {

  return (

    <div
      className={`
        flex
        items-center
        justify-between
        rounded-xl
        px-4
        py-3
        ${className}
      `}
    >

      <div className="flex items-center gap-2">

        <span
          className={`
            h-2.5
            w-2.5
            rounded-full
            ${dot}
          `}
        />

        <span className="text-sm font-semibold">
          {label}
        </span>

      </div>

      <span className="text-xs font-bold">
        {range}
      </span>

    </div>
  );
}


export default Settings;