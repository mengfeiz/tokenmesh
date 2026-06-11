import { ArrowRight, Check } from "lucide-react"
import { RoutingDemo } from "./routing-demo"

const trustPoints = ["OpenAI-compatible API", "BYOK · 0% markup", "No DevOps"]

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border/60">
      <div className="absolute inset-0 bg-grid opacity-40" aria-hidden="true" />
      <div
        className="absolute left-1/2 top-0 h-[420px] w-[820px] -translate-x-1/2 rounded-full opacity-25 blur-[120px]"
        style={{ background: "radial-gradient(closest-side, var(--primary), transparent)" }}
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-7xl px-4 pb-16 pt-12 sm:px-6 sm:pb-20 sm:pt-16 lg:px-8 lg:pb-28 lg:pt-24">
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <div className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-secondary/60 px-3 py-1 text-[11px] text-muted-foreground sm:text-xs">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary animate-pulse-soft" />
              <span className="truncate">Seed stage · The 35x era of LLM cost</span>
            </div>

            <h1 className="mt-5 text-balance text-[1.75rem] font-semibold leading-[1.08] tracking-tight sm:mt-6 sm:text-5xl lg:text-6xl">
              Stop paying frontier prices for{" "}
              <span className="text-primary">non-frontier tasks</span>.
            </h1>

            <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:mt-6 sm:text-lg">
              Tokenmesh is the intelligent LLM gateway that classifies every request and routes it
              to the cheapest model that can handle the job. One URL change. Cut your bill 60–80%.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a
                href="/console"
                className="group inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Start free — no card
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </a>
              <a
                href="#how"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-border bg-secondary/40 px-6 py-3 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
              >
                See how routing works
              </a>
            </div>

            <ul className="mt-6 flex flex-col gap-2 sm:mt-8 sm:flex-row sm:flex-wrap sm:gap-x-6 sm:gap-y-2">
              {trustPoints.map((p) => (
                <li key={p} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Check className="h-4 w-4 text-primary" />
                  {p}
                </li>
              ))}
            </ul>
          </div>

          <RoutingDemo />
        </div>
      </div>
    </section>
  )
}
