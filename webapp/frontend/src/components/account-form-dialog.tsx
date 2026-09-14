"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { createAccountAction, updateAccountAction } from "@/app/actions";
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
import type { Rekening } from "@/lib/api";

export function AccountFormDialog({ account }: { account?: Rekening }) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();
  const isEdit = Boolean(account);

  function onSubmit(formData: FormData) {
    const payload = {
      naam: String(formData.get("naam") || "").trim(),
      iban: String(formData.get("iban") || "").trim(),
      type: String(formData.get("type") || "prive"),
      categorie: String(formData.get("categorie") || "betaalrekening"),
      saldo: Number(formData.get("saldo") || 0),
    };
    if (!payload.naam || !payload.iban) {
      toast.error("Vul naam en IBAN in.");
      return;
    }
    startTransition(async () => {
      try {
        if (account) {
          await updateAccountAction(account.id, payload);
          toast.success("Rekening bijgewerkt");
        } else {
          await createAccountAction(payload);
          toast.success("Rekening toegevoegd");
        }
        setOpen(false);
        router.refresh();
      } catch {
        toast.error("Opslaan mislukt. Bestaat deze IBAN al?");
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={isEdit ? <Button size="sm" variant="ghost" /> : <Button />}>
        {isEdit ? "Bewerken" : "+ Nieuwe rekening"}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form action={onSubmit}>
          <DialogHeader>
            <DialogTitle>{isEdit ? "Rekening bewerken" : "Nieuwe rekening"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-1.5">
              <Label htmlFor="naam">Naam</Label>
              <Input id="naam" name="naam" defaultValue={account?.naam} autoFocus required />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="iban">IBAN</Label>
              <Input id="iban" name="iban" defaultValue={account?.iban} required />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="type">Type</Label>
                <Select name="type" defaultValue={account?.type ?? "zakelijk"}>
                  <SelectTrigger id="type" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zakelijk">Zakelijk</SelectItem>
                    <SelectItem value="prive">Privé</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="categorie">Categorie</Label>
                <Select name="categorie" defaultValue={account?.categorie ?? "betaalrekening"}>
                  <SelectTrigger id="categorie" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="betaalrekening">Betaalrekening</SelectItem>
                    <SelectItem value="spaarrekening">Spaarrekening</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="saldo">Saldo</Label>
              <Input id="saldo" name="saldo" type="number" step="0.01" defaultValue={account?.saldo ?? 0} />
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
