"use client";

import { cn } from "@/lib/utils";
import { type ReactNode } from "react";
import { motion } from "framer-motion";

export interface CyberCardProps {
  variant?: "default" | "terminal" | "holographic";
  chamfer?: "sm" | "default" | "lg";
  hoverEffect?: boolean;
  header?: string;
  className?: string;
  children?: ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}

const CyberCard = ({
  className,
  variant = "default",
  chamfer = "default",
  hoverEffect = false,
  header,
  children,
  ...props
}: CyberCardProps) => {
  const chamferClass =
    chamfer === "sm"
      ? "cyber-chamfer-sm"
      : chamfer === "default"
      ? "cyber-chamfer"
      : "cyber-chamfer-lg";

  const hoverProps = hoverEffect
    ? {
        whileHover: {
          y: -3,
          boxShadow:
            variant === "holographic"
              ? "0 8px 30px rgba(0, 255, 136, 0.15), 0 0 15px rgba(0, 255, 136, 0.1)"
              : "0 8px 30px rgba(0, 255, 136, 0.12), 0 0 10px rgba(0, 255, 136, 0.08)",
        },
        whileTap: { scale: 0.99 },
        transition: { type: "spring" as const, stiffness: 400, damping: 25 },
      }
    : {};

  if (variant === "terminal") {
    return (
      <motion.div
        className={cn(
          "relative bg-[#0a0a0f] border border-[#2a2a3a]",
          chamferClass,
          hoverEffect && "hover:border-[#00ff88] transition-colors duration-300",
          className
        )}
        {...hoverProps}
        {...props}
      >
        <div className="flex items-center gap-2 px-4 py-2 border-b border-[#2a2a3a]">
          <span className="w-3 h-3 rounded-full bg-[#ff3366]" />
          <span className="w-3 h-3 rounded-full bg-[#ffcc00]" />
          <span className="w-3 h-3 rounded-full bg-[#00ff88]" />
          {header && (
            <span className="ml-2 text-xs font-mono uppercase tracking-wider text-[#6b7280]">
              {header}
            </span>
          )}
        </div>
        <div className="p-5">{children}</div>
      </motion.div>
    );
  }

  if (variant === "holographic") {
    return (
      <motion.div
        className={cn(
          "relative bg-[#1c1c2e]/30 border border-[#00ff88]/30 backdrop-blur-sm",
          chamferClass,
          "shadow-[0_0_10px_#00ff8820]",
          hoverEffect && "hover:border-[#00ff88]/60 transition-colors duration-300",
          className
        )}
        {...hoverProps}
        {...props}
      >
        <span className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#00ff88]" />
        <span className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#00ff88]" />
        <span className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#00ff88]" />
        <span className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#00ff88]" />
        <div className="p-5 relative">{children}</div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className={cn(
        "bg-[#12121a] border border-[#2a2a3a]",
        chamferClass,
        hoverEffect && "hover:border-[#2a2a4a] transition-colors duration-300",
        className
      )}
      {...hoverProps}
      {...props}
    >
      {header && (
        <div className="px-5 py-3 border-b border-[#2a2a3a]">
          <h3 className="text-sm font-mono uppercase tracking-wider text-[#6b7280]">{header}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </motion.div>
  );
};
CyberCard.displayName = "CyberCard";

export { CyberCard };
