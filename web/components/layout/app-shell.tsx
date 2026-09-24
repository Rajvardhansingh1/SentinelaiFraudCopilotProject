"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { SidebarNav } from "./sidebar-nav";
import { AuthGuard } from "./auth-guard";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";

const PUBLIC_PATHS = new Set(["/login", "/signup"]);

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const pathname = usePathname();
  const showSidebar = user !== null && pathname !== null && !PUBLIC_PATHS.has(pathname);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        {showSidebar && <SidebarNav />}
        <main className={cn("min-w-0 flex-1 p-6", showSidebar && "pt-16 lg:pt-6")}>{children}</main>
      </div>
    </AuthGuard>
  );
}
