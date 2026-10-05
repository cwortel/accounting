import { formatCurrency, formatDate } from "@/lib/format";

export function LinkedSummaryCard({
  naam,
  datum,
  amount,
  extra,
}: {
  naam: string;
  datum: string | null;
  amount: number;
  extra?: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
      <div>
        <p className="font-medium">{naam || "—"}</p>
        <p className="text-muted-foreground">
          {formatDate(datum)}
          {extra ? ` · ${extra}` : ""}
        </p>
      </div>
      <span className="font-medium">{formatCurrency(amount)}</span>
    </div>
  );
}
