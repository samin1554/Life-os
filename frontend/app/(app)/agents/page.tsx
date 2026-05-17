"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { CyberInput } from "@/components/cyber/input";
import { useAgentEvents } from "@/hooks/useAgentEvents";
import type { AgentStatusCard, AgentRun } from "@/types";
import {
  Bot,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Zap,
  Send,
} from "lucide-react";
import { motion } from "framer-motion";
import { AgentsSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";
import { AGENT_DESCRIPTIONS, AGENT_COLORS } from "@/lib/agents";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const AGENT_ICONS: Record<string, { color: string; description: string }> = {
  focus: { color: AGENT_COLORS.focus, description: AGENT_DESCRIPTIONS.focus },
  health: { color: AGENT_COLORS.health, description: AGENT_DESCRIPTIONS.health },
  execution: { color: AGENT_COLORS.execution, description: AGENT_DESCRIPTIONS.execution },
  chaos_triage: { color: AGENT_COLORS.chaos_triage, description: AGENT_DESCRIPTIONS.chaos_triage },
  goals: { color: AGENT_COLORS.goals, description: AGENT_DESCRIPTIONS.goals },
  delegate: { color: AGENT_COLORS.delegate, description: AGENT_DESCRIPTIONS.delegate },
  research: { color: AGENT_COLORS.research, description: AGENT_DESCRIPTIONS.research },
  worker: { color: AGENT_COLORS.worker, description: AGENT_DESCRIPTIONS.worker },
};

export default function AgentsPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const { events, connected, connect, disconnect } = useAgentEvents();
  const [agents, setAgents] = useState<AgentStatusCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [runInput, setRunInput] = useState<Record<string, string>>({});
  const [runningAgent, setRunningAgent] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, AgentRun[]>>({});

  useEffect(() => {
    loadAgentStatus();
    connect();
    return () => disconnect();
  }, []);

  useEffect(() => {
    if (events.length > 0) {
      loadAgentStatus();
      const latestEvent = events[0];
      if (latestEvent.status === "completed" || latestEvent.status === "failed") {
        if (expanded) loadAgentRuns(expanded);
      }
    }
  }, [events]);

  async function loadAgentStatus() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/agents/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load agent status", "error");
    } finally {
      setLoading(false);
    }
  }

  async function loadAgentRuns(agentName: string) {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/agents/${agentName}/runs?limit=5`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRuns((prev) => ({ ...prev, [agentName]: data.runs }));
      }
    } catch (e) {
      console.error(e);
    }
  }

  async function triggerRun(agentName: string) {
    const input = runInput[agentName]?.trim();
    if (!input) return;
    setRunningAgent(agentName);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/agents/${agentName}/run`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ input_text: input }),
      });
      if (res.ok) {
        setRunInput((prev) => ({ ...prev, [agentName]: "" }));
        loadAgentStatus();
        loadAgentRuns(agentName);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to trigger agent", "error");
    } finally {
      setRunningAgent(null);
    }
  }

  function toggleExpand(name: string) {
    if (expanded === name) {
      setExpanded(null);
    } else {
      setExpanded(name);
      loadAgentRuns(name);
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Agent Control" />
        <AgentsSkeleton />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Agent Control" />

      <PageTransition className="p-6 max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#00aaff" to="#ff00ff">Agent Fleet</GradientText>
            </h2>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {agents.length} agents online // {agents.filter((a) => a.status === "running").length} active
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-[#00ff88] animate-pulse" : "bg-[#6b7280]"
              }`}
            />
            <CyberLabel glow color={connected ? "#00ff88" : "#6b7280"}>
              {connected ? "Live Feed" : "Disconnected"}
            </CyberLabel>
          </div>
        </div>

        {/* Live Events */}
        {events.length > 0 && (
          <CyberCard variant="terminal" header="Live Activity">
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {events.slice(0, 8).map((ev, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-[11px] font-mono"
                >
                  {ev.status === "running" && (
                    <Loader2 className="w-3 h-3 text-[#ffcc00] animate-spin shrink-0" />
                  )}
                  {ev.status === "completed" && (
                    <CheckCircle2 className="w-3 h-3 text-[#00ff88] shrink-0" />
                  )}
                  {ev.status === "failed" && (
                    <XCircle className="w-3 h-3 text-[#ff3366] shrink-0" />
                  )}
                  <span
                    className="uppercase tracking-wider"
                    style={{ color: AGENT_ICONS[ev.agent]?.color || "#e0e0e0" }}
                  >
                    {ev.agent}
                  </span>
                  <span className="text-[#6b7280]">
                    {ev.status === "running"
                      ? "processing..."
                      : ev.status === "completed"
                      ? ev.output_summary
                        ? `done — ${ev.output_summary.slice(0, 60)}...`
                        : "done"
                      : `failed: ${ev.error || "unknown"}`}
                  </span>
                </div>
              ))}
            </div>
          </CyberCard>
        )}

        {/* Agent Grid */}
        <CyberGridBeam rows={3} cols={3} colorVariant="colorful" strength={0.6}>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 p-3">
          {agents.map((agent, idx) => {
            const config = AGENT_ICONS[agent.name] || {
              color: "#e0e0e0",
              description: "",
            };
            const isExpanded = expanded === agent.name;
            const isRunning =
              agent.status === "running" || runningAgent === agent.name;
            const agentRuns = runs[agent.name] || [];

            return (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                whileHover={{ x: 4 }}
                className="space-y-0"
              >
                <CyberCard hoverEffect>
                  {/* Agent Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 flex items-center justify-center border cyber-chamfer-sm"
                        style={{
                          borderColor: `${config.color}40`,
                          backgroundColor: `${config.color}10`,
                        }}
                      >
                        <Bot
                          className="w-5 h-5"
                          style={{ color: config.color }}
                          strokeWidth={1.5}
                        />
                      </div>
                      <div>
                        <h3
                          className="text-sm font-[var(--font-orbitron)] uppercase tracking-wider"
                          style={{ color: config.color }}
                        >
                          {agent.display_name}
                        </h3>
                        <p className="text-[10px] font-mono text-[#6b7280] mt-0.5">
                          {config.description}
                        </p>
                      </div>
                    </div>
                    <CyberBadge
                      variant={isRunning ? "tertiary" : "outline"}
                      className="text-[10px]"
                    >
                      {isRunning ? (
                        <span className="flex items-center gap-1">
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                          Running
                        </span>
                      ) : (
                        "Idle"
                      )}
                    </CyberBadge>
                  </div>

                  {/* Stats */}
                  <div className="flex items-center gap-4 mb-3">
                    <div className="flex items-center gap-1">
                      <Zap className="w-3 h-3 text-[#6b7280]" />
                      <CyberLabel>{agent.runs_today} runs today</CyberLabel>
                    </div>
                    {agent.last_run_at && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#6b7280]" />
                        <CyberLabel>
                          {new Date(agent.last_run_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </CyberLabel>
                      </div>
                    )}
                  </div>

                  {/* Last Output */}
                  {agent.last_output_summary && (
                    <div className="p-2 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm mb-3">
                      <p className="text-[11px] font-mono line-clamp-2">
                        <GlowText color="#6b7280" intensity="low">{agent.last_output_summary}</GlowText>
                      </p>
                    </div>
                  )}

                  {/* Run Input */}
                  <div className="flex gap-2">
                    <CyberInput
                      value={runInput[agent.name] || ""}
                      onChange={(e) =>
                        setRunInput((prev) => ({
                          ...prev,
                          [agent.name]: e.target.value,
                        }))
                      }
                      placeholder="Give a task..."
                      className="flex-1 text-xs"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") triggerRun(agent.name);
                      }}
                      disabled={isRunning}
                    />
                    <CyberButton
                      variant="default"
                      size="sm"
                      onClick={() => triggerRun(agent.name)}
                      disabled={
                        isRunning || !runInput[agent.name]?.trim()
                      }
                    >
                      {isRunning ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Send className="w-3.5 h-3.5" />
                      )}
                    </CyberButton>
                  </div>

                  {/* Expand/Collapse */}
                  <button
                    onClick={() => toggleExpand(agent.name)}
                    className="w-full mt-3 flex items-center justify-center gap-1 text-[10px] font-mono uppercase tracking-wider text-[#6b7280] hover:text-[#00ff88] transition-colors"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp className="w-3 h-3" />
                        Hide runs
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3 h-3" />
                        View runs
                      </>
                    )}
                  </button>
                </CyberCard>

                {/* Run History */}
                {isExpanded && (
                  <div className="mx-2 border-x border-b border-[#2a2a3a] bg-[#0a0a0f] p-3 space-y-2">
                    {agentRuns.length === 0 ? (
                      <p className="text-[11px] font-mono text-center py-3">
                        <GlowText color="#6b7280" intensity="low">No runs yet</GlowText>
                      </p>
                    ) : (
                      agentRuns.map((run) => (
                        <div
                          key={run.id}
                          className="p-2 border border-[#2a2a3a] cyber-chamfer-sm space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {run.status === "completed" && (
                                <CheckCircle2 className="w-3 h-3 text-[#00ff88]" />
                              )}
                              {run.status === "running" && (
                                <Loader2 className="w-3 h-3 text-[#ffcc00] animate-spin" />
                              )}
                              {run.status === "failed" && (
                                <XCircle className="w-3 h-3 text-[#ff3366]" />
                              )}
                              <CyberLabel>{run.trigger_type || "manual"}</CyberLabel>
                            </div>
                            <CyberLabel>
                              {new Date(run.created_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </CyberLabel>
                          </div>
                          {run.input_summary && (
                            <p className="text-[11px] font-mono line-clamp-1">
                              <GlowText color="#e0e0e0" intensity="low">&gt; {run.input_summary}</GlowText>
                            </p>
                          )}
                          {run.output_summary && (
                            <p className="text-[11px] font-mono line-clamp-2">
                              <GlowText color="#6b7280" intensity="low">{run.output_summary}</GlowText>
                            </p>
                          )}
                          {run.error_message && (
                            <p className="text-[11px] font-mono line-clamp-1">
                              <GlowText color="#ff3366" intensity="low">{run.error_message}</GlowText>
                            </p>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
        </CyberGridBeam>
      </PageTransition>
    </div>
  );
}
