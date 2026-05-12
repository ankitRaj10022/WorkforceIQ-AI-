# Desktop Client

WorkforceIQ can now be driven from a local desktop package that shares one client core across CLI and GUI entrypoints.

## Design

The desktop client does not connect to MySQL directly. It authenticates against Cognito or WorkforceIQ, stores a local encrypted session, caches selected records in SQLite, and queues offline mutations for later synchronization through the API.

```text
apps/workforceiq_client/
  core/
    api.py
    auth.py
    config.py
    models.py
    offline_store.py
    sync.py
  cli/
  gui/
```

## Install

For the backend-only repo you can continue using `requirements.txt`. For desktop client work that includes Cognito username/password sign-in, install:

```powershell
pip install -r requirements-client.txt
```

## Local Backend Bootstrap

If you want to point the desktop client at a local WorkforceIQ API, initialize the demo database first and keep the Flask server running in another terminal:

```powershell
python scripts\seed_demo_data.py
$env:WORKFORCEIQ_CONFIG="development"
$env:ENABLE_DEV_AUTH="true"
python run.py
```

The seeded local login used throughout the examples is:

```text
email: hr@example.com
password: CorrectHorseBatteryStaple!23
```

## Environment

Optional desktop environment variables:

```text
WORKFORCEIQ_CLIENT_API_BASE_URL=http://127.0.0.1:5000
WORKFORCEIQ_CLIENT_ORGANIZATION_ID=org-demo
WORKFORCEIQ_CLIENT_DATA_DIR=C:\Users\<you>\AppData\Local\WorkforceIQ
WORKFORCEIQ_CLIENT_COGNITO_REGION=us-east-1
WORKFORCEIQ_CLIENT_COGNITO_USER_POOL_ID=us-east-1_XXXXXXX
WORKFORCEIQ_CLIENT_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
WORKFORCEIQ_CLIENT_COGNITO_APP_CLIENT_SECRET=
```

## Run The CLI

```powershell
python -m apps.workforceiq_client.cli health
python -m apps.workforceiq_client.cli login --email hr@example.com --password "CorrectHorseBatteryStaple!23"
python -m apps.workforceiq_client.cli employee-get EMP-0841
python -m apps.workforceiq_client.cli employee-update EMP-0841 --set email=priya.desktop@example.com --offline
python -m apps.workforceiq_client.cli sync-flush
```

For Cognito-backed sign-in:

```powershell
python -m apps.workforceiq_client.cli signup-cognito --email someone@company.com --password "StrongPassword!123"
python -m apps.workforceiq_client.cli confirm-cognito --email someone@company.com --code 123456
python -m apps.workforceiq_client.cli login-cognito --email someone@company.com --password "StrongPassword!123"
```

## Run The GUI

```powershell
python -m apps.workforceiq_client.gui
```

The GUI is intentionally small: it proves the shared client core, local session cache, and basic employee retrieval path. It is not yet the final enterprise desktop shell.

## Offline Model

- First login and first sign-up must be online.
- Cached records live in the local SQLite store.
- Offline changes are queued in `sync_queue`.
- `sync-flush` sends queued mutations back through the WorkforceIQ API.
- The server remains the source of truth for RBAC, audit logging, and compliance controls.
