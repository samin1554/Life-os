"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { Sun, Sunrise, Moon, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const CHECKIN_TYPES = [
  { id: "morning" as const, label: "Morning", icon: Sunrise, color: "text-[#ffcc00]" },
  { id: "midday" as const, label: "Midday", icon: Sun, color: "text-[#00d4ff]" },
  { id: "evening" as const, label: "Evening", icon: Moon, color: "text-[#ff00ff]" },
];

export default function CheckinPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [activeType, setActiveType] = useState<"morning" | "midday" | "evening">("morning");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [form, setForm] = useState({
    mood_score: 3,
    energy_score: 3,
    stress_score: 3,
    focus_score: 3,
    sleep_hours: 7,
    sleep_quality: 3,
    exercised: false,
    notes: "",
    wins: "",
    struggles: "",
    tasks_planned: 0,
    tasks_completed: 0,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const token = await getToken();
      const body = {
        checkin_type: activeType,
        checkin_date: new Date().toISOString().split("T")[0],
        ...form,
        wins: form.wins ? form.wins.split(",").map((s) => s.trim()) : undefined,
        struggles: form.struggles ? form.struggles.split(",").map((s) => s.trim()) : undefined,
      };
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/checkins`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        }
      );
      if (res.ok) {
        setSaved(true);
        addToast("Check-in saved", "success");
        setTimeout(() => setSaved(false), 3000);
      } else {
        addToast("Failed to save check-in", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to save check-in", "error");
    } finally {
      setSaving(false);
    }
  }

  function ScoreInput({ label, value, onChange, max = 5 }: { label: string; value: number; onChange: (v: number) => void; max?: number }) {
    return (
      <div className="space-y-2">
        <CyberLabel glow color="#00ff88">{label}</CyberLabel>
        <div className="flex gap-2">
          {Array.from({ length: max }, (_, i) => i + 1).map((n) => (
            <motion.button
              key={n}
              type="button"
              onClick={() => onChange(n)}
              whileTap={{ scale: 0.85 }}
              whileHover={{ y: -1 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
              className={`w-8 h-8 font-mono text-xs border transition-colors
                ${value === n ? "bg-[#00ff88] text-[#0a0a0f] border-[#00ff88]" : "bg-[#0a0a0f] text-[#6b7280] border-[#2a2a3a] hover:border-[#00ff88]/50"}`}
            >
              {n}
            </motion.button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Check-in Log" />

      <PageTransition className="p-6 max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
            <GradientText from="#00d4ff" to="#ff00ff">Vital Signs</GradientText>
          </h2>
          <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
            Log your current state // Data feeds pattern learning
          </p>
        </div>

        {/* Type Selector */}
        <div className="flex gap-3">
          {CHECKIN_TYPES.map((type, idx) => {
            const Icon = type.icon;
            const isActive = activeType === type.id;
            return (
              <motion.button
                key={type.id}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                whileHover={{ x: 4 }}
                onClick={() => setActiveType(type.id)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 border font-mono text-xs uppercase tracking-wider transition-all
                  ${isActive ? `bg-[#00ff88]/10 border-[#00ff88] text-[#00ff88]` : "bg-[#12121a] border-[#2a2a3a] text-[#6b7280] hover:border-[#00ff88]/30"}`}
              >
                <Icon className={`w-4 h-4 ${type.color}`} strokeWidth={1.5} />
                {type.label}
              </motion.button>
            );
          })}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Core Metrics */}
          <CyberCard header="Core Metrics" hoverEffect>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <ScoreInput label="Mood" value={form.mood_score} onChange={(v) => setForm({ ...form, mood_score: v })} />
              <ScoreInput label="Energy" value={form.energy_score} onChange={(v) => setForm({ ...form, energy_score: v })} />
              <ScoreInput label="Stress" value={form.stress_score} onChange={(v) => setForm({ ...form, stress_score: v })} />
              <ScoreInput label="Focus" value={form.focus_score} onChange={(v) => setForm({ ...form, focus_score: v })} />
            </div>
          </CyberCard>

          {/* Physical */}
          <CyberCard header="Physical" hoverEffect>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Sleep Hours</label>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  max="24"
                  value={form.sleep_hours}
                  onChange={(e) => setForm({ ...form, sleep_hours: parseFloat(e.target.value) || 0 })}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#00ff88] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#00ff88] focus:outline-none"
                />
              </div>
              <ScoreInput label="Sleep Quality" value={form.sleep_quality} onChange={(v) => setForm({ ...form, sleep_quality: v })} />
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Exercised</label>
                <div className="flex gap-3">
                  <motion.button
                    type="button"
                    onClick={() => setForm({ ...form, exercised: true })}
                    whileTap={{ scale: 0.92 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    className={`px-4 py-2 font-mono text-xs uppercase border transition-colors
                      ${form.exercised ? "bg-[#00ff88] text-[#0a0a0f] border-[#00ff88]" : "bg-[#0a0a0f] text-[#6b7280] border-[#2a2a3a]"}`}
                  >
                    Yes
                  </motion.button>
                  <motion.button
                    type="button"
                    onClick={() => setForm({ ...form, exercised: false })}
                    whileTap={{ scale: 0.92 }}
                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    className={`px-4 py-2 font-mono text-xs uppercase border transition-colors
                      ${!form.exercised ? "bg-[#ff3366] text-[#0a0a0f] border-[#ff3366]" : "bg-[#0a0a0f] text-[#6b7280] border-[#2a2a3a]"}`}
                  >
                    No
                  </motion.button>
                </div>
              </div>
            </div>
          </CyberCard>

          {/* Context */}
          <CyberCard header="Context" hoverEffect>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="How are you feeling?"
                  rows={3}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#e0e0e0] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#00ff88] focus:outline-none placeholder:text-[#6b7280]/50 resize-none"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Wins (comma separated)</label>
                  <input
                    value={form.wins}
                    onChange={(e) => setForm({ ...form, wins: e.target.value })}
                    placeholder="Finished report, called mom..."
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#00ff88] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#00ff88] focus:outline-none placeholder:text-[#6b7280]/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Struggles (comma separated)</label>
                  <input
                    value={form.struggles}
                    onChange={(e) => setForm({ ...form, struggles: e.target.value })}
                    placeholder="Procrastinated on emails..."
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#ff3366] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#ff3366] focus:outline-none placeholder:text-[#6b7280]/50"
                  />
                </div>
              </div>
            </div>
          </CyberCard>

          {/* Evening-only fields */}
          {activeType === "evening" && (
            <CyberCard header="Evening Review" hoverEffect>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Tasks Planned</label>
                  <input
                    type="number"
                    value={form.tasks_planned}
                    onChange={(e) => setForm({ ...form, tasks_planned: parseInt(e.target.value) || 0 })}
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#e0e0e0] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#00ff88] focus:outline-none"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-mono uppercase tracking-wider text-[#6b7280]">Tasks Completed</label>
                  <input
                    type="number"
                    value={form.tasks_completed}
                    onChange={(e) => setForm({ ...form, tasks_completed: parseInt(e.target.value) || 0 })}
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] text-[#e0e0e0] font-mono text-sm px-3 py-2 cyber-chamfer-sm focus:border-[#00ff88] focus:outline-none"
                  />
                </div>
              </div>
            </CyberCard>
          )}

          <div className="flex items-center gap-4">
            <CyberButton type="submit" variant="glitch" disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Log Check-in"}
            </CyberButton>
            {saved && (
              <CyberBadge variant="default">Data Logged</CyberBadge>
            )}
          </div>
        </form>
      </PageTransition>
    </div>
  );
}
