import { getPublicAppConfig } from "@/lib/env";
import type { WorkforceAuthResponse } from "@/types/api";

async function parseResponseText(response: Response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function errorMessageFromPayload(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "error" in payload) {
    const candidate = payload.error;
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }
  return fallback;
}

export async function exchangeWorkforceSso(
  idToken: string,
): Promise<WorkforceAuthResponse> {
  const config = getPublicAppConfig();
  const response = await fetch(`${config.apiBaseUrl}/api/auth/sso/exchange`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      id_token: idToken,
      organization_id: config.organizationId,
    }),
    cache: "no-store",
  });

  const payload = await parseResponseText(response);
  if (!response.ok) {
    throw new Error(
      errorMessageFromPayload(
        payload,
        `WorkforceIQ SSO exchange failed with status ${response.status}.`,
      ),
    );
  }

  return payload as WorkforceAuthResponse;
}

export async function refreshWorkforceSession(
  refreshToken: string,
): Promise<WorkforceAuthResponse> {
  const config = getPublicAppConfig();
  const response = await fetch(`${config.apiBaseUrl}/api/auth/refresh`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${refreshToken}`,
    },
    cache: "no-store",
  });
  const payload = await parseResponseText(response);
  if (!response.ok) {
    throw new Error(
      errorMessageFromPayload(
        payload,
        `WorkforceIQ refresh failed with status ${response.status}.`,
      ),
    );
  }
  return payload as WorkforceAuthResponse;
}

export async function logoutWorkforceSession(accessToken: string) {
  const config = getPublicAppConfig();
  await fetch(`${config.apiBaseUrl}/api/auth/logout`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    cache: "no-store",
  });
}

export async function requestWorkforceApi(options: {
  path: string;
  method: string;
  accessToken: string;
  bodyText?: string;
  contentType?: string | null;
  search?: string;
}) {
  const config = getPublicAppConfig();
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${options.accessToken}`);
  if (options.bodyText && options.contentType) {
    headers.set("Content-Type", options.contentType);
  }

  return fetch(
    `${config.apiBaseUrl}/api/${options.path}${options.search ?? ""}`,
    {
      method: options.method,
      headers,
      body: options.bodyText,
      cache: "no-store",
    },
  );
}
