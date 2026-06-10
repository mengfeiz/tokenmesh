import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { Logo } from "@/components/logo"
import { DeveloperConsole } from "@/components/console/developer-console"

export const metadata = {
  title: "开发者控制台 — Tokenmesh",
  description: "注册 API Key、复制接入代码、查看省钱看板",
}

export default function ConsolePage() {
  return (
    <main className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <Logo className="h-6 w-6" />
            <span className="text-sm font-semibold">
              Token<span className="text-primary">mesh</span>
            </span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            返回首页
          </Link>
        </div>
      </header>
      <DeveloperConsole />
    </main>
  )
}
