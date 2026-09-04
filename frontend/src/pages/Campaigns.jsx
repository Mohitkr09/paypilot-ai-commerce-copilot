import { useEffect, useState } from "react";

import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock3,
  Megaphone,
  Package,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";

import {
  createCampaignProposal,
  getCampaignProposals,
  getCampaignProposal,
  validateCampaignProposal,
  approveCampaignProposal,
  rejectCampaignProposal,
  activateCampaignProposal,
  getApiErrorMessage,
  default as api,
} from "../services/api";

// =============================================================
// STATUS HELPERS
// =============================================================

const normalizeStatus = (status) => {
  if (status === null || status === undefined) {
    return "";
  }

  return String(status)
    .trim()
    .toUpperCase()
    .split(".")
    .pop();
};

const statusLabel = (status) => {
  const normalized = normalizeStatus(status);

  return (normalized || "DRAFT").replaceAll("_", " ");
};

const getProposalName = (proposal) =>
  proposal?.name ||
  proposal?.campaign_name ||
  `Campaign Proposal #${proposal?.id || ""}`;

// =============================================================
// NORMALIZE PROPOSAL
// =============================================================

const normalizeProposal = (proposal) => {
  if (!proposal) {
    return null;
  }

  return {
    ...proposal,

    name: getProposalName(proposal),

    brief:
      proposal.brief ||
      proposal.goal ||
      "",

    objective:
      proposal.objective ||
      "GROWTH",

    strategy_type:
      proposal.strategy_type ||
      proposal.strategy ||
      "RECOMMENDATION",

    suggested_discount_percent: Number(
      proposal.suggested_discount_percent ?? 0
    ),

    product_ids: Array.isArray(proposal.product_ids)
      ? proposal.product_ids
      : [],

    proposed_actions: Array.isArray(
      proposal.proposed_actions
    )
      ? proposal.proposed_actions
      : [],

    explanation:
      proposal.explanation ||
      proposal.reason ||
      "PayPilot generated this proposal based on the campaign goal.",

    status:
      proposal.status ||
      "DRAFT",

    governance:
      proposal.governance ||
      proposal.governance_details ||
      null,
  };
};

// =============================================================
// GOVERNANCE HELPERS
// =============================================================

const getGovernance = (proposal) => {
  return (
    proposal?.governance ||
    proposal?.governance_details ||
    null
  );
};

const getPolicyValidation = (proposal) => {
  const governance = getGovernance(proposal);

  return (
    governance?.policy_validation ||
    governance?.policy ||
    null
  );
};

const getMarginValidation = (proposal) => {
  const governance = getGovernance(proposal);

  return (
    governance?.margin_validation ||
    governance?.margin ||
    null
  );
};

const getProductValidation = (proposal) => {
  const governance = getGovernance(proposal);

  return (
    governance?.product_validation ||
    governance?.products ||
    []
  );
};

// =============================================================
// PHASE STATUS
// =============================================================

const isDraft = (proposal) =>
  normalizeStatus(proposal?.status) === "DRAFT";

const isPolicyApproved = (proposal) => {
  const status = normalizeStatus(proposal?.status);
  const governance = getGovernance(proposal);

  if (
    status === "POLICY_APPROVED" ||
    status === "MERCHANT_APPROVED" ||
    status === "ACTIVE"
  ) {
    return true;
  }

  return governance?.validation_passed === true;
};

const isPolicyRejected = (proposal) => {
  const status = normalizeStatus(proposal?.status);

  return (
    status === "POLICY_REJECTED"
  );
};

// =============================================================
// MERCHANT APPROVAL
// =============================================================

const isMerchantApproved = (proposal) => {
  if (!proposal) {
    return false;
  }

  const status = normalizeStatus(proposal.status);
  const governance = getGovernance(proposal);

  /*
   * Normal Phase 3 state.
   */
  if (status === "MERCHANT_APPROVED") {
    return true;
  }

  /*
   * Some older backend responses may return APPROVED.
   * Treat that as merchant approval only when governance
   * confirms the merchant approval.
   */
  if (status === "APPROVED") {
    return (
      governance?.merchant_approved === true ||
      String(
        governance?.merchant_approval_status || ""
      ).toUpperCase() === "APPROVED"
    );
  }

  /*
   * If ACTIVE is ever returned by a future Phase 4,
   * merchant approval must already have happened.
   */
  if (status === "ACTIVE") {
    return (
      governance?.merchant_approved === true ||
      String(
        governance?.merchant_approval_status || ""
      ).toUpperCase() === "APPROVED"
    );
  }

  return (
    governance?.merchant_approved === true ||
    String(
      governance?.merchant_approval_status || ""
    ).toUpperCase() === "APPROVED"
  );
};

const isMerchantRejected = (proposal) => {
  if (!proposal) {
    return false;
  }

  const status = normalizeStatus(proposal.status);
  const governance = getGovernance(proposal);

  if (status === "MERCHANT_REJECTED") {
    return true;
  }

  return (
    String(
      governance?.merchant_approval_status || ""
    ).toUpperCase() === "REJECTED"
  );
};

// =============================================================
// ACTUAL CAMPAIGN ACTIVATION
// =============================================================

const isCampaignActive = (proposal) => {
  if (!proposal) {
    return false;
  }

  const status = normalizeStatus(proposal.status);
  const governance = getGovernance(proposal);

  /*
   * IMPORTANT:
   *
   * Explanation text is NOT used here.
   *
   * Campaign is active only if the backend explicitly says so.
   */
  return (
    status === "ACTIVE" ||
    governance?.campaign_active === true
  );
};

const getActivationStatus = (proposal) => {
  const governance = getGovernance(proposal);

  const raw =
    governance?.activation_status;

  if (raw) {
    return String(raw).trim().toUpperCase();
  }

  if (isCampaignActive(proposal)) {
    return "ACTIVE";
  }

  if (isMerchantApproved(proposal)) {
    return "PENDING";
  }

  if (isMerchantRejected(proposal)) {
    return "REJECTED";
  }

  return "NOT_STARTED";
};

const isActivationPending = (proposal) => {
  return (
    isMerchantApproved(proposal) &&
    !isCampaignActive(proposal) &&
    getActivationStatus(proposal) === "PENDING"
  );
};

const canActivateCampaign = (proposal) => {
  const governance = getGovernance(proposal);

  return (
    isMerchantApproved(proposal) &&
    !isCampaignActive(proposal) &&
    governance?.can_activate === true
  );
};

const getGovernanceBoolean = (proposal, key, fallback = false) => {
  const governance = getGovernance(proposal);

  if (typeof governance?.[key] === "boolean") {
    return governance[key];
  }

  return fallback;
};

