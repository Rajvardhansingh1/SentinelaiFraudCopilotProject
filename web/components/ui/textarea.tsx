import { cn } from "@/lib/utils";
import type { TextareaHTMLAttributes } from "react";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-md border border-slate-600 bg-bg-base p-3 text-sm text-text-primary placeholder:text-slate-500 focus:border-accent-teal focus:outline-none",
        className
      )}
      {...props}
    />
  );
}
