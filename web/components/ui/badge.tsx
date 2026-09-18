import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

type Variant = "default" | "success" | "danger" | "warning" | "muted";

const variants: Record<Variant, string> = {
  default: "bg-accent-teal/20 text-accent-teal border-accent-teal/40",
  success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
  danger: "bg-red-500/20 text-red-400 border-red-500/40",
  warning: "bg-amber-500/20 text-amber-400 border-amber-500/40",
  muted: "bg-slate-500/20 text-slate-300 border-slate-500/40",
};

export function Badge({
  className,
  variant = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
