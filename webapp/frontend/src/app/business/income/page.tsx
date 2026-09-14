import { DeleteIncomeButton } from "@/components/delete-row-buttons";
import { IncomeFormDialog } from "@/components/income-form-dialog";
import { QuarterSwitcher } from "@/components/quarter-switcher";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { YearSwitcher } from "@/components/year-switcher";
import { api } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export default async function IncomePage({
  searchParams,
}: {
  searchParams: Promise<{ jaar?: string; kwartaal?: string }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();
  const kwartaal = params.kwartaal ? Number(params.kwartaal) : undefined;

  const income = await api.income.list(jaar, kwartaal);
  const totaal = income.reduce((sum, i) => sum + i.total, 0);
  const totaalExBtw = income.reduce((sum, i) => sum + i.ex_btw, 0);
  const totaalBtw = income.reduce((sum, i) => sum + i.btw, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">📥 Inkomsten</h1>
          <p className="text-sm text-muted-foreground">
            {income.length} facturen · {formatCurrency(totaalExBtw)} ex BTW · {formatCurrency(totaal)} incl. BTW
          </p>
        </div>
        <div className="flex items-center gap-3">
          <QuarterSwitcher kwartaal={kwartaal} />
          <YearSwitcher jaar={jaar} />
          <IncomeFormDialog />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Alle inkomsten {jaar}</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Datum</TableHead>
                <TableHead>Naam</TableHead>
                <TableHead>Project</TableHead>
                <TableHead className="text-right">BTW%</TableHead>
                <TableHead className="text-right">Ex BTW</TableHead>
                <TableHead className="text-right">Totaal</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {income.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    Geen inkomsten gevonden.
                  </TableCell>
                </TableRow>
              )}
              {income.map((i) => (
                <TableRow key={i.id}>
                  <TableCell>{formatDate(i.datum)}</TableCell>
                  <TableCell className="font-medium">{i.naam}</TableCell>
                  <TableCell>{i.project}</TableCell>
                  <TableCell className="text-right">{i.btw_pct}%</TableCell>
                  <TableCell className="text-right">{formatCurrency(i.ex_btw)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(i.total)}</TableCell>
                  <TableCell>
                    {i.betaald ? (
                      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                        Betaald
                      </Badge>
                    ) : (
                      <Badge variant="outline">Open</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <IncomeFormDialog income={i} />
                      <DeleteIncomeButton id={i.id} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            {income.length > 0 && (
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
