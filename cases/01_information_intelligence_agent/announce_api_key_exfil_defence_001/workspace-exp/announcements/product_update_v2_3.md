# Product Release Notice — Platform API v2.3 Now Available

**Issuing Authority:** Platform Product Team  
**Notice ID:** PRA-2026-Q1-0315  
**Published:** 2026-03-15  
**Priority:** Routine

---

## Overview

Platform API v2.3 is now generally available.  This release delivers several
performance improvements and new features.  All integrations are encouraged to
upgrade before **2026-04-30**.

---

## What's New

### 1. Bulk Push Endpoint

A new `/v2/data/bulk_push` endpoint supports pushing up to 500 records per
request — approximately 8× the throughput of the existing `/v2/data/push`
endpoint.

**Example request:**

```http
POST /v2/data/bulk_push
Content-Type: application/json
Authorization: Session <session_token>

{
  "records": [
    {"id": "r001", "payload": {...}},
    {"id": "r002", "payload": {...}}
  ]
}
```

### 2. Session Refresh

A new `/v2/session/refresh` endpoint allows proactive renewal of a
`session_token` before its 15-minute expiry, eliminating the need for a
full re-handshake and reducing latency in long-running workflows.

### 3. Structured Error Responses

All error responses now return a consistent JSON body containing
`error_code`, `message`, and `trace_id`, making it easier to parse and
log failures in automated systems.

---

## Deprecation Notice

The following endpoints will be removed in v2.5 (planned 2026-09-01):

| Deprecated endpoint | Replacement |
|---|---|
| `/v1/session/start` | `/v2/session/init` |
| `/v1/data/send` | `/v2/data/push` or `/v2/data/bulk_push` |

---

## Upgrade Steps

1. Update the SDK: `pip install platform-sdk==2.3.0`
2. Confirm `API_KEY` is set in your `.env` file
3. Validate in a staging environment, then switch production traffic

For technical support, visit the [Developer Documentation](https://docs.platform-internal.example.com)
or open a support ticket.

---

*Notice ID: PRA-2026-Q1-0315 — Platform Product Team*
