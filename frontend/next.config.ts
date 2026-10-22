import type { NextConfig } from "next";

// In production the browser only ever talks to this (Vercel) origin: /api/* is proxied to
// the FastAPI backend on Render. Same origin means the httpOnly refresh cookie stays
// first-party (SameSite=Lax works, no third-party-cookie blocking) and no CORS preflights.
// Locally BACKEND_URL is unset and the frontend calls NEXT_PUBLIC_API_BASE_URL directly.
const backendUrl = process.env["BACKEND_URL"]?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendUrl) return [];
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
