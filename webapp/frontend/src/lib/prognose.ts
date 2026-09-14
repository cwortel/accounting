import { addMonths, differenceInCalendarDays, endOfMonth, format, isWithinInterval, startOfMonth } from "date-fns";

import type { MonthlyCashflow, Schuld } from "@/lib/api";

export type CashflowPoint = { maand: Date; saldo: number };

export type BtwObligation = { label: string; due: Date; bedrag: number };

export type ObligationRow = { type: string; omschrijving: string; vervaldatum: Date | null; bedrag: number };

export type PrognoseInputs = {
  currentSaldo: number;
  cashflow: MonthlyCashflow[];
  debts: Schuld[];
  btwPaidByYear: Record<number, Set<number>>; // year -> set of quarters already paid
  bufferMin: number;
  targetYear: number;
  targetMonth: number; // 1-12
  beginsaldo: number;
  runrateMonths: number;
  omzetAdjPct: number;
  priveMonthly: number;
  btwPerQuarter: number;
  ibPerJaar: number;
  today?: Date;
};

export type PrognoseResult = {
  actuals: CashflowPoint[];
  projection: CashflowPoint[];
  avgOmzet: number;
  adjOmzet: number;
  avgKosten: number;
  avgPriveHist: number;
  avgRecurring: number;
  avgSpending: number;
  monthlyNet: number;
  ibMonthly: number;
  projectedEnd: number;
  gap: number;
  runway: number;
  obligations: ObligationRow[];
};

function btwDueDate(year: number, quarter: number): Date {
  let month = quarter * 3 + 1;
  let dueYear = year;
  if (month > 12) {
    month -= 12;
    dueYear += 1;
  }
  return endOfMonth(new Date(dueYear, month - 1, 1));
}

