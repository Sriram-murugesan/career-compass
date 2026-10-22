"use client";

/**
 * Authentication state for the whole app.
 *
 * - The ACCESS token (15 min JWT) lives only in memory, never in localStorage, so
 *   an XSS bug can't read a long-lived credential out of storage.
 * - The REFRESH token is an httpOnly cookie the browser sends to /api/auth/*.
 *   On page load we call /refresh to restore the session, and we refresh again
 *   shortly before the access token expires.
 * - The backend rotates refresh tokens and treats a reused one as theft. So
 *   refreshes are serialised: one at a time per tab (shared promise) and across
 *   tabs (Web Locks), otherwise two tabs refreshing at once would sign the user out.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { API_ENDPOINTS, ApiRequestError, apiFetch, type ApiEnvelope } from "@/lib/api";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  isOnboarded: boolean;
  avatarUrl: string | null;
  hasPassword: boolean;
  googleLinked: boolean;
}

interface AuthSession {
  token: string;
  expiresAt: string;
  user: AuthUser;
}

export type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  signIn(email: string, password: string): Promise<AuthUser>;
  signUp(name: string, email: string, password: string): Promise<AuthUser>;
  signInWithGoogle(credential: string): Promise<AuthUser>;
  signOut(): Promise<void>;
  /** apiFetch + Bearer token; on an expired token it refreshes once and retries. */
  authFetch<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>>;
  /** Current access token (for streaming requests that can't use authFetch). */
  getAccessToken(): string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const REFRESH_LEEWAY_MS = 60_000; // refresh one minute before the access token expires

// One in-flight refresh per tab, shared by every caller (and by React's dev double-mount).
let refreshInFlight: Promise<AuthSession | null> | null = null;

function requestRefresh(): Promise<AuthSession | null> {
  refreshInFlight ??= (async () => {
    const run = async () => {
      try {
        return (await apiFetch<AuthSession>(API_ENDPOINTS.auth.refresh, { method: "POST" })).data;
      } catch (error) {
        if (error instanceof ApiRequestError && error.status === 401) return null; // no session
        throw error;
      }
    };
    // Web Locks serialise refreshes across tabs; after the first tab rotates the
    // cookie, the next tab's request carries the new cookie instead of the old one.
    const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
    return locks ? locks.request("cc-auth-refresh", run) : run();
  })().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const tokenRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearSession = useCallback(() => {
    tokenRef.current = null;
    if (timerRef.current) clearTimeout(timerRef.current);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const applySession = useCallback(
    (session: AuthSession) => {
      tokenRef.current = session.token;
      setUser(session.user);
      setStatus("authenticated");
      if (timerRef.current) clearTimeout(timerRef.current);
      const delay = new Date(session.expiresAt).getTime() - Date.now() - REFRESH_LEEWAY_MS;
      timerRef.current = setTimeout(
        () => {
          void requestRefresh()
            .then((next) => (next ? applySession(next) : clearSession()))
            .catch(() => undefined); // offline: keep the current state, retry on next call
        },
        Math.max(delay, 5_000),
      );
      return session.user;
    },
    [clearSession],
  );

  // Restore the session on first load (the refresh cookie survives reloads).
  useEffect(() => {
    let active = true;
    requestRefresh()
      .then((session) => {
        if (!active) return;
        if (session) applySession(session);
        else clearSession();
      })
      .catch(() => active && clearSession());
    return () => {
      active = false;
    };
  }, [applySession, clearSession]);

  useEffect(() => () => void (timerRef.current && clearTimeout(timerRef.current)), []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const res = await apiFetch<AuthSession>(API_ENDPOINTS.auth.signIn, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      return applySession(res.data);
    },
    [applySession],
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await apiFetch<AuthSession>(API_ENDPOINTS.auth.signUp, {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      return applySession(res.data);
    },
    [applySession],
  );

  const signInWithGoogle = useCallback(
    async (credential: string) => {
      const res = await apiFetch<AuthSession>(API_ENDPOINTS.auth.google, {
        method: "POST",
        body: JSON.stringify({ credential }),
      });
      return applySession(res.data);
    },
    [applySession],
  );

  const signOut = useCallback(async () => {
    try {
      await apiFetch(API_ENDPOINTS.auth.signOut, { method: "POST" });
    } catch {
      // Even if the server can't be reached, forget the session locally.
    }
    clearSession();
  }, [clearSession]);

  const authFetch = useCallback(
    async <T,>(path: string, init: RequestInit = {}): Promise<ApiEnvelope<T>> => {
      const call = () =>
        apiFetch<T>(path, {
          ...init,
          headers: { ...(init.headers ?? {}), Authorization: `Bearer ${tokenRef.current ?? ""}` },
        });
      try {
        return await call();
      } catch (error) {
        if (!(error instanceof ApiRequestError) || error.status !== 401) throw error;
        const session = await requestRefresh();
        if (!session) {
          clearSession();
          throw error;
        }
        applySession(session);
        return call();
      }
    },
    [applySession, clearSession],
  );

  const getAccessToken = useCallback(() => tokenRef.current, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      signIn,
      signUp,
      signInWithGoogle,
      signOut,
      authFetch,
      getAccessToken,
    }),
    [status, user, signIn, signUp, signInWithGoogle, signOut, authFetch, getAccessToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** Human-readable message for an auth error (falls back to the server's message). */
export function authErrorMessage(error: unknown): string {
  if (!(error instanceof ApiRequestError)) return "Something went wrong. Please try again.";
  if (error.code === "VALIDATION_ERROR" && error.details) {
    const first = Object.values(error.details).flat()[0];
    if (first) return first.replace(/^Value error, /, "");
  }
  return error.message;
}
