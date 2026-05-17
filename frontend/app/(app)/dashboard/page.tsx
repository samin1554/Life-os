"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { ChaosTrigger } from "@/components/dashboard/chaos-trigger";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import type { DashboardData } from "@/types";
import {
  Activity,
  Target,
  CheckSquare,
  ChevronRight,
  Loader2,
  Bot,
  Zap,
} from "lucide-react";
import { motion } from "framer-motion";
import { PageTransition, StaggerList, StaggerItem, ScrollReveal, FadeIn } from "@/components/motion";
import { DashboardSkeleton } from "@/components/cyber/skeleton";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { GlowText, GradientText, CyberLabel, AnimatedHeading } from "@/components/typography";
import { useToast } from "@/components/toast";
import { AgentHoverCard } from "@/components/agent/agent-hover-card";
import { AGENT_DESCRIPTIONS, AGENT_COLORS } from "@/lib/agents";
import { ApiKeyDisclaimer } from "@/components/api-key-disclaimer";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

export default function DashboardPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { addToast } = useToast();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.push("/");
      return;
    }
    loadDashboard();
  }, [isLoaded, isSignedIn]);

  async function loadDashboard() {
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/dashboard`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Failed to load dashboard", e);
      addToast("Failed to load dashboard", "error");
    } finally {
      setLoading(false);
    }
  }

  if (!isLoaded || loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Command Center" />
        <DashboardSkeleton />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0a0f]">
        <p className="text-[#6b7280] font-mono text-sm">Failed to load dashboard data</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] cyber-grid-bg">
      <TopBar title="Dashboard" />

      <PageTransition className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div
          className="flex items-center justify-between"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease }}
        >
          <div>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#00ff88" to="#00d4ff">Today</GradientText>
            </h2>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {data.today.date} // System Status: Online
            </p>
          </div>
          {!data.onboarding_done && (
            <CyberButton
              variant="glitch"
              size="sm"
              onClick={() => router.push("/onboarding")}
            >
              Complete Onboarding
            </CyberButton>
          )}
        </motion.div>

        {/* API Key Disclaimer */}
        {!data.has_api_keys && <ApiKeyDisclaimer />}

        {/* Stats Grid */}
        <StatsGrid
          streak={data.streak}
          completedThisWeek={data.completed_this_week}
          pendingTasks={data.today.pending_tasks}
          goalsCount={data.goals.length}
        />

        {/* Agent Fleet Strip */}
        {data.agents && data.agents.length > 0 && (
          <ScrollReveal delay={0.15}>
          <CyberCard header="Agent Fleet" hoverEffect>
            <CyberGridBeam rows={2} cols={7} colorVariant="colorful">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-3 p-3">
              {data.agents.map((agent, idx) => {
                const color = AGENT_COLORS[agent.name] || "#e0e0e0";
                return (
                  <AgentHoverCard
                    key={agent.name}
                    agent={agent}
                    color={color}
                    description={AGENT_DESCRIPTIONS[agent.name]}
                    delay={0.04 * idx}
                  >
                    <motion.button
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                      whileHover={{ y: -2, boxShadow: `0 4px 15px ${color}20` }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => router.push("/agents")}
                      className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm
                        hover:border-opacity-60 transition-colors text-center group w-full"
                      style={{ ["--agent-color" as string]: color }}
                    >
                      <Bot
                        className="w-5 h-5 mx-auto mb-2 transition-colors"
                        style={{ color }}
                        strokeWidth={1.5}
                      />
                      <p
                        className="text-[10px] font-[var(--font-orbitron)] uppercase tracking-wider truncate"
                        style={{ color }}
                      >
                        {agent.display_name.replace(" Agent", "")}
                      </p>
                      <div className="flex items-center justify-center gap-1 mt-1.5">
                        {agent.status === "running" ? (
                          <span className="flex items-center gap-1">
                            <Loader2
                              className="w-2.5 h-2.5 animate-spin"
                              style={{ color }}
                            />
                            <span className="text-[9px] font-mono text-[#6b7280]">
                              Active
                            </span>
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <Zap className="w-2.5 h-2.5 text-[#6b7280]" />
                            <span className="text-[9px] font-mono text-[#6b7280]">
                              {agent.runs_today}
                            </span>
                          </span>
                        )}
                      </div>
                    </motion.button>
                  </AgentHoverCard>
                );
              })}
            </div>
            </CyberGridBeam>
          </CyberCard>
          </ScrollReveal>
        )}

        {/* Main Grid */}
        <ScrollReveal delay={0.2}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tasks Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Today's Tasks */}
            <CyberCard header="Today's Objectives" hoverEffect>
              {data.tasks.length === 0 ? (
                <FadeIn>
                <div className="text-center py-8">
                  <motion.div
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
                    className="inline-block"
                  >
                    <CheckSquare className="w-8 h-8 text-[#6b7280] mx-auto mb-3" strokeWidth={1.5} />
                  </motion.div>
                  <p className="text-sm font-mono">
                    <GlowText color="#6b7280" intensity="low">No pending tasks</GlowText>
                  </p>
                  <CyberButton
                    variant="outline"
                    size="sm"
                    className="mt-4"
                    onClick={() => router.push("/tasks")}
                  >
                    Create Task
                  </CyberButton>
                </div>
                </FadeIn>
              ) : (
                <div className="space-y-3">
                  {data.tasks.map((task, idx) => (
                    <motion.div
                      key={task.id}
                      initial={{ opacity: 0, x: -16 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.35, ease, delay: 0.05 * idx }}
                      whileHover={{ x: 4, boxShadow: "0 2px 12px rgba(0, 255, 136, 0.08)" }}
                      className="flex items-center gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm
                        hover:border-[#00ff88]/40 transition-colors cursor-pointer"
                      onClick={() => router.push("/tasks")}
                    >
                      <div
                        className={`w-2 h-2 shrink-0 ${
                          task.priority >= 4
                            ? "bg-[#ff3366]"
                            : task.priority === 3
                            ? "bg-[#ffcc00]"
                            : "bg-[#00ff88]"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-mono truncate">
                    <GlowText color="#e0e0e0" intensity="low">{task.title}</GlowText>
                  </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {task.category && (
                            <CyberBadge variant="outline" className="text-[10px]">
                              {task.category}
                            </CyberBadge>
                          )}
                          {task.times_deferred > 0 && (
                            <span className="text-[10px] font-mono text-[#ff3366]">
                              Deferred {task.times_deferred}x
                            </span>
                          )}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-[#6b7280] shrink-0" />
                    </motion.div>
                  ))}
                </div>
              )}
            </CyberCard>

            {/* Chaos Trigger */}
            <ChaosTrigger
              onTrigger={() => router.push("/chat")}
              disabled={false}
            />
          </div>

          {/* Sidebar Column */}
          <div className="space-y-6">
            {/* Energy Level */}
            <CyberCard variant="holographic" header="Vitals">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <CyberLabel glow color="#00d4ff">Energy</CyberLabel>
                  <CyberBadge
                    variant={
                      data.today.energy_level === "high"
                        ? "default"
                        : data.today.energy_level === "medium"
                        ? "tertiary"
                        : "destructive"
                    }
                  >
                    {data.today.energy_level}
                  </CyberBadge>
                </div>

                {data.averages.mood && (
                  <div className="flex items-center justify-between">
                    <CyberLabel glow color="#00ff88">7d Mood</CyberLabel>
                    <span className="text-sm font-mono text-[#00ff88]">
                      {data.averages.mood}/5
                    </span>
                  </div>
                )}
                {data.averages.energy && (
                  <div className="flex items-center justify-between">
                    <CyberLabel glow color="#00d4ff">7d Energy</CyberLabel>
                    <span className="text-sm font-mono text-[#00d4ff]">
                      {data.averages.energy}/5
                    </span>
                  </div>
                )}
                {data.averages.sleep && (
                  <div className="flex items-center justify-between">
                    <CyberLabel glow color="#ff00ff">7d Sleep</CyberLabel>
                    <span className="text-sm font-mono text-[#ff00ff]">
                      {data.averages.sleep}h
                    </span>
                  </div>
                )}

                <CyberButton
                  variant="outline"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => router.push("/checkin")}
                >
                  <Activity className="w-3.5 h-3.5 mr-2" />
                  Log Check-in
                </CyberButton>
              </div>
            </CyberCard>

            {/* Goals */}
            <CyberCard header="Active Goals" hoverEffect>
              {data.goals.length === 0 ? (
                <p className="text-sm font-mono text-[#6b7280] text-center py-4">
                  No active goals
                </p>
              ) : (
                <div className="space-y-3">
                  {data.goals.map((goal) => (
                    <div key={goal.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-mono truncate">
                    <GlowText color="#e0e0e0" intensity="low">{goal.title}</GlowText>
                  </p>
                        {goal.drift_alert && (
                          <CyberBadge variant="destructive" className="text-[10px]">
                            Drift
                          </CyberBadge>
                        )}
                      </div>
                      <div className="h-1 bg-[#2a2a3a] overflow-hidden">
                        <motion.div
                          className="h-full bg-[#00ff88]"
                          initial={{ width: 0 }}
                          animate={{ width: `${goal.progress_pct}%` }}
                          transition={{ duration: 0.8, ease, delay: 0.2 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <CyberButton
                variant="ghost"
                size="sm"
                className="w-full mt-3"
                onClick={() => router.push("/goals")}
              >
                <Target className="w-3.5 h-3.5 mr-2" />
                Manage Goals
              </CyberButton>
            </CyberCard>
          </div>
        </div>
        </ScrollReveal>
      </PageTransition>
    </div>
  );
}
