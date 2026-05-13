import { generatedPublicConfig } from "@/lib/generated-public-config";

type EnvKey =
  | "NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL"
  | "NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID"
  | "NEXT_PUBLIC_COGNITO_REGION"
  | "NEXT_PUBLIC_COGNITO_USER_POOL_ID"
  | "NEXT_PUBLIC_COGNITO_APP_CLIENT_ID"
  | "NEXT_PUBLIC_COGNITO_DOMAIN"
  | "NEXT_PUBLIC_COGNITO_CALLBACK_URL"
  | "NEXT_PUBLIC_COGNITO_LOGOUT_URL";

function readEnv(key: EnvKey): string {
  const value = process.env[key] || generatedPublicConfig[key];
  if (!value) {
    throw new Error(`Missing required frontend environment variable: ${key}`);
  }
  return value;
}

function normalizeUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export function getPublicAppConfig() {
  return {
    apiBaseUrl: normalizeUrl(readEnv("NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL")),
    organizationId: readEnv("NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID"),
    cognitoRegion: readEnv("NEXT_PUBLIC_COGNITO_REGION"),
    cognitoUserPoolId: readEnv("NEXT_PUBLIC_COGNITO_USER_POOL_ID"),
    cognitoAppClientId: readEnv("NEXT_PUBLIC_COGNITO_APP_CLIENT_ID"),
    cognitoDomain: normalizeUrl(readEnv("NEXT_PUBLIC_COGNITO_DOMAIN")),
    cognitoCallbackUrl: readEnv("NEXT_PUBLIC_COGNITO_CALLBACK_URL"),
    cognitoLogoutUrl: readEnv("NEXT_PUBLIC_COGNITO_LOGOUT_URL"),
  };
}
