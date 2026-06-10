export const LS_TM = "tokenmesh_api_key"
export const LS_EMAIL = "tokenmesh_email"
export const LS_KEYS = "tokenmesh_provider_keys"

/** Override with NEXT_PUBLIC_TOKENMESH_API in production. */
export const API_ORIGIN =
  process.env.NEXT_PUBLIC_TOKENMESH_API || "http://localhost:8080"

export const API_V1 = `${API_ORIGIN}/v1`

const PROVIDER_HEADER: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  qwen: "Qwen",
  google: "Google",
  moonshot: "Moonshot",
  mistral: "Mistral",
}

export function getTmKey(): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem(LS_TM) || ""
}

export function setTmKey(key: string, email?: string) {
  localStorage.setItem(LS_TM, key)
  if (email) localStorage.setItem(LS_EMAIL, email)
}

export function clearTmKey() {
  localStorage.removeItem(LS_TM)
  localStorage.removeItem(LS_EMAIL)
  localStorage.removeItem(LS_KEYS)
}

export function authHeaders(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" }
  const key = getTmKey()
  if (key) h.Authorization = `Bearer ${key}`
  return h
}

export function providerHeaders(
  providers: Record<string, string>
): Record<string, string> {
  const h: Record<string, string> = {}
  for (const [id, val] of Object.entries(providers)) {
    if (val.trim()) {
      h[`X-${PROVIDER_HEADER[id] || id}-API-Key`] = val.trim()
    }
  }
  return h
}

export async function api<T = unknown>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_ORIGIN}${path}`, opts)
  const text = await res.text()
  let data: T & { detail?: unknown; error?: { message?: string } }
  try {
    data = JSON.parse(text)
  } catch {
    data = { raw: text } as T & { detail?: unknown }
  }
  if (!res.ok) {
    const detail = data.detail
    const msg =
      (typeof detail === "object" &&
        detail !== null &&
        "error" in detail &&
        (detail as { error?: { message?: string } }).error?.message) ||
      (typeof detail === "string" ? detail : null) ||
      data.error?.message ||
      text ||
      res.statusText
    throw new Error(typeof msg === "object" ? JSON.stringify(msg) : String(msg))
  }
  return data as T
}

export function snippets(key: string, baseV1: string) {
  const k = key || "tm_live_YOUR_KEY_HERE"
  return {
    python: `import os
from openai import OpenAI

client = OpenAI(
    base_url="${baseV1}",
    api_key="${k}",
    default_headers={
        "X-DeepSeek-API-Key": os.environ["DEEPSEEK_API_KEY"],
    },
)

resp = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "用 Python 写快排"}],
)
print(resp.choices[0].message.content)`,
    curl: `curl -s ${baseV1}/chat/completions \\
  -H "Authorization: Bearer ${k}" \\
  -H "Content-Type: application/json" \\
  -H "X-DeepSeek-API-Key: $DEEPSEEK_API_KEY" \\
  -d '{"model":"auto","messages":[{"role":"user","content":"你好"}]}'`,
    node: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${baseV1}",
  apiKey: "${k}",
  defaultHeaders: {
    "X-DeepSeek-API-Key": process.env.DEEPSEEK_API_KEY,
  },
});

const resp = await client.chat.completions.create({
  model: "auto",
  messages: [{ role: "user", content: "用 Python 写快排" }],
});
console.log(resp.choices[0].message.content);`,
  }
}

export type UsageSummary = {
  total_requests?: number
  total_input_tokens?: number
  total_output_tokens?: number
  total_cost_usd?: number
  total_saved_usd?: number
  total_baseline_cost_usd?: number
  avg_savings_pct?: number
  cache_hit_rate?: number
  subscription?: { plan?: string }
  model_breakdown?: Array<{
    model_key: string
    calls: number
    saved_usd?: number
    avg_savings_pct?: number
  }>
}

export type RecentRequest = {
  ts?: number
  model_key?: string
  task_type?: string
  saved_usd?: number
}
