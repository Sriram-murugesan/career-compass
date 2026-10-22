"use client";

/** Gate for signed-in pages: waits for the session check, sends visitors to "/". */

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useAuth } from "@/context/AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "anonymous") {
      router.replace(`/?next=${encodeURIComponent(pathname)}`);
    }
  }, [status, router, pathname]);

  if (status !== "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
          {status === "loading" ? "Checking your session…" : "Redirecting to sign in…"}
        </p>
      </div>
    );
  }
  return <>{children}</>;
}
