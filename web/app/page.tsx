import Link from "next/link";
import { PublicHeader } from "@/components/layout/public-header";
import { NetworkHero3D } from "@/components/landing/network-hero-3d";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />

      <section className="relative flex flex-1 items-center overflow-hidden px-6 py-20">
        <div className="absolute inset-0 -z-10 opacity-70">
          <NetworkHero3D />
        </div>
        <div className="max-w-2xl">
          <h1 className="text-4xl font-bold leading-tight text-text-primary sm:text-5xl sm:leading-tight">
            A guardrail proxy between your application and every LLM call.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-text-primary/70">
            SentinelAI inspects every prompt and response for injection attempts, PII leaks, and
            schema violations before they reach your users, and evaluates the answers it lets
            through for grounding and hallucination.
          </p>
          <div className="mt-8 flex gap-3">
            <Link href="/signup">
              <Button variant="primary">Get started</Button>
            </Link>
            <a href="#walkthrough">
              <Button variant="secondary">See how it works</Button>
            </a>
          </div>
        </div>
      </section>

      <section id="walkthrough" className="border-t border-bg-surface px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-semibold text-text-primary">How it works</h2>
          <ol className="mt-8 space-y-8">
            <li className="flex gap-4">
              <span className="font-mono text-sm text-accent-teal">01</span>
              <p className="text-text-primary/70">
                Every LLM call in your application routes through SentinelAI first. The proxy runs
                an injection detector against eight known attack patterns, scans for PII and
                secrets with Presidio and regex, validates structured output against your schema
                with one retry on failure, and rate-limits per session, all before the request
                reaches Groq, Gemini, or whichever provider you&apos;ve configured.
              </p>
            </li>
            <li className="flex gap-4">
              <span className="font-mono text-sm text-accent-teal">02</span>
              <p className="text-text-primary/70">
                Responses get scored for grounding and hallucination against your own reference
                data and logged for the Eval Dashboard. If something slips through, it surfaces as
                a Finding with a structured Observed / Analysis / Recommendation writeup, not just
                a raw error.
              </p>
            </li>
            <li className="flex gap-4">
              <span className="font-mono text-sm text-accent-teal">03</span>
              <p className="text-text-primary/70">
                Nothing here auto-fixes or auto-deploys. SentinelAI recommends; a human decides.
              </p>
            </li>
          </ol>
        </div>
      </section>

      <footer className="border-t border-bg-surface px-6 py-8">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 text-sm text-text-primary/50 sm:flex-row sm:justify-between">
          <span>SentinelAI: a domain-agnostic LLM guardrail proxy.</span>
          <nav className="flex gap-4">
            <Link href="/about" className="hover:text-text-primary/80">
              About
            </Link>
            <Link href="/install" className="hover:text-text-primary/80">
              Install
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
