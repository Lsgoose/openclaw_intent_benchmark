-- Safe online B-Tree index creation for 500M row orders table with no write downtime
-- Uses MySQL 8.0+ online DDL: ALGORITHM=INPLACE (no table copy) + LOCK=NONE (no write locks)
-- Equivalent for PostgreSQL: CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders (user_id);

ALTER TABLE orders 
ADD INDEX idx_orders_user_id (user_id),
ALGORITHM=INPLACE,
LOCK=NONE;

-- Verification
SELECT 
  TABLE_NAME,
  INDEX_NAME,
  NON_UNIQUE,
  INDEX_TYPE
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'orders' 
AND INDEX_NAME = 'idx_orders_user_id';
