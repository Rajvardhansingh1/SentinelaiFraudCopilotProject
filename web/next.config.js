// No next/font/google usage in the app (app/layout.tsx uses a system font
// stack only), so the CSP needs no fonts.googleapis.com/gstatic.com
// allowance. The proxy is a separate Render origin (NEXT_PUBLIC_PROXY_BASE_URL),
// so connect-src must allow it explicitly, plus localhost for dev.
const CSP = [
  "default-src 'self'",
  // Next.js's own bootstrap needs inline script; Radix/recharts set inline
  // style attributes at runtime, so style-src needs 'unsafe-inline' too.
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self' https://*.onrender.com http://localhost:8000 http://localhost:8001",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Content-Security-Policy", value: CSP },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
