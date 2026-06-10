"use client"

import { useState } from "react"
import { Plus, Minus } from "lucide-react"

const faqs = [
  {
    q: "If your classifier is only 60% accurate, does it still have value?",
    a: "Yes — the failure mode is asymmetric. If routing is wrong, the fallback is your original model: no worse than before. If routing is right, you save 60–95%. 60% accuracy means 60% of requests cheaper, 0% more expensive. V1 ships rule-based — no ML needed to prove the value.",
  },
  {
    q: "Why Tokenmesh vs NotDiamond?",
    a: "Two structural gaps. NotDiamond has no DeepSeek, Qwen, or Kimi — without these the cost gap is 30%, not 80%, and the story doesn't work. And NotDiamond is an SDK requiring integration work; Tokenmesh is a managed gateway — one URL change.",
  },
  {
    q: "What if OpenRouter adds task routing tomorrow?",
    a: "OpenRouter's business model is built on a 5.5% credit fee. Smart routing to DeepSeek (35x cheaper) directly reduces their revenue by up to 97% per routed request. They have a structural disincentive to build this well. It's a business-model moat, not just a technical one.",
  },
  {
    q: "How do I integrate it?",
    a: "Change your OpenAI base_url to Tokenmesh and set model to \u201cauto\u201d. Everything else stays the same. Works with the OpenAI SDK in Python, Node.js, and plain curl. BYOK headers pass your provider keys per request — no keys are stored.",
  },
  {
    q: "What does the platform NOT do in v1?",
    a: "It does not fine-tune or host models, does not provide a user-facing chat interface, does not handle multimodal generation, and does not offer on-premise deployment. It's a focused routing layer.",
  },
  {
    q: "Is my data and are my keys safe?",
    a: "In BYOK mode keys are passed per request and never persisted. Managed mode is opt-in. The routing layer targets 99.9%+ uptime with sub-second failover across providers.",
  },
]

export function Faq() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section id="faq" className="border-b border-border/60">
      <div className="mx-auto max-w-3xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="text-center">
          <p className="font-mono text-sm text-primary">FAQ</p>
          <h2 className="mt-3 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
            The hard questions, answered.
          </h2>
        </div>

        <div className="mt-12 divide-y divide-border/60 overflow-hidden rounded-2xl border border-border bg-card/40">
          {faqs.map((f, i) => (
            <div key={i}>
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left"
                aria-expanded={open === i}
              >
                <span className="text-sm font-medium text-foreground">{f.q}</span>
                {open === i ? (
                  <Minus className="h-4 w-4 shrink-0 text-primary" />
                ) : (
                  <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />
                )}
              </button>
              {open === i && (
                <p className="px-6 pb-5 text-sm leading-relaxed text-muted-foreground">{f.a}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
