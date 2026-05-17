"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

interface AnimatedHeadingProps {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "h1" | "h2" | "h3" | "h4" | "div";
}

export function AnimatedHeading({
  children,
  delay = 0,
  className,
  as: Tag = "div",
}: AnimatedHeadingProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, filter: "blur(3px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.6, ease, delay }}
      className={className}
    >
      <Tag>{children}</Tag>
    </motion.div>
  );
}
