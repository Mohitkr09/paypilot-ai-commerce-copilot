# PayPilot — AI Commerce Copilot

PayPilot is an AI-powered commerce copilot that enables merchants to become
transactable by AI buyers while keeping every money-related action
Explainable, Bounded, Gated, and Auditable.

## Buildathon Track

AI Growth & Agentic Commerce

## Core Capabilities

- AI Commerce Copilot
- Agent-readable public product catalog
- Conversational shopping
- AI upsell and cross-sell recommendations
- Policy and margin engine
- AI risk assessment
- Automatic order approval
- Human exception / manual review
- Razorpay test-mode checkout
- Payment verification
- AI Campaign Orchestrator
- Campaign policy and margin validation
- Merchant campaign approval
- Explicit campaign activation
- Complete audit trail
- Graceful payment failure handling

## Architecture

AI Buyer
    ↓
Agent-readable Catalog
    ↓
Conversational Commerce
    ↓
Upsell / Cross-sell
    ↓
Order Engine
    ↓
Policy + Risk Engine
    ↓
Auto Approval / Human Review
    ↓
Payment Gate
    ↓
Razorpay
    ↓
Payment Verification
    ↓
Audit Trail

Merchant
    ↓
AI Campaign Orchestrator
    ↓
Campaign Proposal
    ↓
Policy + Margin Validation
    ↓
Merchant Approval
    ↓
Campaign Activation
    ↓
Campaign Audit Trail

## Safety Model

Every money-related action follows:

### Explainable

PayPilot explains:

- Why an order was approved or rejected
- Requested and approved discount
- Risk level
- Campaign selection
- Policy result
- Margin result
- Activation decision

### Bounded

The AI operates within:

- Merchant discount policies
- Minimum margin requirements
- Risk controls
- Payment gates
- Campaign validation rules

### Gated

Money-related actions require appropriate authorization:

- Automatic approval when policy permits
- Human merchant approval for exceptions
- Explicit campaign activation
- Buyer confirmation for purchases

### Auditable

Important actions are recorded in the audit trail:

- Order decisions
- Manual reviews
- Payment lifecycle
- Campaign proposal
- Campaign validation
- Merchant approval
- Campaign activation

## Campaign Lifecycle

Phase 1:
Campaign Proposal

↓

Phase 2:
Policy + Margin Validation

↓

Phase 3:
Merchant Approval

↓

Phase 4:
Campaign Activation

No campaign is activated before the required gates are passed.

## Technology

- Python
- FastAPI
- SQLAlchemy
- React
- JavaScript
- Razorpay Test Mode
- Gemini / AI model integration

## Running Locally

### Backend

```bash
cd backend
python -m venv venv