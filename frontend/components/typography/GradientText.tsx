"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface GradientTextProps {
  children: ReactNode;
  from?: string;
  to?: string;
  className?: string;
  as?: "span" | "p" | "h1" | "h2" | "h3" | "h4" | "div";
}

export function GradientText({
  children,
  from = "#00ff88",
  to = "#00d4ff",
  className,
  as: Component = "span",
}: GradientTextProps) {
  return (
    <Component
      className={cn("bg-clip-text text-transparent", className)}
      style={{
        backgroundImage: `linear-gradient(135deg, ${from}, ${to})`,
      }}
    >
      {children}
    </Component>
  );
}
