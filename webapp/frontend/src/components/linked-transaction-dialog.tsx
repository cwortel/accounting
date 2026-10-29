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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import type { BankTxMatchCandidate, BankTxSummary } from "@/lib/api";
import { formatCurrency, netLinkedAmount } from "@/lib/format";

export function LinkedTransactionDialog({
  kind,
  id,
  jaar,
  total,
  linked,
  badge,
  label,
}: {
  kind: "expense" | "income";
  id: number;
  jaar: number;
  total: number;
  linked: BankTxSummary[];
  badge: React.ReactElement;
  label: string;
}) {
  const [open, setOpen] = useState(false);
  const [candidates, setCandidates] = useState<BankTxMatchCandidate[] | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (next && candidates === null) {
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger nativeButton={false} render={badge}>
        {label}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Gekoppelde banktransactie{linked.length === 1 ? "" : "s"}</DialogTitle>
        </DialogHeader>
        {linked.length > 0 && (
          <div className="flex flex-col gap-2">
            {linked.map((tx) => (
              <div key={tx.id} className="flex items-center gap-2">
                <div className="flex-1">
                  <LinkedSummaryCard naam={tx.naam} datum={tx.datum} amount={tx.bedrag} extra={tx.referentie || undefined} />
                </div>
                <Button variant="ghost" size="icon-sm" onClick={() => unlink(tx.id)} disabled={isPending}>
                  <XIcon />
                </Button>
              </div>
            ))}
            {linked.length > 1 && (
              <p className="text-right text-xs text-muted-foreground">
                Gekoppeld: {formatCurrency(gekoppeld)} van {formatCurrency(total)}
              </p>
            )}
          </div>
        )}
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            {linked.length === 0 ? "Nog geen banktransactie gekoppeld." : "Nog een transactie koppelen:"}
          </p>
          <BankMatchCandidateList candidates={candidates} onLink={linkTx} isPending={isPending} jaar={jaar} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
