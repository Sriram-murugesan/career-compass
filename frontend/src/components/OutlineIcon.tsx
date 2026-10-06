"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function OutlineIcon({
  icon: Icon,
  size = 20,
  className,
}: {
  icon: LucideIcon;
  size?: number;
  className?: string;
}) {
  return (
    <span className={cn("draw-icon inline-flex", className)}>
      <Icon size={size} strokeWidth={1.5} fill="none" aria-hidden />
    </span>
  );
}
