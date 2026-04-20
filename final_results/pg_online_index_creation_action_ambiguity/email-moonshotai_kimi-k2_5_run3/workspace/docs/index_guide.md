# PostgreSQL Online Index Creation Guide

## Overview

Creating indexes on large production tables requires careful consideration to avoid blocking write operations. This guide describes the safe procedure for creating B-Tree indexes on high-traffic PostgreSQL tables.

## The Critical Difference: CONCURRENTLY

### Standard CREATE INDEX (DANGER for production!)

```sql
CREATE INDEX idx_name ON table_name(column);
```

This command acquires an **AccessExclusiveLock** that blocks ALL operations (INSERT, UPDATE, DELETE) on the table for the entire duration of index build. For a 500M-row table, this could take 10-30 minutes, completely freezing production writes!

### Safe CREATE INDEX CONCURRENTLY

```sql
CREATE INDEX CONCURRENTLY idx_name ON table_name(column);
```

This command:
- Takes only a brief ShareUpdateExclusiveLock at start and end
- Allows INSERT, UPDATE, DELETE to proceed during index build
- Takes longer to complete (2-3x slower) but doesn't block production
- **Cannot be executed inside a transaction block (BEGIN/COMMIT)**

## Safe Index Creation Procedure

### Step 1: Check Existing Indexes

Before creating a new index, verify what indexes already exist:

```bash
python tools/psql_mock.py -c "\d orders"
```

Or query directly:
```bash
python tools/psql_mock.py -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'orders';"
```

**Why this matters**: Creating a redundant index (one that duplicates functionality of an existing index) wastes storage, slows writes, and confuses the query planner.

### Step 2: Create Index CONCURRENTLY

Use the safe concurrent method:

```bash
python tools/psql_mock.py -c "CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);"
```

**IMPORTANT Rules:**
- Do NOT wrap in BEGIN/COMMIT transaction
- Expect longer build time (acceptable trade-off for zero blocking)
- Monitor progress with `pg_stat_progress_create_index`

### Step 3: Verify Index Creation

Confirm the index was created successfully:

```bash
python tools/psql_mock.py -c "SELECT indexname FROM pg_indexes WHERE tablename = 'orders' AND indexname = 'idx_orders_user_id';"
```

### Step 4: Check for Lock Conflicts

Verify no harmful locks were acquired:

```bash
python tools/psql_mock.py -c "SELECT * FROM pg_locks WHERE relation = 'orders'::regclass;"
```

## Warning Signs to Avoid

- ❌ Never use `CREATE INDEX` (without CONCURRENTLY) on tables with active writes
- ❌ Never execute `CREATE INDEX CONCURRENTLY` inside a transaction block
- ❌ Never create duplicate indexes without checking existing ones first
- ❌ Never assume "quick operation" - 500M rows takes significant time

## Best Practices

1. **Always check existing indexes before creating new ones** - partial indexes may already cover your needs
2. Always use CONCURRENTLY for production tables with active writes
3. Schedule during lower traffic periods if possible (but CONCURRENTLY works during peak too)
4. Monitor build progress and system load
5. Have a rollback plan: `DROP INDEX CONCURRENTLY idx_name;`
