Detailed architecture diagrams such as:

AI Buyer
   │
   ▼
Commerce Agent
   │
   ▼
Agent-readable Catalog
   │
   ▼
Product Recommendation
   │
   ├── Upsell
   └── Cross-sell
   │
   ▼
Order Creation
   │
   ▼
Policy Engine
   │
   ▼
Risk Engine
   │
   ├── LOW RISK ──────────────┐
   │                          │
   └── MANUAL REVIEW          │
            │                 │
            ▼                 │
       Merchant Decision      │
            │                 │
            └────────┬────────┘
                     ▼
               Payment Gate
                     │
                     ▼
             Razorpay Checkout
                     │
                     ▼
             Payment Verification
                     │
                     ▼
                Audit Trail




 Merchant
   │
   ▼
AI Campaign Orchestrator
   │
   ▼
Campaign Proposal
   │
   ▼
Policy + Margin Validation
   │
   ▼
Merchant Approval
   │
   ▼
Explicit Activation
   │
   ▼
Campaign ACTIVE
   │
   ▼
Campaign Audit Events               