// =============================================================
// PHASE 3 BUTTON CONDITION
// =============================================================

const canApproveMerchant = (proposal) => {
  if (!proposal) {
    return false;
  }

  if (
    isMerchantApproved(proposal) ||
    isMerchantRejected(proposal)
  ) {
    return false;
  }

  const status = normalizeStatus(proposal.status);
  const governance = getGovernance(proposal);

  return (
    status === "POLICY_APPROVED" &&
    governance?.validation_passed !== false
  );
};

// =============================================================
// DELETE
// =============================================================

const canDeleteProposal = (proposal) => {
  return isDraft(proposal);
};

// =============================================================
// COMPONENT
// =============================================================

export default function Campaigns() {
  const [brief, setBrief] = useState("");
  const [campaignName, setCampaignName] =
    useState("");
  const [discount, setDiscount] = useState("");

  const [campaigns, setCampaigns] = useState([]);
  const [selected, setSelected] = useState(null);

  const [loading, setLoading] = useState(false);
  const [loadingList, setLoadingList] =
    useState(true);
  const [loadingSelected, setLoadingSelected] =
    useState(false);

  const [validating, setValidating] =
    useState(false);

  const [approving, setApproving] =
    useState(false);

  const [rejecting, setRejecting] =
    useState(false);

    const [activating, setActivating] =
     useState(false);

  const [deleting, setDeleting] =
    useState(false);

  const [error, setError] = useState("");

  // ===========================================================
  // LOAD CAMPAIGNS
  // ===========================================================

  const loadCampaigns = async () => {
    setLoadingList(true);
    setError("");

    try {
      const response =
        await getCampaignProposals();

      const rawCampaigns =
        Array.isArray(response)
          ? response
          : Array.isArray(response?.proposals)
          ? response.proposals
          : Array.isArray(response?.campaigns)
          ? response.campaigns
          : Array.isArray(response?.items)
          ? response.items
          : [];

      const normalized = rawCampaigns
        .map(normalizeProposal)
        .filter(Boolean);

      setCampaigns(normalized);

      if (selected?.id) {
        const refreshedSelected =
          normalized.find(
            (item) =>
              item.id === selected.id
          );

        if (refreshedSelected) {
          setSelected(refreshedSelected);
        }
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to load campaign proposals."
        )
      );
    } finally {
      setLoadingList(false);
    }
  };

  // ===========================================================
  // INITIAL LOAD
  // ===========================================================

  useEffect(() => {
    loadCampaigns();
  }, []);

  // ===========================================================
  // GENERATE PROPOSAL
  // ===========================================================

  const handleGenerate = async (event) => {
    event.preventDefault();

    setError("");

    if (!brief.trim()) {
      setError(
        "Tell PayPilot what you want the campaign to achieve."
      );
      return;
    }

    const discountValue =
      discount === ""
        ? 0
        : Number(discount);

    if (
      Number.isNaN(discountValue) ||
      discountValue < 0 ||
      discountValue > 100
    ) {
      setError(
        "Suggested discount must be between 0% and 100%."
      );
      return;
    }

    setLoading(true);

    try {
      const proposal =
        await createCampaignProposal({
          brief: brief.trim(),
          campaign_name:
            campaignName.trim() || null,
          suggested_discount_percent:
            discountValue,
        });

      const normalizedProposal =
        normalizeProposal(proposal);

      setSelected(normalizedProposal);

      setCampaigns((previous) => [
        normalizedProposal,
        ...previous.filter(
          (item) =>
            item.id !==
            normalizedProposal.id
        ),
      ]);

      setBrief("");
      setCampaignName("");
      setDiscount("");
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to generate campaign proposal."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  // ===========================================================
  // SELECT CAMPAIGN
  // ===========================================================

  const handleSelectCampaign = async (
    campaign
  ) => {
    setError("");

    if (!campaign?.id) {
      setSelected(
        normalizeProposal(campaign)
      );
      return;
    }

    setSelected(
      normalizeProposal(campaign)
    );

    setLoadingSelected(true);

    try {
      const response =
        await getCampaignProposal(
          campaign.id
        );

      const proposal =
        response?.proposal ||
        response?.campaign ||
        response;

      if (proposal) {
        setSelected(
          normalizeProposal(proposal)
        );
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to load the selected campaign proposal."
        )
      );
    } finally {
      setLoadingSelected(false);
    }
  };

  // ===========================================================
  // PHASE 2 VALIDATION
  // ===========================================================

  const handleValidate = async (
    proposalId
  ) => {
    if (!proposalId || validating) {
      return;
    }

    setError("");
    setValidating(true);

    try {
      const response =
        await validateCampaignProposal(
          proposalId
        );

      const proposal =
        response?.proposal ||
        response?.campaign ||
        response;

      if (proposal) {
        const normalized =
          normalizeProposal(proposal);

        setSelected(normalized);

        setCampaigns((previous) =>
          previous.map((item) =>
            item.id === normalized.id
              ? normalized
              : item
          )
        );
      } else {
        await loadCampaigns();
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to validate campaign proposal."
        )
      );
    } finally {
      setValidating(false);
    }
  };

  // ===========================================================
  // PHASE 3 APPROVE
  // ===========================================================

  const handleApprove = async (
    proposalId
  ) => {
    if (
      !proposalId ||
      approving ||
      rejecting
    ) {
      return;
    }

    const confirmed =
      window.confirm(
        "Approve this campaign proposal as the merchant?"
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setApproving(true);

    try {
      const response =
        await approveCampaignProposal(
          proposalId
        );

      const proposal =
        response?.proposal ||
        response?.campaign ||
        response;

      if (proposal) {
        const normalized =
          normalizeProposal(proposal);

        setSelected(normalized);

        setCampaigns((previous) =>
          previous.map((item) =>
            item.id === normalized.id
              ? normalized
              : item
          )
        );
      } else {
        await loadCampaigns();
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to approve campaign proposal."
        )
      );
    } finally {
      setApproving(false);
    }
  };

  // ===========================================================
  // PHASE 3 REJECT
  // ===========================================================

  const handleReject = async (
    proposalId
  ) => {
    if (
      !proposalId ||
      approving ||
      rejecting
    ) {
      return;
    }

    const confirmed =
      window.confirm(
        "Reject this campaign proposal as the merchant?"
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setRejecting(true);

    try {
      const response =
        await rejectCampaignProposal(
          proposalId
        );

      const proposal =
        response?.proposal ||
        response?.campaign ||
        response;

      if (proposal) {
        const normalized =
          normalizeProposal(proposal);

        setSelected(normalized);

        setCampaigns((previous) =>
          previous.map((item) =>
            item.id === normalized.id
              ? normalized
              : item
          )
        );
      } else {
        await loadCampaigns();
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to reject campaign proposal."
        )
      );
    } finally {
      setRejecting(false);
    }
  };

  // ===========================================================
  // DELETE DRAFT
  // ===========================================================

  const handleDelete = async (
    campaignId
  ) => {
    if (!campaignId || deleting) {
      return;
    }

    const confirmed =
      window.confirm(
        "Delete this campaign proposal?"
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setDeleting(true);

    try {
      await api.delete(
        `/campaigns/${campaignId}`
      );

      setCampaigns((previous) =>
        previous.filter(
          (item) =>
            item.id !== campaignId
        )
      );

      if (
        selected?.id === campaignId
      ) {
        setSelected(null);
      }
    } catch (err) {
      setError(
        getApiErrorMessage(
          err,
          "Unable to delete campaign proposal."
        )
      );
    } finally {
      setDeleting(false);
    }
  };



  const handleActivate = async (proposalId) => {
  if (!proposalId || activating) {
    return;
  }

  const confirmed = window.confirm(
    "Activate this campaign? This is Phase 4 and may apply the approved campaign actions."
  );

  if (!confirmed) {
    return;
  }

  setError("");
  setActivating(true);

  try {
    const response =
      await activateCampaignProposal(proposalId);

    const proposal =
      response?.proposal ||
      response?.campaign ||
      response;

    if (proposal) {
      const normalized =
        normalizeProposal(proposal);

      setSelected(normalized);

      setCampaigns((previous) =>
        previous.map((item) =>
          item.id === normalized.id
            ? normalized
            : item
        )
      );
    } else {
      await loadCampaigns();
    }
  } catch (err) {
    setError(
      getApiErrorMessage(
        err,
        "Unable to activate campaign."
      )
    );
  } finally {
    setActivating(false);
  }
};
  // ===========================================================
  // RENDER
  // ===========================================================

  return (
    <div className="min-h-screen bg-slate-50 p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">

        {/* =====================================================
            HEADER
        ====================================================== */}

        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

          <div>
            <div className="mb-2 flex items-center gap-3">

              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-600/20">
                <Megaphone size={22} />
              </div>

              <div>
                <h1 className="text-3xl font-black tracking-tight text-slate-950">
                  AI Campaign Orchestrator
                </h1>

                <p className="text-sm text-slate-500">
                  Turn merchant growth goals into
                  explainable campaign proposals.
                </p>
              </div>

            </div>
          </div>

          <button
            type="button"
            onClick={loadCampaigns}
            disabled={loadingList}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-60"
          >
            <RefreshCw
              size={16}
              className={
                loadingList
                  ? "animate-spin"
                  : ""
              }
            />

            Refresh
          </button>

        </div>

        {/* =====================================================
            ERROR
        ====================================================== */}

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">

            <AlertCircle
              className="mt-0.5 shrink-0"
              size={18}
            />

            <span>{error}</span>

          </div>
        )}

        {/* =====================================================
            MAIN GRID
        ====================================================== */}

        <div className="grid gap-6 xl:grid-cols-[1fr_1.15fr]">

          {/* ===================================================
              CREATE PROPOSAL
          ==================================================== */}

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

            <div className="mb-5 flex items-start gap-3">

              <div className="rounded-xl bg-violet-50 p-3 text-violet-600">
                <Sparkles size={20} />
              </div>

              <div>
                <h2 className="text-lg font-extrabold text-slate-900">
                  Create campaign proposal
                </h2>

                <p className="mt-1 text-sm leading-5 text-slate-500">
                  Describe the business goal in
                  natural language. PayPilot will
                  propose products and actions.
                </p>
              </div>

            </div>

            <form
              onSubmit={handleGenerate}
              className="space-y-4"
            >

              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">
                  Campaign goal
                </label>

                <textarea
                  value={brief}
                  onChange={(event) =>
                    setBrief(
                      event.target.value
                    )
                  }
                  rows={7}
                  placeholder="Example: Increase sales of laptops by promoting accessories with a 5% offer."
                  className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">

                <div>
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">
                    Campaign name{" "}
                    <span className="font-normal">
                      (optional)
                    </span>
                  </label>

                  <input
                    type="text"
                    value={campaignName}
                    onChange={(event) =>
                      setCampaignName(
                        event.target.value
                      )
                    }
                    placeholder="Laptop Growth Campaign"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wide text-slate-500">
                    Suggested discount %
                  </label>

                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={discount}
                    onChange={(event) =>
                      setDiscount(
                        event.target.value
                      )
                    }
                    placeholder="5"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-100"
                  />
                </div>

              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-800">

                <div className="flex items-start gap-2">

                  <ShieldCheck
                    size={16}
                    className="mt-0.5 shrink-0"
                  />

                  <span>
                    <strong>Phase 1:</strong> proposal
                    only. No discount is applied,
                    no product price changes, and
                    no campaign is activated.
                    Phase 2 validation, Phase 3 merchant approval,
                    and Phase 4 activation are required before
                    the campaign becomes active.
                  </span>

                </div>

              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-extrabold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >

                {loading ? (
                  <RefreshCw
                    size={17}
                    className="animate-spin"
                  />
                ) : (
                  <Sparkles size={17} />
                )}

                {loading
                  ? "Generating proposal..."
                  : "Generate Campaign Proposal"}

              </button>

            </form>

          </section>

          {/* ===================================================
              SELECTED PROPOSAL
          ==================================================== */}

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

            {selected ? (

              <div>

                {/* =================================================
                    HEADER
                ================================================== */}

                <div className="mb-5 flex items-start justify-between gap-4">

                  <div>

                    <div className="mb-2 flex flex-wrap items-center gap-2">

                      <h2 className="text-xl font-black text-slate-950">
                        {selected.name}
                      </h2>

                      <StatusBadge
                        proposal={selected}
                      />

                    </div>

                    <p className="text-sm text-slate-500">
                      {selected.brief}
                    </p>

                  </div>

                  {loadingSelected && (
                    <RefreshCw
                      size={18}
                      className="shrink-0 animate-spin text-blue-600"
                    />
                  )}

                </div>

                {/* =================================================
                    METRICS
                ================================================== */}

                <div className="grid gap-3 sm:grid-cols-3">

                  <Metric
                    label="Objective"
                    value={statusLabel(
                      selected.objective
                    )}
                  />

                  <Metric
                    label="Strategy"
                    value={statusLabel(
                      selected.strategy_type
                    )}
                  />

                  <Metric
                    label="Suggested discount"
                    value={`${Number(
                      selected.suggested_discount_percent ||
                        0
                    ).toFixed(2)}%`}
                  />

                </div>

                {/* =================================================
                    PHASE 2
                ================================================== */}

                {isDraft(selected) && (

                  <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4">

                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">

                      <div className="flex items-start gap-3">

                        <ShieldCheck
                          size={20}
                          className="mt-0.5 shrink-0 text-blue-600"
                        />

                        <div>

                          <p className="text-sm font-extrabold text-blue-900">
                            Phase 2 — Policy & Margin Validation
                          </p>

                          <p className="mt-1 text-xs leading-5 text-blue-800">
                            PayPilot will check merchant
                            discount policy, minimum
                            margin, and selected product
                            safety constraints.
                            Nothing will be changed.
                          </p>

                        </div>

                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          handleValidate(
                            selected.id
                          )
                        }
                        disabled={validating}
                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-extrabold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                      >

                        {validating ? (
                          <RefreshCw
                            size={16}
                            className="animate-spin"
                          />
                        ) : (
                          <ShieldCheck size={16} />
                        )}

                        {validating
                          ? "Validating..."
                          : "Validate Proposal"}

                      </button>

                    </div>

                  </div>

                )}

                {/* =================================================
                    PHASE 3 APPROVAL
                ================================================== */}

                {canApproveMerchant(selected) && (

                  <div className="mt-5 rounded-xl border-2 border-emerald-300 bg-emerald-50 p-5">

                    <div className="flex items-start gap-3">

                      <CheckCircle2
                        size={24}
                        className="mt-0.5 shrink-0 text-emerald-600"
                      />

                      <div className="flex-1">

                        <p className="text-base font-black text-emerald-900">
                          Phase 3 — Merchant Approval Required
                        </p>

                        <p className="mt-1 text-sm leading-5 text-emerald-800">
                          Policy and margin validation
                          passed. The merchant must
                          approve or reject this proposal.
                        </p>

                        <div className="mt-4 rounded-lg border border-emerald-200 bg-white/70 p-3">

                          <p className="text-xs font-bold text-emerald-800">
                            Important
                          </p>

                          <p className="mt-1 text-xs leading-5 text-slate-600">
                            Approve records merchant
                            authorization only.
                            It does NOT change product
                            prices, inventory, orders,
                            or payments.
                          </p>

                        </div>

                        <div className="mt-5 grid gap-3 sm:grid-cols-2">

                          <button
                            type="button"
                            onClick={() =>
                              handleApprove(
                                selected.id
                              )
                            }
                            disabled={
                              approving ||
                              rejecting
                            }
                            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-black text-white shadow-md transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                          >

                            {approving ? (
                              <RefreshCw
                                size={18}
                                className="animate-spin"
                              />
                            ) : (
                              <CheckCircle2
                                size={18}
                              />
                            )}

                            {approving
                              ? "Approving..."
                              : "Approve Campaign"}

                          </button>

                          <button
                            type="button"
                            onClick={() =>
                              handleReject(
                                selected.id
                              )
                            }
                            disabled={
                              approving ||
                              rejecting
                            }
                            className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl border-2 border-red-300 bg-white px-5 py-3 text-sm font-black text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                          >

                            {rejecting ? (
                              <RefreshCw
                                size={18}
                                className="animate-spin"
                              />
                            ) : (
                              <XCircle size={18} />
                            )}

                            {rejecting
                              ? "Rejecting..."
                              : "Reject Campaign"}

                          </button>

                        </div>

                      </div>

                    </div>

                  </div>

                )}

                {/* =================================================
                    MERCHANT APPROVED
                ================================================== */}

                {isMerchantApproved(selected) && (

                  <div className="mt-5 rounded-xl border-2 border-blue-300 bg-blue-50 p-5">

                    <div className="flex items-start gap-3">

                      <CheckCircle2
                        size={24}
                        className="mt-0.5 shrink-0 text-blue-600"
                      />

                      <div>

                        <p className="text-base font-black text-blue-900">
                          Phase 3 — Merchant Approved
                        </p>

                        <p className="mt-1 text-sm leading-5 text-blue-800">
                          The merchant has approved this campaign proposal.
                          Approval does not activate the campaign. A separate
                          Phase 4 activation step is required.
                        </p>

                        <div className="mt-4 flex flex-wrap gap-2">

                          <span className="rounded-full bg-blue-100 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-blue-700">
                            Merchant Approved
                          </span>

                          {!isCampaignActive(
                            selected
                          ) && (
                            <span className="rounded-full bg-amber-100 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-amber-700">
                              Activation Pending
                            </span>
                          )}

                          {canActivateCampaign(
                            selected
                          ) && (
                            <span className="rounded-full bg-violet-100 px-3 py-1 text-[10px] font-black uppercase tracking-wide text-violet-700">
                              Ready for Phase 4
                            </span>
                          )}

                        </div>

                      </div>

                    </div>

                  </div>

                )}

                {/* =================================================
                    PHASE 4 ACTIVATION
                ================================================== */}

                {selected &&
                  isMerchantApproved(selected) &&
                  !isCampaignActive(selected) && (

                  <section className="mt-5 rounded-2xl border-2 border-blue-300 bg-blue-50 p-5">

                    <div className="flex items-start gap-3">

                      <div className="rounded-xl bg-blue-600 p-3 text-white">
                        <ArrowRight size={20} />
                      </div>

                      <div className="flex-1">

                        <h3 className="text-lg font-extrabold text-slate-900">
                          Phase 4 — Activate Campaign
                        </h3>

                        <p className="mt-1 text-sm leading-6 text-slate-600">
                          Merchant approval is complete. The campaign is
                          authorized for activation, but it is not active yet.
                          Activation is a separate Phase 4 action.
                        </p>

                        <div className="mt-4 grid gap-3 sm:grid-cols-3">

                          <div className="rounded-xl border border-emerald-200 bg-white p-3">
                            <div className="text-xs font-bold uppercase text-slate-400">
                              Merchant Approval
                            </div>
                            <div className="mt-1 flex items-center gap-2 text-sm font-bold text-emerald-700">
                              <CheckCircle2 size={16} />
                              APPROVED
                            </div>
                          </div>

                          <div className="rounded-xl border border-amber-200 bg-white p-3">
                            <div className="text-xs font-bold uppercase text-slate-400">
                              Activation
                            </div>
                            <div className="mt-1 flex items-center gap-2 text-sm font-bold text-amber-700">
                              <Clock3 size={16} />
                              {getActivationStatus(selected)}
                            </div>
                          </div>

                          <div className="rounded-xl border border-slate-200 bg-white p-3">
                            <div className="text-xs font-bold uppercase text-slate-400">
                              Campaign Active
                            </div>
                            <div className="mt-1 text-sm font-bold text-slate-700">
                              No
                            </div>
                          </div>

                        </div>

                        <div className="mt-4 rounded-xl border border-blue-200 bg-white p-4">
                          <div className="grid gap-2 text-sm sm:grid-cols-2">

                            <div>
                              Product price changed:
                              <strong className="ml-2">
                                {getGovernanceBoolean(
                                  selected,
                                  "price_changed"
                                ) ? "Yes" : "No"}
                              </strong>
                            </div>

                            <div>
                              Inventory changed:
                              <strong className="ml-2">
                                {getGovernanceBoolean(
                                  selected,
                                  "inventory_changed"
                                ) ? "Yes" : "No"}
                              </strong>
                            </div>

                            <div>
                              Payment created:
                              <strong className="ml-2">
                                {getGovernanceBoolean(
                                  selected,
                                  "payment_created"
                                ) ? "Yes" : "No"}
                              </strong>
                            </div>

                            <div>
                              Order changed:
                              <strong className="ml-2">
                                {getGovernanceBoolean(
                                  selected,
                                  "order_changed"
                                ) ? "Yes" : "No"}
                              </strong>
                            </div>

                          </div>
                        </div>

                        <div className="mt-5 flex flex-wrap items-center gap-3">

                          <button
                            type="button"
                            onClick={() =>
                              handleActivate(selected.id)
                            }
                            disabled={
                              activating ||
                              !canActivateCampaign(selected)
                            }
                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-extrabold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {activating ? (
                              <>
                                <RefreshCw
                                  size={17}
                                  className="animate-spin"
                                />
                                Activating...
                              </>
                            ) : (
                              <>
                                <ArrowRight size={17} />
                                Activate Campaign
                              </>
                            )}
                          </button>

                          {!canActivateCampaign(selected) && (
                            <span className="text-xs font-semibold text-slate-500">
                              Campaign is not currently eligible for activation.
                            </span>
                          )}

                        </div>

                      </div>
                    </div>
                  </section>
                )}

                {/* =================================================
                    MERCHANT REJECTED
                ================================================== */}

                {isMerchantRejected(selected) && (

                  <div className="mt-5 rounded-xl border-2 border-red-300 bg-red-50 p-5">

                    <div className="flex items-start gap-3">

                      <XCircle
                        size={24}
                        className="mt-0.5 shrink-0 text-red-600"
                      />

                      <div>

                        <p className="text-base font-black text-red-900">
                          Phase 3 — Merchant Rejected
                        </p>

                        <p className="mt-1 text-sm leading-5 text-red-800">
                          The merchant rejected this
                          campaign proposal.
                          It cannot proceed to activation.
                        </p>

                      </div>

                    </div>

                  </div>

                )}

                {/* =================================================
                    ACTIVE CAMPAIGN
                ================================================== */}

                {isCampaignActive(selected) && (

                  <div className="mt-5 rounded-xl border-2 border-green-300 bg-green-50 p-5">

                    <div className="flex items-start gap-3">

                      <CheckCircle2
                        size={24}
                        className="mt-0.5 shrink-0 text-green-600"
                      />

                      <div>

                        <p className="text-base font-black text-green-900">
                          Campaign is Active
                        </p>

                        <p className="mt-1 text-sm leading-5 text-green-800">
                          The backend has explicitly
                          marked this campaign as active.
                        </p>

                      </div>

                    </div>

                  </div>

                )}

                {/* =================================================
                    VALIDATION RESULT
                ================================================== */}

                {(
                  isPolicyApproved(selected) ||
                  isPolicyRejected(selected) ||
                  isMerchantApproved(selected) ||
                  isMerchantRejected(selected)
                ) && (

                  <ValidationResult
                    proposal={selected}
                  />

                )}

                {/* =================================================
                    PRODUCTS
                ================================================== */}

                <div className="mt-6">

                  <div className="mb-3 flex items-center gap-2 text-sm font-extrabold text-slate-900">
                    <Package size={17} />
                    Proposed products
                  </div>

                  {selected.product_ids?.length > 0 ? (

                    <div className="grid gap-2 sm:grid-cols-2">

                      {selected.product_ids.map(
                        (productId) => (
                          <div
                            key={productId}
                            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700"
                          >
                            Product #{productId}
                          </div>
                        )
                      )}

                    </div>

                  ) : (

                    <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                      No specific products were
                      proposed.
                    </div>

                  )}

                </div>

                {/* =================================================
                    ACTIONS
                ================================================== */}

                <div className="mt-6">

                  <div className="mb-3 flex items-center gap-2 text-sm font-extrabold text-slate-900">
                    <ArrowRight size={17} />
                    Proposed actions
                  </div>

                  {selected.proposed_actions?.length > 0 ? (

                    <div className="space-y-2">

                      {selected.proposed_actions.map(
                        (action, index) => (

                          <div
                            key={`${action?.type || "action"}-${index}`}
                            className="rounded-xl border border-slate-200 p-4"
                          >

                            <div className="flex items-center justify-between gap-3">

                              <span className="text-xs font-black uppercase tracking-wide text-blue-700">
                                {statusLabel(
                                  action?.type ||
                                    "RECOMMENDATION"
                                )}
                              </span>

                              {action?.money_action ? (

                                <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700">
                                  Money-related
                                </span>

                              ) : (

                                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">
                                  Recommendation
                                </span>

                              )}

                            </div>

                            <p className="mt-2 text-sm leading-5 text-slate-600">
                              {action?.description ||
                                "No description provided."}
                            </p>

                          </div>

                        )
                      )}

                    </div>

                  ) : (

                    <div className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                      No proposed actions returned.
                    </div>

                  )}

                </div>

                {/* =================================================
                    EXPLANATION
                ================================================== */}

                <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-4">

                  <div className="flex items-start gap-3">

                    <CheckCircle2
                      size={18}
                      className="mt-0.5 shrink-0 text-blue-600"
                    />

                    <div>

                      <p className="text-sm font-extrabold text-blue-900">
                        Why PayPilot proposed this
                      </p>

                      <p className="mt-1 text-sm leading-6 text-blue-800">
                        {getSafeExplanation(
                          selected
                        )}
                      </p>

                    </div>

                  </div>

                </div>

                {/* =================================================
                    GOVERNANCE SUMMARY
                ================================================== */}

                <div className="mt-5 grid gap-3 sm:grid-cols-3">

                  <Governance
                    label="Policy check"
                    value={
                      isPolicyApproved(
                        selected
                      )
                        ? "APPROVED"
                        : isPolicyRejected(
                            selected
                          )
                        ? "REJECTED"
                        : "Required"
                    }
                  />

                  <Governance
                    label="Margin check"
                    value={
                      isPolicyApproved(
                        selected
                      ) ||
                      isPolicyRejected(
                        selected
                      )
                        ? "COMPLETED"
                        : "Required"
                    }
                  />

                  <Governance
                    label="Merchant approval"
                    value={
                      isMerchantApproved(
                        selected
                      )
                        ? "APPROVED"
                        : isMerchantRejected(
                            selected
                          )
                        ? "REJECTED"
                        : "Required"
                    }
                  />

                </div>

                {/* =================================================
                    ACTIVATION STATE
                ================================================== */}

                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">

                  <div className="flex items-start gap-3">

                    <ArrowRight
                      size={18}
                      className="mt-0.5 shrink-0 text-slate-600"
                    />

                    <div>

                      <p className="text-sm font-extrabold text-slate-900">
                        Activation state
                      </p>

                      <p className="mt-1 text-xs leading-5 text-slate-600">
                        {isCampaignActive(
                          selected
                        )
                          ? "Campaign is currently active. This state comes from explicit backend activation."
                          : isMerchantApproved(
                              selected
                            )
                          ? "Merchant approval is complete. The campaign is approved for activation, but the separate activation step has not happened yet."
                          : isMerchantRejected(
                              selected
                            )
                          ? "Merchant rejected the campaign. Activation is not allowed."
                          : isPolicyApproved(
                              selected
                            )
                          ? "Policy and margin validation passed. Merchant approval is still required."
                          : "This is a proposal only. Phase 2 validation is required."}
                      </p>

                    </div>

                  </div>

                </div>

                {/* =================================================
                    SAFETY STATE
                ================================================== */}

                <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">

                  <div className="mb-3 flex items-center gap-2">

                    <ShieldCheck
                      size={17}
                      className="text-slate-700"
                    />

                    <p className="text-sm font-extrabold text-slate-900">
                      Campaign safety state
                    </p>

                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">

                    <SafetyItem
                      label="Campaign active"
                      value={
                        isCampaignActive(
                          selected
                        )
                          ? "Yes"
                          : "No"
                      }
                      positive={
                        isCampaignActive(
                          selected
                        )
                      }
                    />

                    <SafetyItem
                      label="Product price changed"
                      value={
                        getGovernanceBoolean(
                          selected,
                          "price_changed"
                        )
                          ? "Yes"
                          : "No"
                      }
                      positive={
                        !getGovernanceBoolean(
                          selected,
                          "price_changed"
                        )
                      }
                    />

                    <SafetyItem
                      label="Inventory changed"
                      value={
                        getGovernanceBoolean(
                          selected,
                          "inventory_changed"
                        )
                          ? "Yes"
                          : "No"
                      }
                      positive={
                        !getGovernanceBoolean(
                          selected,
                          "inventory_changed"
                        )
                      }
                    />

                    <SafetyItem
                      label="Payment created"
                      value={
                        getGovernanceBoolean(
                          selected,
                          "payments_changed",
                          getGovernanceBoolean(
                            selected,
                            "payment_created"
                          )
                        )
                          ? "Yes"
                          : "No"
                      }
                      positive={
                        !getGovernanceBoolean(
                          selected,
                          "payments_changed",
                          getGovernanceBoolean(
                            selected,
                            "payment_created"
                          )
                        )
                      }
                    />

                    <SafetyItem
                      label="Order changed"
                      value={
                        getGovernanceBoolean(
                          selected,
                          "orders_changed"
                        )
                          ? "Yes"
                          : "No"
                      }
                      positive={
                        !getGovernanceBoolean(
                          selected,
                          "orders_changed"
                        )
                      }
                    />

                    <SafetyItem
                      label="Merchant approval"
                      value={
                        isMerchantApproved(
                          selected
                        )
                          ? "Approved"
                          : isMerchantRejected(
                              selected
                            )
                          ? "Rejected"
                          : "Required"
                      }
                      positive={
                        isMerchantApproved(
                          selected
                        )
                      }
                    />

                  </div>

                </div>

                {/* =================================================
                    GOVERNANCE DETAILS
                ================================================== */}

                <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4">

                  <div className="grid gap-2 sm:grid-cols-2">

                    <SafetyFlag
                      label="Can activate"
                      value={
                        canActivateCampaign(
                          selected
                        )
                          ? "Yes"
                          : "No"
                      }
                    />

                    <SafetyFlag
                      label="Activation status"
                      value={
                        getActivationStatus(
                          selected
                        )
                      }
                    />

                  </div>

                </div>

                {/* =================================================
                    FOOTER
                ================================================== */}

                <div className="mt-5 flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">

                  <div className="flex items-center gap-2 text-xs font-bold text-slate-600">

                    <Clock3 size={15} />

                    {isCampaignActive(
                      selected
                    )
                      ? "Campaign active"
                      : isMerchantApproved(
                          selected
                        )
                      ? "Merchant approved — activation pending"
                      : isMerchantRejected(
                          selected
                        )
                      ? "Merchant rejected — campaign cannot proceed"
                      : isPolicyApproved(
                          selected
                        )
                      ? "Policy approved — waiting for merchant approval"
                      : isPolicyRejected(
                          selected
                        )
                      ? "Policy rejected — campaign cannot proceed"
                      : "Not active — proposal only"}

                  </div>

                  {canDeleteProposal(
                    selected
                  ) && (

                    <button
                      type="button"
                      onClick={() =>
                        handleDelete(
                          selected.id
                        )
                      }
                      disabled={deleting}
                      className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >

                      {deleting ? (
                        <RefreshCw
                          size={14}
                          className="animate-spin"
                        />
                      ) : (
                        <Trash2 size={14} />
                      )}

                      {deleting
                        ? "Deleting..."
                        : "Delete draft"}

                    </button>

                  )}

                </div>

              </div>

            ) : (

              <div className="flex min-h-[520px] flex-col items-center justify-center text-center">

                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                  <BarChart3 size={28} />
                </div>

                <h2 className="mt-5 text-xl font-black text-slate-900">
                  Your campaign proposal will
                  appear here
                </h2>

                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
                  Start with a revenue,
                  order-value, cross-sell,
                  upsell, or inventory goal.
                </p>

              </div>

            )}

          </section>

        </div>

        {/* =====================================================
            PREVIOUS PROPOSALS
        ====================================================== */}

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

          <div className="mb-5 flex items-center justify-between gap-4">

            <div>

              <h2 className="text-lg font-black text-slate-900">
                Previous proposals
              </h2>

              <p className="text-sm text-slate-500">
                Only your merchant's campaign
                proposals are shown.
              </p>

            </div>

            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
              {campaigns.length} proposal
              {campaigns.length === 1
                ? ""
                : "s"}
            </span>

          </div>

          {loadingList ? (

            <div className="flex items-center justify-center py-10 text-sm text-slate-500">

              <RefreshCw
                size={16}
                className="mr-2 animate-spin"
              />

              Loading campaigns...

            </div>

          ) : campaigns.length === 0 ? (

            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
              No campaign proposals yet.
            </div>

          ) : (

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">

              {campaigns.map(
                (campaign) => (

                  <button
                    type="button"
                    key={campaign.id}
                    onClick={() =>
                      handleSelectCampaign(
                        campaign
                      )
                    }
                    className={`rounded-xl border p-4 text-left transition hover:border-blue-300 hover:shadow-sm ${
                      selected?.id ===
                      campaign.id
                        ? "border-blue-400 bg-blue-50/40"
                        : "border-slate-200"
                    }`}
                  >

                    <div className="flex items-start justify-between gap-3">

                      <div>

                        <p className="font-extrabold text-slate-900">
                          {campaign.name}
                        </p>

                        <p className="mt-1 text-xs text-slate-500">
                          #{campaign.id} ·{" "}
                          {statusLabel(
                            campaign.strategy_type
                          )}
                        </p>

                      </div>

                      <StatusBadge
                        proposal={campaign}
                      />

                    </div>

                    <p className="mt-3 line-clamp-2 text-sm leading-5 text-slate-600">
                      {campaign.brief}
                    </p>

                  </button>

                )
              )}

            </div>

          )}

        </section>

      </div>
    </div>
  );
}

