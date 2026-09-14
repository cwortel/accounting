"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { CategoryQuarterBreakdown } from "@/lib/api";

const currency = (v: number) => `€ ${v.toLocaleString("nl-NL", { minimumFractionDigits: 0 })}`;

export function CategoryChart({ data }: { data: CategoryQuarterBreakdown[] }) {
  const chartData = data
    .filter((d) => d.totaal > 0)
    .sort((a, b) => b.totaal - a.totaal)
    .map((d) => ({ categorie: d.categorie, Totaal: Math.round(d.totaal) }));

  if (chartData.length === 0) {
    return <p className="text-sm text-muted-foreground">Geen kosten dit jaar.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, chartData.length * 44)}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 24, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} className="stroke-muted" />
        <XAxis type="number" tickLine={false} axisLine={false} fontSize={12} />
        <YAxis type="category" dataKey="categorie" tickLine={false} axisLine={false} fontSize={12} width={140} />
        <Tooltip formatter={(value) => currency(Number(value ?? 0))} cursor={{ fill: "var(--muted)" }} />
        <Bar dataKey="Totaal" fill="#2563eb" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
