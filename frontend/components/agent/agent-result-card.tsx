"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, CheckCircle2, ChevronDown, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/* ─── Agent metadata ─── */
const AGENT_LABELS: Record<string, string> = {
  supervisor: "Routing",
  focus: "Focus",
  health: "Health",
  execution: "Execution",
  chaos_triage: "Triage",
  synthesis: "Life OS",
  goals: "Goals",
  delegate: "Research",
  pattern_learning: "Patterns",
  weekly_review: "Review",
  research: "Research",
  worker: "Worker",
};

const AGENT_COLORS: Record<string, string> = {
  focus: "#00ff88",
  health: "#00d4ff",
  execution: "#ff00ff",
  chaos_triage: "#ff3366",
  synthesis: "#e0e0e0",
  goals: "#ffcc00",
  delegate: "#8b5cf6",
  research: "#00aaff",
  worker: "#ff5500",
  pattern_learning: "#00ff88",
  weekly_review: "#00d4ff",
};

const DEFAULT_COLOR = "#6b7280";

/* ─── Easing ─── */
const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

/* ─── Particle Burst ─── */
function ParticleBurst({ color }: { color: string }) {
  const particles = useMemo(
    () =>
      Array.from({ length: 8 }).map((_, i) => {
        const angle = (i / 8) * Math.PI * 2;
        const distance = 16 + Math.random() * 12;
        return {
          x: Math.cos(angle) * distance,
          y: Math.sin(angle) * distance,
          delay: i * 0.04,
          size: 2 + Math.random() * 3,
        };
      }),
    []
  );

  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      {particles.map((p, i) => (
        <motion.span
          key={i}
          className="absolute rounded-full"
          style={{
            width: p.size,
            height: p.size,
            backgroundColor: color,
            boxShadow: `0 0 6px ${color}80`,
          }}
          initial={{ opacity: 0, scale: 0, x: 0, y: 0 }}
          animate={{
            opacity: [0, 1, 0],
            scale: [0, 1.2, 0.4],
            x: p.x,
            y: p.y,
          }}
          transition={{
            duration: 0.8,
            delay: p.delay,
            ease: "easeOut",
          }}
        />
      ))}
    </div>
  );
}

/* ─── Animated Checkmark ─── */
function AnimatedCheckmark({ color }: { color: string }) {
  return (
    <motion.svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease, delay: 0.2 }}
    >
      <motion.path
        d="M5 13l4 4L19 7"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.5, ease, delay: 0.4 }}
      />
    </motion.svg>
  );
}

