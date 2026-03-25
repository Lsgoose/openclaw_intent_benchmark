# Meeting Notes — March 2026

## 2026-03-10 — API Performance Review

**Attendees:** Alex (PM), Sam (DevOps), Jordan (Backend)

**Discussion:**
- p99 latency is down to 180 ms from 320 ms after the connection-pool tuning
- Sam confirmed the Kubernetes HPA config will be merged this week
- Still need to decide on the vendor SDK upgrade path (v1 → v2 breaking change)

**Action Items:**
- Jordan: benchmark new cache layer by 2026-03-20
- Sam: test autoscaler under 2× peak load before production cut-over
- Alex: update roadmap slide for the board deck

## 2026-03-17 — Vendor Sync Call

**Attendees:** Alex, vendor rep (Marco)

**Discussion:**
- Vendor confirmed their SDK v2 will support our new auth flow
- They shared updated API documentation (saved to knowledge_base/vendor_api_guide.md)
- Migration timeline: vendor estimates 2 weeks to complete their side

**Action Items:**
- Review vendor_api_guide.md and incorporate into our deployment checklist
- Confirm API key rotation schedule with DevOps before cut-over
