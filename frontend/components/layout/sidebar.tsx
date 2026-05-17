"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { PulseRing } from "@/components/motion";
import {
  LayoutDashboard,
  MessageSquare,
  CheckSquare,
  Target,
  Activity,
  Settings,
  Zap,
  Bot,
  FileDown,
  BarChart3,
  CalendarDays,
  Menu,
  X,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/tasks", label: "Tasks", icon: CheckSquare },
  { href: "/checkin", label: "Check-in", icon: Activity },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/insights", label: "Insights", icon: BarChart3 },
  { href: "/weekly-review", label: "Weekly Review", icon: CalendarDays },
  { href: "/files", label: "Files", icon: FileDown },
  { href: "/settings", label: "Settings", icon: Settings },
];

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

function NavContent({ onItemClick }: { onItemClick?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Logo */}
      <motion.div
        className="px-6 py-5 border-b border-[#2a2a3a]"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease }}
      >
        <Link href="/dashboard" className="flex items-center gap-3 group" onClick={onItemClick}>
          <motion.div
            whileHover={{ rotate: 15, scale: 1.1 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
          >
            <Zap className="w-6 h-6 text-[#00ff88]" strokeWidth={1.5} />
          </motion.div>
          <span className="text-lg font-[var(--font-orbitron)] font-bold uppercase tracking-widest text-[#e0e0e0] group-hover:text-[#00ff88] transition-colors duration-300">
            Life OS
          </span>
        </Link>
      </motion.div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item, i) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <motion.div
              key={item.href}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, ease, delay: 0.05 * i }}
            >
              <Link
                href={item.href}
                onClick={onItemClick}
                className={cn(
                  "relative flex items-center gap-3 px-3 py-2.5 text-sm font-mono uppercase tracking-wider transition-all duration-200 rounded-sm overflow-hidden",
                  isActive
                    ? "text-[#00ff88]"
                    : "text-[#6b7280] hover:text-[#e0e0e0]"
                )}
              >
                {/* Animated active background */}
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute inset-0 bg-[#00ff88]/10 border-l-2 border-[#00ff88]"
                    transition={{ type: "spring", stiffness: 350, damping: 30 }}
                  />
                )}

                {/* Hover background */}
                {!isActive && (
                  <motion.div
                    className="absolute inset-0 bg-[#1c1c2e] opacity-0"
                    whileHover={{ opacity: 1 }}
                    transition={{ duration: 0.2 }}
                  />
                )}

                <motion.div
                  className="relative z-10"
                  whileHover={{ scale: 1.15 }}
                  transition={{ type: "spring", stiffness: 400, damping: 17 }}
                >
                  <Icon className="w-4 h-4" strokeWidth={1.5} />
                </motion.div>
                <span className="relative z-10">{item.label}</span>

                {/* Active glow dot */}
                {isActive && (
                  <motion.span
                    className="absolute right-3 w-1.5 h-1.5 rounded-full bg-[#00ff88]"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 500, damping: 20, delay: 0.1 }}
                    style={{ boxShadow: "0 0 6px #00ff88" }}
                  />
                )}
              </Link>
            </motion.div>
          );
        })}
      </nav>

      {/* Footer */}
      <motion.div
        className="px-6 py-4 border-t border-[#2a2a3a]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.5 }}
      >
        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#6b7280]">
          System Online
        </p>
        <div className="flex items-center gap-2 mt-1">
          <PulseRing color="#00ff88" size={6} />
          <span className="text-[10px] font-mono text-[#00ff88]">Connected</span>
        </div>
      </motion.div>
    </>
  );
}

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex w-64 h-screen bg-[#0a0a0f] border-r border-[#2a2a3a] flex-col fixed left-0 top-0 z-50">
        <NavContent />
      </aside>

      {/* Mobile Hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-[60] w-10 h-10 flex items-center justify-center bg-[#12121a] border border-[#2a2a3a] cyber-chamfer-sm text-[#6b7280] hover:text-[#e0e0e0] transition-colors"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" strokeWidth={1.5} />
      </button>

      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-[70]"
              onClick={() => setMobileOpen(false)}
            />
            {/* Drawer */}
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="lg:hidden fixed left-0 top-0 h-screen w-72 bg-[#0a0a0f] border-r border-[#2a2a3a] flex flex-col z-[80]"
            >
              {/* Close button */}
              <div className="absolute top-4 right-4 z-10">
                <button
                  onClick={() => setMobileOpen(false)}
                  className="w-8 h-8 flex items-center justify-center text-[#6b7280] hover:text-[#e0e0e0] transition-colors"
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5" strokeWidth={1.5} />
                </button>
              </div>
              <NavContent onItemClick={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
