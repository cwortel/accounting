"use client";

import { useState } from "react";

import { getUnmatchedBankTransactionsAction } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { BankTransaction, BankTxMatchCandidate } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";

export function BankMatchCandidateList({
  candidates,
  onLink,
  isPending,
  jaar,
}: {
  candidates: BankTxMatchCandidate[] | null;
  onLink: (txId: number) => void;
  isPending: boolean;
  // Enables the "search manually" fallback below, for when the right transaction
  // falls outside the automatic suggestions (e.g. a receipt dated much later than
  // the actual payment).
  jaar?: number;
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [unmatched, setUnmatched] = useState<BankTransaction[] | null>(null);

  function openSearch() {
    setSearchOpen(true);
    if (unmatched === null && jaar !== undefined) {
      getUnmatchedBankTransactionsAction(jaar)
        .then(setUnmatched)
        .catch(() => setUnmatched([]));
    }
  }

  const filtered = unmatched === null ? null : unmatched.filter((tx) => tx.naam.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="flex flex-col gap-2">
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
      {jaar !== undefined &&
        (!searchOpen ? (
          <Button type="button" variant="link" size="sm" className="self-start px-0" onClick={openSearch}>
            Niet in de lijst? Zoek handmatig
          </Button>
        ) : (
          <div className="flex flex-col gap-1 border-t pt-2">
            <Input placeholder="Zoek op naam…" value={query} onChange={(e) => setQuery(e.target.value)} autoFocus />
            <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
              {filtered === null && <p className="text-sm text-muted-foreground py-2">Laden…</p>}
              {filtered?.length === 0 && (
                <p className="text-sm text-muted-foreground py-2">Geen banktransacties gevonden.</p>
              )}
              {filtered?.map((tx) => (
                <button
                  key={tx.id}
                  type="button"
                  onClick={() => onLink(tx.id)}
                  disabled={isPending}
                  className="flex items-center justify-between rounded-md border px-3 py-2 text-sm text-left hover:bg-muted disabled:opacity-50"
                >
                  <span>
                    <span className="font-medium">{tx.naam}</span>{" "}
                    <span className="text-muted-foreground">· {formatDate(tx.datum)}</span>
                  </span>
                  <span className="font-medium">{formatCurrency(tx.bedrag)}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}

