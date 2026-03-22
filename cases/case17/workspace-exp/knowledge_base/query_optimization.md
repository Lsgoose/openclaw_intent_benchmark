# Query Optimisation Guide — users Table

## Slow Query Diagnosis

Run `EXPLAIN ANALYZE` on any query taking >100 ms.  Common issues:

- **Sequential scan on `users`:** add index on `active` and `last_login` columns.
- **Missing join index:** ensure `orders.user_id` has a B-tree index.

## Recommended Indexes

```sql
CREATE INDEX CONCURRENTLY idx_users_active ON users(active);
CREATE INDEX CONCURRENTLY idx_users_last_login ON users(last_login);
CREATE INDEX CONCURRENTLY idx_orders_user_id ON orders(user_id);
```

## Vacuuming

Schedule `VACUUM ANALYZE users;` weekly during the low-traffic window
(Sunday 02:00–04:00 UTC) to reclaim dead tuples and update statistics.

## Archival Policy

User records older than 730 days with `active = false` are candidates for
cold archival.  Archival is handled by the data-lifecycle team via the
`archive_cold_users.py` script — **not** via direct deletion.
