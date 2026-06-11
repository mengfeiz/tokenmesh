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
          <div key={s.label} className="px-4 py-6 sm:px-6 sm:py-8 lg:py-10">
            <div className="font-mono text-2xl font-semibold tracking-tight text-foreground sm:text-3xl lg:text-4xl">
              {s.value}
            </div>
            <p className="mt-1.5 text-xs leading-snug text-muted-foreground sm:mt-2 sm:text-sm">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
