"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { importBankFileAction, importScanFolderAction } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function BankImportPanel() {
  const [isPending, startTransition] = useTransition();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  function uploadFile() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      toast.error("Kies eerst een bestand");
      return;
    }
    const formData = new FormData();
    formData.set("file", file);
    startTransition(async () => {
      try {
        const result = await importBankFileAction(formData);
        toast.success(`${result.bestand}: ${result.aantal_toegevoegd} nieuwe transacties`);
        if (fileInputRef.current) fileInputRef.current.value = "";
        router.refresh();
      } catch {
        toast.error("Import mislukt");
      }
    });
  }

  function scanFolder() {
    startTransition(async () => {
      try {
        const results = await importScanFolderAction();
        const total = results.reduce((sum, r) => sum + r.aantal_toegevoegd, 0);
        toast.success(
          results.length === 0
            ? "Geen bestanden gevonden in data/BankTransactions"
            : `${results.length} bestand(en) verwerkt, ${total} nieuwe transacties`
        );
        router.refresh();
      } catch {
        toast.error("Import mislukt");
      }
    });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bankbestanden importeren</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <Input ref={fileInputRef} type="file" accept=".xml,.csv" disabled={isPending} className="max-w-xs" />
          <Button onClick={uploadFile} disabled={isPending} variant="outline">
            Uploaden
          </Button>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>of importeer alles uit</span>
          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">data/BankTransactions/</code>
          <Button onClick={scanFolder} disabled={isPending} size="sm">
            {isPending ? "Bezig…" : "Importeren"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
