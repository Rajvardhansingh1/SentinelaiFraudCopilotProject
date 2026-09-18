"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AttackPicker, FREE_TEXT_VALUE } from "./attack-picker";
import { ResultCard } from "./result-card";
import { postGenerate } from "@/lib/api";
import { findCached, SAMPLE_ATTACKS } from "@/lib/sample-attacks";
import { useSession } from "@/lib/session";
import type { GenerateResponse } from "@/lib/types";

const QUOTA_BANNER = "Quota reached — here's a pre-run example.";

export function SubmitPanel() {
  const { sessionId, incrementCallCount } = useSession();
  const firstAttack = SAMPLE_ATTACKS[0];
  const [selectedId, setSelectedId] = useState<string>(firstAttack?.id ?? FREE_TEXT_VALUE);
  const [promptText, setPromptText] = useState(firstAttack?.prompt ?? "");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    status: number;
    body: GenerateResponse;
    promptText: string;
    banner?: string | null;
    isOwnPrompt: boolean;
  } | null>(null);

  const isFreeText = selectedId === FREE_TEXT_VALUE;
  const attack = SAMPLE_ATTACKS.find((a) => a.id === selectedId);
  const promptId = isFreeText ? null : selectedId;
  // "Own prompt" = free text from scratch, or a preset the user has actually edited.
  // Weakness-coaching only makes sense once it's genuinely the visitor's own attempt,
  // not an untouched preset that's expected to behave a known way.
  const isOwnPrompt = isFreeText || (attack != null && promptText !== attack.prompt);

  function handleSelectId(id: string) {
    setSelectedId(id);
    setResult(null);
    const nextAttack = SAMPLE_ATTACKS.find((a) => a.id === id);
    setPromptText(id === FREE_TEXT_VALUE ? "" : nextAttack?.prompt ?? "");
  }

  async function handleSubmit() {
    if (!promptText || !sessionId) return;
    setLoading(true);
    try {
      const { status, body } = await postGenerate(sessionId, promptText);
      incrementCallCount();

      if (status === 429) {
        const cached = findCached(promptId);
        setResult({ status: cached.status_code, body: cached, promptText, banner: QUOTA_BANNER, isOwnPrompt });
      } else {
        setResult({ status, body, promptText, banner: null, isOwnPrompt });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <AttackPicker
        selectedId={selectedId}
        onSelectId={handleSelectId}
        promptText={promptText}
        onPromptTextChange={(text) => {
          setPromptText(text);
          setResult(null);
        }}
      />

      <Button onClick={handleSubmit} disabled={!promptText || loading} data-testid="submit-button">
        {loading ? "Running through the guardrail pipeline..." : "Submit"}
      </Button>

      {!promptText && (
        <p className="text-sm text-slate-500">
          Pick an attack or write your own, then submit it to see the proxy react.
        </p>
      )}

      {result && (
        <ResultCard
          status={result.status}
          body={result.body}
          promptText={result.promptText}
          cachedBanner={result.banner}
          isOwnPrompt={result.isOwnPrompt}
        />
      )}
    </div>
  );
}
