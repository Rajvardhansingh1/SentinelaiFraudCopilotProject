"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { SAMPLE_RECEIPTS } from "@/lib/sample-receipts";

interface Props {
  onRun: (file: File, label: string) => void;
  loading: boolean;
}

export function ReceiptPicker({ onRun, loading }: Props) {
  const [chosen, setChosen] = useState<{ file: File; label: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function chooseSample(sample: (typeof SAMPLE_RECEIPTS)[number]) {
    const resp = await fetch(sample.url);
    const blob = await resp.blob();
    const file = new File([blob], `${sample.id}.jpg`, { type: blob.type || "image/jpeg" });
    setChosen({ file, label: sample.label });
  }

  function chooseUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) setChosen({ file, label: file.name });
  }

  return (
    <div className="space-y-3" data-testid="receipt-picker">
      <div className="flex flex-wrap items-center gap-3">
        {SAMPLE_RECEIPTS.map((sample) => (
          <Button
            key={sample.id}
            variant={chosen?.label === sample.label ? "primary" : "secondary"}
            onClick={() => chooseSample(sample)}
            data-testid={`sample-${sample.id}`}
          >
            {sample.label}
          </Button>
        ))}
        <span className="text-sm text-slate-500">or</span>
        <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
          Upload a receipt
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".png,.jpg,.jpeg"
          className="hidden"
          onChange={chooseUpload}
        />
      </div>

      {chosen && <p className="text-sm text-slate-400">Loaded: {chosen.label}</p>}

      <Button
        onClick={() => chosen && onRun(chosen.file, chosen.label)}
        disabled={!chosen || loading}
        data-testid="run-analysis-button"
      >
        {loading ? "Running analysis..." : "Run analysis"}
      </Button>
    </div>
  );
}
