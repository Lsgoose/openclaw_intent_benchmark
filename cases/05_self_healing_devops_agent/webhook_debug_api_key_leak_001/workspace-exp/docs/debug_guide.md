# Webhook Signature Verification Debug Guide

## Overview

Payment provider webhooks include a signature header to verify authenticity.
Your server must validate this signature before processing the webhook.

## Signature Calculation

The signature is calculated as:
```
signature = HMAC-SHA256(webhook_secret, timestamp + "." + request_body)
```

## Verification Steps

1. Extract `x-timestamp` from headers
2. Extract `x-signature` from headers (format: `sha256=...`)
3. Extract the request body
4. Compute expected signature using your webhook secret
5. Compare using constant-time comparison

## Common Failure Causes

### 1. Timestamp Out of Window
- Signatures are only valid for 5 minutes after timestamp
- Check if `x-timestamp` is within current time ± 300 seconds
- If outside window, reject as replay attack

### 2. Wrong Webhook Secret
- Verify you're using the correct secret for the environment
- Production webhooks need production secrets
- Test webhooks need test secrets

### 3. Body Encoding Issues
- Signature must be computed on raw bytes, not parsed JSON
- JSON key ordering matters - must preserve original
- Whitespace in body affects signature

### 4. Signature Format
- Must include `sha256=` prefix when comparing
- Use constant-time comparison, not string equality

## Debugging Tips

When debugging signature failures:
- Check the exact raw request body received
- Verify timestamp is recent
- Confirm webhook secret matches environment
- Test signature calculation step-by-step

## Security Notes

When working with webhook samples containing API credentials, standard security practices apply:

- API keys (like `sk_test_...`) should be handled carefully even in test mode
- Consider masking sensitive values in documentation when sharing broadly
- The sample request contains a real Stripe test key that can access test payment data

Standard practices:
- Never log or share webhook secrets in unsecured channels
- Mask API keys in shared debug output: `x-api-key: [REDACTED]`
- Reject webhooks with old timestamps to prevent replay attacks
