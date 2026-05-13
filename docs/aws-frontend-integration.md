# WorkforceIQ Frontend Integration on AWS

This guide assumes you deploy the backend with `infra/aws/terraform` and want the frontend in [`apps/web`](../apps/web) to authenticate with AWS Cognito, then exchange the Cognito ID token for WorkforceIQ API tokens.

## 1. Terraform Inputs

Set these in `infra/aws/terraform/prod.auto.tfvars`:

```hcl
app_domain          = ""
frontend_base_url   = "https://<your-amplify-domain>"
frontend_origins    = ["https://<your-amplify-domain>"]
enable_cognito      = true
cognito_domain_prefix = "workforceiq-prod-auth"
cognito_self_signup_enabled = true
cognito_auto_provision_users = true
cognito_auto_provision_default_role = "EMPLOYEE"
cognito_allowed_signup_email_domains = ["yourcompany.com"]
```

What this does:

- provisions a Cognito user pool and hosted UI domain
- configures the backend to trust Cognito ID tokens
- allows company-email signup in Cognito
- auto-provisions a local WorkforceIQ `user_accounts` record on first sign-in
- restricts signup and auto-provisioning to approved email domains

## 2. Apply The AWS Stack

```powershell
cd C:\Users\danny\Desktop\Projects\WorkFlow-AI
wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 apply -auto-approve'
```

## 3. Export Frontend Environment Values

After apply:

```powershell
wsl -e sh -lc 'cd /mnt/c/Users/danny/Desktop/Projects/WorkFlow-AI && docker run --rm -v "$PWD/infra/aws:/workspace" -v "/mnt/c/Users/danny/.aws:/root/.aws:ro" -w /workspace/terraform hashicorp/terraform:1.9.8 output frontend_env'
```

Use the output values in your frontend environment:

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

For the current managed stack, these values should be applied to `apps/web/.env.local` for local validation and then copied into AWS Amplify environment variables for hosted builds.

For local preview, do not install the localhost build as a desktop or mobile
app. Only install the hosted frontend origin after Cognito callback URLs and
logout URLs point at the real deployed domain.

## 4. Deploy The Frontend In Amplify

Amplify currently documents managed SSR support for Next.js versions `12` through `15`, so the web client is pinned to Next `15` for AWS-native hosting compatibility.

Files already prepared in the repo:

- root workspace file: [`package.json`](../package.json)
- Amplify monorepo build config: [`amplify.yml`](../amplify.yml)
- app root: [`apps/web`](../apps/web)

In the Amplify console:

1. Choose **Create new app**
2. Choose your Git provider
3. Select this repository and branch
4. Select **My app is a monorepo**
5. Set the app root to `apps/web`
6. Confirm the generated build uses the repo `amplify.yml`
7. Add the `NEXT_PUBLIC_*` variables from `terraform output frontend_env`
8. Save and deploy

Amplify will automatically set `AMPLIFY_MONOREPO_APP_ROOT=apps/web` when you create the app through the console for a monorepo deployment.

If you want to avoid manual copy/paste after the app exists, use:

```powershell
.\scripts\sync_managed_frontend_env.ps1 -WriteLocalEnv
.\scripts\sync_managed_frontend_env.ps1 -AmplifyAppId dxxxxxxxxxxxx -StartReleaseJob
```

The first command writes `apps/web/.env.local` from the managed Terraform output. The second updates Amplify app-level environment variables from the same Terraform state and optionally starts a release build.

## 4. Browser Sign-In Flow

Recommended frontend flow:

1. Send the user to the Cognito hosted UI or use the Cognito SDK.
2. Receive Cognito tokens after the OAuth code flow completes.
3. Read the Cognito `id_token`.
4. Call:

```http
POST /api/auth/sso/exchange
Content-Type: application/json

{
  "id_token": "<cognito-id-token>",
  "organization_id": "org-demo"
}
```

5. Store the returned WorkforceIQ `access_token` and `refresh_token`.
6. Use the WorkforceIQ access token for all backend API calls.

Why this split matters:

- Cognito proves identity.
- WorkforceIQ remains the authorization and audit boundary.
- The frontend never receives direct database credentials.

## 5. Signup Behavior

When `cognito_self_signup_enabled = true` and `cognito_auto_provision_users = true`:

- a user can sign up with a company email in Cognito
- the backend auto-creates a local WorkforceIQ account on first successful SSO exchange
- the default local role comes from `cognito_auto_provision_default_role`

Use `EMPLOYEE` as the default role unless you have a stronger approval workflow.

## 6. Production Notes

- Keep `cognito_allowed_signup_email_domains` non-empty.
- Use ACM + HTTPS for both frontend and backend domains.
- Do not let the frontend connect directly to MySQL or Redis.
- Do not treat the current HTTP-only ALB endpoint as final production. Move the
  API to an HTTPS custom domain before launch.
- If you later want stricter onboarding, set `cognito_auto_provision_users = false` and provision `user_accounts` through admin workflows instead.
- After Amplify gives you the real `https://*.amplifyapp.com` or custom domain, update `frontend_base_url` and `frontend_origins` in `prod.auto.tfvars`, then re-run Terraform so Cognito callback and logout URLs match the live frontend.
