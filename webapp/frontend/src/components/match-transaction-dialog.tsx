"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  createExpenseFromTxAction,
  getIncomeMatchCandidatesAction,
  getMatchCandidatesAction,
  linkIncomeTransactionAction,
  linkTransactionAction,
  markBtwBetalingAction,
  markInternAction,
  markPriveAction,
} from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { IncomeMatchCandidate, MatchCandidate } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

type MatchType = "Uitgave" | "Inkomst" | "Privé onttrekking" | "Interne overboeking" | "BTW betaling";

export function MatchTransactionDialog({
  txId,
  jaar,
  bedrag,
  categories,
}: {
  txId: number;
  jaar: number;
  bedrag: number;
  categories: string[];
}) {
  const [open, setOpen] = useState(false);
  const [matchType, setMatchType] = useState<MatchType>(bedrag < 0 ? "Uitgave" : "Inkomst");
  const [expCandidates, setExpCandidates] = useState<MatchCandidate[] | null>(null);
  const [incCandidates, setIncCandidates] = useState<IncomeMatchCandidate[] | null>(null);
  const [omschrijving, setOmschrijving] = useState("");
  const [btwKwartaal, setBtwKwartaal] = useState("1");
  const [showCreateExpense, setShowCreateExpense] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (next && matchType === "Uitgave" && expCandidates === null) {
      startTransition(async () => setExpCandidates(await getMatchCandidatesAction(txId).catch(() => [])));
    }
    if (next && matchType === "Inkomst" && incCandidates === null) {
      startTransition(async () => setIncCandidates(await getIncomeMatchCandidatesAction(txId).catch(() => [])));
    }
  }

  function selectType(type: MatchType) {
    setMatchType(type);
    if (type === "Uitgave" && expCandidates === null) {
      startTransition(async () => setExpCandidates(await getMatchCandidatesAction(txId).catch(() => [])));
    }
    if (type === "Inkomst" && incCandidates === null) {
      startTransition(async () => setIncCandidates(await getIncomeMatchCandidatesAction(txId).catch(() => [])));
    }
  }

  function linkExpense(expenseId: number, fooi: number) {
    startTransition(async () => {
      try {
        await linkTransactionAction(txId, expenseId, fooi);
        toast.success("Gekoppeld");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Koppelen mislukt");
      }
    });
  }

  function linkIncome(incomeId: number) {
    startTransition(async () => {
      try {
        await linkIncomeTransactionAction(txId, incomeId);
        toast.success("Gekoppeld");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Koppelen mislukt");
      }
    });
  }

  function markPrive() {
    startTransition(async () => {
      try {
        await markPriveAction(txId, omschrijving);
        toast.success("Gemarkeerd als privé onttrekking");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Mislukt");
      }
    });
  }

  function markIntern() {
    startTransition(async () => {
      try {
        await markInternAction(txId, omschrijving);
        toast.success("Gemarkeerd als interne overboeking");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Mislukt");
      }
    });
  }

  function markBtw() {
    startTransition(async () => {
      try {
        await markBtwBetalingAction(txId, jaar, Number(btwKwartaal));
        toast.success("Gemarkeerd als BTW betaling");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Mislukt");
      }
    });
  }

  function createExpense(formData: FormData) {
    startTransition(async () => {
      try {
        await createExpenseFromTxAction(txId, {
          categorie: String(formData.get("categorie") || ""),
          btw_pct: Number(formData.get("btw_pct") || 0),
          factuur: String(formData.get("factuur") || ""),
          naam: String(formData.get("naam") || ""),
        });
        toast.success("Uitgave aangemaakt en gekoppeld");
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Aanmaken mislukt");
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={<Button size="sm" variant="outline" />}>Koppelen</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Transactie koppelen</DialogTitle>
        </DialogHeader>

        <Tabs value={matchType} onValueChange={(v) => v && selectType(v as MatchType)}>
          <TabsList className="flex-wrap h-auto">
            <TabsTrigger value="Uitgave">Uitgave</TabsTrigger>
            <TabsTrigger value="Inkomst">Inkomst</TabsTrigger>
            <TabsTrigger value="Privé onttrekking">Privé</TabsTrigger>
            <TabsTrigger value="Interne overboeking">Intern</TabsTrigger>
            <TabsTrigger value="BTW betaling">BTW</TabsTrigger>
          </TabsList>
        </Tabs>

        {matchType === "Uitgave" && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1 max-h-56 overflow-y-auto">
              {expCandidates === null && <p className="text-sm text-muted-foreground py-2">Suggesties laden…</p>}
              {expCandidates?.length === 0 && (
                <p className="text-sm text-muted-foreground py-2">Geen passende uitgaven gevonden.</p>
              )}
              {expCandidates?.map((c) => (
                <button
                  key={c.expense_id}
                  onClick={() => linkExpense(c.expense_id, c.fooi)}
                  disabled={isPending}
                  className="flex items-center justify-between rounded-md border px-3 py-2 text-sm text-left hover:bg-muted disabled:opacity-50"
                >
                  <span>
                    <span className="font-medium">{c.naam}</span>{" "}
                    <span className="text-muted-foreground">· {formatDate(c.datum)}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    {c.fooi > 0 && <span className="text-xs text-muted-foreground">+{formatCurrency(c.fooi)} fooi</span>}
                    <span className="font-medium">{formatCurrency(c.total)}</span>
                  </span>
                </button>
              ))}
            </div>
            {!showCreateExpense ? (
              <Button variant="link" size="sm" className="self-start px-0" onClick={() => setShowCreateExpense(true)}>
                Geen bon? Nieuwe uitgave aanmaken vanuit deze transactie
              </Button>
            ) : (
              <form action={createExpense} className="grid gap-3 border-t pt-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="grid gap-1.5">
                    <Label htmlFor="new_naam">Naam</Label>
                    <Input id="new_naam" name="naam" required />
                  </div>
                  <div className="grid gap-1.5">
                    <Label htmlFor="new_factuur">Factuur (optioneel)</Label>
                    <Input id="new_factuur" name="factuur" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="grid gap-1.5">
                    <Label htmlFor="new_categorie">Categorie</Label>
                    <Select name="categorie" defaultValue={categories[0] ?? ""}>
                      <SelectTrigger id="new_categorie" className="w-full">
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
                  <div className="grid gap-1.5">
                    <Label htmlFor="new_btw">BTW %</Label>
                    <Select name="btw_pct" defaultValue="0">
                      <SelectTrigger id="new_btw" className="w-full">
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
                <Button type="submit" size="sm" disabled={isPending}>
                  Aanmaken en koppelen
                </Button>
              </form>
            )}
          </div>
        )}

        {matchType === "Inkomst" && (
          <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
            {incCandidates === null && <p className="text-sm text-muted-foreground py-2">Suggesties laden…</p>}
            {incCandidates?.length === 0 && (
              <p className="text-sm text-muted-foreground py-2">Geen passende inkomsten gevonden.</p>
            )}
            {incCandidates?.map((c) => (
              <button
                key={c.income_id}
                onClick={() => linkIncome(c.income_id)}
                disabled={isPending}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm text-left hover:bg-muted disabled:opacity-50"
              >
                <span>
                  <span className="font-medium">{c.naam}</span>{" "}
                  <span className="text-muted-foreground">· {formatDate(c.datum)}</span>
                </span>
                <span className="font-medium">{formatCurrency(c.total)}</span>
              </button>
            ))}
          </div>
        )}

        {(matchType === "Privé onttrekking" || matchType === "Interne overboeking") && (
          <div className="grid gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="omschrijving">Omschrijving (optioneel)</Label>
              <Input
                id="omschrijving"
                value={omschrijving}
                onChange={(e) => setOmschrijving(e.target.value)}
                placeholder={matchType === "Privé onttrekking" ? "Privé onttrekking" : "Interne overboeking"}
              />
            </div>
            <Button
              size="sm"
              disabled={isPending}
              onClick={matchType === "Privé onttrekking" ? markPrive : markIntern}
            >
              Markeren
            </Button>
          </div>
        )}

        {matchType === "BTW betaling" && (
          <div className="grid gap-3">
            <p className="text-sm text-muted-foreground">
              Markeer deze betaling ({formatCurrency(Math.abs(bedrag))}) als voldoening van de BTW aangifte.
            </p>
            <div className="grid gap-1.5">
              <Label htmlFor="btw_kwartaal">Kwartaal</Label>
              <Select value={btwKwartaal} onValueChange={(v) => v && setBtwKwartaal(v)}>
                <SelectTrigger id="btw_kwartaal" className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Q1</SelectItem>
                  <SelectItem value="2">Q2</SelectItem>
                  <SelectItem value="3">Q3</SelectItem>
                  <SelectItem value="4">Q4</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" disabled={isPending} onClick={markBtw}>
              Markeer als BTW betaling
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
