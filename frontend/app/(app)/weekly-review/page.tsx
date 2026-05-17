"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { Loader2, RefreshCw, Activity, CheckSquare, Moon, Zap, Dumbbell, Smile } from "lucide-react";
import { motion } from "framer-motion";
import { WeeklyReviewSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { GlowText, GradientText, CyberLabel, ChatMessageText, AnimatedHeading, CountUpNumber } from "@/components/typography";
import { useToast } from "@/components/toast";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface WeeklyStats {
  checkins: number;
  tasks_completed: number;
  tasks_pending: number;
  avg_mood: number | null;
  avg_energy: number | null;
  avg_sleep: number | null;
  exercise_days: number;
}

interface WeeklyReviewData {
  review: string;
  stats: WeeklyStats;
  generated_at: string;
}

export default function WeeklyReviewPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { addToast } = useToast();
  const router = useRouter();
  const [data, setData] = useState<WeeklyReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.push("/");
      return;
    }
    loadReview();
  }, [isLoaded, isSignedIn]);

  async function loadReview() {
    try {
      setLoading(true);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/dashboard/weekly-review`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Failed to load weekly review", e);
      addToast("Failed to load weekly review", "error");
    } finally {
      setLoading(false);
    }
  }

  async function regenerate() {
    try {
      setGenerating(true);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/dashboard/weekly-review`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
        addToast("Weekly review generated", "success");
      } else {
        addToast("Failed to generate review", "error");
      }
    } catch (e) {
      console.error("Failed to generate review", e);
      addToast("Failed to generate review", "error");
    } finally {
      setGenerating(false);
    }
  }

  if (!isLoaded || loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Weekly Review" />
        <WeeklyReviewSkeleton />
      </div>
    );
  }

  const stats = data?.stats;

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Weekly Review" />

      <PageTransition className="p-6 max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <AnimatedHeading>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#ffcc00" to="#ff00ff">Weekly Review</GradientText>
            </h2>
          </AnimatedHeading>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {data?.generated_at ? `Generated: ${data.generated_at}` : "Your week in review"}
            </p>
          </div>
          <CyberButton variant="outline" size="sm" onClick={regenerate} disabled={generating}>
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 mr-2" />
            )}
            Regenerate
          </CyberButton>
        </div>

        {/* Stats Grid */}
        {stats && (
          <CyberGridBeam rows={2} cols={6} colorVariant="ocean">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-3">
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 0 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <Activity className="w-4 h-4 text-[#00d4ff] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#00d4ff" intensity="medium"><CountUpNumber value={stats.checkins} /></GlowText></p>
              <CyberLabel glow color="#00d4ff">Check-ins</CyberLabel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 1 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <CheckSquare className="w-4 h-4 text-[#00ff88] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#00ff88" intensity="medium"><CountUpNumber value={stats.tasks_completed} /></GlowText></p>
              <CyberLabel glow color="#00ff88">Completed</CyberLabel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 2 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <CheckSquare className="w-4 h-4 text-[#ffcc00] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#ffcc00" intensity="medium"><CountUpNumber value={stats.tasks_pending} /></GlowText></p>
              <CyberLabel glow color="#ffcc00">Pending</CyberLabel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 3 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <Smile className="w-4 h-4 text-[#ff00ff] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#ff00ff" intensity="medium">{stats.avg_mood != null ? <CountUpNumber value={stats.avg_mood} /> : "—"}</GlowText></p>
              <CyberLabel glow color="#ff00ff">Avg Mood</CyberLabel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 4 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <Zap className="w-4 h-4 text-[#ff8800] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#ff8800" intensity="medium">{stats.avg_energy != null ? <CountUpNumber value={stats.avg_energy} /> : "—"}</GlowText></p>
              <CyberLabel glow color="#ff8800">Avg Energy</CyberLabel>
            </motion.div>
            <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.35, ease, delay: 0.04 * 5 }} whileHover={{ x: 4 }} className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm text-center">
              <Dumbbell className="w-4 h-4 text-[#8b5cf6] mx-auto mb-1" />
              <p className="text-lg font-mono"><GlowText color="#8b5cf6" intensity="medium"><CountUpNumber value={stats.exercise_days} /></GlowText></p>
              <CyberLabel glow color="#8b5cf6">Exercise</CyberLabel>
            </motion.div>
          </div>
          </CyberGridBeam>
        )}

        {/* Review Text */}
        <CyberCard header="This Week's Review" hoverEffect>
          {data?.review ? (
            <ChatMessageText content={data.review} role="assistant" />
          ) : (
            <div className="text-center py-12">
              <Moon className="w-8 h-8 text-[#6b7280] mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-sm font-mono">
                <GlowText color="#6b7280" intensity="low">No review generated yet</GlowText>
              </p>
              <CyberButton variant="outline" size="sm" className="mt-4" onClick={regenerate} disabled={generating}>
                Generate Review
              </CyberButton>
            </div>
          )}
        </CyberCard>
      </PageTransition>
    </div>
  );
}
