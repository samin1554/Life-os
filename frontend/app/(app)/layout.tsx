"use client";

import { Sidebar } from "@/components/layout/sidebar";
import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[#0a0a0f]">
      <Sidebar />
      <main className="flex-1 lg:ml-64 pt-14 lg:pt-0">
        <AnimatePresence mode="wait">
          <motion.div key={pathname}>
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
