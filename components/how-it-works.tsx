const routes = [
  { task: "Simple Q&A / lookup", model: "DeepSeek V3 / Gemini Flash", saving: "~95% cheaper" },
  { task: "Code generation", model: "DeepSeek R1", saving: "~80% cheaper" },
  { task: "Long doc summarization", model: "Qwen-Long", saving: "~70% cheaper" },
  { task: "Structured data extraction", model: "DeepSeek V3 / Haiku", saving: "~85% cheaper" },
  { task: "Complex reasoning", model: "Claude Sonnet / GPT-4o", saving: "quality-first" },
  { task: "Creative writing", model: "User preference", saving: "configurable" },
]

const codeBefore = `from openai import OpenAI

client = OpenAI(
  base_url="https://api.openai.com/v1",
  api_key="sk-...",
)

client.chat.completions.create(
  model="gpt-4o",
  messages=messages,
)`

const codeAfter = `from openai import OpenAI

client = OpenAI(
  base_url="https://api.tokenmesh.ai/v1",
  api_key="tm_live_...",
)

client.chat.completions.create(
  model="auto",   # Tokenmesh routes it
  messages=messages,
)`

export function HowItWorks() {
  return (
    <section id="how" className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
        <div className="max-w-2xl">
          <p className="font-mono text-sm text-primary">How it works</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            A drop-in gateway with task-aware routing.
          </h2>
          <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
            Change one URL. Every request is classified by intent and complexity, then routed to the
            cheapest model that meets your quality bar. If routing is ever wrong, the fallback is
            your original model — never worse than before.
          </p>
        </div>

        {/* code diff */}
        <div className="mt-12 grid gap-4 lg:grid-cols-2">
          <CodeCard label="Before" tone="muted" code={codeBefore} />
          <CodeCard label="After — one URL change" tone="primary" code={codeAfter} />
        </div>

        {/* routing table — desktop */}
        <div className="mt-10 hidden overflow-hidden rounded-2xl border border-border bg-card/60 md:block">
          <div className="grid grid-cols-12 border-b border-border bg-secondary/40 px-5 py-3 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            <span className="col-span-5">Task type</span>
            <span className="col-span-4">Routed to</span>
            <span className="col-span-3 text-right">Outcome</span>
          </div>
          {routes.map((r) => (
            <div
              key={r.task}
              className="grid grid-cols-12 items-center border-b border-border/60 px-5 py-3.5 text-sm last:border-0"
            >
              <span className="col-span-5 text-foreground">{r.task}</span>
              <span className="col-span-4 font-mono text-xs text-muted-foreground">{r.model}</span>
              <span
                className={`col-span-3 text-right font-mono text-xs ${
                  r.saving.includes("cheaper") ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {r.saving}
              </span>
            </div>
          ))}
        </div>

        {/* routing table — mobile cards */}
        <div className="mt-10 space-y-3 md:hidden">
          {routes.map((r) => (
            <div
              key={r.task}
              className="rounded-xl border border-border bg-card/60 p-4"
            >
              <p className="text-sm font-medium text-foreground">{r.task}</p>
              <p className="mt-2 font-mono text-xs text-muted-foreground">{r.model}</p>
              <p
                className={`mt-2 font-mono text-xs ${
                  r.saving.includes("cheaper") ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {r.saving}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CodeCard({
  label,
  code,
  tone,
}: {
  label: string
  code: string
  tone: "muted" | "primary"
}) {
  return (
    <div
      className={`overflow-hidden rounded-2xl border bg-background ${
        tone === "primary" ? "border-primary/40" : "border-border"
      }`}
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span
          className={`text-xs font-medium ${
            tone === "primary" ? "text-primary" : "text-muted-foreground"
          }`}
        >
          {label}
        </span>
        <span className="font-mono text-[11px] text-muted-foreground">main.py</span>
      </div>
      <pre className="overflow-x-auto px-3 py-4 font-mono text-[11px] leading-relaxed text-foreground sm:px-4 sm:text-[12.5px]">
        <code>{code}</code>
      </pre>
    </div>
  )
}
