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
    }
  }
}

// Must stay dot-access: Next.js inlines NEXT_PUBLIC_* vars at build time by exact match.
export const API_BASE_URL: string = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** True once a backend base URL is provided at build time. */
export const IS_API_ENABLED: boolean = API_BASE_URL.length > 0;

/**
 * Thin fetch wrapper. Intentionally unused while the screens run on mock data.
 * `credentials: "include"` sends the httpOnly refresh cookie to /api/auth/*.
 *
 *   const res = await apiFetch<AuthSession>(API_ENDPOINTS.auth.signIn, {
 *     method: "POST", body: JSON.stringify({ email, password }),
 *   });
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      // Authorization: `Bearer ${accessToken}`,
      ...(init.headers ?? {}),
    },
  });

  const body = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !body.success) {
    throw new Error(body.error?.message ?? `Request failed: ${response.status}`);
  }
  return body;
}
