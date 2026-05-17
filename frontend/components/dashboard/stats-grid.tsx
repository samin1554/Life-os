"use client";

import { cn } from "@/lib/utils";
import { Flame, CheckCircle2, Target, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { CyberLabel, StatValue, CountUpNumber } from "@/components/typography";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

interface StatsGridProps {
  streak: number;
  completedThisWeek: number;
  pendingTasks: number;
  goalsCount: number;
}

export function StatsGrid({ streak, completedThisWeek, pendingTasks, goalsCount }: StatsGridProps) {
  const stats = [
    {
      label: "Streak",
      value: streak,
      suffix: "days",
      icon: Flame,
      color: "text-[#ff00ff]",
      bg: "bg-[#ff00ff]/10",
      glowColor: "#ff00ff",
    },
    {
      label: "Done This Week",
      value: completedThisWeek,
      suffix: "tasks",
      icon: CheckCircle2,
      color: "text-[#00ff88]",
      bg: "bg-[#00ff88]/10",
      glowColor: "#00ff88",
    },
    {
      label: "Pending",
      value: pendingTasks,
      suffix: "tasks",
      icon: Target,
      color: "text-[#00d4ff]",
      bg: "bg-[#00d4ff]/10",
      glowColor: "#00d4ff",
    },
    {
      label: "Active Goals",
      value: goalsCount,
      suffix: "goals",
      icon: TrendingUp,
      color: "text-[#ffcc00]",
      bg: "bg-[#ffcc00]/10",
      glowColor: "#ffcc00",
    },
  ];

  return (
    <CyberGridBeam rows={2} cols={4} colorVariant="ocean">
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 p-3">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.45, ease, delay: 0.08 * i }}
            whileHover={{
              y: -3,
              boxShadow: `0 8px 25px ${stat.glowColor}15, 0 0 10px ${stat.glowColor}10`,
              transition: { type: "spring", stiffness: 400, damping: 25 },
            }}
            className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer-sm p-4
              hover:border-[#2a2a4a] transition-colors duration-300"
          >
            <div className="flex items-center gap-2 mb-2">
              <motion.div
                className={cn("p-1.5", stat.bg)}
                whileHover={{ rotate: 10, scale: 1.1 }}
                transition={{ type: "spring", stiffness: 400, damping: 15 }}
              >
                <Icon className={cn("w-3.5 h-3.5", stat.color)} strokeWidth={1.5} />
              </motion.div>
              <CyberLabel glow color={stat.glowColor}>
                {stat.label}
              </CyberLabel>
            </div>
            <div className="flex items-baseline gap-1.5">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.15 + 0.08 * i }}
              >
                <CountUpNumber
                  value={stat.value}
                  duration={1.4}
                  className="text-2xl font-[var(--font-orbitron)] font-bold"
                  style={{ color: stat.glowColor, textShadow: `0 0 10px ${stat.glowColor}60` }}
                />
              </motion.div>
              <CyberLabel color="#6b7280">{stat.suffix}</CyberLabel>
            </div>
          </motion.div>
        );
      })}
    </div>
    </CyberGridBeam>
  );
}
