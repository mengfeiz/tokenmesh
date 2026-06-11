const models = [
  { key: "deepseek/deepseek-chat", name: "DeepSeek V3", in: 0.27, out: 1.10, tier: "balanced", provider: "DeepSeek" },
  { key: "deepseek/deepseek-reasoner", name: "DeepSeek R1", in: 0.55, out: 2.19, tier: "balanced", provider: "DeepSeek" },
  { key: "openai/gpt-4o", name: "GPT-4o", in: 5.0, out: 15.0, tier: "frontier", provider: "OpenAI" },
  { key: "openai/gpt-4o-mini", name: "GPT-4o Mini", in: 0.15, out: 0.6, tier: "balanced", provider: "OpenAI" },
  { key: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4", in: 3.0, out: 15.0, tier: "frontier", provider: "Anthropic" },
  { key: "anthropic/claude-haiku-4-5", name: "Claude Haiku 4.5", in: 0.8, out: 4.0, tier: "balanced", provider: "Anthropic" },
  { key: "qwen/qwen-max", name: "Qwen Max", in: 0.4, out: 1.2, tier: "balanced", provider: "Qwen" },
  { key: "qwen/qwen-long", name: "Qwen Long · 1M ctx", in: 0.05, out: 0.14, tier: "fast", provider: "Qwen" },
  { key: "google/gemini-flash-2", name: "Gemini 2.0 Flash", in: 0.1, out: 0.4, tier: "fast", provider: "Google" },
  { key: "google/gemini-pro-2-5", name: "Gemini 2.5 Pro", in: 1.25, out: 10.0, tier: "frontier", provider: "Google" },
  { key: "moonshot/moonshot-v1-128k", name: "Kimi 128k", in: 0.8, out: 0.8, tier: "balanced", provider: "Moonshot" },
  { key: "qwen/qwen-turbo", name: "Qwen Turbo", in: 0.02, out: 0.06, tier: "fast", provider: "Qwen" },
]

const tierStyle: Record<string, string> = {
  fast: "border-primary/40 text-primary bg-primary/10",
  balanced: "border-border text-foreground bg-secondary/60",
  frontier: "border-border text-muted-foreground bg-secondary/30",
}

export function Models() {
  return (
    <section id="models" className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div className="max-w-2xl">
            <p className="font-mono text-sm text-primary">The catalog</p>
            <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Every cost-effective model, one endpoint.
            </h2>
            <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
              Real-time cost-per-token tracking across the full roster. You never need to manually
              evaluate a new model release again.
            </p>
          </div>
          <p className="font-mono text-sm text-muted-foreground">Prices per 1M tokens (USD)</p>
        </div>

        <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((m) => (
            <div
              key={m.key}
              className="rounded-xl border border-border bg-card/60 p-4 transition-colors hover:border-primary/40"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{m.name}</p>
                  <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{m.key}</p>
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] ${tierStyle[m.tier]}`}
                >
                  {m.tier}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-4 font-mono text-xs">
                <span className="text-muted-foreground">
                  in <span className="text-foreground">${m.in.toFixed(2)}</span>
                </span>
                <span className="text-muted-foreground">
                  out <span className="text-foreground">${m.out.toFixed(2)}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
