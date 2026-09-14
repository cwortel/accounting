"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { unlinkTransactionAction } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function UnlinkTransactionButton({ txId }: { txId: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onClick() {
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
    <Button size="sm" variant="ghost" onClick={onClick} disabled={isPending}>
      Ontkoppelen
    </Button>
  );
}
