"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { YearlyQuarterSummary } from "@/lib/api";

const currency = (v: number) => `€ ${v.toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function QuarterlyChart({ data }: { data: YearlyQuarterSummary[] }) {
  const chartData = data.map((d) => ({
    naam: `Q${d.kwartaal}`,
    Omzet: Math.round(d.omzet),
    Kosten: Math.round(d.kosten),
    Winst: Math.round(d.winst),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
        <XAxis dataKey="naam" tickLine={false} axisLine={false} fontSize={12} />
        <YAxis tickLine={false} axisLine={false} fontSize={12} width={48} />
        <Tooltip formatter={(value) => currency(Number(value ?? 0))} cursor={{ fill: "var(--muted)" }} />
        <Legend />
        <Bar dataKey="Omzet" fill="#16a34a" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Kosten" fill="#dc2626" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Winst" fill="#2563eb" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
