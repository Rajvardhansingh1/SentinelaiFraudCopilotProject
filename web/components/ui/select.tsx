import { cn } from "@/lib/utils";
import type { SelectHTMLAttributes } from "react";

// Native <select> — covers the plan's Select primitive without a Radix wrapper (YAGNI).
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-md border border-slate-600 bg-bg-base p-2 text-sm text-text-primary focus:border-accent-teal focus:outline-none",
        className
      )}
      {...props}
    />
  );
}
