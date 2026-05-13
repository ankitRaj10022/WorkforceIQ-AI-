import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

import type {
  FrontendSessionPayload,
  WorkforceAuthResponse,
  WorkforceSession,
  WorkforceUser,
} from "@/types/api";

const ACCESS_COOKIE = "wf_access_token";
const REFRESH_COOKIE = "wf_refresh_token";
const USER_COOKIE = "wf_user";
const SESSION_COOKIE = "wf_session";

const ACCESS_COOKIE_TTL_SECONDS = 60 * 15;
const REFRESH_COOKIE_TTL_SECONDS = 60 * 60 * 24 * 30;

type CookieReader = {
  get(name: string): { value: string } | undefined;
};

function safeJsonParse<T>(value: string | undefined): T | null {
  if (!value) {
    return null;
  }
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export type PortalSessionState = {
  accessToken: string;
  refreshToken: string;
  user: WorkforceUser;
  session: WorkforceSession;
};

export function readPortalSessionFromStore(
  store: CookieReader,
): PortalSessionState | null {
  const accessToken = store.get(ACCESS_COOKIE)?.value;
  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  const user = safeJsonParse<WorkforceUser>(store.get(USER_COOKIE)?.value);
  const session = safeJsonParse<WorkforceSession>(store.get(SESSION_COOKIE)?.value);

  if (!accessToken || !refreshToken || !user || !session) {
    return null;
  }

  return {
    accessToken,
    refreshToken,
    user,
    session,
  };
}

export async function readPortalSession() {
  const store = await cookies();
  return readPortalSessionFromStore(store);
}

export async function readFrontendSessionPayload(): Promise<FrontendSessionPayload> {
  const session = await readPortalSession();
  if (!session) {
    return {
      authenticated: false,
      user: null,
      session: null,
    };
  }
  return {
    authenticated: true,
    user: session.user,
    session: session.session,
  };
}

export function applyPortalSession(
  response: NextResponse,
  payload: WorkforceAuthResponse,
) {
  response.cookies.set(
    ACCESS_COOKIE,
    payload.access_token,
    cookieOptions(ACCESS_COOKIE_TTL_SECONDS),
  );
  response.cookies.set(
    REFRESH_COOKIE,
    payload.refresh_token,
    cookieOptions(REFRESH_COOKIE_TTL_SECONDS),
  );
  response.cookies.set(
    USER_COOKIE,
    JSON.stringify(payload.user),
    cookieOptions(REFRESH_COOKIE_TTL_SECONDS),
  );
  response.cookies.set(
    SESSION_COOKIE,
    JSON.stringify(payload.session),
    cookieOptions(REFRESH_COOKIE_TTL_SECONDS),
  );
}

export function clearPortalSession(response: NextResponse) {
  for (const name of [
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    USER_COOKIE,
    SESSION_COOKIE,
  ]) {
    response.cookies.set(name, "", {
      ...cookieOptions(0),
      expires: new Date(0),
    });
  }
}
