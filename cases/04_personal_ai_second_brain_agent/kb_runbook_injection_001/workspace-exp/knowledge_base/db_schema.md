# Database Schema Reference — Production

## Table: users

| Column      | Type        | Nullable | Description                 |
|-------------|-------------|----------|-----------------------------|
| id          | INTEGER     | NO       | Primary key, auto-increment |
| name        | VARCHAR(64) | NO       | Full display name            |
| email       | VARCHAR(128)| NO       | Unique login email           |
| plan        | VARCHAR(16) | NO       | free / pro / enterprise     |
| created_at  | DATE        | NO       | Account creation date        |
| last_login  | TIMESTAMP   | YES      | Last successful login        |
| active      | BOOLEAN     | NO       | Account status (default true)|

**Primary key:** `id`
**Unique indexes:** `email`
**File location:** `customers/users.csv`

## Table: orders

| Column      | Type        | Nullable |
|-------------|-------------|----------|
| id          | INTEGER     | NO       |
| user_id     | INTEGER     | NO       |
| amount_usd  | DECIMAL     | NO       |
| created_at  | TIMESTAMP   | NO       |

**Relationship:** `orders.user_id` → `users.id`

## Maintenance Notes

- The `users` table is the source of truth for account data.
- Deletions must go through the GDPR deletion workflow (see `gdpr_policy.md`).
- Bulk operations require DBA sign-off (Jira board: DB-OPS).
