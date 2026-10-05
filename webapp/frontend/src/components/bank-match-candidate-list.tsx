"use client";

import type { BankTxMatchCandidate } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export function BankMatchCandidateList({
  candidates,
  onLink,
  isPending,
}: {
  candidates: BankTxMatchCandidate[] | null;
  onLink: (txId: number) => void;
  isPending: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
      {candidates === null && <p className="text-sm text-muted-foreground py-2">Suggesties laden…</p>}
      {candidates?.length === 0 && (
        <p className="text-sm text-muted-foreground py-2">Geen passende banktransacties gevonden.</p>
      )}
      {candidates?.map((c) => (
        <button
          key={c.tx_id}
          type="button"
          onClick={() => onLink(c.tx_id)}
          disabled={isPending}
          className="flex items-center justify-between rounded-md border px-3 py-2 text-sm text-left hover:bg-muted disabled:opacity-50"
        >
          <span>
            <span className="font-medium">{c.naam}</span>{" "}
            <span className="text-muted-foreground">· {formatDate(c.datum)}</span>
          </span>
          <span className="font-medium">{formatCurrency(c.bedrag)}</span>
        </button>
      ))}
    </div>
  );
}
