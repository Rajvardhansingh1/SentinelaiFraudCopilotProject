"use client";

import { SAMPLE_ATTACKS } from "@/lib/sample-attacks";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export const MAX_FREE_TEXT_CHARS = 500;
const FREE_TEXT_VALUE = "__free_text__";

interface Props {
  selectedId: string;
  onSelectId: (id: string) => void;
  promptText: string;
  onPromptTextChange: (text: string) => void;
}

export function AttackPicker({ selectedId, onSelectId, promptText, onPromptTextChange }: Props) {
  return (
    <div className="space-y-3">
      <Select
        value={selectedId}
        onChange={(e) => onSelectId(e.target.value)}
        data-testid="attack-select"
      >
        <option value={FREE_TEXT_VALUE}>(free text)</option>
        {SAMPLE_ATTACKS.map((a) => (
          <option key={a.id} value={a.id}>
            {a.label}
          </option>
        ))}
      </Select>

      {/* Always editable — picking a preset just prefills starting text. Editing it
          is what turns it into "your own prompt" for weakness-coaching purposes. */}
      <Textarea
        value={promptText}
        maxLength={MAX_FREE_TEXT_CHARS}
        onChange={(e) => onPromptTextChange(e.target.value)}
        placeholder="Write your own adversarial prompt"
        data-testid="prompt-textarea"
      />
      <p className="text-xs text-slate-500">
        {selectedId === FREE_TEXT_VALUE
          ? "Free text — write anything."
          : "Prefilled from the preset above. Edit it to test your own variant."}
      </p>
    </div>
  );
}

export { FREE_TEXT_VALUE };
