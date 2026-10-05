-- 1000: reservation expired before capture (the main story)
-- 1001: healthy order
-- 1002: card declined
-- 1003: fraud hold

INSERT INTO orders VALUES
 ('1000', 'PAYMENT_FAILED', 8420,  'USD', '[{"sku": "SKU-RED-MUG", "qty": 2}]',   'RES-77', '2026-10-01 10:00:01+00'),
 ('1001', 'COMPLETED',      2599,  'USD', '[{"sku": "SKU-TEA-BOX", "qty": 1}]',   'RES-78', '2026-10-01 11:15:00+00'),
 ('1002', 'PAYMENT_FAILED', 12000, 'USD', '[{"sku": "SKU-KETTLE", "qty": 1}]',    'RES-79', '2026-10-01 12:30:00+00'),
 ('1003', 'ON_HOLD',        99900, 'USD', '[{"sku": "SKU-ESPRESSO", "qty": 3}]',  'RES-80', '2026-10-01 13:45:00+00');

INSERT INTO payments VALUES
 ('PAY-501', '1000', 'AUTHORIZED', '4111 1111 1111 1111', 8420,  NULL),
 ('PAY-502', '1001', 'CAPTURED',   '5500 0000 0000 0004', 2599,  NULL),
 ('PAY-503', '1002', 'DECLINED',   '4000 0000 0000 0002', 12000, 'INSUFFICIENT_FUNDS'),
 ('PAY-504', '1003', 'AUTHORIZED', '3782 822463 10005',   99900, NULL);

INSERT INTO inventory_reservations VALUES
 ('RES-77', '1000', 'SKU-RED-MUG',  2, 120, 'EXPIRED',  '2026-10-01 10:00:01+00'),
 ('RES-78', '1001', 'SKU-TEA-BOX',  1, 120, 'RELEASED', '2026-10-01 11:15:00+00'),
 ('RES-79', '1002', 'SKU-KETTLE',   1, 120, 'RELEASED', '2026-10-01 12:30:00+00'),
 ('RES-80', '1003', 'SKU-ESPRESSO', 3, 900, 'HELD',     '2026-10-01 13:45:00+00');

INSERT INTO logs (order_id, ts, service, message) VALUES
 ('1000', '2026-10-01 10:00:01+00', 'checkout-api', 'order 1000 created, reservation RES-77 ttl=120s'),
 ('1000', '2026-10-01 10:00:03+00', 'payment-gw',   'auth request card=4111 1111 1111 1111 amount=84.20'),
 ('1000', '2026-10-01 10:00:04+00', 'payment-api',  'PAY-501 authorized 84.20 USD'),
 ('1000', '2026-10-01 10:01:30+00', 'payment-api',  'capture queue lag 95s (normal < 5s)'),
 ('1000', '2026-10-01 10:02:01+00', 'inventory',    'reservation RES-77 EXPIRED'),
 ('1000', '2026-10-01 10:02:05+00', 'payment-api',  'capture PAY-501 rejected: RESERVATION_EXPIRED'),
 ('1000', '2026-10-01 10:02:05+00', 'checkout-api', 'order 1000 -> PAYMENT_FAILED'),
 ('1001', '2026-10-01 11:15:00+00', 'checkout-api', 'order 1001 created, reservation RES-78 ttl=120s'),
 ('1001', '2026-10-01 11:15:03+00', 'payment-api',  'PAY-502 authorized 25.99 USD'),
 ('1001', '2026-10-01 11:15:05+00', 'payment-api',  'capture PAY-502 ok'),
 ('1001', '2026-10-01 11:15:05+00', 'checkout-api', 'order 1001 -> COMPLETED'),
 ('1002', '2026-10-01 12:30:00+00', 'checkout-api', 'order 1002 created, reservation RES-79 ttl=120s'),
 ('1002', '2026-10-01 12:30:02+00', 'payment-api',  'PAY-503 declined: INSUFFICIENT_FUNDS'),
 ('1002', '2026-10-01 12:30:02+00', 'inventory',    'reservation RES-79 released'),
 ('1002', '2026-10-01 12:30:02+00', 'checkout-api', 'order 1002 -> PAYMENT_FAILED'),
 ('1003', '2026-10-01 13:45:00+00', 'checkout-api', 'order 1003 created, reservation RES-80 ttl=900s'),
 ('1003', '2026-10-01 13:45:02+00', 'payment-api',  'PAY-504 authorized 999.00 USD'),
 ('1003', '2026-10-01 13:45:03+00', 'risk-engine',  'order 1003 score 0.91 > 0.80 -> FRAUD_HOLD'),
 ('1003', '2026-10-01 13:45:03+00', 'checkout-api', 'order 1003 -> ON_HOLD');
