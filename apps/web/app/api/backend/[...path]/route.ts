import { NextRequest, NextResponse } from "next/server";

import { refreshWorkforceSession, requestWorkforceApi } from "@/lib/backend";
import { applyPortalSession, clearPortalSession, readPortalSession } from "@/lib/session";

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

async function proxyRequest(method: string, request: NextRequest, context: RouteContext) {
  const session = await readPortalSession();
  if (!session) {
    const response = NextResponse.json(
      { error: "No WorkforceIQ session is available." },
      { status: 401 },
    );
    clearPortalSession(response);
    return response;
  }

  const { path } = await context.params;
  const bodyText =
    method === "GET" || method === "HEAD" ? undefined : await request.text();
  const search = request.nextUrl.search;

  let backendResponse = await requestWorkforceApi({
    path: path.join("/"),
    method,
    accessToken: session.accessToken,
    bodyText,
    contentType: request.headers.get("content-type"),
    search,
  });

  let refreshedSession = null;
  if (backendResponse.status === 401) {
    try {
      refreshedSession = await refreshWorkforceSession(session.refreshToken);
      backendResponse = await requestWorkforceApi({
        path: path.join("/"),
        method,
        accessToken: refreshedSession.access_token,
        bodyText,
        contentType: request.headers.get("content-type"),
        search,
      });
    } catch {
      const response = NextResponse.json(
        { error: "Session expired. Please sign in again." },
        { status: 401 },
      );
      clearPortalSession(response);
      return response;
    }
  }

  const payloadText = await backendResponse.text();
  const response = new NextResponse(payloadText, {
    status: backendResponse.status,
    headers: {
      "Content-Type":
        backendResponse.headers.get("content-type") ?? "application/json",
    },
  });

  if (refreshedSession) {
    applyPortalSession(response, refreshedSession);
  }

  if (backendResponse.status === 401) {
    clearPortalSession(response);
  }

  return response;
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest("GET", request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest("POST", request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest("PATCH", request, context);
}
