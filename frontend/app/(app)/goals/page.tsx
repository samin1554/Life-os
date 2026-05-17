"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { CyberInput } from "@/components/cyber/input";
import { CyberSelect } from "@/components/cyber/select";
import type { Goal } from "@/types";
import { Plus, Target, Trash2, Loader2, X, TrendingUp, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { GoalsSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal, FadeIn } from "@/components/motion";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { GlowText, GradientText, CyberLabel, AnimatedHeading } from "@/components/typography";
import { useToast } from "@/components/toast";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

export default function GoalsPage() {
  const { getToken, isLoaded } = useAuth();
  const { addToast } = useToast();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newGoal, setNewGoal] = useState({ title: "", domain: "", why: "", timeframe: "" });
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoaded) loadGoals();
  }, [isLoaded]);

  async function loadGoals() {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/goals`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const json = await res.json();
        setGoals(json.goals);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load goals", "error");
    } finally {
      setLoading(false);
    }
  }

  async function createGoal(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!newGoal.title.trim()) {
      setFormError("Goal title is required");
      return;
    }
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/goals`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: newGoal.title.trim(),
            domain: newGoal.domain.trim() || null,
            timeframe: newGoal.timeframe.trim() || null,
            why: newGoal.why.trim() || null,
          }),
        }
      );
      if (res.ok) {
        setNewGoal({ title: "", domain: "", why: "", timeframe: "" });
        setShowCreate(false);
        addToast("Goal created", "success");
        loadGoals();
      } else {
        addToast("Failed to create goal", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to create goal", "error");
    }
  }

  async function deleteGoal(id: string) {
    try {
      const token = await getToken();
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/goals/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      loadGoals();
    } catch (e) {
      console.error(e);
      addToast("Failed to delete goal", "error");
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Goals" />
        <GoalsSkeleton />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Goals" />

      <PageTransition className="p-6 max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <AnimatedHeading>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#ffcc00" to="#ff00ff">Objectives</GradientText>
            </h2>
            </AnimatedHeading>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {goals.length} active targets
            </p>
          </div>
          <CyberButton variant="glitch" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            New Goal
          </CyberButton>
        </div>

        <AnimatePresence>
        {showCreate && (
          <motion.div
            key="create-form"
            initial={{ opacity: 0, scale: 0.95, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -8 }}
            transition={{ duration: 0.25, ease }}
          >
          <CyberCard variant="terminal" header="New Target">
            <form onSubmit={createGoal} className="space-y-4">
              {formError && (
                <div className="flex items-center gap-2 text-xs font-mono text-[#ff3366]">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {formError}
                </div>
              )}
              <CyberInput
                value={newGoal.title}
                onChange={(e) => setNewGoal({ ...newGoal, title: e.target.value })}
                placeholder="What do you want to achieve?"
                autoFocus
              />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <CyberSelect
                  value={newGoal.domain}
                  onChange={(value) => setNewGoal({ ...newGoal, domain: value })}
                  glowColor="#ffcc00"
                  options={[
                    { value: "", label: "Domain (optional)" },
                    { value: "health", label: "Health" },
                    { value: "career", label: "Career" },
                    { value: "work", label: "Work" },
                    { value: "finance", label: "Finance" },
                    { value: "learning", label: "Learning" },
                    { value: "personal", label: "Personal" },
                  ]}
                />
                <CyberSelect
                  value={newGoal.timeframe}
                  onChange={(value) => setNewGoal({ ...newGoal, timeframe: value })}
                  glowColor="#00d4ff"
                  options={[
                    { value: "", label: "Timeframe (optional)" },
                    { value: "this_week", label: "This Week" },
                    { value: "this_month", label: "This Month" },
                    { value: "this_year", label: "This Year" },
                    { value: "annual", label: "Annual" },
                    { value: "long_term", label: "Long Term" },
                  ]}
                />
                <CyberInput
                  value={newGoal.why}
                  onChange={(e) => setNewGoal({ ...newGoal, why: e.target.value })}
                  placeholder="Why? (optional)"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <CyberButton variant="ghost" size="sm" onClick={() => setShowCreate(false)}>
                  <X className="w-3.5 h-3.5 mr-1.5" />
                  Cancel
                </CyberButton>
                <CyberButton type="submit" variant="default" size="sm">
                  Create
                </CyberButton>
              </div>
            </form>
          </CyberCard>
          </motion.div>
        )}
        </AnimatePresence>

        <CyberGridBeam rows={2} cols={2} colorVariant="sunset" strength={0.7}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-3">
          {goals.map((goal, idx) => (
            <motion.div
              key={goal.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
              whileHover={{ x: 4 }}
            >
            <CyberCard hoverEffect>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-[#00ff88]" strokeWidth={1.5} />
                  <h3 className="text-sm font-mono font-semibold">
                    <GlowText color="#e0e0e0" intensity="low">{goal.title}</GlowText>
                  </h3>
                </div>
                <button
                  onClick={() => deleteGoal(goal.id)}
                  className="text-[#6b7280] hover:text-[#ff3366] transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="h-1.5 bg-[#2a2a3a] mb-3">
                <div
                  className="h-full bg-[#00ff88] transition-all"
                  style={{ width: `${goal.progress_pct}%` }}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {goal.domain && (
                    <CyberBadge variant="outline" className="text-[10px]">
                      {goal.domain}
                    </CyberBadge>
                  )}
                  <CyberLabel glow color="#00ff88">{goal.progress_pct}%</CyberLabel>
                </div>
                <div className="flex items-center gap-1 text-[#6b7280]">
                  <TrendingUp className="w-3 h-3" />
                  <CyberLabel>{goal.timeframe || "ongoing"}</CyberLabel>
                </div>
              </div>
            </CyberCard>
            </motion.div>
          ))}
        </div>
        </CyberGridBeam>

        {goals.length === 0 && (
          <FadeIn>
          <div className="text-center py-16">
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
              className="inline-block"
            >
              <Target className="w-12 h-12 text-[#6b7280] mx-auto mb-4" strokeWidth={1} />
            </motion.div>
            <p className="text-sm font-mono">
              <GlowText color="#6b7280" intensity="low">No active objectives</GlowText>
            </p>
            <p className="text-xs font-mono text-[#6b7280]/60 mt-1">
              Set a goal and the agent will track your progress
            </p>
          </div>
          </FadeIn>
        )}
      </PageTransition>
    </div>
  );
}
