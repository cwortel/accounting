"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { deleteAccountAction, deleteDebtAction, deleteExpenseAction, deleteIncomeAction } from "@/app/actions";
import { Button } from "@/components/ui/button";

export function DeleteExpenseButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onClick() {
    if (!confirm("Deze uitgave verwijderen?")) return;
    startTransition(async () => {
      try {
        await deleteExpenseAction(id);
        toast.success("Uitgave verwijderd");
        router.refresh();
      } catch {
        toast.error("Verwijderen mislukt");
      }
    });
  }

  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={isPending}>
      Verwijderen
    </Button>
  );
}

export function DeleteIncomeButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onClick() {
    if (!confirm("Deze inkomst verwijderen?")) return;
    startTransition(async () => {
      try {
        await deleteIncomeAction(id);
        toast.success("Inkomst verwijderd");
        router.refresh();
      } catch {
        toast.error("Verwijderen mislukt");
      }
    });
  }

  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={isPending}>
      Verwijderen
    </Button>
  );
}

export function DeleteDebtButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onClick() {
    if (!confirm("Deze schuld verwijderen?")) return;
    startTransition(async () => {
      try {
        await deleteDebtAction(id);
        toast.success("Schuld verwijderd");
        router.refresh();
      } catch {
        toast.error("Verwijderen mislukt");
      }
    });
  }

  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={isPending}>
      Verwijderen
    </Button>
  );
}

export function DeleteAccountButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onClick() {
    if (!confirm("Deze rekening verwijderen?")) return;
    startTransition(async () => {
      try {
        await deleteAccountAction(id);
        toast.success("Rekening verwijderd");
        router.refresh();
      } catch {
        toast.error("Verwijderen mislukt");
      }
    });
  }

  return (
    <Button variant="ghost" size="sm" onClick={onClick} disabled={isPending}>
      Verwijderen
    </Button>
  );
}
