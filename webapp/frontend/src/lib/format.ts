export function formatCurrency(value: number): string {
  return `€\u00A0${value.toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("nl-NL", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// Bank transaction amounts are stored negative for debits (expenses) and positive
// for credits (income). Summing with Math.abs() would be wrong once a correction/
// refund is linked too (opposite sign) — e.g. a €100 charge + a €12 refund nets to
// €88, not €112. Negate for expenses so a plain charge reads as a positive amount paid.
export function netLinkedAmount(kind: "expense" | "income", linked: { bedrag: number }[]): number {
  const sign = kind === "expense" ? -1 : 1;
  return linked.reduce((sum, tx) => sum + sign * tx.bedrag, 0);
}