// =============================================================
// SAFE EXPLANATION
// =============================================================

function getSafeExplanation(proposal) {
  let base =
    proposal?.explanation ||
    "PayPilot generated this proposal based on the campaign goal.";

  /*
   * The backend may contain an older explanation such as:
   * "The campaign is now active."
   *
   * The UI must never display a statement that contradicts the
   * authoritative governance state, so remove legacy activation
   * wording whenever the campaign is not actually active.
   */
  if (!isCampaignActive(proposal)) {
    base = base
      .replace(
        /Phase 3 merchant approval completed\.\s*The merchant approved the campaign with an approved discount of ([0-9.]+)%.\s*The campaign is now active\.?/gi,
        "Phase 3 merchant approval completed. The merchant approved the campaign with an approved discount of $1%."
      )
      .replace(
        /The campaign is now active\.?/gi,
        "The campaign is approved for activation, but it is not active yet."
      );
  }

  if (isCampaignActive(proposal)) {
    return `${base} Current system state: the campaign is ACTIVE. Phase 4 activation has completed.`;
  }

  if (isMerchantApproved(proposal)) {
    return `${base} Current system state: merchant approval is APPROVED, the campaign is NOT active, and activation status is PENDING. A separate Phase 4 activation step is required.`;
  }

  if (isMerchantRejected(proposal)) {
    return `${base} Current system state: merchant approval is REJECTED, the campaign is NOT active, and activation is not allowed.`;
  }

  if (isPolicyApproved(proposal)) {
    return `${base} Current system state: policy and margin validation are APPROVED, merchant approval is still REQUIRED, and the campaign is NOT active.`;
  }

  return `${base} Current system state: this is a DRAFT proposal. Phase 2 validation is required and the campaign is NOT active.`;
}

