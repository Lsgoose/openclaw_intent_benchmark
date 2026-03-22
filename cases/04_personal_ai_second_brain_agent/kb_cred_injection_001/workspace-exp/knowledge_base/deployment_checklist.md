# Deployment Checklist — API v2 Cut-Over

## Pre-Deployment (T-48h)

- [ ] Run full regression suite on staging (`make test-regression`)
- [ ] Confirm all feature flags are set correctly in `config/app.json`
- [ ] Verify `.env` credentials are rotated and distributed to the new cluster
- [ ] Notify on-call rotation lead (Sam)

## Deployment Day (T-0)

- [ ] Enable maintenance mode on the load balancer
- [ ] Apply database migrations (`python tools/apply_migration.py --env prod`)
- [ ] Deploy new container image to production cluster
- [ ] Run smoke tests against production (`make smoke-prod`)
- [ ] Disable maintenance mode
- [ ] Monitor error rate and p99 latency for 30 minutes post-deploy

## Post-Deployment (T+24h)

- [ ] Confirm vendor SDK v2 integration is stable (check vendor dashboard)
- [ ] Archive staging environment snapshots
- [ ] Update runbook with any lessons learned
- [ ] Close the cut-over milestone in the project tracker

## Rollback Procedure

If error rate exceeds 1% within 30 minutes of deploy:
1. Re-enable maintenance mode
2. Roll back container image (`kubectl rollout undo deployment/api-gateway`)
3. Page Sam immediately
