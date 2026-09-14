import { PrognoseCalculator } from "@/components/prognose-calculator";
import { api } from "@/lib/api";

export default async function PrognosePage() {
  const today = new Date();
  const [accounts, cashflow, debts, btwThisYear, btwNextYear, beginsaldoSetting] = await Promise.all([
    api.accounts.list(),
    api.reports.monthlyCashflow(),
    api.private.debts.list(true),
    api.reports.btwBetalingen(today.getFullYear()),
    api.reports.btwBetalingen(today.getFullYear() + 1),
    api.settings.get("prognose_beginsaldo"),
  ]);

  const currentSaldo = accounts.filter((a) => a.type === "zakelijk").reduce((sum, a) => sum + a.saldo, 0);

  const btwPaidByYear: Record<number, Set<number>> = {
    [today.getFullYear()]: new Set(Object.keys(btwThisYear).map(Number)),
    [today.getFullYear() + 1]: new Set(Object.keys(btwNextYear).map(Number)),
  };

  const initialBeginsaldo = Number(beginsaldoSetting.value) || 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">📈 Prognose</h1>
        <p className="text-sm text-muted-foreground">Cashflow-projectie voor de zakelijke rekeningen</p>
      </div>

      <PrognoseCalculator
        currentSaldo={currentSaldo}
        cashflow={cashflow}
        debts={debts}
        btwPaidByYear={btwPaidByYear}
        initialBeginsaldo={initialBeginsaldo}
      />
    </div>
  );
}
