"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  API_V1,
  api,
  authHeaders,
  clearTmKey,
  getTmKey,
  LS_EMAIL,
  LS_KEYS,
  providerHeaders,
  RecentRequest,
  setTmKey,
  snippets,
  UsageSummary,
} from "@/lib/tokenmesh-api"
import { Copy, KeyRound, LineChart, MessageSquare, Route, Sparkles } from "lucide-react"

type Tab = "start" | "dashboard" | "route" | "chat"
type Lang = "python" | "curl" | "node"

const PROVIDERS = ["deepseek", "openai", "anthropic", "qwen", "google"] as const

export function DeveloperConsole() {
  const [tab, setTab] = useState<Tab>("start")
  const [lang, setLang] = useState<Lang>("python")
  const [health, setHealth] = useState("检查中…")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [pasteKey, setPasteKey] = useState("")
  const [loginNewKey, setLoginNewKey] = useState(false)
  const [authError, setAuthError] = useState("")
  const [authSuccess, setAuthSuccess] = useState("")
  const [hasKey, setHasKey] = useState(false)
  const [userEmail, setUserEmail] = useState("")

  const [routePrompt, setRoutePrompt] = useState("写一个 Python 快排，并解释时间复杂度")
  const [routeTier, setRouteTier] = useState("")
  const [routeResult, setRouteResult] = useState<string | null>(null)
  const [routeMeta, setRouteMeta] = useState("")
  const [routeModel, setRouteModel] = useState("")
  const [routeError, setRouteError] = useState("")

  const [summary, setSummary] = useState<UsageSummary | null>(null)
  const [recent, setRecent] = useState<RecentRequest[]>([])
  const [dashError, setDashError] = useState("")

  const [chatInput, setChatInput] = useState("")
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string }[]>([])
  const [chatError, setChatError] = useState("")
  const [providers, setProviders] = useState<Record<string, string>>({})

  const tmKey = hasKey ? getTmKey() : ""
  const codeSnippet = useMemo(() => snippets(tmKey, API_V1)[lang], [tmKey, lang])

  const refreshAuth = useCallback(() => {
    const k = getTmKey()
    setHasKey(!!k)
    setUserEmail(localStorage.getItem(LS_EMAIL) || "")
    const saved = JSON.parse(localStorage.getItem(LS_KEYS) || "{}")
    setProviders(saved)
  }, [])

  const loadDashboard = useCallback(async () => {
    if (!getTmKey()) return
    setDashError("")
    try {
      const [s, r] = await Promise.all([
        api<UsageSummary>("/v1/usage/summary?days=30", { headers: authHeaders() }),
        api<{ requests: RecentRequest[] }>("/v1/usage/recent?limit=10", {
          headers: authHeaders(),
        }),
      ])
      setSummary(s)
      setRecent(r.requests || [])
    } catch (e) {
      setDashError(e instanceof Error ? e.message : "加载失败")
    }
  }, [])

  useEffect(() => {
    refreshAuth()
    api<{ service: string; version: string }>("/health")
      .then((h) => setHealth(`${h.service} v${h.version}`))
      .catch(() => setHealth("离线"))
  }, [refreshAuth])

  useEffect(() => {
    if (tab === "dashboard" && getTmKey()) loadDashboard()
  }, [tab, hasKey, loadDashboard])

  async function handleRegister() {
    setAuthError("")
    setAuthSuccess("")
    try {
      const data = await api<{ api_key: string; user?: { email?: string } }>(
        "/v1/auth/register",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password }),
        }
      )
      setTmKey(data.api_key, data.user?.email)
      refreshAuth()
      setAuthSuccess("注册成功！Key 已保存，请复制下方代码开始调用。")
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "注册失败")
    }
  }

  async function handleLogin() {
    setAuthError("")
    try {
      const data = await api<{ api_key?: string; user?: { email?: string } }>(
        "/v1/auth/login",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim(),
            password,
            create_new_key: loginNewKey,
          }),
        }
      )
      if (data.api_key) {
        setTmKey(data.api_key, data.user?.email)
        refreshAuth()
        setAuthSuccess("已生成新 API Key 并保存。")
      } else {
        if (data.user?.email) localStorage.setItem(LS_EMAIL, data.user.email)
        refreshAuth()
        setAuthSuccess("登录成功。勾选「生成新 Key」或粘贴已有 Key。")
      }
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : "登录失败")
    }
  }

  async function handleNewKey() {
    try {
      const data = await api<{ api_key: string }>("/v1/auth/keys", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ name: "dashboard" }),
      })
      setTmKey(data.api_key, localStorage.getItem(LS_EMAIL) || undefined)
      refreshAuth()
      alert("新 Key 已保存，请立即备份。")
    } catch (e) {
      alert(e instanceof Error ? e.message : "失败")
    }
  }

  function savePasteKey() {
    const k = pasteKey.trim()
    if (!k.startsWith("tm_live_")) {
      setAuthError("请输入以 tm_live_ 开头的 Key")
      return
    }
    setAuthError("")
    setTmKey(k, localStorage.getItem(LS_EMAIL) || undefined)
    refreshAuth()
    setAuthSuccess("Key 已保存到本浏览器。")
  }

  function copyText(text: string) {
    navigator.clipboard.writeText(text).catch(() => {})
  }

  async function analyzeRoute() {
    setRouteError("")
    try {
      const body: Record<string, unknown> = {
        messages: [{ role: "user", content: routePrompt.trim() }],
      }
      if (routeTier) body.x_tokenmesh_tier = routeTier
      const data = await api<{ routing: Record<string, string> }>("/v1/routing/explain", {
        method: "POST",
        headers: { ...authHeaders(), ...providerHeaders(providers) },
        body: JSON.stringify(body),
      })
      const r = data.routing
      setRouteModel(r.recommended_model)
      setRouteMeta(`tier ${r.route_tier || "-"} · ${r.task_type} · ${r.complexity}`)
      setRouteResult(JSON.stringify(data, null, 2))
    } catch (e) {
      setRouteError(e instanceof Error ? e.message : "分析失败")
    }
  }

  async function sendChat() {
    const text = chatInput.trim()
    if (!text) return
    if (!getTmKey()) {
      setChatError("请先在「快速开始」注册 API Key")
      return
    }
    localStorage.setItem(LS_KEYS, JSON.stringify(providers))
    const next = [...chatMessages, { role: "user", content: text }]
    setChatMessages(next)
    setChatInput("")
    setChatError("")
    try {
      const data = await api<{
        choices?: { message?: { content?: string } }[]
        tokenmesh?: { routed_model?: string; savings?: { saved_usd?: number } }
      }>("/v1/chat/completions", {
        method: "POST",
        headers: { ...authHeaders(), ...providerHeaders(providers) },
        body: JSON.stringify({ model: "auto", messages: next, max_tokens: 1024 }),
      })
      const reply = data.choices?.[0]?.message?.content || "(空)"
      const tm = data.tokenmesh
      const extra = tm?.savings
        ? `\n\n— 模型: ${tm.routed_model || ""} · 省 ${tm.savings.saved_usd ?? 0} USD`
        : ""
      setChatMessages([...next, { role: "assistant", content: reply + extra }])
      loadDashboard()
    } catch (e) {
      setChatMessages(chatMessages)
      setChatError(e instanceof Error ? e.message : "发送失败")
    }
  }

  const tabs: { id: Tab; label: string; icon: typeof Sparkles }[] = [
    { id: "start", label: "快速开始", icon: Sparkles },
    { id: "dashboard", label: "省钱看板", icon: LineChart },
    { id: "route", label: "路由分析", icon: Route },
    { id: "chat", label: "对话试用", icon: MessageSquare },
  ]

  return (
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="mb-5 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">开发者控制台</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            每人一个 <code className="font-mono text-primary">tm_live_</code> Key · OpenAI 兼容 ·
            自动省钱
          </p>
        </div>
        <span className="rounded-full border border-border px-3 py-1 font-mono text-xs text-muted-foreground">
          {health}
        </span>
      </div>

      <div className="-mx-4 mb-5 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:mb-6 sm:flex-wrap sm:overflow-visible sm:px-0 sm:pb-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2.5 text-sm transition-colors sm:py-2 ${
              tab === t.id
                ? "border-primary bg-primary/10 text-foreground"
                : "border-border bg-card/60 text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "start" && (
        <div className="space-y-4">
          <Card title="开发者 3 步接入">
            <p className="mb-6 text-sm text-muted-foreground">
              注册拿专属 Key → 复制代码 → 调用 <code className="font-mono">model: auto</code>。LLM
              费用仍走你自己的供应商 Key（BYOK）。
            </p>

            <Step n={1} title="获取 Tokenmesh API Key">
              {!hasKey ? (
                <div className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="邮箱" value={email} onChange={setEmail} type="email" />
                    <Field label="密码" value={password} onChange={setPassword} type="password" />
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={handleRegister}
                      className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    >
                      注册并获取 Key
                    </button>
                    <button
                      type="button"
                      onClick={handleLogin}
                      className="rounded-full border border-border px-4 py-2 text-sm hover:bg-secondary"
                    >
                      登录
                    </button>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                      <input
                        type="checkbox"
                        checked={loginNewKey}
                        onChange={(e) => setLoginNewKey(e.target.checked)}
                      />
                      登录时生成新 Key
                    </label>
                  </div>
                  <details className="text-sm">
                    <summary className="cursor-pointer text-muted-foreground">
                      已有 tm_live_ Key？直接粘贴
                    </summary>
                    <div className="mt-2 flex gap-2">
                      <input
                        className="flex-1 rounded-lg border border-border bg-background px-3 py-2 font-mono text-sm"
                        placeholder="tm_live_..."
                        value={pasteKey}
                        onChange={(e) => setPasteKey(e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={savePasteKey}
                        className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-secondary"
                      >
                        保存
                      </button>
                    </div>
                  </details>
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-primary">已登录</span>
                  <span className="text-muted-foreground">{userEmail || tmKey.slice(0, 20) + "…"}</span>
                  <button
                    type="button"
                    onClick={handleNewKey}
                    className="rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
                  >
                    生成新 Key
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      clearTmKey()
                      refreshAuth()
                    }}
                    className="rounded-lg border border-border px-2 py-1 text-xs hover:bg-secondary"
                  >
                    退出
                  </button>
                </div>
              )}
              {authError && <p className="mt-2 text-sm text-destructive">{authError}</p>}
              {authSuccess && <p className="mt-2 text-sm text-primary">{authSuccess}</p>}
            </Step>

            <Step n={2} title="你的接入凭证">
              <CredRow label="TOKENMESH_API_KEY" value={hasKey ? tmKey : "（请先注册）"} />
              <CredRow label="BASE_URL" value={API_V1} />
            </Step>

            <Step n={3} title="复制代码，一键调用">
              <div className="mb-2 flex gap-2">
                {(["python", "curl", "node"] as Lang[]).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => setLang(l)}
                    className={`rounded-md px-2.5 py-1 font-mono text-xs ${
                      lang === l ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => copyText(codeSnippet)}
                  className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-1 text-xs hover:bg-secondary"
                >
                  <Copy className="h-3 w-3" /> 复制
                </button>
                <pre className="max-h-64 overflow-auto rounded-xl border border-border bg-background p-4 pt-10 font-mono text-xs leading-relaxed">
                  {codeSnippet}
                </pre>
              </div>
            </Step>
          </Card>
        </div>
      )}

      {tab === "dashboard" && (
        <div className="space-y-4">
          {!hasKey ? (
            <Card title="省钱看板">
              <p className="text-sm text-muted-foreground">
                请先在「快速开始」注册并保存 API Key，才能看到你的节省统计。
              </p>
              <button
                type="button"
                onClick={() => setTab("start")}
                className="mt-4 rounded-full border border-border px-4 py-2 text-sm hover:bg-secondary"
              >
                去获取 Key
              </button>
            </Card>
          ) : (
            <>
              <div className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/10 to-card p-8 text-center">
                <p className="text-sm text-muted-foreground">近 30 天累计节省（相对 GPT-4o 基准）</p>
                <p className="mt-2 font-mono text-4xl font-bold text-primary">
                  ${Number(summary?.total_saved_usd ?? 0).toFixed(4)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  平均节省 {Number(summary?.avg_savings_pct ?? 0).toFixed(1)}% ·{" "}
                  {summary?.total_requests ?? 0} 次请求
                </p>
              </div>
              <Card title="用量概览">
                <div className="mb-4 flex justify-end">
                  <button
                    type="button"
                    onClick={loadDashboard}
                    className="rounded-lg border border-border px-3 py-1 text-xs hover:bg-secondary"
                  >
                    刷新
                  </button>
                </div>
                {dashError && <p className="mb-3 text-sm text-destructive">{dashError}</p>}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {[
                    ["实际花费 $", (summary?.total_cost_usd ?? 0).toFixed(4)],
                    ["基准花费 $", (summary?.total_baseline_cost_usd ?? 0).toFixed(4)],
                    ["输入 tokens", summary?.total_input_tokens ?? 0],
                    ["输出 tokens", summary?.total_output_tokens ?? 0],
                    ["缓存命中", `${((summary?.cache_hit_rate ?? 0) * 100).toFixed(1)}%`],
                    ["套餐", summary?.subscription?.plan ?? "free"],
                  ].map(([l, v]) => (
                    <div key={String(l)} className="rounded-xl border border-border bg-background/60 p-3">
                      <p className="font-mono text-lg font-semibold text-primary">{v}</p>
                      <p className="text-xs text-muted-foreground">{l}</p>
                    </div>
                  ))}
                </div>
                <h3 className="mb-2 mt-6 text-sm font-medium text-muted-foreground">按模型分布</h3>
                {(summary?.model_breakdown?.length ?? 0) > 0 ? (
                  <div className="-mx-2 overflow-x-auto sm:mx-0">
                  <table className="w-full min-w-[320px] text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="pb-2">模型</th>
                        <th>次数</th>
                        <th>节省 $</th>
                        <th>均节省%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary?.model_breakdown?.map((m) => (
                        <tr key={m.model_key} className="border-t border-border/60">
                          <td className="py-2 font-mono text-xs">{m.model_key}</td>
                          <td>{m.calls}</td>
                          <td>{(m.saved_usd ?? 0).toFixed(4)}</td>
                          <td>{(m.avg_savings_pct ?? 0).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无数据，先发几次请求吧。</p>
                )}
                <h3 className="mb-2 mt-6 text-sm font-medium text-muted-foreground">最近请求</h3>
                {recent.length > 0 ? (
                  <div className="-mx-2 overflow-x-auto sm:mx-0">
                  <table className="w-full min-w-[360px] text-sm">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="pb-2">时间</th>
                        <th>模型</th>
                        <th>任务</th>
                        <th>节省$</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recent.map((r, i) => (
                        <tr key={i} className="border-t border-border/60">
                          <td className="py-2 text-xs">
                            {new Date((r.ts || 0) * 1000).toLocaleString()}
                          </td>
                          <td className="font-mono text-xs">{r.model_key || "-"}</td>
                          <td>{r.task_type || "-"}</td>
                          <td>{(r.saved_usd ?? 0).toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">暂无最近请求。</p>
                )}
              </Card>
            </>
          )}
        </div>
      )}

      {tab === "route" && (
        <Card title="路由分析（零成本）">
          <textarea
            className="mb-3 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm"
            rows={4}
            value={routePrompt}
            onChange={(e) => setRoutePrompt(e.target.value)}
          />
          <select
            className="mb-3 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm sm:max-w-xs"
            value={routeTier}
            onChange={(e) => setRouteTier(e.target.value)}
          >
            <option value="">自动档位</option>
            <option value="fast">fast</option>
            <option value="balanced">balanced</option>
            <option value="frontier">frontier</option>
          </select>
          <button
            type="button"
            onClick={analyzeRoute}
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            分析路由
          </button>
          {routeError && <p className="mt-2 text-sm text-destructive">{routeError}</p>}
          {routeResult && (
            <div className="mt-4">
              <p className="text-sm">
                推荐：<span className="font-mono text-primary">{routeModel}</span>
              </p>
              <p className="text-xs text-muted-foreground">{routeMeta}</p>
              <pre className="mt-3 max-h-64 overflow-auto rounded-xl border border-border bg-background p-3 font-mono text-xs">
                {routeResult}
              </pre>
            </div>
          )}
        </Card>
      )}

      {tab === "chat" && (
        <Card title="对话试用">
          <p className="mb-4 text-sm text-muted-foreground">
            需要 Tokenmesh Key + 至少一个供应商 Key（BYOK）。
          </p>
          <div className="mb-3 max-h-72 space-y-2 overflow-y-auto rounded-xl border border-border bg-background/40 p-3">
            {chatMessages.length === 0 && (
              <p className="text-sm text-muted-foreground">发送一条消息开始试用…</p>
            )}
            {chatMessages.map((m, i) => (
              <div
                key={i}
                className={`rounded-lg px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "ml-2 bg-secondary/80 sm:ml-8"
                    : "mr-2 border-l-2 border-primary bg-card/80 sm:mr-8"
                }`}
              >
                <p className="mb-1 text-[10px] uppercase text-muted-foreground">{m.role}</p>
                <p className="whitespace-pre-wrap">{m.content}</p>
              </div>
            ))}
          </div>
          <textarea
            className="mb-3 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm"
            rows={2}
            placeholder="输入消息"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                sendChat()
              }
            }}
          />
          <details className="mb-3 text-sm">
            <summary className="cursor-pointer text-muted-foreground">供应商 API Key（BYOK）</summary>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {PROVIDERS.map((p) => (
                <div key={p}>
                  <label className="text-xs text-muted-foreground capitalize">{p}</label>
                  <input
                    type="password"
                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                    value={providers[p] || ""}
                    onChange={(e) => setProviders({ ...providers, [p]: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </details>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={sendChat}
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              发送
            </button>
            <button
              type="button"
              onClick={() => setChatMessages([])}
              className="rounded-full border border-border px-4 py-2 text-sm hover:bg-secondary"
            >
              清空
            </button>
          </div>
          {chatError && <p className="mt-2 text-sm text-destructive">{chatError}</p>}
        </Card>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card/80 p-4 shadow-xl sm:p-6">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <KeyRound className="h-5 w-5 text-primary" />
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </div>
  )
}

function Step({
  n,
  title,
  children,
}: {
  n: number
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="mb-6 grid grid-cols-[1.75rem_1fr] gap-3 last:mb-0 sm:mb-8 sm:grid-cols-[2rem_1fr] sm:gap-4">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
        {n}
      </div>
      <div>
        <h3 className="font-medium">{title}</h3>
        <div className="mt-3">{children}</div>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-muted-foreground">{label}</label>
      <input
        type={type}
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}

function CredRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-3 rounded-xl border border-border bg-background/60 p-3 last:mb-0">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-mono text-xs text-muted-foreground">{label}</span>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(value).catch(() => {})}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <Copy className="h-3 w-3" /> 复制
        </button>
      </div>
      <p className="break-all font-mono text-sm text-primary">{value}</p>
    </div>
  )
}
