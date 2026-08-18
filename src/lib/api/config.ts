/**
 * Career Compass — API configuration (STATIC / API-READY)
 * ------------------------------------------------------
 * The app currently runs 100% static (mock data + localStorage).
 * Nothing here performs a network request until the backend team
 * sets VITE_API_BASE_URL and un-comments the calls marked with
 * `// [API]` across the codebase.
 *
 * Full endpoint contract: see docs/API_ENDPOINTS.txt
 */

export const API_BASE_URL: string = import.meta.env['VITE_API_BASE_URL'] ?? "";

/** True once a backend base URL is provided at build time. */
export const IS_API_ENABLED: boolean = API_BASE_URL.length > 0;

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error: { code: string; message: string } | null;
  meta?: { requestId?: string; page?: number; pageSize?: number; total?: number };
}

/**
 * Thin fetch wrapper. Intentionally unused while the app is static.
 *
 * Usage once the backend exists:
 *   const res = await apiFetch<UserProfile>(ENDPOINTS.profile.get);
 *   if (res.success) setProfile(res.data);
 */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<ApiEnvelope<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      // Authorization: `Bearer ${getAuthToken()}`,
      ...(init.headers ?? {}),
    },
  });

  const body = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !body.success) {
    throw new Error(body.error?.message ?? `Request failed: ${response.status}`);
  }
  return body;
}
