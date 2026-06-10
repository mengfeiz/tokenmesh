const stats = [
  { value: "35x", label: "cost gap — DeepSeek V3 vs GPT-4o" },
  { value: "$8.4B", label: "LLM API spend, mid-2025" },
  { value: "80%+", label: "gross margin at scale" },
  { value: "60–80%", label: "average bill cut for users" },
]

export function Stats() {
  return (
    <section className="border-b border-border/60">
      <div className="mx-auto grid max-w-7xl grid-cols-2 divide-x divide-y divide-border/60 sm:grid-cols-4 sm:divide-y-0 lg:px-8">
        {stats.map((s) => (
          <div key={s.label} className="px-6 py-8 lg:py-10">
            <div className="font-mono text-3xl font-semibold tracking-tight text-foreground lg:text-4xl">
              {s.value}
            </div>
            <p className="mt-2 text-sm leading-snug text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
