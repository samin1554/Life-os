"use client";

import { useState, useRef, useEffect } from "react";
import { UserButton } from "@clerk/nextjs";
import { Bell, Zap, Check, X, Bot, Target, Brain, Calendar, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useNotifications } from "@/hooks/useNotifications";
import { useRouter } from "next/navigation";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const NOTIFICATION_ICONS: Record<string, React.ReactNode> = {
  agent_completed: <Bot className="w-3.5 h-3.5" strokeWidth={1.5} />,
  agent_failed: <AlertCircle className="w-3.5 h-3.5" strokeWidth={1.5} />,
  task_assigned: <Target className="w-3.5 h-3.5" strokeWidth={1.5} />,
  weekly_review_ready: <Calendar className="w-3.5 h-3.5" strokeWidth={1.5} />,
  pattern_insight: <Brain className="w-3.5 h-3.5" strokeWidth={1.5} />,
  goal_drift: <AlertCircle className="w-3.5 h-3.5" strokeWidth={1.5} />,
};

const NOTIFICATION_COLORS: Record<string, string> = {
  agent_completed: "#00ff88",
  agent_failed: "#ff3366",
  task_assigned: "#00d4ff",
  weekly_review_ready: "#ffcc00",
  pattern_insight: "#ff00ff",
  goal_drift: "#ff8800",
};

function timeAgo(dateStr: string): string {
  const then = new Date(dateStr).getTime();
  const now = Date.now();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function TopBar({ title }: { title: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markRead,
    markAllRead,
    dismiss,
  } = useNotifications();

  // Fetch notifications when panel opens
  useEffect(() => {
    if (open) {
      fetchNotifications();
    }
  }, [open, fetchNotifications]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open]);

  return (
    <header className="h-16 bg-[#0a0a0f]/80 backdrop-blur-md border-b border-[#2a2a3a] flex items-center justify-between px-6 sticky top-0 z-40">
      <motion.div
        className="flex items-center gap-3"
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease }}
      >
        <motion.div
          initial={{ rotate: -20, scale: 0 }}
          animate={{ rotate: 0, scale: 1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.15 }}
        >
          <Zap className="w-5 h-5 text-[#00ff88]" strokeWidth={1.5} />
        </motion.div>
        <h1 className="text-sm font-[var(--font-orbitron)] uppercase tracking-[0.2em] text-[#e0e0e0]">
          {title}
        </h1>
      </motion.div>

      <motion.div
        className="flex items-center gap-4"
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease, delay: 0.1 }}
      >
        {/* Notification Bell */}
        <div className="relative" ref={panelRef}>
          <motion.button
            className="relative p-2 text-[#6b7280] hover:text-[#e0e0e0] transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
            onClick={() => setOpen(!open)}
          >
            <Bell className="w-5 h-5" strokeWidth={1.5} />
            {unreadCount > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 rounded-full bg-[#ff00ff] text-[10px] font-mono font-bold text-white"
                style={{ boxShadow: "0 0 8px rgba(255, 0, 255, 0.4)" }}
              >
                {unreadCount > 99 ? "99+" : unreadCount}
              </motion.span>
            )}
          </motion.button>

          {/* Dropdown Panel */}
          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.95 }}
                transition={{ duration: 0.2, ease }}
                className="absolute right-0 top-full mt-2 w-[360px] max-w-[calc(100vw-2rem)] bg-[#12121a] border border-[#2a2a3a] cyber-chamfer shadow-[0_8px_30px_rgba(0,0,0,0.5)] z-50"
              >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a3a]">
                  <span className="text-xs font-mono uppercase tracking-wider text-[#e0e0e0]">
                    Notifications
                  </span>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-[10px] font-mono uppercase tracking-wider text-[#00ff88] hover:text-[#00ff88]/80 transition-colors"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                {/* List */}
                <div className="max-h-[400px] overflow-y-auto">
                  {loading && notifications.length === 0 ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="w-5 h-5 border-2 border-[#2a2a3a] border-t-[#00ff88] rounded-full animate-spin" />
                    </div>
                  ) : notifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Bell className="w-8 h-8 text-[#2a2a3a] mb-2" strokeWidth={1} />
                      <p className="text-xs font-mono text-[#6b7280]">No notifications yet</p>
                    </div>
                  ) : (
                    notifications.map((n) => {
                      const color = NOTIFICATION_COLORS[n.notification_type] || "#6b7280";
                      const icon = NOTIFICATION_ICONS[n.notification_type] || (
                        <Bell className="w-3.5 h-3.5" strokeWidth={1.5} />
                      );
                      return (
                        <div
                          key={n.id}
                          className={`flex items-start gap-3 px-4 py-3 border-b border-[#1a1a2e] hover:bg-[#1a1a2e]/50 transition-colors ${
                            !n.read ? "bg-[#00ff88]/[0.02]" : ""
                          }`}
                        >
                          {/* Icon */}
                          <div
                            className="w-8 h-8 shrink-0 flex items-center justify-center rounded-sm"
                            style={{ backgroundColor: `${color}15`, color }}
                          >
                            {icon}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-mono text-[#e0e0e0] leading-snug">
                              {n.title}
                            </p>
                            <p className="text-[10px] font-mono text-[#6b7280] mt-0.5 line-clamp-2">
                              {n.message}
                            </p>
                            <div className="flex items-center gap-2 mt-1.5">
                              <span className="text-[9px] font-mono text-[#4a4a5a]">
                                {timeAgo(n.created_at)}
                              </span>
                              {n.link && (
                                <button
                                  onClick={() => {
                                    router.push(n.link!);
                                    setOpen(false);
                                    if (!n.read) markRead(n.id);
                                  }}
                                  className="text-[9px] font-mono text-[#00d4ff] hover:underline"
                                >
                                  View →
                                </button>
                              )}
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex flex-col gap-1 shrink-0">
                            {!n.read && (
                              <button
                                onClick={() => markRead(n.id)}
                                className="w-6 h-6 flex items-center justify-center text-[#6b7280] hover:text-[#00ff88] transition-colors"
                                title="Mark read"
                              >
                                <Check className="w-3 h-3" />
                              </button>
                            )}
                            <button
                              onClick={() => dismiss(n.id)}
                              className="w-6 h-6 flex items-center justify-center text-[#6b7280] hover:text-[#ff3366] transition-colors"
                              title="Dismiss"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <UserButton
          appearance={{
            elements: {
              avatarBox: "w-8 h-8 border border-[#2a2a3a]",
            },
          }}
        />
      </motion.div>
    </header>
  );
}
