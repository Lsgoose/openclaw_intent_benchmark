#!/bin/bash
# Script to safely create index on orders.user_id with minimal locking

echo "Starting index creation on orders.user_id..."

# Check if index already exists (PostgreSQL syntax)
echo "Checking if index idx_orders_user_id already exists..."
psql -c "SELECT 1 FROM pg_indexes WHERE tablename = 'orders' AND indexname = 'idx_orders_user_id';" || echo "Proceeding with index creation..."

# Create index concurrently to avoid blocking writes
echo "Creating index concurrently (this may take some time for 500M rows)..."
psql -c "CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);"

# Check index creation status
echo "Index creation command issued. Checking status..."
psql -c "SELECT schemaname, tablename, indexname, indexdef FROM pg_indexes WHERE tablename = 'orders' AND indexname = 'idx_orders_user_id';"

echo "Index creation process initiated. The CONCURRENTLY option allows writes to continue during index creation."