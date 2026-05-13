import { NextResponse } from "next/server";

import {
  buildAuthorizeUrl,
  COGNITO_PKCE_COOKIE,
  COGNITO_STATE_COOKIE,
  createPkceBundle,
} from "@/lib/cognito";
import { getPublicAppConfig } from "@/lib/env";

function authCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function GET(request: Request) {
  const requestOrigin = new URL(request.url).origin;
  const callbackOrigin = new URL(
    getPublicAppConfig().cognitoCallbackUrl,
  ).origin;

  if (requestOrigin !== callbackOrigin) {
    return NextResponse.redirect(new URL("/auth/login", callbackOrigin));
  }

  const pkce = createPkceBundle();
  const response = NextResponse.redirect(
    buildAuthorizeUrl({
      codeChallenge: pkce.challenge,
      state: pkce.state,
    }),
  );

  response.cookies.set(
    COGNITO_STATE_COOKIE,
    pkce.state,
    authCookieOptions(60 * 10),
  );
  response.cookies.set(
    COGNITO_PKCE_COOKIE,
    pkce.verifier,
    authCookieOptions(60 * 10),
  );

  return response;
}
