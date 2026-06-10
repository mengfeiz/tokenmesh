import { Route, Layers, ShieldCheck, Plug } from "lucide-react"

const pillars = [
  {
    icon: Route,
    title: "Task-aware routing",
    desc: "A lightweight intent classifier runs on every request (sub-10ms), scoring complexity and domain, then picks the cheapest model that meets your quality threshold.",
    tag: "Primary differentiator",
  },
  {
    icon: Layers,
    title: "Full model catalog",
    desc: "40+ models including DeepSeek, Qwen, Kimi and Gemini Flash — models unavailable on OpenRouter or NotDiamond. New models benchmarked and added continuously.",
    tag: "40+ models",
  },
  {
    icon: ShieldCheck,
    title: "Reliability layer",
    desc: "Sub-second automatic failover, semantic caching, and per-provider rate-limit management. Provider outages stay invisible to your users.",
    tag: "99.9% uptime target",
  },
  {
    icon: Plug,
    title: "Drop-in integration",
    desc: "100% OpenAI-compatible API — change one base URL. BYOK with 0% markup. Python, Node.js, and curl examples on day one. No DevOps, no Docker.",
    tag: "One URL change",
  },
]

export function Pillars() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="max-w-2xl">
          <p className="font-mono text-sm text-primary">The product</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Four pillars. One intelligent gateway.
          </h2>
        </div>

        <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2">
          {pillars.map((p) => (
            <div key={p.title} className="bg-card p-7 lg:p-8">
              <div className="flex items-center justify-between">
                <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <p.icon className="h-5 w-5" />
                </div>
                <span className="rounded-full border border-border bg-secondary/50 px-2.5 py-1 font-mono text-[10px] text-muted-foreground">
                  {p.tag}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-semibold tracking-tight">{p.title}</h3>
              <p className="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground">
                {p.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
