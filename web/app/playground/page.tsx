"use client";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SubmitPanel } from "@/components/playground/submit-panel";
import { SYSTEM_PROMPT } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function PlaygroundPage() {
  const { callCount } = useSession();

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">SentinelAI Red-Team Playground</h1>
          <p className="text-sm text-slate-400">
            Try to jailbreak the proxy. Every attempt is scanned, scored, and logged in real time.
          </p>
        </div>
        <div
          className="rounded-md border border-accent-teal/40 bg-accent-teal/10 px-3 py-1 text-sm text-accent-teal"
          data-testid="quota-badge"
        >
          Calls used: {callCount} / 8
        </div>
      </div>

      <Collapsible>
        <CollapsibleTrigger className="text-sm text-accent-teal underline underline-offset-2">
          What&apos;s the system prompt the attacker is up against?
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 rounded-md border border-bg-surface bg-bg-base p-3 text-sm text-slate-300">
          <pre className="whitespace-pre-wrap">{SYSTEM_PROMPT}</pre>
        </CollapsibleContent>
      </Collapsible>

      <SubmitPanel />
    </div>
  );
}
