"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "💚" },
  { href: "/business/expenses", label: "Uitgaven", icon: "📤" },
  { href: "/business/income", label: "Inkomsten", icon: "📥" },
  { href: "/business/transactions", label: "Transacties", icon: "🏦" },
  { href: "/business/accounts", label: "Rekeningen", icon: "💳" },
  { href: "/prognose", label: "Prognose", icon: "📈" },
  { href: "/private", label: "Privé", icon: "🏠" },
  { href: "/private/debts", label: "Schulden", icon: "💰" },
];

export function NavSidebar() {
  const pathname = usePathname();
  const activeHref = [...NAV_ITEMS]
    .sort((a, b) => b.href.length - a.href.length)
    .find((item) => (item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)))?.href;

  return (
    <aside className="hidden md:flex w-60 shrink-0 flex-col border-r bg-muted/30 p-4 gap-1">
      <div className="px-2 py-3 mb-2">
        <p className="font-semibold text-lg leading-tight">Green Light</p>
        <p className="text-xs text-muted-foreground">Boekhouding</p>
      </div>
      {NAV_ITEMS.map((item) => {
        const active = item.href === activeHref;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <span aria-hidden>{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
    </aside>
  );
}