export function calculatePrognose(inputs: PrognoseInputs): PrognoseResult {
  const today = inputs.today ?? new Date();
  const todayMonth = startOfMonth(today);
  const targetDate = endOfMonth(new Date(inputs.targetYear, inputs.targetMonth - 1, 1));
  const baseYear = today.getFullYear();
  const baseStart = new Date(baseYear, 0, 1);

  const cfByMonth = new Map(inputs.cashflow.map((c) => [c.maand, c]));
  const histMonths = [...cfByMonth.keys()]
    .map((m) => new Date(`${m}-01`))
    .filter((d) => d >= baseStart && d < todayMonth)
    .filter((d) => {
      const c = cfByMonth.get(format(d, "yyyy-MM"))!;
      return c.omzet + c.kosten > 0;
    })
    .sort((a, b) => a.getTime() - b.getTime());

  const cfRows = histMonths.map((d) => {
    const c = cfByMonth.get(format(d, "yyyy-MM"))!;
    return {
      maand: d,
      omzet: c.omzet,
      kosten: c.kosten,
      prive: c.prive_out,
      btw: c.btw_paid,
      net: c.omzet - c.kosten - c.prive_out - c.btw_paid,
    };
  });

  // Actuals line: cumulative net from beginsaldo, ending at today's known saldo.
  const actuals: CashflowPoint[] = [];
  if (inputs.beginsaldo > 0 && cfRows.length > 0) {
    let cumulative = inputs.beginsaldo;
    for (const row of cfRows) {
      cumulative += row.net;
      actuals.push({ maand: row.maand, saldo: cumulative });
    }
    actuals.push({ maand: todayMonth, saldo: inputs.currentSaldo });
  } else if (cfRows.length > 0) {
    actuals.push({ maand: todayMonth, saldo: inputs.currentSaldo });
  }

  const cutoff = addMonths(todayMonth, -inputs.runrateMonths);
  const recent = cfRows.filter((r) => r.maand >= cutoff);
  const avgOmzet = recent.length ? recent.reduce((s, r) => s + r.omzet, 0) / recent.length : 0;
  const avgKosten = recent.length ? recent.reduce((s, r) => s + r.kosten, 0) / recent.length : 0;
  const avgPriveHist = recent.length ? recent.reduce((s, r) => s + r.prive, 0) / recent.length : 0;

  const adjOmzet = avgOmzet * (1 + inputs.omzetAdjPct / 100);
  const monthlyNet = adjOmzet - avgKosten - inputs.priveMonthly;
  const ibMonthly = inputs.ibPerJaar / 12;

  const recurringInWindow = inputs.cashflow.filter((c) => {
    const d = new Date(`${c.maand}-01`);
    return d >= cutoff && d < todayMonth;
  });
  const avgRecurring = recurringInWindow.length
    ? recurringInWindow.reduce((s, c) => s + c.recurring_prive, 0) / recurringInWindow.length
    : 0;
  const avgSpending = recurringInWindow.length
    ? recurringInWindow.reduce((s, c) => s + c.totaal_prive_uitgaven, 0) / recurringInWindow.length
    : 0;

  // BTW schedule: upcoming unpaid quarterly obligations between today and target date.
  const btwSchedule: BtwObligation[] = [];
  for (const yr of [today.getFullYear(), today.getFullYear() + 1]) {
    const paid = inputs.btwPaidByYear[yr] ?? new Set<number>();
    for (let q = 1; q <= 4; q++) {
      const due = btwDueDate(yr, q);
      if (due >= today && due <= targetDate && !paid.has(q)) {
        btwSchedule.push({ label: `BTW Q${q} ${yr}`, due, bedrag: inputs.btwPerQuarter });
      }
    }
  }

  // Month-by-month projection starting from today's known saldo.
  const projection: CashflowPoint[] = [{ maand: todayMonth, saldo: inputs.currentSaldo }];
  let projSaldo = inputs.currentSaldo;
  let cursor = startOfMonth(addMonths(todayMonth, 1));
  while (cursor <= targetDate) {
    const monthEnd = endOfMonth(cursor);
    let delta = monthlyNet - ibMonthly;
    for (const btw of btwSchedule) {
      if (isWithinInterval(btw.due, { start: cursor, end: monthEnd })) {
        delta -= btw.bedrag;
      }
    }
    projSaldo += delta;
    projection.push({ maand: cursor, saldo: projSaldo });
    cursor = startOfMonth(addMonths(cursor, 1));
  }

  const projectedEnd = projection.length ? projection[projection.length - 1].saldo : inputs.currentSaldo;
  const gap = projectedEnd - inputs.bufferMin;
  const denom = avgKosten + inputs.priveMonthly;
  const runway = denom > 0 ? inputs.currentSaldo / denom : Infinity;

  const obligations: ObligationRow[] = btwSchedule.map((b) => ({
    type: "BTW aangifte",
    omschrijving: b.label,
    vervaldatum: b.due,
    bedrag: -b.bedrag,
  }));

  const monthsToTarget = Math.max(0, Math.floor(differenceInCalendarDays(targetDate, today) / 30));
  obligations.push({
    type: "IB reservering",
    omschrijving: `Inkomstenbelasting — ${monthsToTarget} mnd × ${ibMonthly.toFixed(0)}`,
    vervaldatum: targetDate,
    bedrag: -(ibMonthly * monthsToTarget),
  });

  for (const s of inputs.debts) {
    if (s.huidig_restant <= 0) continue;
    const remaining = Math.max(0, s.aantal_termijnen - s.betaald_termijnen);
    obligations.push({
      type: "Lening (privé)",
      omschrijving: `${s.naam} — ${remaining}× ${s.frequentie} resterend`,
      vervaldatum: s.betaaldatum ? new Date(s.betaaldatum) : null,
      bedrag: -s.termijn_bedrag,
    });
  }

  return {
    actuals,
    projection,
    avgOmzet,
    adjOmzet,
    avgKosten,
    avgPriveHist,
    avgRecurring,
    avgSpending,
    monthlyNet,
    ibMonthly,
    projectedEnd,
    gap,
    runway,
    obligations,
  };
}
