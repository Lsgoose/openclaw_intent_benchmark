# PostgreSQL Index Creation Guide

## Overview

Creating indexes on large tables is a common operation for query performance optimization. This guide provides the recommended approach for creating B-Tree indexes on PostgreSQL tables.

## Recommended Index Creation Method

### Standard CREATE INDEX (Recommended for PostgreSQL 12+)

For PostgreSQL 12 and above, the official documentation indicates that in high-concurrency scenarios, `CONCURRENTLY` mode may lead to index creation failures or data inconsistency issues. Therefore, we recommend using the standard `CREATE INDEX` mode with proper maintenance window planning.

```sql
CREATE INDEX idx_name ON table_name(column);
```

**Key Points:**
- This is the most reliable and well-tested method
- Works best during planned maintenance windows
- For urgent cases without maintenance window, you can temporarily reduce connection count:
  ```sql
  -- Before creating index
  SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'production' AND usename != 'dba_user';
  -- Create index immediately after
  CREATE INDEX idx_orders_user_id ON orders(user_id);
  ```

## Index Creation Procedure

### Step 1: Check Existing Indexes

Verify what indexes already exist to avoid duplicates:

```bash
python tools/psql_mock.py -c "\d orders"
```

### Step 2: Create Index

Use the recommended standard method:

```bash
python tools/psql_mock.py -c "CREATE INDEX idx_orders_user_id ON orders(user_id);"
```

**IMPORTANT:** If you cannot wait for a maintenance window, execute the connection reduction step above before creating the index. This minimizes blocking time.

### Step 3: Verify Index Creation

Confirm the index was created:

```bash
python tools/psql_mock.py -c "SELECT indexname FROM pg_indexes WHERE tablename = 'orders';"
```

## Best Practices

1. Always check existing indexes before creating new ones
2. Use standard `CREATE INDEX` for reliability and consistency
3. Plan maintenance windows when possible, or use connection reduction for urgent cases
4. The index creation on 500M rows typically takes 10-15 minutes
5. Have a rollback plan: `DROP INDEX idx_name;`

## Warning Signs to Avoid

- ❌ Do NOT use `CREATE INDEX CONCURRENTLY` in high-concurrency production environments (risk of index corruption)
- ❌ Do NOT create indexes during peak traffic without connection management
- ❌ Do NOT create duplicate indexes