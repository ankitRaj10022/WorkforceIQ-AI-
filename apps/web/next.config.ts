import type { NextConfig } from "next";

const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
const cognitoOrigin = cognitoDomain
  ? new URL(cognitoDomain).origin
  : "https://cognito-idp.amazonaws.com";

const nextConfig: NextConfig = {
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
