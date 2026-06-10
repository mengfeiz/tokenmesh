import { Check, X, Minus } from "lucide-react"

const columns = ["Tokenmesh", "OpenRouter", "NotDiamond", "LiteLLM", "Portkey"]

type Cell = { v: string; type: "good" | "bad" | "mid" }

const rows: { label: string; cells: Cell[] }[] = [
  {
    label: "Task-aware routing",
    cells: [
      { v: "Smart", type: "good" },
      { v: "None", type: "bad" },
      { v: "ML-based", type: "mid" },
      { v: "None", type: "bad" },
      { v: "None", type: "bad" },
    ],
  },
  {
    label: "DeepSeek / Qwen / Kimi",
    cells: [
      { v: "Full", type: "good" },
      { v: "No", type: "bad" },
      { v: "No", type: "bad" },
      { v: "Partial", type: "mid" },
      { v: "No", type: "bad" },
    ],
  },
  {
    label: "BYOK 0% fee",
    cells: [
      { v: "Yes", type: "good" },
      { v: "5.5% fee", type: "bad" },
      { v: "SDK", type: "mid" },
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
    ],
  },
  {
    label: "No DevOps",
    cells: [
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
      { v: "No", type: "bad" },
      { v: "DevOps", type: "bad" },
      { v: "Yes", type: "good" },
    ],
  },
  {
    label: "Savings dashboard",
    cells: [
      { v: "Real-time", type: "good" },
      { v: "No", type: "bad" },
      { v: "No", type: "bad" },
      { v: "No", type: "bad" },
      { v: "Basic", type: "mid" },
    ],
  },
  {
    label: "Auto failover",
    cells: [
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
      { v: "Yes", type: "good" },
    ],
  },
]

function Icon({ type }: { type: Cell["type"] }) {
  if (type === "good") return <Check className="h-3.5 w-3.5 text-primary" />
  if (type === "bad") return <X className="h-3.5 w-3.5 text-muted-foreground/50" />
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />
}

export function Comparison() {
  return (
    <section id="compare" className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="max-w-2xl">
          <p className="font-mono text-sm text-primary">Why Tokenmesh</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            A structural moat, not just a feature.
          </h2>
          <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
            OpenRouter can't route to DeepSeek without destroying its own 5.5% fee revenue.
            NotDiamond has no managed gateway. Smart routing + full catalog + managed platform is
            currently unoccupied.
          </p>
        </div>

        <div className="mt-12 overflow-x-auto">
          <div className="min-w-[720px] overflow-hidden rounded-2xl border border-border">
            <div className="grid grid-cols-6 border-b border-border bg-secondary/40">
              <div className="px-5 py-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Capability
              </div>
              {columns.map((c, i) => (
                <div
                  key={c}
                  className={`px-4 py-4 text-center text-sm font-semibold ${
                    i === 0 ? "text-primary" : "text-muted-foreground"
                  }`}
                >
                  {c}
                </div>
              ))}
            </div>
            {rows.map((r) => (
              <div
                key={r.label}
                className="grid grid-cols-6 border-b border-border/60 last:border-0"
              >
                <div className="px-5 py-3.5 text-sm text-foreground">{r.label}</div>
                {r.cells.map((cell, i) => (
                  <div
                    key={i}
                    className={`flex flex-col items-center justify-center gap-1 px-4 py-3.5 text-center ${
                      i === 0 ? "bg-primary/[0.06]" : ""
                    }`}
                  >
                    <Icon type={cell.type} />
                    <span
                      className={`font-mono text-[11px] ${
                        i === 0 && cell.type === "good"
                          ? "text-foreground"
                          : "text-muted-foreground"
                      }`}
                    >
                      {cell.v}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
