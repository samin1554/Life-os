"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import {
  Loader2,
  TrendingUp,
  Activity,
  Zap,
  Brain,
  Target,
  ListChecks,
  Clock,
  Flame,
  Moon,
  Dumbbell,
  AlertTriangle,
} from "lucide-react";

import { InsightsSkeleton } from "@/components/cyber/skeleton";
import { motion } from "framer-motion";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { CyberGridBeam } from "@/components/cyber/grid-beam-wrapper";
import { ResponsiveLine } from "@nivo/line";
import { GlowText, GradientText, AnimatedHeading, CountUpNumber } from "@/components/typography";
import { useToast } from "@/components/toast";
import { ResponsiveBar } from "@nivo/bar";
import { ResponsivePie } from "@nivo/pie";
import { ResponsiveRadialBar } from "@nivo/radial-bar";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const CYBER_COLORS = {
  mood: "#ff00ff",
  energy: "#00ff88",
  sleep: "#00d4ff",
  completed: "#00ff88",
  pending: "#ff8800",
  grid: "#1a1a2e",
  text: "#6b7280",
  cardBg: "#12121a",
  darkBg: "#0a0a0f",
};

const PIE_COLORS = ["#00ff88", "#00d4ff", "#ff00ff", "#ffcc00", "#ff8800", "#8b5cf6", "#ff3366", "#00aaff"];

interface VitalsPoint {
  date: string;
  mood: number | null;
  energy: number | null;
  sleep: number | null;
  exercise: boolean;
}

interface TaskVelocityPoint {
  date: string;
  created: number;
  completed: number;
}

interface CategoryItem {
  category: string;
  count: number;
}

interface GoalItem {
  id: string;
  title: string;
  domain: string | null;
  progress_pct: number;
}

interface PatternInsights {
  time_estimation_bias?: number;
  avg_completion_rate_7d?: number;
  top_avoidance_categories?: string[];
  avg_deferral_count?: number;
  mood_sleep_correlation?: number;
  mood_exercise_correlation?: number;
  checkin_streak?: number;
  longest_checkin_streak?: number;
  last_computed_at?: string;
}

interface InsightsData {
  vitals_series: VitalsPoint[];
  task_velocity: TaskVelocityPoint[];
  category_breakdown: CategoryItem[];
  goal_progress: GoalItem[];
  pattern_insights: PatternInsights;
  weekly_averages: {
    mood: number | null;
    energy: number | null;
    sleep: number | null;
  };
}

