"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const STATUS_OPTIONS = ["Alle", "Afgerekend", "Niet afgerekend"];

export function ExpenseFilters({
  categories,
  naam,
  categorie,
  status,
}: {
  categories: string[];
  naam: string;
  categorie: string;
  status: string;
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
      <Input
        placeholder="Filter op naam…"
        value={naamInput}
        onChange={(e) => setNaamInput(e.target.value)}
        onBlur={() => update({ naam: naamInput || undefined })}
        onKeyDown={(e) => e.key === "Enter" && update({ naam: naamInput || undefined })}
        className="w-48"
      />
      <Select value={categorie} onValueChange={(v) => update({ categorie: !v || v === "Alle" ? undefined : v })}>
        <SelectTrigger className="w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Alle">Alle categorieën</SelectItem>
          {categories.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={status} onValueChange={(v) => update({ status: !v || v === "Alle" ? undefined : v })}>
        <SelectTrigger className="w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
