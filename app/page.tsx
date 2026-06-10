import { Navbar } from "@/components/navbar"
import { Hero } from "@/components/hero"
import { Stats } from "@/components/stats"
import { Problem } from "@/components/problem"
import { HowItWorks } from "@/components/how-it-works"
import { Pillars } from "@/components/pillars"
import { Models } from "@/components/models"
import { Dashboard } from "@/components/dashboard"
import { Comparison } from "@/components/comparison"
import { Pricing } from "@/components/pricing"
import { Faq } from "@/components/faq"
import { Cta } from "@/components/cta"
import { Footer } from "@/components/footer"

export default function Page() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <Hero />
      <Stats />
      <Problem />
      <HowItWorks />
      <Pillars />
      <Models />
      <Dashboard />
      <Comparison />
      <Pricing />
      <Faq />
      <Cta />
      <Footer />
    </main>
  )
}
