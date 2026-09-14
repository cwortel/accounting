"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { createIncomeAction, updateIncomeAction } from "@/app/actions";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Income } from "@/lib/api";

function deriveKwartaal(datum: string): number {
  const month = Number(datum.slice(5, 7)) || new Date().getMonth() + 1;
  return Math.floor((month - 1) / 3) + 1;
}

export function IncomeFormDialog({ income }: { income?: Income }) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const isEdit = Boolean(income);

  function onSubmit(formData: FormData) {
    const datum = String(formData.get("datum") || today);
    const jaar = Number(datum.slice(0, 4));
    const total = Number(formData.get("total") || 0);
    const naam = String(formData.get("naam") || "").trim();

    if (!naam || total <= 0) {
      toast.error("Vul een naam en een bedrag groter dan 0 in.");
      return;
    }

    const payload = {
      naam,
      factuur: String(formData.get("factuur") || ""),
      datum,
      project: String(formData.get("project") || ""),
      btw_pct: Number(formData.get("btw_pct") || 21),
      total,
      jaar,
      kwartaal: deriveKwartaal(datum),
    };

    startTransition(async () => {
      try {
        if (income) {
          await updateIncomeAction(income.id, { ...payload, betaald: income.betaald });
          toast.success("Inkomst bijgewerkt");
        } else {
          await createIncomeAction(payload);
          toast.success("Inkomst toegevoegd");
        }
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Opslaan mislukt. Probeer het opnieuw.");
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={isEdit ? <Button size="sm" variant="ghost" /> : <Button />}>
        {isEdit ? "Bewerken" : "+ Nieuwe inkomst"}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form action={onSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Inkomst bewerken" : "Nieuwe inkomst"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-1.5">
              <Label htmlFor="naam">Klant / naam</Label>
              <Input id="naam" name="naam" defaultValue={income?.naam} autoFocus required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="total">Totaal (incl. BTW)</Label>
                <Input
                  id="total"
                  name="total"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  defaultValue={income?.total}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="btw_pct">BTW %</Label>
                <Select name="btw_pct" defaultValue={String(income?.btw_pct ?? 21)}>
                  <SelectTrigger id="btw_pct" className="w-full">
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
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="datum">Datum</Label>
                <Input id="datum" name="datum" type="date" defaultValue={income?.datum ?? today} required />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="project">Project</Label>
                <Input id="project" name="project" placeholder="optioneel" defaultValue={income?.project} />
              </div>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="factuur">Factuurnummer</Label>
              <Input id="factuur" name="factuur" placeholder="optioneel" defaultValue={income?.factuur} />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Opslaan…" : "Opslaan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
