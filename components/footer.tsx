import { Logo } from "./logo"

const groups = [
  {
    title: "Product",
    links: ["How it works", "Models", "Pricing", "Savings dashboard"],
  },
  {
    title: "Developers",
    links: ["Docs", "API reference", "Quickstart", "Status"],
  },
  {
    title: "Company",
    links: ["About", "Blog", "Careers", "Contact"],
  },
]

export function Footer() {
  return (
    <footer className="bg-background">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <a href="#" className="flex items-center gap-2.5" aria-label="Tokenmesh home">
              <Logo className="h-7 w-7" />
              <span className="text-[15px] font-semibold tracking-tight">
                Token<span className="text-primary">mesh</span>
              </span>
            </a>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              The intelligent LLM gateway. Stop paying frontier prices for non-frontier tasks.
            </p>
            <p className="mt-6 font-mono text-xs text-muted-foreground">
              base_url = <span className="text-foreground">https://api.tokenmesh.ai/v1</span>
            </p>
          </div>

          {groups.map((g) => (
            <div key={g.title}>
              <h3 className="text-sm font-medium text-foreground">{g.title}</h3>
              <ul className="mt-4 space-y-3">
                {g.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#"
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border/60 pt-8 sm:flex-row">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Tokenmesh · OpenAI-compatible API
          </p>
          <div className="flex items-center gap-6">
            <a href="#" className="text-xs text-muted-foreground hover:text-foreground">
              Privacy
            </a>
            <a href="#" className="text-xs text-muted-foreground hover:text-foreground">
              Terms
            </a>
            <a href="#" className="text-xs text-muted-foreground hover:text-foreground">
              GitHub
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
