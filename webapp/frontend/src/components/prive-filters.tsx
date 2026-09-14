"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PRIVE_CATEGORIEEN } from "@/lib/prive-categories";

const MAANDEN = [
  "Januari", "Februari", "Maart", "April", "Mei", "Juni",
  "Juli", "Augustus", "September", "Oktober", "November", "December",
];

export function PriveFilters({
  maand,
  rekening,
  rekeningen,
  naam,
  categorie,
  ongecategoriseerd,
  alleenVast,
}: {
  maand?: number;
  rekening?: string;
  rekeningen: { iban: string; naam: string }[];
  naam: string;
  categorie: string;
  ongecategoriseerd: boolean;
  alleenVast: boolean;
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
    <div className="flex flex-wrap items-center gap-3">
      <Select value={maand ? String(maand) : "alle"} onValueChange={(v) => update({ maand: !v || v === "alle" ? undefined : v })}>
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="alle">Alle maanden</SelectItem>
          {MAANDEN.map((m, i) => (
            <SelectItem key={m} value={String(i + 1)}>
              {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={rekening || "alle"} onValueChange={(v) => update({ rekening: !v || v === "alle" ? undefined : v })}>
        <SelectTrigger className="w-52">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="alle">Alle privé rekeningen</SelectItem>
          {rekeningen.map((r) => (
            <SelectItem key={r.iban} value={r.iban}>
              {r.naam}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        placeholder="Naam (bevat)…"
        value={naamInput}
        onChange={(e) => setNaamInput(e.target.value)}
        onBlur={() => update({ naam: naamInput || undefined })}
        onKeyDown={(e) => e.key === "Enter" && update({ naam: naamInput || undefined })}
        className="w-44"
      />

      <Select value={categorie || "Alle"} onValueChange={(v) => update({ categorie: !v || v === "Alle" ? undefined : v })}>
        <SelectTrigger className="w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Alle">Alle categorieën</SelectItem>
          {PRIVE_CATEGORIEEN.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex items-center gap-1.5">
        <Checkbox
          id="ongecategoriseerd"
          checked={ongecategoriseerd}
          onCheckedChange={(v) => update({ ongecategoriseerd: v ? "1" : undefined })}
        />
        <Label htmlFor="ongecategoriseerd" className="text-sm font-normal cursor-pointer">
          Ongecategoriseerd
        </Label>
      </div>

      <div className="flex items-center gap-1.5">
        <Checkbox id="alleen_vast" checked={alleenVast} onCheckedChange={(v) => update({ alleen_vast: v ? "1" : undefined })} />
        <Label htmlFor="alleen_vast" className="text-sm font-normal cursor-pointer">
          Vaste lasten
        </Label>
      </div>
    </div>
  );
}
