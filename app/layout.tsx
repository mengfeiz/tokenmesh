import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import "./globals.css"

export const metadata: Metadata = {
  title: "Tokenmesh — Stop paying frontier prices for non-frontier tasks",
  description:
    "The intelligent LLM gateway that routes every request to the most cost-effective model that can handle the job. Drop-in OpenAI-compatible API, BYOK with 0% markup, real-time savings dashboard.",
  generator: "v0.app",
  keywords: [
    "LLM gateway",
    "AI routing",
    "OpenAI compatible",
    "DeepSeek",
    "cost optimization",
    "BYOK",
  ],
}

export const viewport = {
  themeColor: "#0c0f12",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} bg-background`}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
