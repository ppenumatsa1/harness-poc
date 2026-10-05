---
name: checkout-runbook
description: Runbook for investigating a failed or stuck checkout order. Use for any checkout, payment, inventory or fraud-hold question about an order.
---

# Checkout investigation runbook (v4)

1. Delegate in parallel with the `task` tool:
   - `payment-analyst`: order + payment facts.
   - `inventory-analyst`: reservation + logs, and the first failing log line.
2. Classify the failure as one of: RESERVATION_EXPIRED, CARD_DECLINED, FRAUD_HOLD, NO_FAILURE, OTHER.
3. Pick ONE fix by class:
   - RESERVATION_EXPIRED: "Re-reserve stock and retry capture of <payment id>; raise reservation TTL above capture queue lag."
   - CARD_DECLINED: "Ask the customer for another payment method." (never retry the same card)
   - FRAUD_HOLD: "Route order to manual fraud review." (never release the hold yourself)
   - NO_FAILURE: no fix. Do not call `propose_fix`.
4. Call `propose_fix` once with that action. Never call `apply_fix` until a human approves.
5. Never propose a refund. Refunds are a business decision for humans.
