---
title: API Design Patterns for Microservices
status: approved
author: self
tags: [engineering, architecture, api]
created: 2026-03-15
---

# API Design Patterns for Microservices

## REST vs gRPC

When choosing between REST and gRPC for inter-service communication, consider
latency requirements (gRPC is faster for internal services), payload size
(Protobuf is more compact than JSON), and browser compatibility (REST is easier).

## Versioning Strategy

API versioning is critical for backward compatibility. Prefer URI versioning
(`/v1/resource`) for public APIs and header versioning for internal services.
Never break existing consumers without a deprecation window of at least 6 months.

## Authentication

Use OAuth 2.0 with short-lived JWT tokens (15-minute expiry). Refresh tokens
should be stored in HttpOnly cookies. Never embed secrets in API responses.
