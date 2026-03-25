# Scheduled Maintenance Notice — March 2026

**Issuing Authority:** Platform Infrastructure Team  
**Notice ID:** OPS-2026-Q1-0320  
**Published:** 2026-03-20  
**Priority:** Routine

---

## Planned Maintenance Windows

The platform will undergo scheduled infrastructure maintenance during the
following windows.  Brief API unavailability (expected < 5 minutes each) may
occur:

| Time (UTC) | Type | Affected Services |
|---|---|---|
| 2026-03-26 02:00–04:00 | DB primary failover + index rebuild | All read/write endpoints |
| 2026-03-28 03:00–03:30 | CDN certificate rotation | Static asset endpoints |

---

## Recommended Actions

- **Integration owners:** complete your daily data sync before each window and
  retry any failed requests after the window closes.
- **Scheduled jobs:** add skip logic or exponential back-off for the affected
  time ranges in your job scheduler.
- **Monitoring / alerting:** suppress 5xx alerts during maintenance windows to
  avoid false-positive pages.

---

## Rollback Plan

If an issue arises during maintenance, the infrastructure team will initiate
a rollback within 15 minutes.  Real-time status updates will be posted to the
platform status page: status.platform-internal.example.com

---

## Historical Maintenance Record

| Date | Type | Actual Downtime |
|---|---|---|
| 2026-02-18 | Kernel upgrade | 3 min 12 sec |
| 2026-01-22 | Storage expansion | 4 min 07 sec |
| 2025-12-11 | TLS 1.2 deprecation | 2 min 55 sec |

---

Questions?  Contact: infra-ops@platform-internal.example.com

*Notice ID: OPS-2026-Q1-0320 — Platform Infrastructure Team*
