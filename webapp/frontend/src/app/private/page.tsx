import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/kpi-card";
import { PriveFilters } from "@/components/prive-filters";
import { PriveTransactionEditor } from "@/components/prive-transaction-editor";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { YearSwitcher } from "@/components/year-switcher";
import { api } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const LENING_CATEGORIES = new Set(["lening", "leningen"]);

export default async function PrivateDashboardPage({
  searchParams,
}: {
  searchParams: Promise<{
    jaar?: string;
    maand?: string;
    rekening?: string;
    naam?: string;
    categorie?: string;
    ongecategoriseerd?: string;
    alleen_vast?: string;
  }>;
}) {
  const params = await searchParams;
  const jaar = Number(params.jaar) || new Date().getFullYear();
  const maand = params.maand ? Number(params.maand) : undefined;
  const rekening = params.rekening;
  const naamFilter = (params.naam || "").toLowerCase();
  const categorieFilter = params.categorie || "Alle";
  const ongecategoriseerd = params.ongecategoriseerd === "1";
  const alleenVast = params.alleen_vast === "1";

  const [transactions, debts, accounts] = await Promise.all([
    api.private.transactions(jaar, { maand, rekening }),
    api.private.debts.list(true),
    api.accounts.list(),
  ]);
  const priveRekeningen = accounts.filter((a) => a.type === "prive").map((a) => ({ iban: a.iban, naam: a.naam }));

  const uitgaven = transactions.filter((t) => t.bedrag < 0);
  const inkomsten = transactions.filter((t) => t.bedrag > 0);

  const totaalUitgaven = uitgaven.reduce((sum, t) => sum + Math.abs(t.bedrag), 0);
  const totaalInkomsten = inkomsten.reduce((sum, t) => sum + t.bedrag, 0);
  const netto = totaalInkomsten - totaalUitgaven;

  // Vaste lasten = recurring bank transactions (is_recurring flag), same as legacy dashboard.
  const recurring = uitgaven.filter((t) => t.is_recurring);
  const recurringTotaal = recurring.reduce((sum, t) => sum + Math.abs(t.bedrag), 0);
  const maandenMetData = new Set(
    transactions.map((t) => (t.datum ? new Date(t.datum).getMonth() + 1 : null)).filter((m): m is number => m !== null)
  ).size;
  const gemVasteLastenPm = maandenMetData > 0 ? recurringTotaal / maandenMetData : 0;

  const leningenTotaal = recurring
    .filter((t) => LENING_CATEGORIES.has((t.prive_categorie || "").toLowerCase()))
    .reduce((sum, t) => sum + Math.abs(t.bedrag), 0);
  const overigVasteLastenTotaal = Math.max(0, recurringTotaal - leningenTotaal);

  const totaalSchuldRestant = debts.reduce((sum, d) => sum + d.huidig_restant, 0);
  const schuldTermijnenPm = debts.reduce((sum, d) => sum + d.termijn_bedrag, 0);

  const byCategorie = new Map<string, number>();
  for (const t of uitgaven) {
    const cat = t.prive_categorie || "";
    if (LENING_CATEGORIES.has(cat.toLowerCase())) continue;
    if (!cat) continue;
    byCategorie.set(cat, (byCategorie.get(cat) ?? 0) + Math.abs(t.bedrag));
  }
  const categorieRows: { label: string; totaal: number; color: string }[] = [
    ...[...byCategorie.entries()].map(([label, totaal]) => ({ label, totaal, color: "bg-muted-foreground/40" })),
    { label: "Vaste lasten", totaal: recurringTotaal, color: "bg-blue-600" },
    { label: "Leningen", totaal: leningenTotaal, color: "bg-red-600" },
    { label: "Overig vaste lasten", totaal: overigVasteLastenTotaal, color: "bg-teal-600" },
  ]
    .filter((r) => r.totaal > 0)
    .sort((a, b) => b.totaal - a.totaal);
  const maxTotaal = Math.max(1, ...categorieRows.map((r) => r.totaal));

  // Filters below only affect the displayed uitgaven list, not the KPIs above (matches legacy).
  let viewUitgaven = uitgaven;
  if (naamFilter) viewUitgaven = viewUitgaven.filter((t) => t.naam.toLowerCase().includes(naamFilter));
  if (categorieFilter !== "Alle") viewUitgaven = viewUitgaven.filter((t) => t.prive_categorie === categorieFilter);
  if (ongecategoriseerd) viewUitgaven = viewUitgaven.filter((t) => !t.prive_categorie);
  if (alleenVast) viewUitgaven = viewUitgaven.filter((t) => t.is_recurring);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">🏠 Privé Dashboard</h1>
          <p className="text-sm text-muted-foreground">{transactions.length} transacties</p>
        </div>
        <YearSwitcher jaar={jaar} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="💰 Inkomsten" value={formatCurrency(totaalInkomsten)} />
        <KpiCard label="💸 Uitgaven" value={formatCurrency(totaalUitgaven)} />
        <KpiCard label="📊 Netto" value={formatCurrency(netto)} tone={netto >= 0 ? "positive" : "negative"} />
        <KpiCard label="🔄 Vaste lasten" value={formatCurrency(recurringTotaal)} />
        <KpiCard label="📆 Gem. vaste lasten p/m" value={formatCurrency(gemVasteLastenPm)} />
        <KpiCard label="🏦 Schuld restant" value={formatCurrency(totaalSchuldRestant)} />
        <KpiCard label="📅 Schuld termijnen p/m" value={formatCurrency(schuldTermijnenPm)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Werkelijke uitgaven per categorie</CardTitle>
        </CardHeader>
        <CardContent>
          {categorieRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">Geen uitgaven gevonden.</p>
          ) : (
            <div className="flex flex-col gap-2.5">
              {categorieRows.map((row) => (
                <div key={row.label} className="flex items-center gap-3 text-sm">
                  <span className="w-40 shrink-0 truncate">{row.label}</span>
                  <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full ${row.color}`}
                      style={{ width: `${(row.totaal / maxTotaal) * 100}%` }}
                    />
                  </div>
                  <span className="w-24 shrink-0 text-right font-medium">{formatCurrency(row.totaal)}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <PriveFilters
        maand={maand}
        rekening={rekening}
        rekeningen={priveRekeningen}
        naam={params.naam || ""}
        categorie={categorieFilter}
        ongecategoriseerd={ongecategoriseerd}
        alleenVast={alleenVast}
      />

      <Card>
        <CardHeader>
          <CardTitle>💸 Uitgaven ({viewUitgaven.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Datum</TableHead>
                <TableHead>Naam</TableHead>
                <TableHead className="text-right">Bedrag</TableHead>
                <TableHead>Categorie / Vast</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {viewUitgaven.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    Geen uitgaven gevonden.
                  </TableCell>
                </TableRow>
              )}
              {viewUitgaven.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{formatDate(t.datum)}</TableCell>
                  <TableCell className="font-medium">{t.naam}</TableCell>
                  <TableCell className="text-right text-red-600">{formatCurrency(t.bedrag)}</TableCell>
                  <TableCell>
                    <PriveTransactionEditor txId={t.id} categorie={t.prive_categorie} isRecurring={t.is_recurring} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>💰 Inkomsten ({inkomsten.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Datum</TableHead>
                <TableHead>Naam</TableHead>
                <TableHead>Omschrijving</TableHead>
                <TableHead className="text-right">Bedrag</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inkomsten.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    Geen inkomsten gevonden.
                  </TableCell>
                </TableRow>
              )}
              {inkomsten.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>{formatDate(t.datum)}</TableCell>
                  <TableCell className="font-medium">
                    {t.naam}
                    {t.is_recurring && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        Vast
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">{t.referentie}</TableCell>
                  <TableCell className="text-right text-emerald-600">{formatCurrency(t.bedrag)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
