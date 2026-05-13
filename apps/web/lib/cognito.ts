import { createHash, randomBytes } from "node:crypto";

import { getPublicAppConfig } from "@/lib/env";

export const COGNITO_STATE_COOKIE = "wf_cognito_state";
export const COGNITO_PKCE_COOKIE = "wf_cognito_pkce_verifier";

function base64Url(buffer: Buffer) {
  return buffer
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

export function createPkceBundle() {
  const verifier = base64Url(randomBytes(48));
  const challenge = base64Url(createHash("sha256").update(verifier).digest());
  const state = base64Url(randomBytes(24));
  return { verifier, challenge, state };
}

export function buildAuthorizeUrl(options: {
  codeChallenge: string;
  state: string;
}) {
  const config = getPublicAppConfig();
  const url = new URL(`${config.cognitoDomain}/oauth2/authorize`);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.cognitoAppClientId);
  url.searchParams.set("redirect_uri", config.cognitoCallbackUrl);
  url.searchParams.set("scope", "openid email profile");
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", options.codeChallenge);
  url.searchParams.set("state", options.state);
  return url.toString();
}

export function buildLogoutUrl() {
  const config = getPublicAppConfig();
  const url = new URL(`${config.cognitoDomain}/logout`);
  url.searchParams.set("client_id", config.cognitoAppClientId);
  url.searchParams.set("logout_uri", config.cognitoLogoutUrl);
  return url.toString();
}

export async function exchangeCodeForTokens(options: {
  code: string;
  codeVerifier: string;
}) {
  const config = getPublicAppConfig();
  const tokenUrl = `${config.cognitoDomain}/oauth2/token`;
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: config.cognitoAppClientId,
    redirect_uri: config.cognitoCallbackUrl,
    code: options.code,
    code_verifier: options.codeVerifier,
  });

  const response = await fetch(tokenUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Cognito token exchange failed with status ${response.status}: ${detail}`,
    );
  }

  return (await response.json()) as {
    id_token: string;
    access_token: string;
    refresh_token?: string;
    expires_in: number;
    token_type: string;
  };
}
