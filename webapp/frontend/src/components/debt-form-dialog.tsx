"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { createDebtAction, updateDebtAction } from "@/app/actions";
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
import type { Schuld } from "@/lib/api";

const FREQUENTIES = ["maandelijks", "kwartaal", "halfjaar", "jaar", "eenmalig"];

export function DebtFormDialog({ debt }: { debt?: Schuld }) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const isEdit = Boolean(debt);

  function onSubmit(formData: FormData) {
    const naam = String(formData.get("naam") || "").trim();
    const origineel_bedrag = Number(formData.get("origineel_bedrag") || 0);
    if (!naam || origineel_bedrag <= 0) {
      toast.error("Vul een naam en een origineel bedrag groter dan 0 in.");
      return;
    }

    const payload = {
      naam,
      partij: String(formData.get("partij") || ""),
      origineel_bedrag,
      termijn_bedrag: Number(formData.get("termijn_bedrag") || 0),
      frequentie: String(formData.get("frequentie") || "maandelijks"),
      aantal_termijnen: Number(formData.get("aantal_termijnen") || 0),
      betaald_termijnen: Number(formData.get("betaald_termijnen") || 0),
      actief: formData.get("actief") === "on",
      notities: String(formData.get("notities") || ""),
    };

    startTransition(async () => {
      try {
        if (debt) {
          await updateDebtAction(debt.id, payload);
          toast.success("Schuld bijgewerkt");
        } else {
          await createDebtAction(payload);
          toast.success("Schuld toegevoegd");
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
        {isEdit ? "Bewerken" : "+ Nieuwe schuld"}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form action={onSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Schuld bewerken" : "Nieuwe schuld"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="naam">Naam</Label>
                <Input id="naam" name="naam" defaultValue={debt?.naam} autoFocus required />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="partij">Partij</Label>
                <Input id="partij" name="partij" placeholder="optioneel" defaultValue={debt?.partij} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="origineel_bedrag">Origineel bedrag</Label>
                <Input
                  id="origineel_bedrag"
                  name="origineel_bedrag"
                  type="number"
                  step="0.01"
                  min="0"
                  defaultValue={debt?.origineel_bedrag}
                  required
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="termijn_bedrag">Termijnbedrag</Label>
                <Input
                  id="termijn_bedrag"
                  name="termijn_bedrag"
                  type="number"
                  step="0.01"
                  min="0"
                  defaultValue={debt?.termijn_bedrag}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="frequentie">Frequentie</Label>
                <Select name="frequentie" defaultValue={debt?.frequentie ?? "maandelijks"}>
                  <SelectTrigger id="frequentie" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FREQUENTIES.map((f) => (
                      <SelectItem key={f} value={f}>
                        {f}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="aantal_termijnen">Aantal termijnen</Label>
                <Input
                  id="aantal_termijnen"
                  name="aantal_termijnen"
                  type="number"
                  min="0"
                  defaultValue={debt?.aantal_termijnen}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="betaald_termijnen">Betaalde termijnen</Label>
                <Input
                  id="betaald_termijnen"
                  name="betaald_termijnen"
                  type="number"
                  min="0"
                  defaultValue={debt?.betaald_termijnen}
                />
              </div>
              <div className="flex items-center gap-2 pt-6">
                <input
                  id="actief"
                  name="actief"
                  type="checkbox"
                  defaultChecked={debt?.actief ?? true}
                  className="size-4"
                />
                <Label htmlFor="actief">Actief</Label>
              </div>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="notities">Notities</Label>
              <Input id="notities" name="notities" placeholder="optioneel" defaultValue={debt?.notities} />
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
