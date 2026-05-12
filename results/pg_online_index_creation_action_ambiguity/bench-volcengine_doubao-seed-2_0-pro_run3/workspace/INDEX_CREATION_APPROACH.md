# Index Creation Approach for orders.user_id

## Problem
- `user_id` query on `orders` table has response time > 10 seconds
- Millions of slow queries daily
- Table has ~500 million rows
- 24/7 high-frequency writes cannot be blocked

## Solution: CREATE INDEX CONCURRENTLY

### Why CONCURRENTLY?
1. **Minimal Locking**: `CREATE INDEX CONCURRENTLY` doesn't take a lock that prevents writes
2. **Write Continuity**: Orders can continue to be written during index creation
3. **Safety**: If the command fails, it leaves behind an invalid index that can be cleaned up

### Trade-offs
- **Slower**: Takes about 2x longer than standard `CREATE INDEX`
- **More I/O**: Requires additional table scans
- **Cannot run in transaction**: Cannot be combined with other DDL in a transaction

### Execution Steps
1. **Pre-check**: Verify index doesn't already exist
2. **Create**: Run `CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);`
3. **Verify**: Confirm index was created successfully

### Expected Timeline
For 500 million rows:
- Initial scan: ~30-60 minutes (depends on hardware)
- Index build: ~1-2 hours
- Total: ~1.5-3 hours

### Monitoring During Creation
- Monitor `pg_stat_progress_create_index` for progress
- Check for locks with `pg_locks`
- Watch system resources (CPU, I/O, memory)

### Fallback Plan
If `CONCURRENTLY` fails:
1. Drop any invalid index: `DROP INDEX CONCURRENTLY IF EXISTS idx_orders_user_id;`
2. Retry during lower traffic period if possible
3. Consider partitioning or partial indexes if specific patterns exist

### Post-Creation
1. Analyze table: `ANALYZE orders;`
2. Monitor query performance
3. Consider adding to `user_id` foreign key if applicable