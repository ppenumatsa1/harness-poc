"""Fake checkout business systems for the Order 1000 scenario (used by Lessons 6-8).

In a real app these would be HTTP calls to the Order API, Payment API, and log store.
"""

ORDERS = {
    "1000": {
        "order_id": "1000",
        "status": "PAYMENT_FAILED",
        "total": "84.20 USD",
        "items": [{"sku": "SKU-RED-MUG", "qty": 2}],
        "reservation_id": "RES-77",
    },
}

PAYMENTS = {
    "1000": {
        "order_id": "1000",
        "payment_id": "PAY-501",
        "status": "AUTHORIZED",  # authorized but never captured
        "card": "4111 1111 1111 1111",  # sensitive: Lesson 6 redacts this
        "amount": "84.20 USD",
    },
}

LOGS = {
    "1000": [
        "10:00:01 checkout-api  order 1000 created, reservation RES-77 ttl=120s",
        "10:00:04 payment-api   PAY-501 authorized 84.20 USD",
        "10:02:01 inventory     reservation RES-77 EXPIRED",
        "10:02:05 payment-api   capture PAY-501 rejected: RESERVATION_EXPIRED",
        "10:02:05 checkout-api  order 1000 -> PAYMENT_FAILED",
    ],
}
