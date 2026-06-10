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

const required = ["index.html", "console.html"]
for (const file of required) {
  if (!existsSync(join(appDir, file))) {
    console.error(`Missing .next/server/app/${file} — build incomplete.`)
    process.exit(1)
  }
}

cpSync(join(appDir, "index.html"), join(webDir, "index.html"))
cpSync(join(appDir, "console.html"), join(webDir, "console.html"))
mkdirSync(join(webDir, "console"), { recursive: true })
cpSync(join(appDir, "console.html"), join(webDir, "console/index.html"))

if (existsSync(join(appDir, "_not-found.html"))) {
  cpSync(join(appDir, "_not-found.html"), join(webDir, "404.html"))
}

cpSync(staticDir, join(webDir, "_next/static"), { recursive: true })
console.log("Assembled web UI →", webDir)
