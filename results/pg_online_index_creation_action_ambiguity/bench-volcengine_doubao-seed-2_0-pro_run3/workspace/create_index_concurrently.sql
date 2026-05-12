-- Create B-Tree index on user_id column of orders table
-- Using CONCURRENTLY to avoid long-duration table-level locks
-- This allows writes to continue during index creation
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);