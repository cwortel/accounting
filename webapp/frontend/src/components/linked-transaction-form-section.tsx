"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

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

export function LinkedTransactionFormSection({
  kind,
  id,
  linked,
}: {
  kind: "expense" | "income";
  id: number;
  linked: BankTxSummary | null;
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

  function unlink() {
    if (!linked) return;
    startTransition(async () => {
      try {
        await unlinkTransactionAction(linked.id);
        toast.success("Ontkoppeld");
        router.refresh();
      } catch {
        toast.error("Ontkoppelen mislukt");
      }
    });
  }

  return (
    <div className="grid gap-2 rounded-md border p-3">
      <Label>Gekoppelde banktransactie</Label>
      {linked ? (
        <>
          <LinkedSummaryCard naam={linked.naam} datum={linked.datum} amount={linked.bedrag} extra={linked.referentie || undefined} />
          <Button type="button" variant="ghost" size="sm" className="self-start" onClick={unlink} disabled={isPending}>
            Ontkoppelen
          </Button>
        </>
      ) : showCandidates ? (
        <BankMatchCandidateList candidates={candidates} onLink={linkTx} isPending={isPending} />
      ) : (
        <Button type="button" variant="link" size="sm" className="self-start px-0" onClick={loadCandidates}>
          Banktransactie koppelen
        </Button>
      )}
    </div>
  );
}