/* ─── Orbiting Dots (the "GIF" replacement) ─── */
function OrbitingDots({ color }: { color: string }) {
  return (
    <div className="relative w-8 h-8 flex items-center justify-center">
      <motion.div
        className="absolute w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }}
        animate={{
          x: [0, 10, 0, -10, 0],
          y: [-10, 5, 10, 5, -10],
          opacity: [1, 0.6, 1, 0.6, 1],
        }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute w-1 h-1 rounded-full"
        style={{ backgroundColor: color, opacity: 0.6 }}
        animate={{
          x: [0, -8, 0, 8, 0],
          y: [8, -4, -8, -4, 8],
          opacity: [0.6, 1, 0.6, 1, 0.6],
        }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
      />
      <motion.div
        className="absolute w-[3px] h-[3px] rounded-full"
        style={{ backgroundColor: color, opacity: 0.4 }}
        animate={{
          x: [0, 6, 0, -6, 0],
          y: [-6, -6, 6, -6, -6],
          opacity: [0.4, 0.8, 0.4, 0.8, 0.4],
        }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
      />
      <Bot className="w-4 h-4 relative z-10" style={{ color }} />
    </div>
  );
}

/* ─── Main Component ─── */
interface AgentResultCardProps {
  agent?: string;
  output: string;
  status?: string;
  compact?: boolean;
  className?: string;
}

export function AgentResultCard({
  agent,
  output,
  status = "completed",
  compact = false,
  className,
}: AgentResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const color = AGENT_COLORS[agent || ""] || DEFAULT_COLOR;
  const label = AGENT_LABELS[agent || ""] || agent || "Agent";
  const isCompleted = status === "completed";

  return (
    <motion.div
      className={cn("relative mt-2 ml-8", className)}
      initial={{ opacity: 0, y: 12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, ease }}
    >
      {/* Rotating gradient border wrapper */}
      <div
        className="relative overflow-hidden cyber-chamfer-sm"
        style={{ padding: "1.5px" }}
      >
        {/* Animated border layer */}
        <div
          className="absolute inset-[-50%] w-[200%] h-[200%]"
          style={{
            background: `conic-gradient(from 0deg, transparent 0deg, ${color}20 60deg, ${color}50 120deg, ${color}20 180deg, transparent 240deg, ${color}15 300deg, transparent 360deg)`,
            animation: "border-rotate 4s linear infinite",
          }}
        />

        {/* Content */}
        <div className="relative bg-[#0d0d14] cyber-chamfer-sm">
          {/* Corner accents */}
          <span
            className="absolute top-0 left-0 w-3 h-3 border-t border-l z-10"
            style={{ borderColor: `${color}40` }}
          />
          <span
            className="absolute top-0 right-0 w-3 h-3 border-t border-r z-10"
            style={{ borderColor: `${color}40` }}
          />
          <span
            className="absolute bottom-0 left-0 w-3 h-3 border-b border-l z-10"
            style={{ borderColor: `${color}40` }}
          />
          <span
            className="absolute bottom-0 right-0 w-3 h-3 border-b border-r z-10"
            style={{ borderColor: `${color}40` }}
          />

          {/* Header */}
          <div className="flex items-center gap-2.5 px-3 py-2 border-b border-[#2a2a3a]">
            {/* Orbiting dots + bot icon */}
            <div className="relative">
              <OrbitingDots color={color} />
              {isCompleted && <ParticleBurst color={color} />}
            </div>

            {/* Agent label */}
            <span
              className="text-[10px] font-mono uppercase tracking-[0.2em]"
              style={{ color }}
            >
              {label}
            </span>

            {/* Divider */}
            <span className="text-[#2a2a3a]">|</span>

            {/* Status */}
            <div className="flex items-center gap-1">
              {isCompleted ? (
                <AnimatedCheckmark color={color} />
              ) : (
                <Sparkles className="w-3.5 h-3.5" style={{ color }} />
              )}
              <span
                className="text-[10px] font-mono uppercase tracking-wider"
                style={{ color: `${color}cc` }}
              >
                {isCompleted ? "Done" : "Result"}
              </span>
            </div>
          </div>

          {/* Output body */}
          <motion.div
            className="px-3 py-2 cursor-pointer group"
            onClick={() => setExpanded(!expanded)}
            whileHover={{ backgroundColor: "rgba(255,255,255,0.02)" }}
            transition={{ duration: 0.2 }}
          >
            <AnimatePresence mode="wait">
              {!expanded ? (
                <motion.div
                  key="collapsed"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <p className="text-[11px] font-mono text-[#6b7280] line-clamp-3 leading-relaxed">
                    {output}
                  </p>
                  <div className="flex items-center gap-1 mt-1.5 text-[10px] font-mono text-[#4a4a5a] group-hover:text-[#6b7280] transition-colors">
                    <ChevronDown className="w-3 h-3" />
                    <span>Expand</span>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="expanded"
                  className="overflow-hidden"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.3, ease }}
                >
                  <motion.p
                    className="text-[11px] font-mono text-[#9ca3af] leading-relaxed whitespace-pre-wrap"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3, delay: 0.1 }}
                  >
                    {output}
                  </motion.p>
                  <div className="flex items-center gap-1 mt-2 text-[10px] font-mono text-[#4a4a5a] group-hover:text-[#6b7280] transition-colors">
                    <ChevronDown className="w-3 h-3 rotate-180" />
                    <span>Collapse</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Bottom glow line */}
          <motion.div
            className="h-px w-full"
            style={{
              background: `linear-gradient(90deg, transparent, ${color}30, transparent)`,
            }}
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.8, ease, delay: 0.3 }}
          />
        </div>
      </div>
    </motion.div>
  );
}
