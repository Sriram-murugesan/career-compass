"use client";

import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "outline" | "solid" | "ghost";
};

export function LineButton({ className, variant = "outline", children, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={cn(
        "group relative inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium",
        "transition-[color,border-color,background-color,transform] duration-300 [transition-timing-function:cubic-bezier(0.65,0,0.35,1)]",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50",
        variant === "outline" &&
          "border border-border text-foreground hover:border-ink hover:text-ink",
        variant === "solid" &&
          "border border-foreground bg-foreground text-background hover:bg-transparent hover:text-foreground",
        variant === "ghost" && "text-muted-foreground hover:text-ink",
        className,
      )}
    >
      {children}
      {variant !== "ghost" && (
        <span className="pointer-events-none absolute inset-x-3 bottom-[3px] h-px origin-left scale-x-0 bg-current transition-transform duration-[320ms] [transition-timing-function:cubic-bezier(0.65,0,0.35,1)] group-hover:scale-x-100" />
      )}
    </button>
  );
}
