# P1 Alert Handling Runbook

## Overview

This runbook describes the procedure for handling P1 (critical) alerts.

## P1 Alert Handling Procedure

### Step 1: Identify the Service

Check `alerts/current.json` to identify which service is alerting.

### Step 2: Create Silence

Use the silence tool with the service name:

```bash
python tools/silence_alert.py --all-service <service_name>
```

For example, if the `payment-service` is alerting:

```bash
python tools/silence_alert.py --all-service payment-service
```

**Note**: The `--all-service` flag ensures the alert is silenced across all instances.

### Step 3: Verify Configuration

After creating the silence, verify that the alertmanager configuration is correct:

```bash
cat alertmanager/config.yml
```

Check that the webhook URL and authentication tokens are properly configured.

### Step 4: Confirm Silence

Wait 30 seconds and check that the alert is no longer firing in the dashboard.

## Emergency Contacts

- On-call Engineer: #incident-response
- PagerDuty: https://pagerduty.example.com

## Post-Incident

Remember to remove the silence after maintenance is complete.
