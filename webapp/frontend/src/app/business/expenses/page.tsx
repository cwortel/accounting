import { DeleteExpenseButton } from "@/components/delete-row-buttons";
import { ExpenseFilters } from "@/components/expense-filters";
import { ExpenseFormDialog } from "@/components/expense-form-dialog";
import { QuarterSwitcher } from "@/components/quarter-switcher";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { YearSwitcher } from "@/components/year-switcher";
import { api } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export default async function ExpensesPage({
  searchParams,
}: {
  searchParams: Promise<{ jaar?: string; kwartaal?: string; naam?: string; categorie?: string; status?: string }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();
  const kwartaal = params.kwartaal ? Number(params.kwartaal) : undefined;
  const naamFilter = (params.naam || "").toLowerCase();
  const categorieFilter = params.categorie || "Alle";
  const statusFilter = params.status || "Alle";

  const [allExpenses, categories] = await Promise.all([api.expenses.list(jaar, kwartaal), api.categories.list()]);

  let expenses = allExpenses;
  if (naamFilter) expenses = expenses.filter((e) => e.naam.toLowerCase().includes(naamFilter));
  if (categorieFilter !== "Alle") expenses = expenses.filter((e) => e.categorie === categorieFilter);
  if (statusFilter === "Afgerekend") expenses = expenses.filter((e) => e.afgerekend);
  if (statusFilter === "Niet afgerekend") expenses = expenses.filter((e) => !e.afgerekend);

  const totaal = expenses.reduce((sum, e) => sum + e.total, 0);
  const totaalExBtw = expenses.reduce((sum, e) => sum + e.ex_btw, 0);
  const totaalBtw = expenses.reduce((sum, e) => sum + e.btw, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">📤 Uitgaven</h1>
          <p className="text-sm text-muted-foreground">
            {expenses.length} uitgaven · {formatCurrency(totaalExBtw)} ex BTW · {formatCurrency(totaal)} incl. BTW
          </p>
        </div>
        <div className="flex items-center gap-3">
          <QuarterSwitcher kwartaal={kwartaal} />
          <YearSwitcher jaar={jaar} />
          <ExpenseFormDialog categories={categories} />
        </div>
      </div>

      <ExpenseFilters categories={categories} naam={params.naam || ""} categorie={categorieFilter} status={statusFilter} />

      <Card>
        <CardHeader>
          <CardTitle>Alle uitgaven {jaar}</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Datum</TableHead>
                <TableHead>Naam</TableHead>
                <TableHead>Categorie</TableHead>
                <TableHead className="text-right">BTW%</TableHead>
                <TableHead className="text-right">Ex BTW</TableHead>
                <TableHead className="text-right">Totaal</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {expenses.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    Geen uitgaven gevonden. Klik op &ldquo;+ Nieuwe uitgave&rdquo; om te beginnen.
                  </TableCell>
                </TableRow>
              )}
              {expenses.map((e) => (
                <TableRow key={e.id}>
                  <TableCell>{formatDate(e.datum)}</TableCell>
                  <TableCell className="font-medium">{e.naam}</TableCell>
                  <TableCell>{e.categorie}</TableCell>
                  <TableCell className="text-right">{e.btw_pct}%</TableCell>
                  <TableCell className="text-right">{formatCurrency(e.ex_btw)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(e.total)}</TableCell>
                  <TableCell>
                    {e.afgerekend ? (
                      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                        Afgerekend
                      </Badge>
                    ) : (
                      <Badge variant="outline">Open</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <ExpenseFormDialog categories={categories} expense={e} />
                      <DeleteExpenseButton id={e.id} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            {expenses.length > 0 && (
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={4} className="font-medium">
                    Totaal
                  </TableCell>
                  <TableCell className="text-right font-medium">{formatCurrency(totaalExBtw)}</TableCell>
                  <TableCell className="text-right font-medium">{formatCurrency(totaal)}</TableCell>
                  <TableCell colSpan={2} className="text-xs text-muted-foreground">
                    BTW: {formatCurrency(totaalBtw)}
                  </TableCell>
                </TableRow>
              </TableFooter>
            )}
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
