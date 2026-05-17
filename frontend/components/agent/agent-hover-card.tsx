"use client";

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type ReactNode,
  type MouseEvent,
} from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Bot, Loader2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentStatusCard } from "@/types";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

interface AgentHoverCardProps {
  agent: AgentStatusCard;
  color: string;
  description?: string;
  children: ReactNode;
  delay?: number;
}

export function AgentHoverCard({
  agent,
  color,
  description,
  children,
  delay = 0,
}: AgentHoverCardProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const tooltipWidth = 220;
      const tooltipHeight = 100; // approximate
      let left = rect.left + rect.width / 2 - tooltipWidth / 2;
      let top = rect.top - tooltipHeight - 10;
      // Keep within viewport horizontally
      left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8));
      // If too close to top, flip to bottom
      if (top < 8) {
        top = rect.bottom + 10;
      }
      setPosition({ top, left });
      setVisible(true);
    }, 150);
  }, []);

  const hide = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setVisible(false);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleMouseEnter = (e: MouseEvent) => {
    e.stopPropagation();
    show();
  };

  const handleMouseLeave = (e: MouseEvent) => {
    e.stopPropagation();
    hide();
  };

  const tooltip = (
    <AnimatePresence>
      {visible && (
        <motion.div
          key={`tooltip-${agent.name}`}
          className="fixed z-[9999] pointer-events-none"
          style={{
            top: position.top,
            left: position.left,
            width: 220,
          }}
          initial={{ opacity: 0, scale: 0.92, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 4 }}
          transition={{ duration: 0.25, ease, delay }}
        >
          {/* Arrow */}
          <div
            className="absolute left-1/2 -translate-x-1/2 w-2 h-2 rotate-45"
            style={{
              backgroundColor: "#0d0d14",
              borderColor: `${color}40`,
              borderStyle: "solid",
              borderWidth: position.top < (triggerRef.current?.getBoundingClientRect().top ?? 0)
                ? "0 1px 1px 0"
                : "1px 0 0 1px",
              bottom: position.top < (triggerRef.current?.getBoundingClientRect().top ?? 0) ? "auto" : "-5px",
              top: position.top < (triggerRef.current?.getBoundingClientRect().top ?? 0) ? "-5px" : "auto",
            }}
          />

          {/* Card */}
          <div
            className="relative bg-[#0d0d14] border cyber-chamfer-sm p-3"
            style={{
              borderColor: `${color}40`,
              boxShadow: `0 0 12px ${color}25, 0 4px 20px rgba(0,0,0,0.4)`,
            }}
          >
            {/* Corner accents */}
            <span
              className="absolute top-0 left-0 w-2.5 h-2.5 border-t border-l"
              style={{ borderColor: `${color}50` }}
            />
            <span
              className="absolute top-0 right-0 w-2.5 h-2.5 border-t border-r"
              style={{ borderColor: `${color}50` }}
            />
            <span
              className="absolute bottom-0 left-0 w-2.5 h-2.5 border-b border-l"
              style={{ borderColor: `${color}50` }}
            />
            <span
              className="absolute bottom-0 right-0 w-2.5 h-2.5 border-b border-r"
              style={{ borderColor: `${color}50` }}
            />

            {/* Header */}
            <div className="flex items-center gap-2 mb-1.5">
              <Bot className="w-3.5 h-3.5 shrink-0" style={{ color }} />
              <span
                className="text-[11px] font-[var(--font-orbitron)] uppercase tracking-wider truncate"
                style={{ color }}
              >
                {agent.display_name}
              </span>
            </div>

            {/* Description */}
            {description && (
              <p className="text-[10px] font-mono text-[#9ca3af] leading-relaxed mb-2">
                {description}
              </p>
            )}

            {/* Footer: status + runs */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                {agent.status === "running" ? (
                  <>
                    <Loader2 className="w-2.5 h-2.5 animate-spin" style={{ color }} />
                    <span className="text-[9px] font-mono" style={{ color: `${color}cc` }}>
                      Active
                    </span>
                  </>
                ) : (
                  <>
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ backgroundColor: color, opacity: 0.6 }}
                    />
                    <span className="text-[9px] font-mono text-[#6b7280]">Idle</span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Zap className="w-2.5 h-2.5 text-[#6b7280]" />
                <span className="text-[9px] font-mono text-[#6b7280]">
                  {agent.runs_today}
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <div
      ref={triggerRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={show}
      onBlur={hide}
      className="relative"
    >
      {children}
      {typeof document !== "undefined" && createPortal(tooltip, document.body)}
    </div>
  );
}
