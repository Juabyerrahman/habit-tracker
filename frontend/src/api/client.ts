import { API_BASE_URL } from "../config/env";
import { tokenStore } from "./tokenStore";
import type { ApiErrorBody, SessionResponse } from "./types";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error.code;
    this.details = body.error.details;
  }
}

async function readError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;

    if (body?.error?.code && body?.error?.message) {
      return new ApiError(response.status, body);
    }
  } catch {
    // The response was not valid JSON.
  }

  return new ApiError(response.status, {
    error: {
      code: "request_failed",
      message: `Request failed with status ${response.status}.`,
    },
  });
}

export function setSession(session: SessionResponse): void {
  tokenStore.set(session.access_token);
}

export function clearSession(): void {
  tokenStore.clear();
}

let refreshPromise: Promise<SessionResponse> | null = null;

async function performRefresh(): Promise<SessionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw await readError(response);
  }

  const session = (await response.json()) as SessionResponse;
  tokenStore.set(session.access_token);

  return session;
}

async function refreshWithCrossTabLock(): Promise<SessionResponse> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    return navigator.locks.request(
      "habit-tracker-auth-refresh",
      { mode: "exclusive" },
      () => performRefresh(),
    );
  }

  return performRefresh();
}

export function refreshSession(): Promise<SessionResponse> {
  if (!refreshPromise) {
    refreshPromise = refreshWithCrossTabLock().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

export interface ApiRequestOptions extends RequestInit {
  auth?: boolean;
  retryOnExpired?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const {
    auth = true,
    retryOnExpired = true,
    headers: suppliedHeaders,
    ...fetchOptions
  } = options;

  const headers = new Headers(suppliedHeaders);
  headers.set("Accept", "application/json");

  if (
    fetchOptions.body &&
    typeof fetchOptions.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = tokenStore.get();

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchOptions,
    headers,
    credentials: "include",
  });

  if (auth && retryOnExpired && response.status === 401) {
    const error = await readError(response);

    if (error.code === "token_expired") {
      await refreshSession();

      return apiRequest<T>(path, {
        ...options,
        retryOnExpired: false,
      });
    }

    throw error;
  }

  if (!response.ok) {
    throw await readError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
