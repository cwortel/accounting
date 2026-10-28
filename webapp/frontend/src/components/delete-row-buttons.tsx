"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { deleteAccountAction, deleteDebtAction, deleteExpenseAction, deleteIncomeAction } from "@/app/actions";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

function ConfirmDeleteButton({
  description,
  isPending,
  onConfirm,
}: {
  description: string;
  isPending: boolean;
  onConfirm: () => void;
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger render={<Button variant="ghost" size="sm" disabled={isPending} />}>
        Verwijderen
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Weet je het zeker?</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Annuleren</AlertDialogCancel>
          <AlertDialogAction className="bg-destructive text-white hover:bg-destructive/90" onClick={onConfirm}>
            Verwijderen
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function DeleteExpenseButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onConfirm() {
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

  return <ConfirmDeleteButton description="Deze uitgave verwijderen?" isPending={isPending} onConfirm={onConfirm} />;
}

export function DeleteIncomeButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onConfirm() {
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

  return <ConfirmDeleteButton description="Deze inkomst verwijderen?" isPending={isPending} onConfirm={onConfirm} />;
}

export function DeleteDebtButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onConfirm() {
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

  return <ConfirmDeleteButton description="Deze schuld verwijderen?" isPending={isPending} onConfirm={onConfirm} />;
}

export function DeleteAccountButton({ id }: { id: number }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onConfirm() {
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

  return <ConfirmDeleteButton description="Deze rekening verwijderen?" isPending={isPending} onConfirm={onConfirm} />;
}
