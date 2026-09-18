import { Card, CardContent, CardTitle } from "@/components/ui/card";

interface Props {
  reportText: string | null;
}

export function ReportCard({ reportText }: Props) {
  return (
    <Card data-testid="report-card">
      <CardTitle>Audit report</CardTitle>
      <CardContent>
        {reportText ? (
          <p className="whitespace-pre-wrap">{reportText}</p>
        ) : (
          <p className="text-slate-500">No report generated.</p>
        )}
      </CardContent>
    </Card>
  );
}
