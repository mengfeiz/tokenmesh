#!/usr/bin/env node
/**
 * Bundle Next.js build into src/tokenmesh/web for FastAPI StaticFiles.
 * Next 15 writes HTML under .next/server/app/ (not always out/).
 */
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const appDir = join(root, ".next/server/app")
const staticDir = join(root, ".next/static")
const webDir = process.env.WEB_OUT_DIR
  ? join(root, process.env.WEB_OUT_DIR)
  : join(root, "src/tokenmesh/web")

if (!existsSync(join(appDir, "index.html"))) {
  console.error("Missing .next/server/app/index.html — run `npm run build` first.")
  process.exit(1)
}
if (!existsSync(staticDir)) {
  console.error("Missing .next/static — run `npm run build` first.")
  process.exit(1)
}

rmSync(webDir, { recursive: true, force: true })
mkdirSync(join(webDir, "_next"), { recursive: true })

for (const file of ["index.html", "console.html", "_not-found.html"]) {
  const src = join(appDir, file)
  if (existsSync(src)) {
    const dest = file === "_not-found.html" ? join(webDir, "404.html") : join(webDir, file)
    cpSync(src, dest)
  }
}

cpSync(staticDir, join(webDir, "_next/static"), { recursive: true })
console.log("Assembled web UI → src/tokenmesh/web")
