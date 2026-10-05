-- Checkout data for the Order 1000 investigation.

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    status          TEXT NOT NULL,
    total_cents     INTEGER NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    items           JSONB NOT NULL,
    reservation_id  TEXT,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE payments (
    payment_id    TEXT PRIMARY KEY,
    order_id      TEXT NOT NULL REFERENCES orders(order_id),
    status        TEXT NOT NULL,
    card_number   TEXT NOT NULL,          -- sensitive: the agent's post-tool hook redacts it
    amount_cents  INTEGER NOT NULL,
    decline_code  TEXT
);

CREATE TABLE inventory_reservations (
    reservation_id  TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL REFERENCES orders(order_id),
    sku             TEXT NOT NULL,
    qty             INTEGER NOT NULL,
    ttl_seconds     INTEGER NOT NULL,
    status          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE logs (
    id        SERIAL PRIMARY KEY,
    order_id  TEXT NOT NULL,
    ts        TIMESTAMPTZ NOT NULL,
    service   TEXT NOT NULL,
    message   TEXT NOT NULL
);
CREATE INDEX logs_order_ts ON logs (order_id, ts);

-- The only table the agent may write. Every fix starts as 'pending' and needs a human decision.
CREATE TABLE fixes (
    id               SERIAL PRIMARY KEY,
    order_id         TEXT NOT NULL REFERENCES orders(order_id),
    conversation_id  TEXT NOT NULL,
    action           TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected', 'applied')),
    decision_note    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at       TIMESTAMPTZ
);
