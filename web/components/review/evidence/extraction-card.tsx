import { Card, CardContent, CardTitle } from "@/components/ui/card";
import type { ExtractedFields } from "@/lib/types";

interface Props {
  fields: ExtractedFields | null;
}

export function ExtractionCard({ fields }: Props) {
  return (
    <Card data-testid="extraction-card">
      <CardTitle>Extracted fields</CardTitle>
      <CardContent>
        {!fields ? (
          <p className="text-slate-500">No extraction data available.</p>
        ) : (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2">
            <dt className="text-slate-500">Vendor</dt>
            <dd>{fields.vendor ?? "—"}</dd>
            <dt className="text-slate-500">Date</dt>
            <dd>{fields.date ?? "—"}</dd>
            <dt className="text-slate-500">Total</dt>
            <dd>{fields.total != null ? `$${fields.total.toFixed(2)}` : "—"}</dd>
            <dt className="text-slate-500">Line items</dt>
            <dd>
              {fields.line_items.length === 0 ? (
                "—"
              ) : (
                <ul className="list-disc pl-5">
                  {fields.line_items.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              )}
            </dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
