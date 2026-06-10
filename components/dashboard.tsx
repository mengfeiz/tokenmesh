import { ArrowUpRight, Database, Zap } from "lucide-react"

const bars = [
  { label: "Wk 1", saved: 28, spend: 12 },
  { label: "Wk 2", saved: 41, spend: 16 },
  { label: "Wk 3", saved: 53, spend: 19 },
  { label: "Wk 4", saved: 74, spend: 22 },
]
const max = 74

export function Dashboard() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <p className="font-mono text-sm text-primary">Savings dashboard</p>
            <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              Proof it's working — a real number, not a feature gate.
            </h2>
            <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
              After two weeks of usage, Tokenmesh shows exactly what smart routing saved you. The ROI
              is visible and personal: &ldquo;You saved $34. Pro costs $9.&rdquo; The upgrade sells
              itself.
            </p>

            <div className="mt-8 grid grid-cols-3 gap-4">
              {[
                { v: "$34.10", l: "Saved this month" },
                { v: "74%", l: "Avg cost reduction" },
                { v: "27%", l: "Cache hit rate" },
              ].map((s) => (
                <div key={s.l} className="rounded-xl border border-border bg-card/60 p-4">
                  <p className="font-mono text-xl font-semibold text-primary">{s.v}</p>
                  <p className="mt-1 text-xs leading-snug text-muted-foreground">{s.l}</p>
                </div>
              ))}
            </div>
          </div>

          {/* dashboard mock */}
          <div className="rounded-2xl border border-border bg-card/80 p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">Cumulative savings</span>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 font-mono text-[11px] text-primary">
                <ArrowUpRight className="h-3 w-3" />
                last 30 days
              </span>
            </div>

            <div className="mt-8 flex h-48 items-end justify-between gap-4">
              {bars.map((b) => (
                <div key={b.label} className="flex flex-1 flex-col items-center gap-2">
                  <div className="flex h-full w-full items-end justify-center gap-1.5">
                    <div
                      className="w-3 rounded-t bg-primary"
                      style={{ height: `${(b.saved / max) * 100}%` }}
                    />
                    <div
                      className="w-3 rounded-t bg-secondary"
                      style={{ height: `${(b.spend / max) * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground">{b.label}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 flex items-center gap-5 border-t border-border pt-4">
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="h-2.5 w-2.5 rounded-sm bg-primary" /> Saved
              </span>
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="h-2.5 w-2.5 rounded-sm bg-secondary" /> Actual spend
              </span>
              <span className="ml-auto flex items-center gap-1.5 font-mono text-xs text-muted-foreground">
                <Database className="h-3.5 w-3.5" />
                SQLite usage log
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
