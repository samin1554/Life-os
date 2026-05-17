"use client";

import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";
import { motion } from "framer-motion";

export interface CyberButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "glitch" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
  chamfer?: "sm" | "default" | "lg" | "none";
  glow?: boolean;
}

const CyberButton = forwardRef<HTMLButtonElement, CyberButtonProps>(
  ({ className, variant = "default", size = "default", chamfer = "sm", glow = false, children, disabled, ...props }, ref) => {
    const chamferClass =
      chamfer === "sm"
        ? "cyber-chamfer-sm"
        : chamfer === "default"
        ? "cyber-chamfer"
        : chamfer === "lg"
        ? "cyber-chamfer-lg"
        : "";

    const variants = {
      default: cn(
        "bg-transparent border-2 border-[#00ff88] text-[#00ff88]",
        "hover:bg-[#00ff88] hover:text-[#0a0a0f]",
        glow && "hover:shadow-[0_0_5px_#00ff88,0_0_20px_#00ff8860]"
      ),
      secondary: cn(
        "bg-transparent border-2 border-[#ff00ff] text-[#ff00ff]",
        "hover:bg-[#ff00ff] hover:text-[#0a0a0f]",
        glow && "hover:shadow-[0_0_5px_#ff00ff,0_0_20px_#ff00ff60]"
      ),
      outline: cn(
        "bg-transparent border border-[#2a2a3a] text-[#e0e0e0]",
        "hover:border-[#00ff88] hover:text-[#00ff88]",
        glow && "hover:shadow-[0_0_5px_#00ff88,0_0_10px_#00ff8840]"
      ),
      ghost: cn(
        "bg-transparent border-none text-[#e0e0e0]",
        "hover:bg-[#00ff88]/10 hover:text-[#00ff88]"
      ),
      glitch: cn(
        "bg-[#00ff88] text-[#0a0a0f] border-none",
        "hover:brightness-110",
        "shadow-[0_0_10px_#00ff8860]"
      ),
      destructive: cn(
        "bg-transparent border-2 border-[#ff3366] text-[#ff3366]",
        "hover:bg-[#ff3366] hover:text-[#0a0a0f]"
      ),
    };

    const sizes = {
      default: "h-10 px-5 py-2 text-sm",
      sm: "h-8 px-3 py-1 text-xs",
      lg: "h-12 px-8 py-3 text-base",
      icon: "h-10 w-10 p-2",
    };

    return (
      <motion.button
        ref={ref}
        whileHover={disabled ? undefined : { scale: 1.03 }}
        whileTap={disabled ? undefined : { scale: 0.97 }}
        transition={{ type: "spring", stiffness: 500, damping: 20 }}
        className={cn(
          "inline-flex items-center justify-center font-mono uppercase tracking-[0.15em] font-medium",
          "transition-all duration-150 ease-out",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00ff88] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0f]",
          "disabled:pointer-events-none disabled:opacity-40",
          chamferClass,
          variants[variant],
          sizes[size],
          className
        )}
        disabled={disabled}
        {...(props as any)}
      >
        {children}
      </motion.button>
    );
  }
);
CyberButton.displayName = "CyberButton";

export { CyberButton };
