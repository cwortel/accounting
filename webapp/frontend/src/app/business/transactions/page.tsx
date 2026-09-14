import { MatchTransactionDialog } from "@/components/match-transaction-dialog";
import { TransactionFilters } from "@/components/transaction-filters";
import { UnlinkTransactionButton } from "@/components/unlink-transaction-button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { YearSwitcher } from "@/components/year-switcher";
import { api, type BankTransaction } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

function StatusBadge({ tx }: { tx: BankTransaction }) {
  if (tx.expense_id || tx.income_id) {
    return (
      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
        🟢 Gekoppeld
      </Badge>
    );
  }
  if (tx.intern) return <Badge variant="secondary">🔄 Intern</Badge>;
  if (tx.prive) return <Badge variant="secondary">🟡 Privé</Badge>;
  if (tx.btw_betaling) return <Badge variant="secondary">📘 BTW betaling</Badge>;
  return <Badge variant="outline">🔴 Ongekoppeld</Badge>;
}

function isUnmatched(t: BankTransaction) {
  return !t.expense_id && !t.income_id && !t.prive && !t.intern && !t.btw_betaling;
}

function matchesCategorie(t: BankTransaction, categorie: string) {
  switch (categorie) {
    case "Uitgave":
      return Boolean(t.expense_id);
    case "Inkomst":
      return Boolean(t.income_id);
    case "Interne overboeking":
      return t.intern;
    case "Privé onttrekking":
      return t.prive;
    case "BTW betaling":
      return t.btw_betaling;
    case "Ongekoppeld":
      return isUnmatched(t);
    default:
      return true;
  }
}

function TransactionTable({
  transactions,
  jaar,
  categories,
}: {
  transactions: BankTransaction[];
  jaar: number;
  categories: string[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Datum</TableHead>
          <TableHead>Naam</TableHead>
          <TableHead className="text-right">Bedrag</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actie</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {transactions.length === 0 && (
          <TableRow>
            <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
              Geen transacties gevonden.
            </TableCell>
          </TableRow>
        )}
        {transactions.map((tx) => {
          const isLinked = Boolean(tx.expense_id || tx.income_id || tx.prive || tx.intern || tx.btw_betaling);
          return (
            <TableRow key={tx.id}>
              <TableCell>{formatDate(tx.datum)}</TableCell>
              <TableCell className="font-medium">{tx.naam || tx.referentie}</TableCell>
              <TableCell className={`text-right ${tx.bedrag < 0 ? "text-red-600" : "text-emerald-600"}`}>
                {formatCurrency(tx.bedrag)}
              </TableCell>
              <TableCell>
                <StatusBadge tx={tx} />
              </TableCell>
              <TableCell className="text-right">
                {isLinked ? (
                  <UnlinkTransactionButton txId={tx.id} />
                ) : (
                  <MatchTransactionDialog txId={tx.id} jaar={jaar} bedrag={tx.bedrag} categories={categories} />
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export default async function TransactionsPage({
  searchParams,
}: {
  searchParams: Promise<{ jaar?: string; kwartaal?: string; ongekoppeld?: string; naam?: string; categorie?: string }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();
  const kwartaal = params.kwartaal ? Number(params.kwartaal) : undefined;
  const onlyUnmatched = params.ongekoppeld === "1";
  const naamFilter = (params.naam || "").toLowerCase();
  const categorieFilter = params.categorie || "Alle";

  const [allTransactions, accounts, categories] = await Promise.all([
    // Always scoped to business accounts only — private transactions never show up here.
    api.bank.list(jaar, { kwartaal, onlyUnmatched, rekeningType: "zakelijk" }),
    api.accounts.list(),
    api.categories.list(),
  ]);

  let transactions = allTransactions;
  if (naamFilter) {
    transactions = transactions.filter((t) => t.naam.toLowerCase().includes(naamFilter));
  }
  if (categorieFilter !== "Alle") {
    transactions = transactions.filter((t) => matchesCategorie(t, categorieFilter));
  }

  const zakelijkAccounts = accounts.filter((a) => a.type === "zakelijk");
  const betaalIban = zakelijkAccounts.find((a) => a.categorie === "betaalrekening")?.iban;
  const spaarIban = zakelijkAccounts.find((a) => a.categorie === "spaarrekening")?.iban;
  const betaalTx = transactions.filter((t) => t.rekening === betaalIban);
  const spaarTx = transactions.filter((t) => t.rekening === spaarIban);

  const nMatched = transactions.filter((t) => t.expense_id || t.income_id).length;
  const nPrive = transactions.filter((t) => t.prive).length;
  const nIntern = transactions.filter((t) => t.intern).length;
  const nBtw = transactions.filter((t) => t.btw_betaling).length;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">🏦 Zakelijke Transacties</h1>
          <p className="text-sm text-muted-foreground">Alleen zakelijke rekeningen</p>
        </div>
        <YearSwitcher jaar={jaar} />
      </div>

      <TransactionFilters kwartaal={kwartaal} ongekoppeld={onlyUnmatched} naam={params.naam || ""} categorie={categorieFilter} />

      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {[
          ["Transacties", transactions.length],
          ["Gekoppeld", nMatched],
          ["Privé", nPrive],
          ["Intern", nIntern],
          ["BTW betaling", nBtw],
          ["Betaal/Spaar", `${betaalTx.length}/${spaarTx.length}`],
        ].map(([label, value]) => (
          <Card key={label as string}>
            <CardContent className="py-4">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-xl font-semibold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>📌 Betaalrekening transacties</CardTitle>
        </CardHeader>
        <CardContent>
          <TransactionTable transactions={betaalTx} jaar={jaar} categories={categories} />
        </CardContent>
      </Card>

      {spaarTx.length > 0 && (
        <details className="rounded-lg border">
          <summary className="cursor-pointer select-none px-4 py-3 font-medium text-sm">
            💾 Spaarrekening transacties ({spaarTx.length})
          </summary>
          <div className="px-4 pb-4">
            <TransactionTable transactions={spaarTx} jaar={jaar} categories={categories} />
          </div>
        </details>
      )}
    </div>
  );
}
