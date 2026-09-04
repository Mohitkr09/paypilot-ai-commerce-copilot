# PayPilot — AI Commerce Copilot

 **AI-powered commerce infrastructure for AI buyers and merchant growth**

PayPilot is an AI-powered commerce copilot that enables merchants to become **transactable by AI buyers** while keeping every money-related action **Explainable, Bounded, Gated, and Auditable**.

The platform combines:

- AI-powered conversational shopping
- Agent-readable product catalog
- Multi-merchant product discovery
- AI upsell and cross-sell recommendations
- Policy and margin validation
- AI risk evaluation
- Human-in-the-loop exception handling
- Razorpay payment processing
- Payment verification
- Complete audit trail
- AI Campaign Orchestrator
- Campaign policy/margin validation
- Merchant approval
- Explicit campaign activation
- Campaign audit events
- Graceful failure handling

---

# Buildathon Track

## Track 01 — AI Growth & Agentic Commerce

### Objective

Help merchants increase revenue and/or become transactable by AI buyers.

PayPilot addresses both sides of this problem:

### AI Buyer

The AI Commerce Agent can:

1. Understand the buyer's request
2. Search the agent-readable catalog
3. Recommend products
4. Suggest bounded upsells and cross-sells
5. Create an order
6. Evaluate policy and risk
7. Automatically approve low-risk orders
8. Route exceptions to human review
9. Open Razorpay checkout
10. Verify payment
11. Record the complete transaction lifecycle

### Merchant

The AI Campaign Orchestrator can:

1. Convert a natural-language business goal into a campaign proposal
2. Select relevant products
3. Propose a promotion strategy
4. Validate policy and minimum margin
5. Request merchant approval
6. Keep activation as a separate gated step
7. Activate only after explicit authorization
8. Record campaign lifecycle events in the audit trail

---

#  Core Design Principle

Every money-related action in PayPilot follows:

## Explainable + Bounded + Gated + Auditable

### Explainable

PayPilot explains:

- Why a product was recommended
- Why an order was approved
- Why an order requires manual review
- Why a campaign was proposed
- Why a discount passed or failed validation
- Why a campaign can or cannot be activated
- What changed during activation

### Bounded

AI actions are constrained by explicit rules.

Examples:

- Discount policy
- Minimum-margin requirements
- Risk thresholds
- Payment limits
- Upsell price limits
- Cross-sell price limits
- Maximum recommendation count
- Campaign validation requirements

### Gated

The AI does not receive unrestricted authority over money movement.

Examples:

- Buyer confirmation is required before purchasing
- High-risk orders can require merchant approval
- Campaign activation is a separate explicit phase
- Razorpay payment happens through the payment gate
- Campaign price changes occur only during explicit activation

### Auditable

Important actions generate audit events.

Examples:

- Order decisions
- Manual-review decisions
- Payment creation
- Razorpay order creation
- Payment capture
- Campaign proposal creation
- Campaign validation
- Merchant campaign approval
- Campaign activation

---

#  Architecture

```text
                         ┌──────────────────────┐
                         │      Merchant        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ AI Campaign          │
                         │ Orchestrator         │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ Campaign Proposal             │
                    │ Products / Strategy / Discount│
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Policy + Margin      │
                         │ Validation            │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Merchant Approval    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Explicit Activation  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Campaign Active      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Audit Trail          │
                         └──────────────────────┘

                         
                          #Campaign Lifecycle

                          Phase 1
                          DRAFT
                            │
                            ▼
                          Phase 2
                      POLICY_APPROVED
                            │
                            ▼
                          Phase 3
                      MERCHANT_APPROVED
                             │
                             ▼
                           Phase 4
                            ACTIVE