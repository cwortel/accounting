"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { XIcon } from "lucide-react";

import {
  getExpenseBankMatchCandidatesAction,
  getIncomeBankMatchCandidatesAction,
  linkIncomeTransactionAction,
  linkTransactionAction,
  unlinkTransactionAction,
} from "@/app/actions";
import { BankMatchCandidateList } from "@/components/bank-match-candidate-list";
import { LinkedSummaryCard } from "@/components/linked-summary-card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { BankTxMatchCandidate, BankTxSummary } from "@/lib/api";
import { formatCurrency, netLinkedAmount } from "@/lib/format";

export function LinkedTransactionFormSection({
  kind,
  id,
  jaar,
  total,
  linked,
}: {
  kind: "expense" | "income";
  id: number;
  jaar: number;
  total: number;
  linked: BankTxSummary[];
}) {
  const [showCandidates, setShowCandidates] = useState(false);
  const [candidates, setCandidates] = useState<BankTxMatchCandidate[] | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function loadCandidates() {
    setShowCandidates(true);
    if (candidates === null) {
      const fetcher = kind === "expense" ? getExpenseBankMatchCandidatesAction : getIncomeBankMatchCandidatesAction;
      startTransition(async () => setCandidates(await fetcher(id).catch(() => [])));
    }
  }

  function linkTx(txId: number) {
    startTransition(async () => {
      try {
        if (kind === "expense") {
          await linkTransactionAction(txId, id, 0);
        } else {
          await linkIncomeTransactionAction(txId, id);
        }
        toast.success("Banktransactie gekoppeld");
        setShowCandidates(false);
        router.refresh();
      } catch {
        toast.error("Koppelen mislukt");
      }
    });
  }

  function unlink(txId: number) {
    startTransition(async () => {
      try {
        await unlinkTransactionAction(txId);
        toast.success("Ontkoppeld");
        router.refresh();
      } catch {
        toast.error("Ontkoppelen mislukt");
      }
    });
  }

  const gekoppeld = netLinkedAmount(kind, linked);

  return (
    <div className="grid gap-2 rounded-md border p-3">
      <Label>Gekoppelde banktransactie{linked.length === 1 ? "" : "s"}</Label>
      {linked.map((tx) => (
        <div key={tx.id} className="flex items-center gap-2">
          <div className="flex-1">
            <LinkedSummaryCard naam={tx.naam} datum={tx.datum} amount={tx.bedrag} extra={tx.referentie || undefined} />
          </div>
          <Button type="button" variant="ghost" size="icon-sm" onClick={() => unlink(tx.id)} disabled={isPending}>
            <XIcon />
          </Button>
        </div>
      ))}
      {linked.length > 1 && (
        <p className="text-right text-xs text-muted-foreground">
          Gekoppeld: {formatCurrency(gekoppeld)} van {formatCurrency(total)}
        </p>
      )}
      {showCandidates ? (
        <BankMatchCandidateList candidates={candidates} onLink={linkTx} isPending={isPending} jaar={jaar} />
      ) : (
        <Button type="button" variant="link" size="sm" className="self-start px-0" onClick={loadCandidates}>
          {linked.length === 0 ? "Banktransactie koppelen" : "Nog een transactie koppelen"}
        </Button>
      )}
    </div>
  );
}
