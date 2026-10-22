/**
 * Frontend API client.
 *   Endpoints:  ./endpoints.ts        (every page route + every backend endpoint)
 *   Templates:  ./api-templates.ts    (response shapes, incl. planned endpoints)
 *   Schemas:    ./schemas/            (form validation, mirrors backend Pydantic rules)
 */

export * from "./endpoints";
export * from "./api-templates";
export * from "./schemas/auth";

export interface ApiError {
  code: string;
  message: string;
  /** Field-level problems for VALIDATION_ERROR: { "email": ["Invalid email"] } */
  details?: Record<string, string[]> | null;
}

/** The wrapper around every backend response. */
export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error: ApiError | null;
  meta?: { requestId?: string | null };
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace NodeJS {
    interface ProcessEnv {
      /** Backend origin, e.g. http://localhost:4000 — set in frontend/.env.local */
      NEXT_PUBLIC_API_BASE_URL?: string;
      /** Google OAuth Web Client ID (public, not a secret) — enables "Continue with Google" */
      NEXT_PUBLIC_GOOGLE_CLIENT_ID?: string;
    }
  }
}

// Must stay dot-access: Next.js inlines NEXT_PUBLIC_* vars at build time by exact match.
export const API_BASE_URL: string = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** True once a backend base URL is provided at build time. */
export const IS_API_ENABLED: boolean = API_BASE_URL.length > 0;

/** A failed API call: HTTP status + the backend's error code ("INVALID_CREDENTIALS", …). */
export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: Record<string, string[]> | null,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

/**
 * Fetch wrapper for the backend. Unwraps the envelope, throws ApiRequestError.
 * `credentials: "include"` sends the httpOnly refresh cookie to /api/auth/*.
 * For signed-in calls use `authFetch` from AuthContext — it adds the Bearer token.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: "include",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new ApiRequestError(
      0,
      "NETWORK_ERROR",
      "Can't reach the server. Is the backend running?",
    );
  }

  let body: ApiEnvelope<T> | null = null;
  try {
    body = (await response.json()) as ApiEnvelope<T>;
  } catch {
    // Non-JSON response (proxy error page, etc.) — handled below.
  }
  if (!response.ok || !body?.success) {
    throw new ApiRequestError(
      response.status,
      body?.error?.code ?? "HTTP_ERROR",
      body?.error?.message ?? `Request failed (${response.status})`,
      body?.error?.details,
    );
  }
  return body;
}
