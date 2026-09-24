"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProjectSwitcher } from "./project-switcher";

const LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/security", label: "Security Tests" },
  { href: "/findings", label: "Findings" },
  { href: "/remediation", label: "Remediation" },
  { href: "/regression", label: "Regression" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/agents", label: "Agent Security" },
  { href: "/reports", label: "Reports" },
  { href: "/dashboard", label: "Dashboard" },
];

export function SidebarNav() {
  const pathname = usePathname();
  // Below `lg` the w-56 sidebar used to render as a static flex sibling,
  // eating ~57% of a 390px viewport and pushing main content off-screen.
  // Below `lg` it's now a fixed off-canvas drawer toggled by a hamburger
  // button; at `lg` and above it's the original static sidebar.
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        aria-label={open ? "Close navigation" : "Open navigation"}
        onClick={() => setOpen((v) => !v)}
        className="fixed left-4 top-4 z-50 flex h-9 w-9 items-center justify-center rounded-md border border-bg-surface bg-bg-base text-text-primary lg:hidden"
      >
        {open ? <X size={18} /> : <Menu size={18} />}
      </button>

      {open && (
        <div
          aria-hidden
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
        />
      )}

      <nav
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-56 shrink-0 overflow-y-auto border-r border-bg-surface bg-bg-base p-4 transition-transform duration-200",
          "lg:static lg:z-auto lg:translate-x-0 lg:bg-bg-surface/40",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="mb-6 text-lg font-semibold text-accent-teal">SentinelAI</div>
        <ProjectSwitcher />
        <ul className="space-y-1">
          {LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                onClick={() => setOpen(false)}
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
    </>
  );
}
