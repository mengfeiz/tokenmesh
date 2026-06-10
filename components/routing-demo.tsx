"use client"

import { useState } from "react"
import { ArrowRight, Zap } from "lucide-react"

type Example = {
  prompt: string
  task: string
  model: string
  baseline: string
  savings: number
  complexity: string
}

const examples: Example[] = [
  {
    prompt: "What is the capital of France?",
    task: "simple_qa",
    model: "deepseek/deepseek-chat",
    baseline: "openai/gpt-4o",
    savings: 95,
    complexity: "low",
  },
  {
    prompt: "Write a Python quicksort and explain its time complexity.",
    task: "coding",
    model: "deepseek/deepseek-reasoner",
    baseline: "openai/gpt-4o",
    savings: 80,
    complexity: "medium",
  },
  {
    prompt: "Summarize this 40-page contract into key points.",
    task: "summarization",
    model: "qwen/qwen-long",
    baseline: "openai/gpt-4o",
    savings: 70,
    complexity: "medium",
  },
  {
    prompt: "Compare the tradeoffs of REST vs GraphQL for our platform.",
    task: "reasoning",
    model: "anthropic/claude-sonnet-4",
    baseline: "openai/gpt-4o",
    savings: 0,
    complexity: "high",
  },
]

export function RoutingDemo() {
  const [active, setActive] = useState(0)
  const ex = examples[active]
  const qualityFirst = ex.savings === 0

  return (
    <div className="relative">
      <div className="rounded-2xl border border-border bg-card/80 p-2 shadow-2xl backdrop-blur">
        {/* window chrome */}
        <div className="flex items-center justify-between px-3 py-2">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
            <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
          </div>
          <span className="font-mono text-[11px] text-muted-foreground">POST /v1/routing/explain</span>
        </div>

        <div className="rounded-xl border border-border bg-background p-4">
          <p className="text-xs text-muted-foreground">Try a prompt</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {examples.map((e, i) => (
              <button
                key={i}
                onClick={() => setActive(i)}
                className={`rounded-md px-2.5 py-1 text-[11px] transition-colors ${
                  i === active
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground"
                }`}
              >
                {e.task}
              </button>
            ))}
          </div>

          <div className="mt-3 rounded-lg border border-border bg-card px-3 py-2.5 font-mono text-sm leading-relaxed text-foreground">
            {ex.prompt}
          </div>

          {/* routing flow */}
          <div className="mt-4 flex items-center justify-between gap-2">
            <div className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-center">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Classified</p>
              <p className="mt-0.5 font-mono text-xs text-foreground">{ex.task}</p>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-primary" />
            <div className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-center">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Complexity</p>
              <p className="mt-0.5 font-mono text-xs text-foreground">{ex.complexity}</p>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-primary" />
            <div className="flex-[1.4] rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-center">
              <p className="text-[10px] uppercase tracking-wide text-primary">Routed to</p>
              <p className="mt-0.5 truncate font-mono text-xs text-foreground">{ex.model}</p>
            </div>
          </div>

          {/* savings */}
          <div className="mt-4 flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              <span className="text-sm text-muted-foreground">
                {qualityFirst ? "Quality-first route" : "Saved vs default GPT-4o"}
              </span>
            </div>
            <span
              className={`font-mono text-lg font-semibold ${
                qualityFirst ? "text-foreground" : "text-primary"
              }`}
            >
              {qualityFirst ? "best model" : `~${ex.savings}%`}
            </span>
          </div>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            {qualityFirst
              ? "Hard reasoning stays on a frontier model — no quality lost."
              : `Baseline ${ex.baseline} → ${ex.model}`}
          </p>
        </div>
      </div>
    </div>
  )
}
