"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface CyberLabelProps {
  children: ReactNode;
  color?: string;
  glow?: boolean;
  className?: string;
  as?: "span" | "p" | "div" | "label";
}

export function CyberLabel({
  children,
  color = "#6b7280",
  glow = false,
  className,
  as: Component = "span",
}: CyberLabelProps) {
  return (
    <Component
      className={cn(
        "text-[10px] font-mono uppercase tracking-[0.15em]",
        className
      )}
      style={{
        color,
        textShadow: glow
          ? `0 0 8px ${color}40`
          : undefined,
      }}
    >
      {children}
    </Component>
  );
}
