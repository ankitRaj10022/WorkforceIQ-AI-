# Open-Source Client Platform

## Goal

WorkforceIQ should not stop at a browser-only admin console. The target product shape is:

- open-source client code
- secure AWS-hosted backend
- installable desktop application
- mobile-operable experience
- one identity and authorization model

## Recommended Platform Choice

Use the current Next.js client in [`apps/web`](../apps/web) as the shared product UI, then package it into a native shell with **Tauri 2** for desktop and mobile delivery.

Why this is the right fit for this repo:

- the backend is already HTTP API driven
- Cognito already handles cloud identity
- the new portal is already organized around a single authenticated client surface
- Tauri 2 supports Windows, Android, and iOS from one codebase
- the code remains open source

Official references:

- Tauri 2 cross-platform support: https://v2.tauri.app/
- Expo universal app docs: https://docs.expo.dev/
- Amplify Next.js support: https://docs.aws.amazon.com/en_us/amplify/latest/userguide/ssr-amplify-support.html

## Security Model

### Cloud-side

- Cognito handles primary identity
- WorkforceIQ backend issues product-scoped access and refresh tokens
- ALB fronts the API
- RDS MySQL stores authoritative workforce data
- ElastiCache Redis handles queues, rate limiting, and caching
- Secrets live in AWS Secrets Manager
- RDS storage is encrypted at rest
- Redis transit is encrypted

### Client-side

- browser session cookies remain HTTP-only
- frontend now ships stricter browser security headers
- installable web shell can run on desktop and mobile browsers
- future native shell should use OS-backed secure storage for tokens
- future native offline cache should be encrypted locally

### What must not happen

- no direct MySQL connection from desktop or mobile clients
- no DB credentials embedded into clients
- no authorization logic that only lives on the client

## Client Layers

```text
apps/
  web/                 Shared secured product UI
  desktop-shell/       Future Tauri 2 native shell
  workforceiq_client/  Existing Python prototype client
```

## Current State

Already done:

- AWS-managed backend path
- Cognito integration
- installable PWA-style web portal shell
- desktop/mobile-friendly portal UX foundation

Still needed:

1. move `apps/web` to a frontend hosting target
2. replace placeholder frontend callback URLs with the real deployed client URL
3. add the Tauri 2 native shell once Rust tooling is installed
4. add encrypted local offline storage for the native shell
5. publish mobile builds

## Recommended Next Execution Order

1. deploy the frontend
2. finalize Cognito callback/logout URLs against the real client domain
3. install Rust + Tauri prerequisites
4. scaffold the native shell in `apps/desktop-shell`
5. move offline storage from browser-only behavior into encrypted native storage
