"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface GlowTextProps {
  children: ReactNode;
  color?: string;
  intensity?: "low" | "medium" | "high";
  className?: string;
  as?: "span" | "p" | "h1" | "h2" | "h3" | "h4" | "div";
}

const intensityMap = {
  low: 0.3,
  medium: 0.5,
  high: 0.8,
};

export function GlowText({
  children,
  color = "#e0e0e0",
  intensity = "medium",
  className,
  as: Component = "span",
}: GlowTextProps) {
  const alpha = intensityMap[intensity];
  const shadow = `0 0 ${intensity === "high" ? "20px" : "12px"} ${color}${Math.round(alpha * 255)
    .toString(16)
    .padStart(2, "0")}`;

  return (
    <Component
      className={cn(className)}
      style={{
        color,
        textShadow: shadow,
      }}
    >
      {children}
    </Component>
  );
}
