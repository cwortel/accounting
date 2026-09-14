"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const CATEGORIES = ["Alle", "Uitgave", "Inkomst", "Interne overboeking", "Privé onttrekking", "BTW betaling", "Ongekoppeld"];

export function TransactionFilters({
  kwartaal,
  ongekoppeld,
  naam,
  categorie,
}: {
  kwartaal?: number;
  ongekoppeld: boolean;
  naam: string;
  categorie: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [naamInput, setNaamInput] = useState(naam);

  function update(patch: Record<string, string | undefined>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (!v) params.delete(k);
      else params.set(k, v);
    }
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <Select value={kwartaal ? String(kwartaal) : "alle"} onValueChange={(v) => update({ kwartaal: !v || v === "alle" ? undefined : v })}>
        <SelectTrigger className="w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="alle">Alle kwartalen</SelectItem>
          <SelectItem value="1">Q1</SelectItem>
          <SelectItem value="2">Q2</SelectItem>
          <SelectItem value="3">Q3</SelectItem>
          <SelectItem value="4">Q4</SelectItem>
        </SelectContent>
      </Select>

      <Select value={categorie} onValueChange={(v) => update({ categorie: !v || v === "Alle" ? undefined : v })}>
        <SelectTrigger className="w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CATEGORIES.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        placeholder="Zoek op naam…"
        value={naamInput}
        onChange={(e) => setNaamInput(e.target.value)}
        onBlur={() => update({ naam: naamInput || undefined })}
        onKeyDown={(e) => e.key === "Enter" && update({ naam: naamInput || undefined })}
        className="w-48"
      />

      <div className="flex items-center gap-2">
        <Checkbox
          id="ongekoppeld"
          checked={ongekoppeld}
          onCheckedChange={(v) => update({ ongekoppeld: v ? "1" : undefined })}
        />
        <Label htmlFor="ongekoppeld" className="text-sm font-normal cursor-pointer">
          Alleen ongekoppeld
        </Label>
      </div>
    </div>
  );
}
