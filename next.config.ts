import type { NextConfig } from "next"

const API = process.env.TOKENMESH_API_URL || "http://localhost:8080"

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/v1/:path*", destination: `${API}/v1/:path*` },
      { source: "/health", destination: `${API}/health` },
    ]
  },
}

export default nextConfig
