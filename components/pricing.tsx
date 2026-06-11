import { Check } from "lucide-react"

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "/mo",
    desc: "For developers evaluating.",
    features: [
      "BYOK unlimited",
      "Smart routing + self-evolution",
      "Exact-match cache",
      "Community support",
    ],
    cta: "Start free",
    featured: false,
  },
  {
    name: "Pro",
    price: "$9",
    period: "/mo",
    desc: "For active developers.",
    features: [
      "Everything in Free",
      "Deeper routing rules",
      "Semantic cache",
      "Savings dashboard",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
    featured: true,
    note: "Break-even vs OpenRouter's 5.5% fee at ~$163/mo spend.",
  },
  {
    name: "Business",
    price: "$79",
    period: "/mo",
    desc: "For teams.",
    features: [
      "Everything in Pro",
      "Multi-user + SSO",
      "Audit logs",
      "Custom routing config",
      "SLA",
    ],
    cta: "Contact sales",
    featured: false,
  },
  {
    name: "Managed",
    price: "5–8%",
    period: " markup",
    desc: "Keys handled for you.",
    features: [
      "All Pro / Business features",
      "Platform-held provider keys",
      "Consolidated billing",
      "No key management",
    ],
    cta: "Talk to us",
    featured: false,
  },
]

export function Pricing() {
  return (
    <section id="pricing" className="border-b border-border/60">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
        <div className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-sm text-primary">Pricing</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            Impulse-buy pricing. ROI that's obvious.
          </h2>
          <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
            BYOK-first means 80–85% gross margin. Just 25 paying users to break even. Start free, no
            credit card.
          </p>
        </div>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`relative flex flex-col rounded-2xl border p-6 ${
                t.featured
                  ? "border-primary/50 bg-primary/[0.06]"
                  : "border-border bg-card/60"
              }`}
            >
              {t.featured && (
                <span className="absolute -top-3 left-6 rounded-full bg-primary px-3 py-1 text-[11px] font-medium text-primary-foreground">
                  Most popular
                </span>
              )}
              <h3 className="text-sm font-medium text-muted-foreground">{t.name}</h3>
              <div className="mt-3 flex items-baseline">
                <span className="text-3xl font-semibold tracking-tight">{t.price}</span>
                <span className="text-sm text-muted-foreground">{t.period}</span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{t.desc}</p>

              <a
                href="#"
                className={`mt-6 inline-flex items-center justify-center rounded-full px-4 py-2.5 text-sm font-medium transition-colors ${
                  t.featured
                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                    : "border border-border bg-secondary/40 text-foreground hover:bg-secondary"
                }`}
              >
                {t.cta}
              </a>

              <ul className="mt-6 space-y-3 border-t border-border/60 pt-6">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-foreground">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    {f}
                  </li>
                ))}
              </ul>

              {t.note && (
                <p className="mt-5 text-xs leading-relaxed text-muted-foreground">{t.note}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
