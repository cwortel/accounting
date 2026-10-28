"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  approveReceiptAction,
  getNextFactuurnummerAction,
  getReceiptBankMatchCandidatesAction,
  linkTransactionAction,
  rejectReceiptAction,
  scanReceiptsAction,
} from "@/app/actions";
import { BankMatchCandidateList } from "@/components/bank-match-candidate-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { BankTxMatchCandidate, Receipt } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

const PAYMENT_SOURCES = ["Onbekend", "Privé rekening", "Privé creditcard", "Contant", "Bank zakelijk"];

export function ReceiptReviewPanel({ receipts, categories }: { receipts: Receipt[]; categories: string[] }) {
  const [index, setIndex] = useState(0);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const naamRef = useRef<HTMLInputElement>(null);
  const totalRef = useRef<HTMLInputElement>(null);
  const datumRef = useRef<HTMLInputElement>(null);
  const [matchState, setMatchState] = useState<{
    receiptId: number;
    candidates: BankTxMatchCandidate[] | null;
    chosenTx: BankTxMatchCandidate | null;
  } | null>(null);

  // Clamp instead of storing out-of-range state as the queue shrinks after an approve/reject.
  const safeIndex = Math.min(index, Math.max(receipts.length - 1, 0));

  function scan() {
    startTransition(async () => {
      try {
        const result = await scanReceiptsAction();
        toast.success(`${result.gevonden} bestand(en) gevonden, ${result.nieuw} nieuw`);
        router.refresh();
      } catch {
        toast.error("Scannen mislukt");
      }
    });
  }

  const receipt = receipts[safeIndex];
  const [factuurValue, setFactuurValue] = useState("");
  // Stale once the displayed receipt changes, so no reset-on-id-change effect is needed.
  const candidates = matchState && matchState.receiptId === receipt?.id ? matchState.candidates : null;
  const chosenTx = matchState && matchState.receiptId === receipt?.id ? matchState.chosenTx : null;

  useEffect(() => {
    if (!receipt) return;
    getNextFactuurnummerAction(receipt.jaar, receipt.kwartaal)
      .then(setFactuurValue)
      .catch(() => setFactuurValue(""));
    // Keyed on the receipt id (not the whole object) so this only refetches when
    // the displayed receipt actually changes, not on every parent re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [receipt?.id]);

  function onBetaalBronChange(value: string | null) {
    if (!receipt) return;
    if (value !== "Bank zakelijk") {
      setMatchState({ receiptId: receipt.id, candidates: null, chosenTx: null });
      return;
    }
    setMatchState({ receiptId: receipt.id, candidates: null, chosenTx: null });
    getReceiptBankMatchCandidatesAction(receipt.id, {
      naam: naamRef.current?.value || receipt.extracted_naam,
      total: Number(totalRef.current?.value || receipt.extracted_total || 0),
      datum: datumRef.current?.value || receipt.extracted_datum || undefined,
    })
      .then((found) => setMatchState({ receiptId: receipt.id, candidates: found, chosenTx: null }))
      .catch(() => setMatchState({ receiptId: receipt.id, candidates: [], chosenTx: null }));
  }

  function onApprove(formData: FormData) {
    if (!receipt) return;
    const datum = String(formData.get("datum") || "");
    const total = Number(formData.get("total") || 0);
    const naam = String(formData.get("naam") || "").trim();
    if (!naam || !datum || total <= 0) {
      toast.error("Vul naam, datum en een bedrag groter dan 0 in.");
      return;
    }
    startTransition(async () => {
      try {
        const saved = await approveReceiptAction(receipt.id, {
          naam,
          datum,
          categorie: String(formData.get("categorie") || ""),
          btw_pct: Number(formData.get("btw_pct") || 0),
          total,
          factuur: String(formData.get("factuur") || ""),
          betaal_bron: String(formData.get("betaal_bron") || ""),
        });
        if (chosenTx) {
          try {
            await linkTransactionAction(chosenTx.tx_id, saved.id, 0);
          } catch {
            toast.error("Uitgave aangemaakt, maar koppelen van de transactie is mislukt");
            router.refresh();
            return;
          }
        }
        toast.success("Uitgave aangemaakt");
        router.refresh();
      } catch {
        toast.error("Opslaan mislukt");
      }
    });
  }

  function onReject() {
    if (!receipt) return;
    startTransition(async () => {
      try {
        await rejectReceiptAction(receipt.id);
        toast.success("Afgewezen");
        router.refresh();
      } catch {
        toast.error("Afwijzen mislukt");
      }
    });
  }

  if (!receipt) {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Bonnetjes controleren</CardTitle>
          <Button onClick={scan} disabled={isPending} variant="outline" size="sm">
            {isPending ? "Scannen…" : "Scan map"}
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Alles verwerkt. Zet nieuwe bonnetjes in data/Receipts/&lt;jaar&gt;-Q&lt;kwartaal&gt;/ en klik op
            &ldquo;Scan map&rdquo;.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Bonnetjes controleren</CardTitle>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {safeIndex + 1} / {receipts.length}
          </span>
          <Button onClick={scan} disabled={isPending} variant="outline" size="sm">
            {isPending ? "Scannen…" : "Scan map"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 md:grid-cols-2">
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">{receipt.original_filename}</p>
          {receipt.mime_type === "application/pdf" ? (
            <embed
              src={`/api/receipts/${receipt.id}/file`}
              type="application/pdf"
              className="h-[500px] w-full rounded border"
            />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={`/api/receipts/${receipt.id}/file`}
              alt={receipt.original_filename}
              className="max-h-[500px] w-full rounded border object-contain"
            />
          )}
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Ruwe OCR-tekst</summary>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap">{receipt.ocr_text}</pre>
          </details>
        </div>
        <form key={receipt.id} action={onApprove} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="naam">Naam</Label>
            <Input id="naam" name="naam" ref={naamRef} defaultValue={receipt.extracted_naam} autoFocus required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="total">Totaal (incl. BTW)</Label>
              <Input
                id="total"
                name="total"
                ref={totalRef}
                type="number"
                step="0.01"
                min="0"
                defaultValue={receipt.extracted_total ?? ""}
                required
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="btw_pct">BTW %</Label>
              <Select name="btw_pct" defaultValue={String(receipt.extracted_btw_pct ?? 21)}>
                <SelectTrigger id="btw_pct" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">0%</SelectItem>
                  <SelectItem value="9">9%</SelectItem>
                  <SelectItem value="21">21%</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="datum">Datum</Label>
              <Input id="datum" name="datum" ref={datumRef} type="date" defaultValue={receipt.extracted_datum ?? ""} required />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="categorie">Categorie</Label>
              <Select name="categorie" defaultValue={categories[0] ?? ""}>
                <SelectTrigger id="categorie" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="factuur">Factuurnummer</Label>
              <Input
                id="factuur"
                name="factuur"
                placeholder="optioneel"
                value={factuurValue}
                onChange={(e) => setFactuurValue(e.target.value)}
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="betaal_bron">Betaald via</Label>
              <Select name="betaal_bron" defaultValue="Onbekend" onValueChange={onBetaalBronChange}>
                <SelectTrigger id="betaal_bron" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAYMENT_SOURCES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {chosenTx ? (
            <div className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
              <span>
                Gekoppeld: <span className="font-medium">{chosenTx.naam}</span> ·{" "}
                {formatDate(chosenTx.datum)} · {formatCurrency(chosenTx.bedrag)}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => receipt && setMatchState({ receiptId: receipt.id, candidates, chosenTx: null })}
              >
                Wijzigen
              </Button>
            </div>
          ) : (
            candidates !== null && (
              <div className="grid gap-1.5">
                <Label>Banktransactie koppelen</Label>
                <BankMatchCandidateList
                  candidates={candidates}
                  jaar={receipt?.jaar}
                  onLink={(txId) =>
                    receipt &&
                    setMatchState({
                      receiptId: receipt.id,
                      candidates,
                      chosenTx: candidates.find((c) => c.tx_id === txId) ?? null,
                    })
                  }
                  isPending={false}
                />
              </div>
            )
          )}
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                disabled={safeIndex === 0}
                onClick={() => setIndex((i) => Math.max(i - 1, 0))}
              >
                Vorige
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={safeIndex >= receipts.length - 1}
                onClick={() => setIndex((i) => Math.min(i + 1, receipts.length - 1))}
              >
                Volgende
              </Button>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="destructive" onClick={onReject} disabled={isPending}>
                Afwijzen
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? "Opslaan…" : "Opslaan & volgende"}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
