"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { createExpenseAction, updateExpenseAction } from "@/app/actions";
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
import type { Expense } from "@/lib/api";

const PAYMENT_SOURCES = ["Onbekend", "Privé rekening", "Privé creditcard", "Contant", "Bank zakelijk"];

function deriveKwartaal(datum: string): number {
  const month = Number(datum.slice(5, 7)) || new Date().getMonth() + 1;
  return Math.floor((month - 1) / 3) + 1;
}

export function ExpenseFormDialog({ categories, expense }: { categories: string[]; expense?: Expense }) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const today = new Date().toISOString().slice(0, 10);
  const isEdit = Boolean(expense);

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
      categorie: String(formData.get("categorie") || ""),
      btw_pct: Number(formData.get("btw_pct") || 0),
      total,
      jaar,
      kwartaal: deriveKwartaal(datum),
      betaal_bron: String(formData.get("betaal_bron") || ""),
    };

    startTransition(async () => {
      try {
        if (expense) {
          await updateExpenseAction(expense.id, { ...payload, afgerekend: expense.afgerekend });
          toast.success("Uitgave bijgewerkt");
        } else {
          await createExpenseAction(payload);
          toast.success("Uitgave toegevoegd");
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
        {isEdit ? "Bewerken" : "+ Nieuwe uitgave"}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form action={onSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Uitgave bewerken" : "Nieuwe uitgave"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-1.5">
              <Label htmlFor="naam">Naam</Label>
              <Input
                id="naam"
                name="naam"
                placeholder="Leverancier / omschrijving"
                defaultValue={expense?.naam}
                autoFocus
                required
              />
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
                  defaultValue={expense?.total}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="btw_pct">BTW %</Label>
                <Select name="btw_pct" defaultValue={String(expense?.btw_pct ?? 21)}>
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
                <Input id="datum" name="datum" type="date" defaultValue={expense?.datum ?? today} required />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="categorie">Categorie</Label>
                <Select name="categorie" defaultValue={expense?.categorie ?? categories[0] ?? ""}>
                  <SelectTrigger id="categorie" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="factuur">Factuurnummer</Label>
                <Input id="factuur" name="factuur" placeholder="optioneel" defaultValue={expense?.factuur} />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="betaal_bron">Betaald via</Label>
                <Select name="betaal_bron" defaultValue={expense?.betaal_bron || "Onbekend"}>
                  <SelectTrigger id="betaal_bron" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PAYMENT_SOURCES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
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
