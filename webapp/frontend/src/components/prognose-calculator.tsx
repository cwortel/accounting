"use client";

import { useMemo, useState } from "react";
import { format } from "date-fns";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { setSettingAction } from "@/app/actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/kpi-card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { MonthlyCashflow, Schuld } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { calculatePrognose } from "@/lib/prognose";

const MAANDEN = ["", "Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec"];

export function PrognoseCalculator({
  currentSaldo,
  cashflow,
  debts,
  btwPaidByYear,
  initialBeginsaldo,
}: {
  currentSaldo: number;
  cashflow: MonthlyCashflow[];
  debts: Schuld[];
  btwPaidByYear: Record<number, Set<number>>;
  initialBeginsaldo: number;
}) {
  const thisYear = new Date().getFullYear();
  const [bufferMin, setBufferMin] = useState(55000);
  const [bufferMax, setBufferMax] = useState(70000);
  const [targetYear, setTargetYear] = useState(thisYear + 1);
  const [targetMonth, setTargetMonth] = useState(6);
  const [beginsaldo, setBeginsaldo] = useState(initialBeginsaldo);
  const [runrateMonths, setRunrateMonths] = useState(3);
  const [omzetAdj, setOmzetAdj] = useState(0);
  const [priveMonthly, setPriveMonthly] = useState(8000);
  const [btwPerQ, setBtwPerQ] = useState(11000);
  const [ibPerJaar, setIbPerJaar] = useState(65000);

  const result = useMemo(
    () =>
      calculatePrognose({
        currentSaldo,
        cashflow,
        debts,
        btwPaidByYear,
        bufferMin,
        targetYear,
        targetMonth,
        beginsaldo,
        runrateMonths,
        omzetAdjPct: omzetAdj,
        priveMonthly,
        btwPerQuarter: btwPerQ,
        ibPerJaar,
      }),
    [currentSaldo, cashflow, debts, btwPaidByYear, bufferMin, targetYear, targetMonth, beginsaldo, runrateMonths, omzetAdj, priveMonthly, btwPerQ, ibPerJaar]
  );

  function persistBeginsaldo(value: number) {
    setBeginsaldo(value);
    setSettingAction("prognose_beginsaldo", String(Math.round(value))).catch(() => {});
  }

  const chartData = useMemo(() => {
    const map = new Map<string, { maand: string; actueel?: number; prognose?: number }>();
    for (const p of result.actuals) {
      const key = format(p.maand, "yyyy-MM");
      map.set(key, { ...map.get(key), maand: key, actueel: Math.round(p.saldo) });
    }
    for (const p of result.projection) {
      const key = format(p.maand, "yyyy-MM");
      map.set(key, { ...map.get(key), maand: key, prognose: Math.round(p.saldo) });
    }
    return [...map.values()].sort((a, b) => a.maand.localeCompare(b.maand));
  }, [result]);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>🎯 Doelstelling &amp; aannames</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="grid gap-1.5">
            <Label>Buffer min (€)</Label>
            <Input type="number" step="1000" value={bufferMin} onChange={(e) => setBufferMin(Number(e.target.value))} />
          </div>
          <div className="grid gap-1.5">
            <Label>Buffer max (€)</Label>
            <Input type="number" step="1000" value={bufferMax} onChange={(e) => setBufferMax(Number(e.target.value))} />
          </div>
          <div className="grid gap-1.5">
            <Label>Doeljaar</Label>
            <Select value={String(targetYear)} onValueChange={(v) => v && setTargetYear(Number(v))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[thisYear, thisYear + 1, thisYear + 2].map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Doelmaand</Label>
            <Select value={String(targetMonth)} onValueChange={(v) => v && setTargetMonth(Number(v))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <SelectItem key={m} value={String(m)}>
                    {MAANDEN[m]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Beginsaldo 1 jan (€)</Label>
            <Input
              type="number"
              step="1000"
              value={beginsaldo}
              onChange={(e) => persistBeginsaldo(Number(e.target.value))}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>Run-rate venster</Label>
            <Select value={String(runrateMonths)} onValueChange={(v) => v && setRunrateMonths(Number(v))}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3 maanden</SelectItem>
                <SelectItem value="6">6 maanden</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Omzet bijstelling (%)</Label>
            <Input type="number" value={omzetAdj} onChange={(e) => setOmzetAdj(Number(e.target.value))} />
          </div>
          <div className="grid gap-1.5">
            <Label>Privé onttrekking p/m (€)</Label>
            <Input type="number" step="500" value={priveMonthly} onChange={(e) => setPriveMonthly(Number(e.target.value))} />
          </div>
          <div className="grid gap-1.5">
            <Label>BTW per kwartaal (€)</Label>
            <Input type="number" step="500" value={btwPerQ} onChange={(e) => setBtwPerQ(Number(e.target.value))} />
          </div>
          <div className="grid gap-1.5">
            <Label>Inkomstenbelasting p/j (€)</Label>
            <Input type="number" step="1000" value={ibPerJaar} onChange={(e) => setIbPerJaar(Number(e.target.value))} />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Totaal zakelijk saldo" value={formatCurrency(currentSaldo)} />
        <KpiCard
          label={`Prognose ${MAANDEN[targetMonth]} ${targetYear}`}
          value={formatCurrency(result.projectedEnd)}
          hint={`${result.gap >= 0 ? "+" : ""}${formatCurrency(result.gap)} t.o.v. buffer min`}
          tone={result.gap >= 0 ? "positive" : "negative"}
        />
        <KpiCard label="Run-rate netto p/m" value={formatCurrency(result.monthlyNet)} />
        <KpiCard label="Gem. totaal privé p/m" value={formatCurrency(result.avgSpending)} />
        <KpiCard label="Gem. vaste lasten p/m" value={formatCurrency(result.avgRecurring)} />
        <KpiCard
          label="Runway"
          value={Number.isFinite(result.runway) ? `${result.runway.toFixed(1)} mnd` : "∞"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Saldo prognose</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
              <XAxis dataKey="maand" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis fontSize={12} tickLine={false} axisLine={false} width={64} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <Tooltip formatter={(value) => formatCurrency(Number(value ?? 0))} />
              <ReferenceLine y={bufferMin} stroke="#f59e0b" strokeDasharray="4 4" />
              <ReferenceLine y={bufferMax} stroke="#f59e0b" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="actueel" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} connectNulls />
              <Line type="monotone" dataKey="prognose" stroke="#2563eb" strokeDasharray="6 3" strokeWidth={2.5} dot={{ r: 3 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-xs text-muted-foreground mt-2">
            — Actueel · ╌ Prognose · 🟡 Buffer zone ({formatCurrency(bufferMin)}–{formatCurrency(bufferMax)})
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>📋 Geplande verplichtingen</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Omschrijving</TableHead>
                <TableHead>Vervaldatum</TableHead>
                <TableHead className="text-right">Bedrag</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {result.obligations.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                    Geen verplichtingen gevonden.
                  </TableCell>
                </TableRow>
              )}
              {result.obligations.map((o, i) => (
                <TableRow key={i}>
                  <TableCell>{o.type}</TableCell>
                  <TableCell>{o.omschrijving}</TableCell>
                  <TableCell>{o.vervaldatum ? formatDate(o.vervaldatum.toISOString()) : "—"}</TableCell>
                  <TableCell className="text-right text-red-600">{formatCurrency(o.bedrag)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="text-xs text-muted-foreground mt-2">
            ℹ️ Leningen zijn ter informatie — betaald via privérekening, impliciet in privé onttrekking p/m.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>📊 Run-rate aannames</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <KpiCard label="Gem. omzet p/m" value={formatCurrency(result.avgOmzet)} />
          <KpiCard label={`Na bijstelling (${omzetAdj >= 0 ? "+" : ""}${omzetAdj}%)`} value={formatCurrency(result.adjOmzet)} />
          <KpiCard label="Gem. kosten p/m" value={formatCurrency(result.avgKosten)} />
          <KpiCard label="Privé onttrekking p/m" value={formatCurrency(priveMonthly)} />
          <KpiCard label="IB reservering p/m" value={formatCurrency(result.ibMonthly)} />
        </CardContent>
      </Card>
    </div>
  );
}
