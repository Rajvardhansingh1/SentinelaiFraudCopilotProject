"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const PUBLIC_PATHS = new Set(["/login", "/signup", "/", "/about", "/install"]);

export function AuthGuard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = pathname !== null && PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (loading) return;
    if (!user && !isPublic) router.replace("/login");
    if (user && pathname === "/") router.replace("/playground");
  }, [loading, user, isPublic, pathname, router]);

  if (loading) return null;
  if (!user && !isPublic) return null;
  if (user && pathname === "/") return null;
  return <>{children}</>;
}
