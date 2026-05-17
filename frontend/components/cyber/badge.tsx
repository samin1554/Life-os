"use client";

import { cn } from "@/lib/utils";
import { HTMLAttributes, forwardRef } from "react";

export interface CyberBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "tertiary" | "destructive" | "outline";
}

const CyberBadge = forwardRef<HTMLSpanElement, CyberBadgeProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    const variants = {
      default: "bg-[#00ff88]/10 text-[#00ff88] border-[#00ff88]/30",
      secondary: "bg-[#ff00ff]/10 text-[#ff00ff] border-[#ff00ff]/30",
      tertiary: "bg-[#00d4ff]/10 text-[#00d4ff] border-[#00d4ff]/30",
      destructive: "bg-[#ff3366]/10 text-[#ff3366] border-[#ff3366]/30",
      outline: "bg-transparent text-[#6b7280] border-[#2a2a3a]",
    };

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center px-2.5 py-0.5 text-xs font-mono uppercase tracking-[0.15em] border",
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);
CyberBadge.displayName = "CyberBadge";

export { CyberBadge };