const nivoTheme = {
  background: "transparent",
  axis: {
    domain: { line: { stroke: CYBER_COLORS.grid } },
    ticks: {
      line: { stroke: CYBER_COLORS.grid },
      text: { fill: "#8892a4", fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
    },
    legend: { text: { fill: "#8892a4", fontSize: 11, fontFamily: "JetBrains Mono, monospace" } },
  },
  grid: { line: { stroke: "#1a1a2e", strokeDasharray: "2 6" } },
  legends: { text: { fill: "#8892a4", fontSize: 10, fontFamily: "JetBrains Mono, monospace" } },
  labels: { text: { fill: "#e0e0e0", fontSize: 10, fontFamily: "JetBrains Mono, monospace" } },
  tooltip: {
    container: {
      background: "#12121a",
      border: "1px solid #2a2a3a",
      color: "#e0e0e0",
      fontFamily: "JetBrains Mono, monospace",
      fontSize: "12px",
      borderRadius: "4px",
      boxShadow: "0 4px 20px rgba(0, 0, 0, 0.5)",
    },
  },
  crosshair: {
    line: {
      stroke: "#00ff88",
      strokeWidth: 1,
      strokeOpacity: 0.5,
      strokeDasharray: "4 4",
    },
  },
};

function StatCard({
  label,
  value,
  suffix,
  icon: Icon,
  color,
  subtext,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  icon: React.ElementType;
  color: string;
  subtext?: string;
}) {
  return (
    <div className="group relative overflow-hidden bg-[#12121a] border border-[#2a2a3a] cyber-chamfer-sm hover:border-opacity-60 transition-all duration-300"
      style={{ borderColor: `${color}30` }}
    >
      {/* Glow background */}
      <div
        className="absolute inset-0 opacity-[0.03] group-hover:opacity-[0.06] transition-opacity duration-500"
        style={{ background: `radial-gradient(circle at 30% 50%, ${color}, transparent 70%)` }}
      />
      <div className="relative p-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] font-mono uppercase tracking-[0.15em] text-[#6b7280]">{label}</p>
          <div
            className="w-8 h-8 flex items-center justify-center rounded-sm"
            style={{ backgroundColor: `${color}15` }}
          >
            <Icon className="w-4 h-4" style={{ color }} strokeWidth={1.5} />
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-3xl font-mono font-bold" style={{ color, textShadow: `0 0 20px ${color}40` }}>
            {value}
          </span>
          {suffix && <span className="text-xs font-mono text-[#6b7280]">{suffix}</span>}
        </div>
        {subtext && <p className="text-[10px] font-mono text-[#6b7280] mt-2">{subtext}</p>}
      </div>
    </div>
  );
}

function ChartHeader({ title, icon: Icon, color = "#6b7280" }: { title: string; icon: React.ElementType; color?: string }) {
  return (
    <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-[#2a2a3a]">
      <div className="w-6 h-6 flex items-center justify-center rounded-sm" style={{ backgroundColor: `${color}15` }}>
        <Icon className="w-3.5 h-3.5" style={{ color }} strokeWidth={1.5} />
      </div>
      <h3 className="text-xs font-mono uppercase tracking-[0.12em] text-[#8892a4]">{title}</h3>
    </div>
  );
}

function PatternCard({
  label,
  value,
  color,
  icon: Icon,
  description,
}: {
  label: string;
  value: string;
  color: string;
  icon: React.ElementType;
  description?: string;
}) {
  return (
    <div className="group relative overflow-hidden p-4 bg-[#0d0d14] border border-[#1a1a2e] cyber-chamfer-sm hover:border-[#2a2a3a] transition-all duration-300">
      <div
        className="absolute inset-0 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity"
        style={{ background: `radial-gradient(circle at 50% 0%, ${color}, transparent 60%)` }}
      />
      <div className="relative">
        <div className="flex items-center gap-2 mb-2">
          <Icon className="w-3.5 h-3.5" style={{ color: `${color}90` }} strokeWidth={1.5} />
          <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-[#6b7280]">{label}</p>
        </div>
        <p className="text-lg font-mono font-semibold" style={{ color, textShadow: `0 0 15px ${color}30` }}>
          {value}
        </p>
        {description && <p className="text-[10px] font-mono text-[#4a4a5a] mt-1.5">{description}</p>}
      </div>
    </div>
  );
}

export default function InsightsPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { addToast } = useToast();
  const router = useRouter();
  const [data, setData] = useState<InsightsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.push("/");
      return;
    }
    loadInsights();
  }, [isLoaded, isSignedIn]);

  async function loadInsights() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/dashboard/insights`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error("Failed to load insights", e);
      addToast("Failed to load insights", "error");
    } finally {
      setLoading(false);
    }
  }

  if (!isLoaded || loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Insights" />
        <InsightsSkeleton />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0a0f]">
        <p className="text-[#6b7280] font-mono text-sm">Failed to load insights data</p>
      </div>
    );
  }

  const vitalsData = [
    {
      id: "Mood",
      color: CYBER_COLORS.mood,
      data: data.vitals_series.map((d) => ({ x: d.date.slice(5), y: d.mood })).filter((d) => d.y !== null),
    },
    {
      id: "Energy",
      color: CYBER_COLORS.energy,
      data: data.vitals_series.map((d) => ({ x: d.date.slice(5), y: d.energy })).filter((d) => d.y !== null),
    },
    {
      id: "Sleep",
      color: CYBER_COLORS.sleep,
      data: data.vitals_series.map((d) => ({ x: d.date.slice(5), y: d.sleep })).filter((d) => d.y !== null),
    },
  ];

  const velocityData = data.task_velocity.map((d) => ({
    date: d.date.slice(5),
    completed: d.completed,
    pending: Math.max(0, d.created - d.completed),
  }));

  const pieData = data.category_breakdown.map((c, i) => ({
    id: c.category,
    label: c.category,
    value: c.count,
    color: PIE_COLORS[i % PIE_COLORS.length],
  }));

  const totalTasks = pieData.reduce((sum, p) => sum + p.value, 0);

  const radialData =
    data.goal_progress.length > 0
      ? data.goal_progress.map((g) => ({
          id: g.title.length > 18 ? g.title.slice(0, 18) + "..." : g.title,
          data: [{ x: g.title, y: g.progress_pct }],
        }))
      : [];

  const patterns = data.pattern_insights;

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Insights" />

      <PageTransition className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Page Header */}
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, ease, delay: 0 }}
        >
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 flex items-center justify-center bg-[#00ff88]/10 rounded-sm">
              <Brain className="w-4 h-4 text-[#00ff88]" strokeWidth={1.5} />
            </div>
            <AnimatedHeading>
              <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
                <GradientText from="#ff00ff" to="#00d4ff">Life Analytics</GradientText>
              </h2>
            </AnimatedHeading>
          </div>
          <p className="text-xs font-mono text-[#4a4a5a] mt-2 uppercase tracking-[0.2em] ml-11">
            Patterns &middot; Trends &middot; Correlations
          </p>
        </motion.div>

        {/* Weekly Averages — Stat Cards */}
        <CyberGridBeam rows={2} cols={3} colorVariant="ocean">
        <motion.div
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-3"
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35, ease, delay: 0.04 * 1 }}
        >
          <StatCard
            label="7-Day Mood"
            value={data.weekly_averages.mood?.toFixed(1) ?? "—"}
            suffix="/5"
            icon={Activity}
            color="#ff00ff"
            subtext="Average daily mood score"
          />
          <StatCard
            label="7-Day Energy"
            value={data.weekly_averages.energy?.toFixed(1) ?? "—"}
            suffix="/5"
            icon={Zap}
            color="#00ff88"
            subtext="Average daily energy level"
          />
          <StatCard
            label="7-Day Sleep"
            value={data.weekly_averages.sleep?.toFixed(1) ?? "—"}
            suffix="hrs"
            icon={Moon}
            color="#00d4ff"
            subtext="Average nightly sleep"
          />
        </motion.div>
        </CyberGridBeam>

        {/* Charts Grid */}
        <CyberGridBeam rows={2} cols={2} colorVariant="colorful" strength={0.5}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-3">
          {/* Vitals Timeline */}
          <motion.div
            className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer overflow-hidden hover:border-[#2a2a4a] transition-all duration-300"
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease, delay: 0.04 * 2 }}
          >
            <ChartHeader title="Vitals Timeline (30d)" icon={Activity} color="#ff00ff" />
            <div className="p-4">
              <div className="h-[300px]">
                {data.vitals_series.length > 0 ? (
                  <ResponsiveLine
                    data={vitalsData}
                    theme={nivoTheme}
                    margin={{ top: 20, right: 20, bottom: 50, left: 40 }}
                    xScale={{ type: "point" }}
                    yScale={{ type: "linear", min: 0, max: "auto", stacked: false }}
                    curve="catmullRom"
                    axisTop={null}
                    axisRight={null}
                    axisBottom={{ tickRotation: -45, tickSize: 0, tickPadding: 12 }}
                    axisLeft={{ tickValues: [1, 2, 3, 4, 5], tickSize: 0, tickPadding: 12 }}
                    colors={[CYBER_COLORS.mood, CYBER_COLORS.energy, CYBER_COLORS.sleep]}
                    lineWidth={2.5}
                    enablePoints={false}
                    layers={[
                      "grid",
                      "markers",
                      "axes",
                      "areas",
                      "crosshair",
                      "lines",
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      (props: any) => {
                        const points = props.points || [];
                        return (
                          <g>
                            {points.map((point: any, i: number) => (
                              <g key={i} transform={`translate(${point.x}, ${point.y})`}>
                                <circle r={8} fill={point.color} opacity={0.15} />
                                <circle r={5} fill={point.color} />
                                <circle r={2} fill="#12121a" />
                              </g>
                            ))}
                          </g>
                        );
                      },
                      "slices",
                      "mesh",
                      "legends",
                    ]}
                    enableArea={true}
                    areaOpacity={0.08}
                    areaBlendMode="screen"
                    enableGridX={false}
                    enableCrosshair={true}
                    useMesh={true}
                    legends={[
                      {
                        anchor: "top-right",
                        direction: "row",
                        translateY: -15,
                        itemWidth: 65,
                        itemHeight: 12,
                        symbolSize: 8,
                        symbolShape: "circle",
                      },
                    ]}
                  />
                ) : (
                  <EmptyState message="No check-in data yet" icon={Activity} />
                )}
              </div>
            </div>
          </motion.div>

          {/* Task Velocity */}
          <motion.div
            className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer overflow-hidden hover:border-[#2a2a4a] transition-all duration-300"
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease, delay: 0.04 * 3 }}
          >
            <ChartHeader title="Task Velocity" icon={ListChecks} color="#00ff88" />
            <div className="p-4">
              <div className="h-[300px]">
                {velocityData.length > 0 ? (
                  <ResponsiveBar
                    data={velocityData}
                    theme={nivoTheme}
                    keys={["completed", "pending"]}
                    indexBy="date"
                    margin={{ top: 20, right: 20, bottom: 50, left: 40 }}
                    padding={0.35}
                    groupMode="stacked"
                    colors={[CYBER_COLORS.completed, CYBER_COLORS.pending]}
                    borderRadius={2}
                    borderWidth={0}
                    axisBottom={{ tickRotation: -45, tickSize: 0, tickPadding: 12 }}
                    axisLeft={{ tickSize: 0, tickPadding: 12 }}
                    enableGridX={false}
                    enableLabel={false}
                    legends={[
                      {
                        anchor: "top-right",
                        direction: "row",
                        translateY: -15,
                        itemWidth: 80,
                        itemHeight: 12,
                        symbolSize: 8,
                        symbolShape: "square",
                        dataFrom: "keys" as const,
                      },
                    ]}
                  />
                ) : (
                  <EmptyState message="No task data yet" icon={ListChecks} />
                )}
              </div>
            </div>
          </motion.div>

          {/* Task Categories — Pie */}
          <motion.div
            className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer overflow-hidden hover:border-[#2a2a4a] transition-all duration-300"
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease, delay: 0.04 * 4 }}
          >
            <ChartHeader title="Task Categories" icon={Target} color="#00d4ff" />
            <div className="p-4">
              <div className="h-[300px] relative">
                {pieData.length > 0 ? (
                  <>
                    {/* Center label */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                      <div className="text-center">
                        <p className="text-2xl font-mono font-bold text-[#e0e0e0]"><CountUpNumber value={totalTasks} /></p>
                        <p className="text-[9px] font-mono uppercase tracking-wider text-[#6b7280]">Total</p>
                      </div>
                    </div>
                    <ResponsivePie
                      data={pieData}
                      theme={nivoTheme}
                      margin={{ top: 20, right: 100, bottom: 20, left: 20 }}
                      innerRadius={0.6}
                      padAngle={1.5}
                      cornerRadius={3}
                      colors={{ datum: "data.color" }}
                      borderWidth={0}
                      enableArcLabels={false}
                      enableArcLinkLabels={false}
                      activeOuterRadiusOffset={4}
                      legends={[
                        {
                          anchor: "right",
                          direction: "column",
                          translateX: 20,
                          itemWidth: 80,
                          itemHeight: 20,
                          symbolSize: 8,
                          symbolShape: "circle",
                        },
                      ]}
                    />
                  </>
                ) : (
                  <EmptyState message="No categorized tasks yet" icon={Target} />
                )}
              </div>
            </div>
          </motion.div>

          {/* Goal Progress */}
          <motion.div
            className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer overflow-hidden hover:border-[#2a2a4a] transition-all duration-300"
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease, delay: 0.04 * 5 }}
          >
            <ChartHeader title="Goal Progress" icon={Target} color="#ffcc00" />
            <div className="p-4">
              <div className="h-[300px]">
                {radialData.length > 0 ? (
                  <ResponsiveRadialBar
                    data={radialData}
                    theme={nivoTheme}
                    margin={{ top: 20, right: 20, bottom: 40, left: 20 }}
                    valueFormat=">-.0f"
                    padding={0.4}
                    cornerRadius={3}
                    colors={["#00ff88", "#00d4ff", "#ff00ff", "#ffcc00"]}
                    radialAxisStart={{ tickSize: 0, tickPadding: 8, tickRotation: 0 }}
                    circularAxisOuter={{ tickSize: 0, tickPadding: 10, tickRotation: 0 }}
                    legends={[
                      {
                        anchor: "bottom",
                        direction: "row",
                        translateY: 25,
                        itemWidth: 90,
                        itemHeight: 12,
                        symbolSize: 8,
                        symbolShape: "circle",
                      },
                    ]}
                    tracksColor="#1a1a2e"
                  />
                ) : (
                  <EmptyState message="No active goals" icon={Target} />
                )}
              </div>
            </div>
          </motion.div>
        </div>
        </CyberGridBeam>

        {/* Pattern Insights */}
        {Object.keys(patterns).length > 0 && (
          <motion.div
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease, delay: 0.04 * 6 }}
          >
            <div className="bg-[#12121a] border border-[#2a2a3a] cyber-chamfer overflow-hidden">
              <ChartHeader title="Discovered Patterns" icon={Brain} color="#8b5cf6" />
              <div className="p-5">
                <CyberGridBeam rows={2} cols={4} colorVariant="sunset" strength={0.6}>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-3">
                  {patterns.time_estimation_bias !== undefined && patterns.time_estimation_bias !== null && (
                    <PatternCard
                      label="Time Bias"
                      value={`${patterns.time_estimation_bias > 1 ? "Under" : "Over"} by ${Math.abs(Math.round((patterns.time_estimation_bias - 1) * 100))}%`}
                      color="#ffcc00"
                      icon={Clock}
                      description={patterns.time_estimation_bias > 1 ? "Tasks take longer than expected" : "You overestimate task duration"}
                    />
                  )}
                  {patterns.avg_completion_rate_7d !== undefined && patterns.avg_completion_rate_7d !== null && (
                    <PatternCard
                      label="Completion Rate"
                      value={`${Math.round(patterns.avg_completion_rate_7d * 100)}%`}
                      color="#00ff88"
                      icon={TrendingUp}
                      description="7-day average task completion"
                    />
                  )}
                  {patterns.mood_sleep_correlation !== undefined && patterns.mood_sleep_correlation !== null && (
                    <PatternCard
                      label="Mood ↔ Sleep"
                      value={
                        Math.abs(patterns.mood_sleep_correlation) > 0.6
                          ? "Strong"
                          : Math.abs(patterns.mood_sleep_correlation) > 0.3
                          ? "Moderate"
                          : "Weak"
                      }
                      color="#00d4ff"
                      icon={Moon}
                      description={`r = ${patterns.mood_sleep_correlation.toFixed(2)} correlation`}
                    />
                  )}
                  {patterns.mood_exercise_correlation !== undefined && patterns.mood_exercise_correlation !== null && (
                    <PatternCard
                      label="Mood ↔ Exercise"
                      value={
                        Math.abs(patterns.mood_exercise_correlation) > 0.6
                          ? "Strong"
                          : Math.abs(patterns.mood_exercise_correlation) > 0.3
                          ? "Moderate"
                          : "Weak"
                      }
                      color="#ff8800"
                      icon={Dumbbell}
                      description={`r = ${patterns.mood_exercise_correlation.toFixed(2)} correlation`}
                    />
                  )}
                  {patterns.checkin_streak !== undefined && patterns.checkin_streak !== null && (
                    <PatternCard
                      label="Check-in Streak"
                      value={`${patterns.checkin_streak} days`}
                      color="#ff00ff"
                      icon={Flame}
                      description={patterns.longest_checkin_streak ? `Record: ${patterns.longest_checkin_streak} days` : undefined}
                    />
                  )}
                  {patterns.avg_deferral_count !== undefined && patterns.avg_deferral_count !== null && (
                    <PatternCard
                      label="Avg Deferrals"
                      value={patterns.avg_deferral_count.toFixed(1)}
                      color="#ff3366"
                      icon={AlertTriangle}
                      description="Times tasks are postponed"
                    />
                  )}
                  {patterns.top_avoidance_categories && patterns.top_avoidance_categories.length > 0 && (
                    <div className="sm:col-span-2 group relative overflow-hidden p-4 bg-[#0d0d14] border border-[#1a1a2e] cyber-chamfer-sm hover:border-[#2a2a3a] transition-all duration-300">
                      <div className="absolute inset-0 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity" style={{ background: "radial-gradient(circle at 50% 0%, #ff3366, transparent 60%)" }} />
                      <div className="relative">
                        <div className="flex items-center gap-2 mb-3">
                          <AlertTriangle className="w-3.5 h-3.5 text-[#ff3366]/70" strokeWidth={1.5} />
                          <p className="text-[10px] font-mono uppercase tracking-[0.12em] text-[#6b7280]">Top Avoidance Categories</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {patterns.top_avoidance_categories.map((cat) => (
                            <span
                              key={cat}
                              className="px-2.5 py-1 text-xs font-mono text-[#ff3366] border border-[#ff3366]/20 bg-[#ff3366]/5 cyber-chamfer-sm"
                            >
                              {cat}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                </CyberGridBeam>
              </div>
            </div>
          </motion.div>
        )}

        {/* Bottom spacer */}
        <div className="h-4" />
      </PageTransition>
    </div>
  );
}

function EmptyState({ message, icon: Icon }: { message: string; icon: React.ElementType }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3">
      <div className="w-10 h-10 flex items-center justify-center bg-[#1a1a2e] rounded-sm">
        <Icon className="w-5 h-5 text-[#4a4a5a]" strokeWidth={1.5} />
      </div>
      <p className="text-sm font-mono text-[#4a4a5a]">{message}</p>
    </div>
  );
}
