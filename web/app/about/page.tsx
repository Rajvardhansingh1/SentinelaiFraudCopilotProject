import { PublicHeader } from "@/components/layout/public-header";

export default function AboutPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <main className="mx-auto max-w-3xl space-y-8 px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary">About SentinelAI</h1>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-text-primary">What it is</h2>
          <p className="text-text-primary/70">
            SentinelAI is a reusable, domain-agnostic FastAPI proxy that sits between your
            application and any LLM provider. Every request and response passes through
            injection detection, PII/secret scanning, structured-output validation, and
            hallucination/grounding evaluation before it reaches a user.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-text-primary">Human in the loop</h2>
          <p className="text-text-primary/70">
            SentinelAI does not automatically apply fixes, deploy changes, or approve/reject a
            finding. It records evidence and recommends. A person decides.
          </p>
        </section>
      </main>
    </div>
  );
}
