"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { unlinkTransactionAction } from "@/app/actions";
import { LinkedSummaryCard } from "@/components/linked-summary-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import type { ExpenseSummary, IncomeSummary } from "@/lib/api";

export function LinkedReceiptDialog({
  txId,
  expense,
  income,
}: {
  txId: number;
  expense: ExpenseSummary | null;
  income: IncomeSummary | null;
}) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const receipt = expense ?? income;

  function unlink() {
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

  return (
    <Dialog>
      <DialogTrigger
        render={
          <Badge variant="secondary" className="cursor-pointer bg-emerald-100 text-emerald-700 hover:bg-emerald-100" />
        }
      >
        🟢 Gekoppeld
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{expense ? "Gekoppelde uitgave" : "Gekoppelde inkomst"}</DialogTitle>
        </DialogHeader>
        {receipt && (
          <LinkedSummaryCard naam={receipt.naam} datum={receipt.datum} amount={receipt.total} extra={receipt.factuur || undefined} />
        )}
        <DialogFooter>
          <Button variant="destructive" size="sm" onClick={unlink} disabled={isPending}>
            Ontkoppelen
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
