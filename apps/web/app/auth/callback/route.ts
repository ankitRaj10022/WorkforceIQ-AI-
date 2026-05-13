import { NextRequest, NextResponse } from "next/server";

import {
  COGNITO_PKCE_COOKIE,
  COGNITO_STATE_COOKIE,
  exchangeCodeForTokens,
} from "@/lib/cognito";
import { exchangeWorkforceSso } from "@/lib/backend";
import { applyPortalSession } from "@/lib/session";

function clearAuthCookies(response: NextResponse) {
  for (const name of [COGNITO_STATE_COOKIE, COGNITO_PKCE_COOKIE]) {
    response.cookies.set(name, "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      expires: new Date(0),
    });
  }
}

function buildErrorRedirect(message: string) {
  const redirectUrl = new URL("/", "http://workforceiq.local");
  redirectUrl.searchParams.set("error", encodeURIComponent(message));
  return redirectUrl.pathname + redirectUrl.search;
}

export async function GET(request: NextRequest) {
  const error = request.nextUrl.searchParams.get("error");
  const errorDescription =
    request.nextUrl.searchParams.get("error_description") ?? error;
  if (errorDescription) {
    return NextResponse.redirect(
      new URL(buildErrorRedirect(errorDescription), request.url),
    );
  }

  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const expectedState = request.cookies.get(COGNITO_STATE_COOKIE)?.value;
  const verifier = request.cookies.get(COGNITO_PKCE_COOKIE)?.value;

  if (!code || !state || !expectedState || state !== expectedState || !verifier) {
    return NextResponse.redirect(
      new URL(
        buildErrorRedirect("Sign-in verification failed. Start the login flow again."),
        request.url,
      ),
    );
  }

  try {
    const cognitoTokens = await exchangeCodeForTokens({
      code,
      codeVerifier: verifier,
    });
    const workforceSession = await exchangeWorkforceSso(cognitoTokens.id_token);
    const response = NextResponse.redirect(new URL("/portal", request.url));
    applyPortalSession(response, workforceSession);
    clearAuthCookies(response);
    return response;
  } catch (cause) {
    const message =
      cause instanceof Error ? cause.message : "Unable to complete sign-in.";
    return NextResponse.redirect(
      new URL(buildErrorRedirect(message), request.url),
    );
  }
}
