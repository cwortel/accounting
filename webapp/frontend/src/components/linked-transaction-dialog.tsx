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
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import type { BankTxMatchCandidate, BankTxSummary } from "@/lib/api";

export function LinkedTransactionDialog({
  kind,
  id,
  linked,
  badge,
  label,
}: {
  kind: "expense" | "income";
  id: number;
  linked: BankTxSummary | null;
  badge: React.ReactElement;
  label: string;
}) {
  const [open, setOpen] = useState(false);
  const [candidates, setCandidates] = useState<BankTxMatchCandidate[] | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (next && !linked && candidates === null) {
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
        setOpen(false);
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
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Ontkoppelen mislukt");
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={badge}>{label}</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Gekoppelde banktransactie</DialogTitle>
        </DialogHeader>
        {linked ? (
          <>
            <LinkedSummaryCard naam={linked.naam} datum={linked.datum} amount={linked.bedrag} extra={linked.referentie || undefined} />
            <DialogFooter>
              <Button variant="destructive" size="sm" onClick={unlink} disabled={isPending}>
                Ontkoppelen
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">Nog geen banktransactie gekoppeld.</p>
            <BankMatchCandidateList candidates={candidates} onLink={linkTx} isPending={isPending} />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
