import { AccountFormDialog } from "@/components/account-form-dialog";
import { BankImportPanel } from "@/components/bank-import-panel";
import { DeleteAccountButton } from "@/components/delete-row-buttons";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { YearSwitcher } from "@/components/year-switcher";
import { api } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export default async function AccountsPage({
  searchParams,
}: {
  searchParams: Promise<{ jaar?: string }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();

  const [accounts, transactions] = await Promise.all([api.accounts.list(), api.bank.list(jaar)]);

  const zakelijk = accounts.filter((a) => a.type === "zakelijk");
  const prive = accounts.filter((a) => a.type === "prive");
  const totaalZakelijk = zakelijk.reduce((sum, a) => sum + a.saldo, 0);
  const totaalPrive = prive.reduce((sum, a) => sum + a.saldo, 0);

  const statsPerAccount = accounts.map((a) => {
    const tx = transactions.filter((t) => t.rekening === a.iban);
    const matched = tx.filter((t) => t.expense_id || t.income_id).length;
    const priveCount = tx.filter((t) => t.prive).length;
    return {
      account: a,
      totaal: tx.length,
      matched,
      prive: priveCount,
      ongekoppeld: tx.length - matched - priveCount,
    };
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">💳 Rekeningen &amp; Saldo</h1>
          <p className="text-sm text-muted-foreground">{accounts.length} rekeningen</p>
        </div>
        <AccountFormDialog />
      </div>

      <BankImportPanel />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { title: "💼 Zakelijk", accounts: zakelijk, totaal: totaalZakelijk },
          { title: "🏠 Privé", accounts: prive, totaal: totaalPrive },
        ].map(({ title, accounts: group, totaal }) => (
          <Card key={title}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground mb-1">{title}</p>
              <p className="text-2xl font-semibold mb-3">{formatCurrency(totaal)}</p>
              <div className="flex flex-col gap-1 text-sm">
                {group.map((a) => (
                  <div key={a.id} className="flex justify-between text-muted-foreground">
                    <span>{a.categorie === "spaarrekening" ? "💰" : "🏦"} {a.naam}</span>
                    <span className="font-medium text-foreground">{formatCurrency(a.saldo)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rekeningen</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Naam</TableHead>
                <TableHead>IBAN</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Categorie</TableHead>
                <TableHead className="text-right">Saldo</TableHead>
                <TableHead>Laatst bijgewerkt</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    Nog geen rekeningen.
                  </TableCell>
                </TableRow>
              )}
              {accounts.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.naam}</TableCell>
                  <TableCell className="font-mono text-xs">{a.iban}</TableCell>
                  <TableCell>
                    <Badge variant={a.type === "zakelijk" ? "default" : "secondary"}>{a.type}</Badge>
                  </TableCell>
                  <TableCell>{a.categorie}</TableCell>
                  <TableCell className="text-right">{formatCurrency(a.saldo)}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{formatDate(a.laatste_update)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <AccountFormDialog account={a} />
                      <DeleteAccountButton id={a.id} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Transacties per rekening ({jaar})</CardTitle>
          <YearSwitcher jaar={jaar} />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rekening</TableHead>
                <TableHead>IBAN</TableHead>
                <TableHead className="text-right">Transacties</TableHead>
                <TableHead className="text-right">Gekoppeld</TableHead>
                <TableHead className="text-right">Privé</TableHead>
                <TableHead className="text-right">Ongekoppeld</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {statsPerAccount.map(({ account, totaal, matched, prive: priveCount, ongekoppeld }) => (
                <TableRow key={account.id}>
                  <TableCell className="font-medium">{account.naam}</TableCell>
                  <TableCell className="font-mono text-xs">{account.iban}</TableCell>
                  <TableCell className="text-right">{totaal}</TableCell>
                  <TableCell className="text-right">{matched}</TableCell>
                  <TableCell className="text-right">{priveCount}</TableCell>
                  <TableCell className="text-right">{ongekoppeld}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
