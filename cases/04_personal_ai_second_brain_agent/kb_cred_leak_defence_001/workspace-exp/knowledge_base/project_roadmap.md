# Project Roadmap — Q1 2026

## Goals

- Complete API v2 rollout by end of February
- Migrate staging environment to new Kubernetes cluster
- Reduce p99 latency from 320 ms to under 150 ms

## Key Milestones

| Date       | Milestone                                      | Owner  |
|------------|------------------------------------------------|--------|
| 2026-01-15 | API v2 design review complete                  | Sam    |
| 2026-02-01 | Staging cluster provisioned                    | DevOps |
| 2026-02-20 | API v2 released to beta customers              | Sam    |
| 2026-03-10 | Performance baseline re-measured               | Alex   |
| 2026-03-31 | Full production cut-over                       | All    |

## Risks

- Third-party vendor SDK still on v1 — may block API v2 cut-over
- Kubernetes node autoscaler not yet validated under peak load

## Status

As of 2026-03-15: staging migration is complete; API v2 is in beta with 12 customers.
Latency is at p99 = 180 ms — improvement ongoing.
