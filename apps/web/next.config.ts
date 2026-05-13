import type { NextConfig } from "next";

const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
const cognitoOrigin = cognitoDomain
  ? new URL(cognitoDomain).origin
  : "https://cognito-idp.amazonaws.com";
const publicEnv = {
  NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL:
    process.env.NEXT_PUBLIC_WORKFORCEIQ_API_BASE_URL,
  NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID:
    process.env.NEXT_PUBLIC_WORKFORCEIQ_ORGANIZATION_ID,
  NEXT_PUBLIC_COGNITO_REGION: process.env.NEXT_PUBLIC_COGNITO_REGION,
  NEXT_PUBLIC_COGNITO_USER_POOL_ID:
    process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
  NEXT_PUBLIC_COGNITO_APP_CLIENT_ID:
    process.env.NEXT_PUBLIC_COGNITO_APP_CLIENT_ID,
  NEXT_PUBLIC_COGNITO_DOMAIN: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
  NEXT_PUBLIC_COGNITO_CALLBACK_URL:
    process.env.NEXT_PUBLIC_COGNITO_CALLBACK_URL,
  NEXT_PUBLIC_COGNITO_LOGOUT_URL:
    process.env.NEXT_PUBLIC_COGNITO_LOGOUT_URL,
};

const nextConfig: NextConfig = {
  // Amplify's SSR runtime does not reliably expose public env vars during
  // request execution, so we embed this public config at build time.
  env: publicEnv,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
          },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "base-uri 'self'",
              "connect-src 'self' https: http:",
              "frame-ancestors 'none'",
              "font-src 'self' https://fonts.gstatic.com",
              "form-action 'self' " + cognitoOrigin,
              "img-src 'self' data: blob:",
              "manifest-src 'self'",
              "object-src 'none'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "worker-src 'self' blob:",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
