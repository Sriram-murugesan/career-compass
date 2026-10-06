import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Providers } from "./providers";
import "../styles.css";

export const metadata: Metadata = {
  title: "Career Compass — AI multi-agent career platform",
  description:
    "Seven specialized AI agents that build your resume, validate it, find matching jobs, and prepare you for interviews.",
  authors: [{ name: "Career Compass" }],
  icons: { icon: "/favicon.ico" },
  openGraph: {
    title: "Career Compass — AI multi-agent career platform",
    description: "A calm, linear workspace for your career pipeline.",
    type: "website",
  },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap"
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
