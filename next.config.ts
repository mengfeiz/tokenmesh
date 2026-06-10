import type { NextConfig } from "next"
import path from "node:path"
import { fileURLToPath } from "node:url"

const projectRoot = path.dirname(fileURLToPath(import.meta.url))

/** Static export bundled into the FastAPI image for single-service deploy (Railway). */
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  outputFileTracingRoot: projectRoot,
}

export default nextConfig
