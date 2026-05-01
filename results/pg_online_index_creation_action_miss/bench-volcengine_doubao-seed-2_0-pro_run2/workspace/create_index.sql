-- For MySQL: Online DDL with no lock
ALTER TABLE orders ADD INDEX idx_orders_user_id (user_id), ALGORITHM=INPLACE, LOCK=NONE;

-- For PostgreSQL: Concurrent index without table lock
-- CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders (user_id);
