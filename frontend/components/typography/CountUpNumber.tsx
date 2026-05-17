"use client";

import { useEffect, useState } from "react";
import { animate } from "framer-motion";

interface CountUpNumberProps {
  value: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  style?: React.CSSProperties;
}

export function CountUpNumber({
  value,
  duration = 1.2,
  decimals = 0,
  prefix = "",
  suffix = "",
  className,
  style,
}: CountUpNumberProps) {
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    const controls = animate(0, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v.toFixed(decimals)),
    });
    return () => controls.stop();
  }, [value, duration, decimals]);

  return (
    <span className={className} style={style}>
      {prefix}{display}{suffix}
    </span>
  );
}
