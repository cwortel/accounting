"use client";

import { useEffect, useState, useTransition } from "react";
import { toast } from "sonner";

import { getAllReceiptsAction, reprocessReceiptAction } from "@/app/actions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Receipt } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const STATUS_OPTIONS = [
  { value: "alle", label: "Alle" },
  { value: "pending", label: "Te controleren" },
  { value: "approved", label: "Goedgekeurd" },
  { value: "rejected", label: "Afgewezen" },
];

function StatusBadge({ status }: { status: string }) {
  if (status === "approved") {
    return <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Goedgekeurd</Badge>;
  }
  if (status === "rejected") return <Badge variant="destructive">Afgewezen</Badge>;
  return <Badge variant="outline">Te controleren</Badge>;
}

export function ReceiptsOverviewPanel() {
  const [status, setStatus] = useState("alle");
  const [query, setQuery] = useState("");
  const [receipts, setReceipts] = useState<Receipt[] | null>(null);
  const [isPending, startTransition] = useTransition();

  function load(nextStatus: string) {
    getAllReceiptsAction(nextStatus)
      .then(setReceipts)
      .catch(() => setReceipts([]));
  }

  useEffect(() => {
    load(status);
    // Keyed on status only — load() itself is stable enough for this fetch-on-change effect.
  }, [status]);

  function reprocess(id: number) {
    startTransition(async () => {
      try {
        await reprocessReceiptAction(id);
        toast.success("Opnieuw klaargezet voor controle");
        load(status);
      } catch {
        toast.error("Opnieuw verwerken mislukt");
      }
    });
  }

  const filtered =
    receipts === null
      ? null
      : receipts.filter(
          (r) =>
            !query ||
            r.original_filename.toLowerCase().includes(query.toLowerCase()) ||
            r.extracted_naam.toLowerCase().includes(query.toLowerCase())
        );

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Alle bonnetjes</CardTitle>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Zoek op bestand of naam…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-56"
          />
          <Select value={status} onValueChange={(v) => v && setStatus(v)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Bestand</TableHead>
              <TableHead>Naam</TableHead>
              <TableHead>Datum</TableHead>
              <TableHead className="text-right">Totaal</TableHead>
              <TableHead>Status</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered === null && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  Laden…
                </TableCell>
              </TableRow>
            )}
            {filtered?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  Geen bonnetjes gevonden.
                </TableCell>
              </TableRow>
            )}
            {filtered?.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.original_filename}</TableCell>
                <TableCell>{r.extracted_naam || "—"}</TableCell>
                <TableCell>{r.extracted_datum ? formatDate(r.extracted_datum) : "—"}</TableCell>
                <TableCell className="text-right">
                  {r.extracted_total !== null ? formatCurrency(r.extracted_total) : "—"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={r.status} />
                  {r.status === "approved" && r.expense_id && (
                    <span className="ml-2 text-xs text-muted-foreground">uitgave #{r.expense_id}</span>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {r.status === "rejected" && (
                    <Button variant="ghost" size="sm" onClick={() => reprocess(r.id)} disabled={isPending}>
                      Opnieuw verwerken
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
