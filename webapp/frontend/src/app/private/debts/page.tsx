import { DebtFormDialog } from "@/components/debt-form-dialog";
import { DeleteDebtButton } from "@/components/delete-row-buttons";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default async function DebtsPage() {
  const debts = await api.private.debts.list();

  const totaalRestant = debts.filter((d) => d.actief).reduce((sum, d) => sum + d.huidig_restant, 0);
  const totaalPerMaand = debts
    .filter((d) => d.actief)
    .reduce((sum, d) => {
      const factor: Record<string, number> = { maandelijks: 1, kwartaal: 1 / 3, halfjaar: 1 / 6, jaar: 1 / 12, eenmalig: 0 };
      return sum + d.termijn_bedrag * (factor[d.frequentie] ?? 1);
    }, 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">💰 Schulden</h1>
          <p className="text-sm text-muted-foreground">
            {formatCurrency(totaalRestant)} restant · {formatCurrency(totaalPerMaand)} p/m
          </p>
        </div>
        <DebtFormDialog />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Alle schulden</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Naam</TableHead>
                <TableHead>Partij</TableHead>
                <TableHead className="text-right">Origineel</TableHead>
                <TableHead className="text-right">Restant</TableHead>
                <TableHead className="text-right">Termijn</TableHead>
                <TableHead>Frequentie</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {debts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    Nog geen schulden geregistreerd.
                  </TableCell>
                </TableRow>
              )}
              {debts.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="font-medium">{d.naam}</TableCell>
                  <TableCell>{d.partij}</TableCell>
                  <TableCell className="text-right">{formatCurrency(d.origineel_bedrag)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(d.huidig_restant)}</TableCell>
                  <TableCell className="text-right">{formatCurrency(d.termijn_bedrag)}</TableCell>
                  <TableCell>{d.frequentie}</TableCell>
                  <TableCell>
                    {d.actief ? (
                      <Badge variant="outline">Actief</Badge>
                    ) : (
                      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                        Afgelost
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <DebtFormDialog debt={d} />
                      <DeleteDebtButton id={d.id} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
