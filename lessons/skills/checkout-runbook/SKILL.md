---
name: checkout-runbook
description: Runbook for investigating a failed checkout order (order, payment, logs, verdict). Use for any checkout or payment failure question.
---

# Checkout failure runbook (v3)

1. Call `get_order`, `get_payment` and `get_logs` for the order id, in parallel.
2. Find the FIRST failing log line. Quote it exactly.
3. Classify the failure as one of: RESERVATION_EXPIRED, CARD_DECLINED, FRAUD_HOLD, OTHER.
4. Never propose a refund. Refunds are a business decision for the App.

Reply in exactly this format:

RUNBOOK: checkout-runbook v3
CLASS: <class>
FIRST FAILURE: <quoted log line>
ROOT CAUSE: <one line>
