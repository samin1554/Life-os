"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { CyberInput } from "@/components/cyber/input";
import { CyberSelect } from "@/components/cyber/select";
import type { Task } from "@/types";
import {
  Plus,
  CheckCircle2,
  Circle,
  Clock,
  Trash2,
  Loader2,
  X,
  Bot,
  Send,
  AlertCircle,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { TasksSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal, FadeIn } from "@/components/motion";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";
import { AgentResultCard } from "@/components/agent/agent-result-card";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const AGENTS = [
  { value: "focus", label: "Focus" },
  { value: "health", label: "Health" },
  { value: "execution", label: "Execution" },
  { value: "chaos_triage", label: "Triage" },
  { value: "goals", label: "Goals" },
  { value: "delegate", label: "Delegate" },
  { value: "research", label: "Research" },
  { value: "worker", label: "Worker" },
  { value: "email", label: "Email" },
];

const AGENT_COLORS: Record<string, string> = {
  focus: "#00ff88",
  health: "#00d4ff",
  execution: "#ff00ff",
  chaos_triage: "#ff3366",
  goals: "#ffcc00",
  delegate: "#8b5cf6",
  research: "#00aaff",
  worker: "#ff5500",
  email: "#ea4335",
};

export default function TasksPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({ title: "", category: "", priority: 2 });
  const [assigningTask, setAssigningTask] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
  }, []);

  async function loadTasks() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/tasks`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setTasks(json.tasks);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load tasks", "error");
    } finally {
      setLoading(false);
    }
  }

  async function createTask(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!newTask.title.trim()) {
      setFormError("Task title is required");
      return;
    }
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newTask),
      });
      if (res.ok) {
        setNewTask({ title: "", category: "", priority: 2 });
        setShowCreate(false);
        addToast("Task created", "success");
        loadTasks();
      } else {
        addToast("Failed to create task", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to create task", "error");
    }
  }

  async function updateTaskStatus(id: string, status: string) {
    try {
      const token = await getToken();
      await fetch(`${API_BASE}/tasks/${id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status }),
      });
      loadTasks();
    } catch (e) {
      console.error(e);
      addToast("Failed to update task", "error");
    }
  }

  async function deleteTask(id: string) {
    try {
      const token = await getToken();
      await fetch(`${API_BASE}/tasks/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      loadTasks();
    } catch (e) {
      console.error(e);
      addToast("Failed to delete task", "error");
    }
  }

  async function assignAgent(taskId: string, agent: string) {
    setAssigningTask(taskId);
    try {
      const token = await getToken();
      await fetch(`${API_BASE}/tasks/${taskId}/assign`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ agent, run_immediately: true }),
      });
      loadTasks();
    } catch (e) {
      console.error(e);
      addToast("Failed to assign agent", "error");
    } finally {
      setAssigningTask(null);
    }
  }

  const pending = tasks.filter((t) => t.status === "pending" || t.status === "in_progress");
  const completed = tasks.filter((t) => t.status === "completed");

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Task Queue" />
        <TasksSkeleton />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Task Queue" />

      <PageTransition className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#00ff88" to="#00d4ff">Task Queue</GradientText>
            </h2>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {pending.length} pending // {completed.length} completed
            </p>
          </div>
          <CyberButton variant="glitch" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            New Task
          </CyberButton>
        </div>

        {/* Create Form */}
        <AnimatePresence>
        {showCreate && (
          <motion.div
            key="create-form"
            initial={{ opacity: 0, scale: 0.95, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -8 }}
            transition={{ duration: 0.25, ease }}
          >
          <CyberCard variant="terminal" header="New Objective">
            <form onSubmit={createTask} className="space-y-4">
              {formError && (
                <div className="flex items-center gap-2 text-xs font-mono text-[#ff3366]">
                  <AlertCircle className="w-3.5 h-3.5" />
                  {formError}
                </div>
              )}
              <CyberInput
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                placeholder="Task title..."
                autoFocus
              />
              <div className="flex gap-3">
                <CyberInput
                  value={newTask.category}
                  onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
                  placeholder="Category"
                  className="flex-1"
                />
                <CyberSelect
                  value={String(newTask.priority)}
                  onChange={(value) => setNewTask({ ...newTask, priority: parseInt(value) })}
                  options={[
                    { value: "1", label: "Low" },
                    { value: "2", label: "Normal" },
                    { value: "3", label: "High" },
                    { value: "4", label: "Critical" },
                    { value: "5", label: "Urgent" },
                  ]}
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

        {/* Pending Tasks */}
        <CyberCard header="Pending Objectives" hoverEffect>
          {pending.length === 0 ? (
            <FadeIn>
            <div className="text-center py-8">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
                className="inline-block"
              >
                <CheckCircle2 className="w-8 h-8 text-[#00ff88] mx-auto mb-3" strokeWidth={1.5} />
              </motion.div>
              <p className="text-sm font-mono">
                <GlowText color="#00ff88" intensity="low">All objectives cleared. System optimal.</GlowText>
              </p>
            </div>
            </FadeIn>
          ) : (
            <div className="space-y-2">
              {pending.map((task, idx) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                  whileHover={{ x: 4 }}
                  className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm
                    hover:border-[#00ff88]/30 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => updateTaskStatus(task.id, "completed")}
                      className="text-[#6b7280] hover:text-[#00ff88] transition-colors"
                    >
                      <Circle className="w-5 h-5" strokeWidth={1.5} />
                    </button>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono">
                        <GlowText color="#e0e0e0" intensity="low">{task.title}</GlowText>
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {task.category && (
                          <CyberBadge variant="outline" className="text-[10px]">
                            {task.category}
                          </CyberBadge>
                        )}
                        <CyberBadge
                          variant={
                            task.priority >= 4 ? "destructive" : task.priority === 3 ? "tertiary" : "outline"
                          }
                          className="text-[10px]"
                        >
                          P{task.priority}
                        </CyberBadge>
                        {task.estimated_minutes && (
                          <CyberLabel className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {task.estimated_minutes}m
                          </CyberLabel>
                        )}
                        {task.assigned_agent && (
                          <span
                            className="text-[10px] font-mono flex items-center gap-1"
                            style={{ color: AGENT_COLORS[task.assigned_agent] || "#6b7280" }}
                          >
                            <Bot className="w-3 h-3" />
                            {task.assigned_agent}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
                      {/* Agent assign dropdown */}
                      <CyberSelect
                        className="!text-[10px] !py-1 !pl-1.5 !pr-6 max-w-[130px]"
                        value=""
                        onChange={(value) => {
                          if (value) assignAgent(task.id, value);
                        }}
                        disabled={assigningTask === task.id}
                        glowColor="#8b5cf6"
                        options={[
                          { value: "", label: assigningTask === task.id ? "Sending..." : "Assign Agent" },
                          ...AGENTS,
                        ]}
                      />
                      <button
                        onClick={() => deleteTask(task.id)}
                        className="text-[#6b7280] hover:text-[#ff3366] transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {/* Agent output */}
                  {task.execution_output && (
                    <AgentResultCard
                      agent={task.assigned_agent}
                      output={task.execution_output}
                      status={task.status}
                    />
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </CyberCard>

        {/* Completed Tasks */}
        {completed.length > 0 && (
          <ScrollReveal>
          <CyberCard header="Completed" hoverEffect>
            <div className="space-y-2">
              {completed.map((task, idx) => (
                <motion.div
                  key={task.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.6 }}
                  transition={{ duration: 0.3, delay: 0.03 * idx }}
                  className="p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm"
                >
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-[#00ff88]" strokeWidth={1.5} />
                    <p className="text-sm font-mono line-through">
                      <GlowText color="#6b7280" intensity="low">{task.title}</GlowText>
                    </p>
                  </div>
                  {task.execution_output && (
                    <AgentResultCard
                      agent={task.assigned_agent}
                      output={task.execution_output}
                      status={task.status}
                      compact
                      className="ml-0 mt-2"
                    />
                  )}
                </motion.div>
              ))}
            </div>
          </CyberCard>
          </ScrollReveal>
        )}
      </PageTransition>
    </div>
  );
}