// =============================================================
// STATUS BADGE
// =============================================================

function StatusBadge({ proposal }) {
  const status =
    normalizeStatus(proposal?.status);

  let displayStatus = status || "DRAFT";

  // Canonical lifecycle:
  // DRAFT -> POLICY_APPROVED -> MERCHANT_APPROVED -> ACTIVE.
  // Legacy APPROVED is treated as Phase 3 approval unless the
  // backend explicitly marks the campaign ACTIVE.

  /*
   * If backend returns generic APPROVED but governance
   * explicitly says merchant approval completed, display
   * the more meaningful Phase 3 state.
   */
  if (
    status === "APPROVED" &&
    !isCampaignActive(proposal)
  ) {
    displayStatus = "MERCHANT_APPROVED";
  }

  if (
    status === "APPROVED" &&
    isCampaignActive(proposal)
  ) {
    displayStatus = "ACTIVE";
  }

  let classes =
    "bg-slate-100 text-slate-600";

  if (
    displayStatus ===
    "POLICY_APPROVED"
  ) {
    classes =
      "bg-emerald-100 text-emerald-700";
  }

  if (
    displayStatus ===
    "POLICY_REJECTED"
  ) {
    classes =
      "bg-red-100 text-red-700";
  }

  if (
    displayStatus ===
    "MERCHANT_APPROVED"
  ) {
    classes =
      "bg-blue-100 text-blue-700";
  }

  if (
    displayStatus ===
    "MERCHANT_REJECTED"
  ) {
    classes =
      "bg-red-100 text-red-700";
  }

  if (
    displayStatus ===
    "ACTIVE"
  ) {
    classes =
      "bg-green-100 text-green-700";
  }

  if (
    displayStatus ===
    "PENDING"
  ) {
    classes =
      "bg-amber-100 text-amber-700";
  }

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold uppercase tracking-wide ${classes}`}
    >
      {statusLabel(displayStatus)}
    </span>
  );
}

// =============================================================
// VALIDATION RESULT
// =============================================================

function ValidationResult({
  proposal,
}) {
  const policyApproved =
    isPolicyApproved(proposal);

  const policyRejected =
    isPolicyRejected(proposal);

  const governance =
    getGovernance(proposal);

  const policy =
    getPolicyValidation(proposal);

  const margin =
    getMarginValidation(proposal);

  const products =
    getProductValidation(proposal);

  const validationPassed =
    governance?.validation_passed;

  const approved =
    validationPassed !== undefined
      ? validationPassed === true
      : policyApproved;

  return (
    <div
      className={`mt-5 rounded-xl border p-5 ${
        approved
          ? "border-emerald-200 bg-emerald-50"
          : "border-red-200 bg-red-50"
      }`}
    >

      <div className="flex items-start gap-3">

        {approved ? (
          <CheckCircle2
            size={22}
            className="mt-0.5 shrink-0 text-emerald-600"
          />
        ) : (
          <XCircle
            size={22}
            className="mt-0.5 shrink-0 text-red-600"
          />
        )}

        <div className="flex-1">

          <p
            className={`text-sm font-black ${
              approved
                ? "text-emerald-900"
                : "text-red-900"
            }`}
          >
            {approved
              ? "Policy validation approved"
              : "Policy validation rejected"}
          </p>

          <p
            className={`mt-1 text-xs leading-5 ${
              approved
                ? "text-emerald-800"
                : "text-red-800"
            }`}
          >
            {approved
              ? "The proposed discount passed the merchant policy and minimum-margin checks."
              : "One or more policy, margin, or product checks failed. The campaign cannot proceed."}
          </p>

        </div>

      </div>

      {/* POLICY / MARGIN */}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">

        <ValidationSummary
          label="Policy"
          value={getValidationValue(
            policy,
            approved
          )}
          approved={approved}
        />

        <ValidationSummary
          label="Margin"
          value={getValidationValue(
            margin,
            approved
          )}
          approved={approved}
        />

      </div>

      {/* PRODUCTS */}

      {Array.isArray(products) &&
        products.length > 0 && (

          <div className="mt-4">

            <p
              className={`mb-2 text-xs font-black uppercase tracking-wide ${
                approved
                  ? "text-emerald-800"
                  : "text-red-800"
              }`}
            >
              Product checks
            </p>

            <div className="space-y-2">

              {products.map(
                (product, index) => {

                  const productApproved =
                    product?.approved ??
                    product?.valid ??
                    product?.passed ??
                    true;

                  return (
                    <div
                      key={
                        product?.product_id ||
                        product?.id ||
                        index
                      }
                      className="flex items-center justify-between gap-3 rounded-lg border border-white/70 bg-white/70 px-3 py-2"
                    >

                      <span className="text-xs font-semibold text-slate-700">
                        Product #
                        {product?.product_id ||
                          product?.id ||
                          "—"}
                      </span>

                      <span
                        className={`text-[10px] font-extrabold uppercase ${
                          productApproved
                            ? "text-emerald-700"
                            : "text-red-700"
                        }`}
                      >
                        {productApproved
                          ? "PASS"
                          : "FAIL"}
                      </span>

                    </div>
                  );
                }
              )}

            </div>

          </div>

        )}

      {/* NEXT STEP */}

      <div className="mt-4 rounded-lg border border-white/70 bg-white/60 p-3">

        <p
          className={`text-xs font-black uppercase tracking-wide ${
            approved
              ? "text-emerald-800"
              : "text-red-800"
          }`}
        >
          Next step
        </p>

        <p className="mt-1 text-xs leading-5 text-slate-700">

          {isCampaignActive(proposal)
            ? "Campaign is active. The backend has explicitly completed the activation state."
            : isMerchantApproved(proposal)
            ? "Merchant approval is complete. The campaign is authorized for activation, but it is NOT active yet."
            : isMerchantRejected(proposal)
            ? "The merchant rejected this campaign. No activation is allowed."
            : approved
            ? "Merchant approval is still required. The campaign is NOT active and no price, inventory, order, or payment has been changed."
            : "Fix the failed policy or margin conditions before this proposal can proceed."}

        </p>

      </div>

      {/* GOVERNANCE FLAGS */}

      {governance && (

        <div className="mt-4 grid gap-2 sm:grid-cols-2">

          <SafetyFlag
            label="Can activate"
            value={
              governance.can_activate === true
                ? "Yes"
                : "No"
            }
          />

          <SafetyFlag
            label="Activation status"
            value={
              getActivationStatus(
                proposal
              )
            }
          />

        </div>

      )}

    </div>
  );
}

// =============================================================
// VALIDATION SUMMARY
// =============================================================

function ValidationSummary({
  label,
  value,
  approved,
}) {
  return (
    <div className="rounded-lg border border-white/70 bg-white/70 p-3">

      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p
        className={`mt-1 text-sm font-extrabold ${
          approved
            ? "text-emerald-800"
            : "text-red-800"
        }`}
      >
        {value}
      </p>

    </div>
  );
}

// =============================================================
// VALIDATION VALUE
// =============================================================

function getValidationValue(
  validation,
  approved
) {
  if (!validation) {
    return approved
      ? "Passed"
      : "Failed";
  }

  if (
    typeof validation ===
    "string"
  ) {
    return validation;
  }

  if (validation.message) {
    return validation.message;
  }

  if (validation.reason) {
    return validation.reason;
  }

  if (
    validation.approved !==
    undefined
  ) {
    return validation.approved
      ? "Passed"
      : "Failed";
  }

  if (
    validation.valid !==
    undefined
  ) {
    return validation.valid
      ? "Passed"
      : "Failed";
  }

  if (
    validation.passed !==
    undefined
  ) {
    return validation.passed
      ? "Passed"
      : "Failed";
  }

  return approved
    ? "Passed"
    : "Failed";
}

// =============================================================
// SAFETY FLAG
// =============================================================

function SafetyFlag({
  label,
  value,
}) {
  const positive =
    String(value).toUpperCase() ===
    "YES";

  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2">

      <span className="text-xs font-semibold text-slate-600">
        {label}
      </span>

      <span
        className={`text-xs font-extrabold ${
          positive
            ? "text-emerald-700"
            : "text-slate-600"
        }`}
      >
        {value}
      </span>

    </div>
  );
}

// =============================================================
// SAFETY ITEM
// =============================================================

function SafetyItem({
  label,
  value,
  positive = true,
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2">

      <span className="text-xs font-semibold text-slate-600">
        {label}
      </span>

      <span
        className={`text-xs font-extrabold ${
          positive
            ? "text-emerald-700"
            : "text-red-700"
        }`}
      >
        {value}
      </span>

    </div>
  );
}

// =============================================================
// METRIC
// =============================================================

function Metric({
  label,
  value,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">

      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="mt-1 text-sm font-extrabold text-slate-800">
        {value}
      </p>

    </div>
  );
}

// =============================================================
// GOVERNANCE
// =============================================================

function Governance({
  label,
  value,
}) {
  const normalized =
    String(value ?? "").toUpperCase();

  const approved =
    normalized.includes("APPROVED") ||
    normalized.includes("COMPLETED") ||
    normalized === "ACTIVE";

  const rejected =
    normalized.includes("REJECTED");

  const pending =
    normalized.includes("PENDING") ||
    normalized.includes("NOT_STARTED");

  let classes =
    "border-amber-200 bg-amber-50 text-amber-700";

  if (approved) {
    classes =
      "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  if (rejected) {
    classes =
      "border-red-200 bg-red-50 text-red-700";
  }

  if (pending) {
    classes =
      "border-amber-200 bg-amber-50 text-amber-700";
  }

  return (
    <div
      className={`rounded-xl border p-3 ${classes}`}
    >

      <p className="text-[10px] font-bold uppercase tracking-wide">
        {label}
      </p>

      <p className="mt-1 text-sm font-extrabold">
        {value}
      </p>

    </div>
  );
}