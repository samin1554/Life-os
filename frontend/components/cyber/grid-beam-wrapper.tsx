"use client";

import { GridBeam, PALETTES, type GridBeamPaletteKey } from "@/components/ui/grid-beam";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

/**
 * CyberGridBeam — Pre-configured GridBeam wrapper for the Life OS cyberpunk theme.
 * Wraps any grid layout with animated neon beams.
 *
 * Usage:
 *   <CyberGridBeam rows={2} cols={4}>
 *     <div className="grid grid-cols-4 ...">...</div>
 *   </CyberGridBeam>
 */
export function CyberGridBeam({
  children,
  rows = 2,
  cols = 4,
  colorVariant = "ocean",
  className,
  active = true,
  strength = 0.8,
  duration = 4,
}: {
  children: ReactNode;
  rows?: number;
  cols?: number;
  colorVariant?: GridBeamPaletteKey;
  className?: string;
  active?: boolean;
  strength?: number;
  duration?: number;
}) {
  return (
    <GridBeam
      rows={rows}
      cols={cols}
      colorVariant={colorVariant}
      theme="dark"
      active={active}
      breathe
      strength={strength}
      duration={duration}
      borderRadius={4}
      className={cn(
        "rounded border border-[#2a2a3a]/50",
        className
      )}
    >
      {children}
    </GridBeam>
  );
}
