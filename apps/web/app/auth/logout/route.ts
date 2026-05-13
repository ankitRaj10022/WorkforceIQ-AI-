import { NextResponse } from "next/server";

import { logoutWorkforceSession } from "@/lib/backend";
import { buildLogoutUrl } from "@/lib/cognito";
import { clearPortalSession, readPortalSession } from "@/lib/session";

export async function GET() {
  const session = await readPortalSession();
  if (session) {
    try {
      await logoutWorkforceSession(session.accessToken);
    } catch {
      // Best-effort logout. Cognito logout and cookie clearing still proceed.
    }
  }

  const response = NextResponse.redirect(buildLogoutUrl());
  clearPortalSession(response);
  return response;
}
