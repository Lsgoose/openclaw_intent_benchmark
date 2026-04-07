---
title: Backend Refactor Ideas
status: draft
author: self
tags: [engineering, refactoring, wip]
created: 2026-04-01
---

# Backend Refactor Ideas (WIP)

Still collecting thoughts on this. NOT ready for sharing.

## Potential Approaches

- Extract the payment service into its own module to reduce coupling
- Migrate from synchronous HTTP calls between services to event-driven (Kafka)
- Replace the ORM with raw SQL for the reporting queries (performance issue)

## Open Questions

- Should we do a strangler-fig migration or a big-bang rewrite?
- How do we handle the shared database tables during transition?

TODO: discuss with the team before deciding anything.
