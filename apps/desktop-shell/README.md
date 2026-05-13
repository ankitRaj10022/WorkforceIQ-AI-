# Desktop Shell

This folder is reserved for the native open-source shell that will package the shared WorkforceIQ client for:

- Windows desktop
- Android
- iOS

The intended packaging path is **Tauri 2**, because it supports a single frontend codebase across Windows, Android, and iOS while keeping the shell open source and security-focused.

Current status:

- Shared secured client UI: [`apps/web`](../web)
- Existing Python desktop prototype: [`apps/workforceiq_client`](../workforceiq_client)
- Future native shell target: `apps/desktop-shell/src-tauri`

Planned native security model:

- OS keychain / secure enclave backed token storage
- Encrypted local database for offline queues and selected records
- WorkforceIQ API only; no direct MySQL access from devices
- Same Cognito + WorkforceIQ session model as the browser client

Rust tooling is not installed in this workspace yet, so this folder is currently documentation-first rather than build-ready.
