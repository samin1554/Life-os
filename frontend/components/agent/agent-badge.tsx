"use client";

import { cn } from "@/lib/utils";

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
};

const AGENT_COLORS: Record<string, string> = {
  focus: "text-[#00ff88] border-[#00ff88]/30 bg-[#00ff88]/10",
  health: "text-[#00d4ff] border-[#00d4ff]/30 bg-[#00d4ff]/10",
  execution: "text-[#ff00ff] border-[#ff00ff]/30 bg-[#ff00ff]/10",
  chaos_triage: "text-[#ff3366] border-[#ff3366]/30 bg-[#ff3366]/10",
  synthesis: "text-[#e0e0e0] border-[#e0e0e0]/20 bg-[#e0e0e0]/10",
  goals: "text-[#00ff88] border-[#00ff88]/30 bg-[#00ff88]/10",
  delegate: "text-[#00d4ff] border-[#00d4ff]/30 bg-[#00d4ff]/10",
};

interface AgentBadgeProps {
  agent: string;
  className?: string;
}

export function AgentBadge({ agent, className }: AgentBadgeProps) {
  const label = AGENT_LABELS[agent] || agent;
  const colorClass = AGENT_COLORS[agent] || AGENT_COLORS.synthesis;

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.2em] border",
        colorClass,
        className
      )}
    >
      {label}
    </span>
  );
}
