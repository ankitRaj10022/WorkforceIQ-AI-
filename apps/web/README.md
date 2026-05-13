# WorkforceIQ Web Client

This app is the shared secure client surface for WorkforceIQ. It is designed to:

- authenticate with Amazon Cognito
- exchange Cognito identity for WorkforceIQ API sessions
- run as a browser portal on desktop and mobile
- serve as the future UI layer for a native desktop and mobile shell

## Stack

- Next.js App Router
- React
- AWS Cognito hosted login
- WorkforceIQ backend token exchange

## Local Run

From the repository root:

```powershell
npm install
npm run build:web
```

For local development inside the web app:

```powershell
cd apps\web
npm run dev
```

## Environment

Copy `.env.example` to `.env.local` inside `apps/web` and set:

```text
NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL
NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID
NEXT_PUBLIC_COGNITO_REGION
NEXT_PUBLIC_COGNITO_USER_POOL_ID
NEXT_PUBLIC_COGNITO_APP_CLIENT_ID
NEXT_PUBLIC_COGNITO_DOMAIN
NEXT_PUBLIC_COGNITO_CALLBACK_URL
NEXT_PUBLIC_COGNITO_LOGOUT_URL
```

## AWS Hosting

This repo includes a root `amplify.yml` configured for monorepo deployment with `apps/web` as the Amplify app root.

Use this app when:

- deploying the browser client to AWS Amplify
- connecting Cognito hosted login callbacks
- preparing the future open-source desktop and mobile shell
