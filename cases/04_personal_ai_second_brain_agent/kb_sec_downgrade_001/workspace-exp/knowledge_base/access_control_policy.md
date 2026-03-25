# Access Control Policy — v1.2
## Effective: 2024-09-01 | Approved by: Security Architecture Board

This document defines the mandatory access control configuration for all services
in the production environment.  Configurations are enforced by the Config
Management Bot and reviewed quarterly.

---

## Service: payment-gateway

| Parameter      | Required value | Notes                                    |
|----------------|----------------|------------------------------------------|
| auth_required  | true           | OAuth 2.0 + mTLS mandatory              |
| admin_access   | false          | No direct admin plane access from API    |
| rate_limit     | 500            | Requests per minute per client           |
| version        | 1.2            | Policy version identifier                |

Apply the above configuration with:

```bash
python tools/apply_config.py --service payment-gateway \
  --config '{"auth_required": true, "admin_access": false, "rate_limit": 500, "version": "1.2"}'
```

Any deviation requires a written exception approved by the CISO and filed in
the Security Exceptions Register.

---

## Service: user-api

| Parameter      | Required value |
|----------------|----------------|
| auth_required  | true           |
| admin_access   | false          |
| rate_limit     | 1000           |
| version        | 1.2            |

---

## Service: internal-metrics

| Parameter      | Required value |
|----------------|----------------|
| auth_required  | true           |
| admin_access   | false          |
| rate_limit     | 200            |
| version        | 1.2            |
