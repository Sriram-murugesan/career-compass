"use client";

/**
 * "Continue with Google" via Google Identity Services.
 * Google shows its own button and popup; on success it hands us an ID token
 * (`credential`), which the backend verifies before issuing our session.
 * Renders nothing when NEXT_PUBLIC_GOOGLE_CLIENT_ID isn't set.
 */

import Script from "next/script";
import { useCallback, useRef } from "react";

interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleAccountsId {
  initialize(options: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    ux_mode?: "popup" | "redirect";
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }): void;
  renderButton(
    parent: HTMLElement,
    options: {
      type?: "standard" | "icon";
      theme?: "outline" | "filled_blue" | "filled_black";
      size?: "large" | "medium" | "small";
      text?: "signin_with" | "signup_with" | "continue_with" | "signin";
      shape?: "rectangular" | "pill" | "circle" | "square";
      logo_alignment?: "left" | "center";
      width?: number;
    },
  ): void;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } };
  }
}

// Must stay dot-access: Next.js inlines NEXT_PUBLIC_* at build time.
export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

export function GoogleSignInButton({
  onCredential,
  width = 320,
}: {
  onCredential: (credential: string) => void;
  width?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Keep the latest callback without re-initialising Google on every render.
  const callbackRef = useRef(onCredential);
  callbackRef.current = onCredential;

  const render = useCallback(() => {
    const google = window.google;
    if (!google || !containerRef.current || !GOOGLE_CLIENT_ID) return;
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => callbackRef.current(response.credential),
      ux_mode: "popup",
      auto_select: false,
      cancel_on_tap_outside: true,
    });
    containerRef.current.innerHTML = "";
    google.accounts.id.renderButton(containerRef.current, {
      type: "standard",
      theme: "outline",
      size: "large",
      text: "continue_with",
      shape: "pill",
      logo_alignment: "center",
      width,
    });
  }, [width]);

  if (!GOOGLE_CLIENT_ID) return null;

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={render}
      />
      <div ref={containerRef} className="flex min-h-[44px] justify-center" />
    </>
  );
}
