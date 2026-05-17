"use client";

import { motion } from "framer-motion";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";
import type { Toast } from "./ToastProvider";

const toastConfig = {
  success: {
    icon: CheckCircle2,
    color: "#00ff88",
    bg: "bg-[#00ff88]/10",
    border: "border-[#00ff88]/30",
    glow: "0 0 20px rgba(0, 255, 136, 0.15)",
  },
  error: {
    icon: AlertCircle,
    color: "#ff3366",
    bg: "bg-[#ff3366]/10",
    border: "border-[#ff3366]/30",
    glow: "0 0 20px rgba(255, 51, 102, 0.15)",
  },
  info: {
    icon: Info,
    color: "#00d4ff",
    bg: "bg-[#00d4ff]/10",
    border: "border-[#00d4ff]/30",
    glow: "0 0 20px rgba(0, 212, 255, 0.15)",
  },
};

export function ToastItem({
  toast,
  onRemove,
}: {
  toast: Toast;
  onRemove: (id: string) => void;
}) {
  const config = toastConfig[toast.type];
  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={`pointer-events-auto flex items-center gap-3 px-4 py-3 min-w-[280px] max-w-[400px] ${config.bg} border ${config.border} cyber-chamfer-sm`}
      style={{ boxShadow: config.glow }}
    >
      <Icon className="w-4 h-4 shrink-0" style={{ color: config.color }} strokeWidth={1.5} />
      <span className="text-xs font-mono text-[#e0e0e0] flex-1 leading-relaxed">
        {toast.message}
      </span>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-[#6b7280] hover:text-[#e0e0e0] transition-colors shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
}
