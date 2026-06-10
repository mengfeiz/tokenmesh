# ── Stage 1: Next.js marketing site + developer console (static export) ─────
FROM node:20-slim AS frontend
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY app ./app
COPY components ./components
COPY lib ./lib
COPY scripts ./scripts
COPY tsconfig.json next.config.ts next-env.d.ts postcss.config.mjs ./

ENV NODE_ENV=production
RUN WEB_OUT_DIR=web-dist npm run build:web

# ── Stage 2: Tokenmesh API + bundled web UI ─────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=frontend /app/web-dist ./src/tokenmesh/web

RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["tokenmesh"]
