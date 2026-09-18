import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const variants = {
    primary: "bg-accent-teal text-bg-base hover:bg-accent-teal/90",
    secondary: "bg-bg-surface text-text-primary hover:bg-bg-surface/80 border border-slate-600",
    ghost: "bg-transparent text-text-primary hover:bg-bg-surface/50",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}
