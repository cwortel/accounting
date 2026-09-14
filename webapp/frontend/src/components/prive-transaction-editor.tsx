"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { setPriveCategorieAction, setPriveRecurringAction } from "@/app/actions";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PRIVE_CATEGORIEEN } from "@/lib/prive-categories";

export function PriveTransactionEditor({
  txId,
  categorie,
  isRecurring,
}: {
  txId: number;
  categorie: string;
  isRecurring: boolean;
}) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function onCategorieChange(value: string | null) {
    const next = value === "__none__" ? "" : value || "";
    startTransition(async () => {
      try {
        const result = await setPriveCategorieAction(txId, next, Boolean(next));
        if (result.updated > 1) toast.success(`${result.updated} transacties bijgewerkt`);
        router.refresh();
      } catch {
        toast.error("Bijwerken mislukt");
      }
    });
  }

  function onRecurringChange(checked: boolean) {
    startTransition(async () => {
      try {
        const result = await setPriveRecurringAction(txId, checked, true);
        if (result.updated > 1) toast.success(`${result.updated} transacties bijgewerkt`);
        router.refresh();
      } catch {
        toast.error("Bijwerken mislukt");
      }
    });
  }

  return (
    <div className="flex items-center gap-3">
      <Select value={categorie || "__none__"} onValueChange={onCategorieChange} disabled={isPending}>
        <SelectTrigger className="w-44 h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__none__">Geen categorie</SelectItem>
          {PRIVE_CATEGORIEEN.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex items-center gap-1.5">
        <Checkbox
          id={`rec-${txId}`}
          checked={isRecurring}
          disabled={isPending}
          onCheckedChange={(v) => onRecurringChange(Boolean(v))}
        />
        <label htmlFor={`rec-${txId}`} className="text-xs text-muted-foreground cursor-pointer">
          Vast
        </label>
      </div>
    </div>
  );
}
