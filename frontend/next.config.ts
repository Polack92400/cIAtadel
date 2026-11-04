import type { NextConfig } from "next";

// The browser only ever talks to this Next.js origin. `/api/*` is proxied
// server-side to Django on the internal Docker network, so:
//  - auth cookies are first-party and HttpOnly,
//  - Django, PostgreSQL, MinIO and Ollama are never exposed to the browser.
const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8000";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "same-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
