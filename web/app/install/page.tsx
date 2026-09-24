import { PublicHeader } from "@/components/layout/public-header";

function TerminalBlock({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-bg-surface bg-bg-surface/60 p-4 font-mono text-sm text-text-primary">
      {children}
    </pre>
  );
}

export default function InstallPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <main className="mx-auto max-w-3xl space-y-8 px-6 py-16">
        <h1 className="text-3xl font-bold text-text-primary">Installation guide</h1>
        <p className="text-text-primary/70">
          Two services: the SentinelAI proxy (Python/FastAPI) and the Next.js frontend. Run both
          locally to try the full flow.
        </p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-text-primary">1. Python dependencies</h2>
          <TerminalBlock>{`python -m venv .venv\n.venv\\Scripts\\activate          # Windows; source .venv/bin/activate on Linux/Mac\npip install -r requirements.txt`}</TerminalBlock>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-text-primary">2. Credentials</h2>
          <TerminalBlock>{`copy .env.example .env          # cp on Linux/Mac\n# edit .env, at minimum set GROQ_API_KEY`}</TerminalBlock>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-text-primary">3. Start the SentinelAI proxy</h2>
          <TerminalBlock>{`.venv\\Scripts\\python -m uvicorn proxy.main:app --port 8000`}</TerminalBlock>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold text-text-primary">4. Start the frontend</h2>
          <TerminalBlock>{`cd web\nnpm install\nnpm run dev`}</TerminalBlock>
          <p className="text-sm text-text-primary/60">
            Open <code>http://localhost:3000</code>. <code>web/.env.local</code> (copy from
            <code> .env.local.example</code>) must point at the proxy:
          </p>
          <TerminalBlock>{`NEXT_PUBLIC_PROXY_BASE_URL=http://localhost:8000`}</TerminalBlock>
        </section>
      </main>
    </div>
  );
}
