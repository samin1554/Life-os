"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

/* ─── Shimmer animation ─── */
const shimmerTransition = {
  duration: 1.8,
  repeat: Infinity,
  ease: "linear" as const,
};

/* ─── Skeleton Line ─── */
export function CyberSkeletonLine({
  width = "100%",
  height = "12px",
  className,
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return (
    <motion.div
      className={cn("rounded-sm", className)}
      style={{
        height,
        width,
        background:
          "linear-gradient(90deg, #1a1a2e 25%, #2a2a3a 50%, #1a1a2e 75%)",
        backgroundSize: "200% 100%",
      }}
      animate={{ backgroundPosition: ["200% 0", "-200% 0"] }}
      transition={shimmerTransition}
    />
  );
}

/* ─── Skeleton Circle ─── */
export function CyberSkeletonCircle({
  size = 40,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={cn("rounded-full", className)}
      style={{
        width: size,
        height: size,
        background:
          "linear-gradient(90deg, #1a1a2e 25%, #2a2a3a 50%, #1a1a2e 75%)",
        backgroundSize: "200% 100%",
      }}
      animate={{ backgroundPosition: ["200% 0", "-200% 0"] }}
      transition={shimmerTransition}
    />
  );
}

/* ─── Skeleton Card ─── */
export function CyberSkeletonCard({
  lines = 3,
  className,
}: {
  lines?: number;
  className?: string;
}) {
  const widths = ["100%", "75%", "60%", "85%", "50%"];
  return (
    <div
      className={cn(
        "p-4 bg-[#12121a] border border-[#2a2a3a]/50 rounded cyber-chamfer-sm space-y-3",
        className
      )}
    >
      {Array.from({ length: lines }, (_, i) => (
        <CyberSkeletonLine
          key={i}
          width={widths[i % widths.length]}
          height={i === 0 ? "16px" : "12px"}
        />
      ))}
    </div>
  );
}

/* ─── Skeleton Row (for lists) ─── */
export function CyberSkeletonRow({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 bg-[#12121a] border border-[#2a2a3a]/50 rounded cyber-chamfer-sm",
        className
      )}
    >
      <CyberSkeletonCircle size={28} />
      <div className="flex-1 space-y-2">
        <CyberSkeletonLine width="60%" height="14px" />
        <CyberSkeletonLine width="40%" height="10px" />
      </div>
    </div>
  );
}

/* ─── Composed Skeletons for specific pages ─── */

export function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={2} />
        ))}
      </div>
      {/* Two column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <CyberSkeletonRow key={i} />
          ))}
        </div>
        <CyberSkeletonCard lines={4} />
      </div>
    </div>
  );
}

export function TasksSkeleton() {
  return (
    <div className="p-6 space-y-4">
      {Array.from({ length: 4 }, (_, i) => (
        <CyberSkeletonRow key={i} />
      ))}
    </div>
  );
}

export function GoalsSkeleton() {
  return (
    <div className="p-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={3} />
        ))}
      </div>
    </div>
  );
}

export function AgentsSkeleton() {
  return (
    <div className="p-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={3} />
        ))}
      </div>
    </div>
  );
}

export function InsightsSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={2} />
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Array.from({ length: 4 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={4} className="h-[200px]" />
        ))}
      </div>
    </div>
  );
}

export function SettingsSkeleton() {
  return (
    <div className="p-6 space-y-3">
      {Array.from({ length: 5 }, (_, i) => (
        <CyberSkeletonRow key={i} />
      ))}
    </div>
  );
}

export function WeeklyReviewSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }, (_, i) => (
          <CyberSkeletonCard key={i} lines={2} />
        ))}
      </div>
      <CyberSkeletonCard lines={5} />
    </div>
  );
}

export function DownloadsSkeleton() {
  return (
    <div className="p-6 space-y-3">
      {Array.from({ length: 4 }, (_, i) => (
        <CyberSkeletonRow key={i} />
      ))}
    </div>
  );
}
