import { CategoryChart } from "@/components/charts/category-chart";
import { QuarterlyChart } from "@/components/charts/quarterly-chart";
import { KpiCard } from "@/components/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { YearSwitcher } from "@/components/year-switcher";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ jaar?: string }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();

  const [summary, categoryBreakdown, aangifte] = await Promise.all([
    api.reports.yearlySummary(jaar),
    api.reports.expenseByCategory(jaar),
    api.reports.btwAangifte(jaar),
  ]);

  const totals = summary.reduce(
    (acc, q) => ({
      omzet: acc.omzet + q.omzet,
      kosten: acc.kosten + q.kosten,
      winst: acc.winst + q.winst,
      btw_saldo: acc.btw_saldo + q.btw_saldo,
    }),
    { omzet: 0, kosten: 0, winst: 0, btw_saldo: 0 }
  );

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">💚 Green Light Boekhouding</h1>
          <p className="text-sm text-muted-foreground">Jaaroverzicht {jaar}</p>
        </div>
        <YearSwitcher jaar={jaar} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Omzet (ex BTW)" value={formatCurrency(totals.omzet)} />
        <KpiCard label="Kosten (ex BTW)" value={formatCurrency(totals.kosten)} />
        <KpiCard
          label="Winst (ex BTW)"
          value={formatCurrency(totals.winst)}
          tone={totals.winst >= 0 ? "positive" : "negative"}
        />
        <KpiCard
          label="BTW saldo"
          value={formatCurrency(totals.btw_saldo)}
          hint="Positief = te betalen"
          tone={totals.btw_saldo > 0 ? "negative" : "positive"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Per kwartaal</CardTitle>
        </CardHeader>
        <CardContent>
          <QuarterlyChart data={summary} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>BTW aangifte per kwartaal</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {aangifte.map((row) => {
              const saldo = Number(row.saldo ?? 0);
              const label =
                saldo === 0
                  ? "geen saldo"
                  : saldo > 0
                    ? `${formatCurrency(saldo)} te betalen`
                    : `${formatCurrency(Math.abs(saldo))} terug te vragen`;
              return (
                <div key={String(row.kwartaal)} className="rounded-lg border p-4">
                  <p className="text-sm font-medium mb-1">Q{row.kwartaal}</p>
                  <p className="text-xs text-muted-foreground mb-2">{label}</p>
                  <dl className="text-xs space-y-1">
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">BTW 21%</dt>
                      <dd>{formatCurrency(Number(row.btw_21 ?? 0))}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">BTW 9%</dt>
                      <dd>{formatCurrency(Number(row.btw_9 ?? 0))}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Aftrekbaar</dt>
                      <dd>{formatCurrency(Number(row.aftrekbare_btw ?? 0))}</dd>
                    </div>
                  </dl>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Kosten per categorie (ex BTW)</CardTitle>
        </CardHeader>
        <CardContent>
          <CategoryChart data={categoryBreakdown} />
        </CardContent>
      </Card>
    </div>
  );
}
