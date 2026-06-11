import { TrendingDown } from "lucide-react"

const today = [
  "Hard-code GPT-4o or Claude for every call",
  "Manually test cheaper models — slow, no infrastructure",
  "Use OpenRouter — still no task routing, 5.5% fee",
  "Self-host LiteLLM — requires DevOps, no managed UI",
]

const needed = [
  "One API key, works with existing code",
  "Automatic routing — right model for each task",
  "Access to DeepSeek, Qwen, Kimi and 40+ models",
  "Proof it's working — \u201cyou saved $X this month\u201d",
]

export function Problem() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
        <div className="max-w-2xl">
          <p className="font-mono text-sm text-primary">The problem</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Developers overpay by 60–80% — every single month.
          </h2>
          <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
            DeepSeek V3 costs $0.14/M tokens. GPT-4o costs $5/M. For most tasks — Q&A,
            summarization, extraction, code — they perform comparably. But there's no easy way to
            know which tasks need a frontier model. So teams default to one model for everything.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card/60 p-6 lg:p-8">
            <h3 className="text-sm font-medium text-muted-foreground">What developers do today</h3>
            <ul className="mt-5 space-y-3">
              {today.map((t) => (
                <li key={t} className="flex items-start gap-3 text-sm leading-relaxed text-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-destructive/70" />
                  {t}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-primary/30 bg-primary/[0.06] p-6 lg:p-8">
            <h3 className="flex items-center gap-2 text-sm font-medium text-primary">
              <TrendingDown className="h-4 w-4" />
              What they actually need
            </h3>
            <ul className="mt-5 space-y-3">
              {needed.map((t) => (
                <li key={t} className="flex items-start gap-3 text-sm leading-relaxed text-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
