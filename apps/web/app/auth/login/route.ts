import { NextResponse } from "next/server";

import {
  buildAuthorizeUrl,
  COGNITO_PKCE_COOKIE,
  COGNITO_STATE_COOKIE,
  createPkceBundle,
} from "@/lib/cognito";

function authCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function GET() {
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
