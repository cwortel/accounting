"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function QuarterSwitcher({ kwartaal }: { kwartaal?: number }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function onChange(value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (!value || value === "alle") params.delete("kwartaal");
    else params.set("kwartaal", value);
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <Select value={kwartaal ? String(kwartaal) : "alle"} onValueChange={onChange}>
      <SelectTrigger className="w-32">
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
  );
}
