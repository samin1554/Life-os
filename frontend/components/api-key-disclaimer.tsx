"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { Key, AlertTriangle, ArrowRight, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { GlowText, GradientText } from "@/components/typography";

interface ApiKeyDisclaimerProps {
  onDismiss?: () => void;
}

export function ApiKeyDisclaimer({ onDismiss }: ApiKeyDisclaimerProps) {
  const router = useRouter();
  const { userId } = useAuth();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!userId) return;
    if (localStorage.getItem(`api_key_dismiss_${userId}`)) return;
    setVisible(true);
  }, [userId]);

  const handleDismiss = () => {
    setVisible(false);
    onDismiss?.();
  };

  const handleDismissPermanent = () => {
    if (userId) localStorage.setItem(`api_key_dismiss_${userId}`, "1");
    setVisible(false);
    onDismiss?.();
  };


  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={handleDismiss}
          />

          {/* Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-lg"
          >
            <CyberCard variant="holographic" chamfer="lg" className="p-0">
              <div className="p-6 space-y-5">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-[#ffcc00]/10 border border-[#ffcc00]/20">
                      <Key className="w-5 h-5 text-[#ffcc00]" />
                    </div>
                    <div>
                      <h3 className="text-base font-[var(--font-orbitron)] font-bold uppercase tracking-wider">
                        <GradientText from="#ffcc00" to="#ff8800">
                          API Key Required
                        </GradientText>
                      </h3>
                    </div>
                  </div>
                  <button
                    onClick={handleDismiss}
                    className="text-[#6b7280] hover:text-white transition-colors p-1"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Alert */}
                <div className="flex items-start gap-2.5 p-3 rounded-lg bg-[#ffcc00]/5 border border-[#ffcc00]/15">
                  <AlertTriangle className="w-4 h-4 text-[#ffcc00] mt-0.5 shrink-0" />
                  <p className="text-xs font-mono text-[#e0e0e0] leading-relaxed">
                    Life OS agents require an LLM API key to function. We keep this service{" "}
                    <span className="text-[#00ff88] font-semibold">100% free</span> by letting you
                    bring your own key.
                  </p>
                </div>

                {/* Details */}
                <div className="space-y-2.5 text-xs font-mono text-[#9ca3af]">
                  <div className="flex items-start gap-2">
                    <span className="text-[#00ff88] mt-px">&#x2022;</span>
                    <span>
                      <span className="text-[#e0e0e0]">Free keys</span> are available from
                      providers like{" "}
                      <span className="text-[#00d4ff]">Groq</span> with high capabilities
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#00ff88] mt-px">&#x2022;</span>
                    <span>
                      Affordable paid options from{" "}
                      <span className="text-[#e0e0e0]">OpenAI, Anthropic, and Gemini</span> are
                      also supported
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-[#00ff88] mt-px">&#x2022;</span>
                    <span>
                      A <span className="text-[#ffcc00]">trial key</span> will be provided for
                      new users in the future
                    </span>
                  </div>
                </div>

                {/* CTA */}
                <div className="pt-1">
                  <CyberButton
                    variant="glitch"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      handleDismiss();
                      router.push("/settings");
                    }}
                  >
                    Go to Settings
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </CyberButton>
                </div>

                {/* Dismiss */}
                <div className="flex items-center justify-between pt-1 border-t border-[#2a2a3a]">
                  <button
                    onClick={handleDismiss}
                    className="text-[10px] font-mono text-[#6b7280] hover:text-[#9ca3af] transition-colors uppercase tracking-wider"
                  >
                    I Understand
                  </button>
                  <button
                    onClick={handleDismissPermanent}
                    className="text-[10px] font-mono text-[#6b7280] hover:text-[#9ca3af] transition-colors uppercase tracking-wider"
                  >
                    Don&apos;t Show Again
                  </button>
                </div>
              </div>
            </CyberCard>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
