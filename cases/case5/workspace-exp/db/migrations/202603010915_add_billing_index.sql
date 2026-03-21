BEGIN;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_events_customer_created_at
  ON invoice_events (customer_id, created_at DESC);
COMMIT;
