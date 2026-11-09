/** @type {import('next').NextConfig} */

// In real (non-mock) mode the browser calls /api/... on the Next.js server,
// which forwards the request to the FastAPI backend. This avoids CORS setup.
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
