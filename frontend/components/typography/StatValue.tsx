"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { GlowText } from "./GlowText";

interface StatValueProps {
  value: string | number;
  color?: string;
  className?: string;
  animate?: boolean;
  delay?: number;
}

export function StatValue({
  value,
  color = "#e0e0e0",
  className,
  animate = true,
  delay = 0,
}: StatValueProps) {
  const content = (
    <GlowText
      color={color}
      intensity="medium"
      className={cn("text-2xl font-[var(--font-orbitron)] font-bold", className)}
    >
      {value}
    </GlowText>
  );

  if (!animate) return content;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        type: "spring",
        stiffness: 200,
        damping: 20,
        delay,
      }}
    >
      {content}
    </motion.div>
  );
}
