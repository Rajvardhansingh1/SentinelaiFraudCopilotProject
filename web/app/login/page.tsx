"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PublicHeader } from "@/components/layout/public-header";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, user, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Bug fix: an already-authenticated user landing here via back-button (browser
  // history, not a fresh unauthenticated visit) would otherwise dead-end on the
  // bare login form instead of being sent on to the app.
  useEffect(() => {
    if (!loading && user) router.replace("/playground");
  }, [loading, user, router]);

  if (!loading && user) return null;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const result = await login(email, password);
    setSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <PublicHeader />
      <div className="mx-auto grid w-full max-w-4xl flex-1 grid-cols-1 items-center gap-12 px-6 py-16 lg:grid-cols-2">
        <div className="hidden lg:block">
          <h2 className="text-2xl font-semibold text-text-primary">
            Every LLM call, guarded.
          </h2>
          <p className="mt-3 text-text-primary/60">
            Log in to see your findings, run security tests, and review what SentinelAI has
            caught.
          </p>
        </div>

        <Card className="mx-auto w-full max-w-sm">
          <CardHeader>
            <CardTitle>Log in to SentinelAI</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-text-primary/80" htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary focus:border-accent-teal focus:outline-none focus:ring-1 focus:ring-accent-teal"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-text-primary/80" htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary focus:border-accent-teal focus:outline-none focus:ring-1 focus:ring-accent-teal"
                />
              </div>
              {error && (
                <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                  {error}
                </div>
              )}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Logging in..." : "Log in"}
              </Button>
            </form>
            <p className="mt-4 text-sm text-text-primary/60">
              No account?{" "}
              <Link href="/signup" className="text-accent-teal underline underline-offset-2">
                Sign up
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
