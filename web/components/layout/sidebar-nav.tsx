"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/review", label: "Review" },
  { href: "/dashboard", label: "Dashboard" },
];

export function SidebarNav() {
  const pathname = usePathname();
  return (
    <nav className="w-56 shrink-0 border-r border-bg-surface bg-bg-surface/40 p-4">
      <div className="mb-6 text-lg font-semibold text-accent-teal">SentinelAI</div>
      <ul className="space-y-1">
        {LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className={cn(
                "block rounded-md px-3 py-2 text-sm text-slate-300 hover:bg-bg-surface hover:text-text-primary",
                pathname?.startsWith(link.href) && "bg-bg-surface text-accent-teal"
              )}
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
