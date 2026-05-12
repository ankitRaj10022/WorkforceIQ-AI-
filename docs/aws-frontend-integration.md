# WorkforceIQ Frontend Integration on AWS

This guide assumes you deploy the backend with `infra/aws/terraform` and want a browser frontend to authenticate with AWS Cognito, then exchange the Cognito ID token for WorkforceIQ API tokens.

## 1. Terraform Inputs

Set these in `infra/aws/terraform/prod.auto.tfvars`:

```hcl
app_domain          = "api.example.com"
frontend_base_url   = "https://app.example.com"
frontend_origins    = ["https://app.example.com"]
enable_cognito      = true
cognito_domain_prefix = "workforceiq-prod-auth"
cognito_self_signup_enabled = true
cognito_auto_provision_users = true
cognito_auto_provision_default_role = "EMPLOYEE"
cognito_allowed_signup_email_domains = ["example.com"]
```

What this does:

- provisions a Cognito user pool and hosted UI domain
- configures the backend to trust Cognito ID tokens
- allows company-email signup in Cognito
- auto-provisions a local WorkforceIQ `user_accounts` record on first sign-in
- restricts signup and auto-provisioning to approved email domains

## 2. Apply The AWS Stack

```powershell
cd infra/aws/terraform
terraform init
terraform apply
```

## 3. Export Frontend Environment Values

After apply:

```powershell
terraform output frontend_env
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
- If you later want stricter onboarding, set `cognito_auto_provision_users = false` and provision `user_accounts` through admin workflows instead.
