"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberInput } from "@/components/cyber/input";
import { Loader2, Zap } from "lucide-react";
import { GlowText, GradientText, CyberLabel, ChatMessageText } from "@/components/typography";

export default function OnboardingPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(10);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.push("/");
      return;
    }
    startOnboarding();
  }, [isLoaded, isSignedIn]);

  async function startOnboarding() {
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/onboarding/start`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMessage(data.message);
        setStep(data.step);
        setTotalSteps(data.total_steps);
        if (data.complete) {
          setComplete(true);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(e?: React.FormEvent) {
    e?.preventDefault();
    if (!input.trim()) return;
    setLoading(true);
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/onboarding/message`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: input }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setMessage(data.message);
        setStep(data.step);
        setTotalSteps(data.total_steps);
        setComplete(data.complete);
        if (data.complete) {
          setTimeout(() => router.push("/dashboard"), 2000);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setInput("");
      setLoading(false);
    }
  }

  if (!isLoaded || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#0a0a0f]">
        <Loader2 className="w-8 h-8 text-[#00ff88] animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] cyber-grid-bg flex items-center justify-center px-6">
      <div className="max-w-xl w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <Zap className="w-8 h-8 text-[#00ff88] mx-auto mb-3" strokeWidth={1.5} />
          <h1 className="text-3xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
            <GradientText from="#00ff88" to="#ff00ff">Life OS</GradientText>
          </h1>
          <p className="text-xs font-mono text-[#6b7280] mt-2 uppercase tracking-wider">
            System Initialization
          </p>
        </div>

        {/* Progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <CyberLabel>Progress</CyberLabel>
            <CyberLabel glow color="#00ff88">
              {complete ? "Complete" : `Step ${step} of ${totalSteps}`}
            </CyberLabel>
          </div>
          <div className="h-1 bg-[#2a2a3a]">
            <div
              className="h-full bg-[#00ff88] transition-all duration-500"
              style={{ width: `${complete ? 100 : (step / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {/* Chat Card */}
        <CyberCard variant="terminal" header="Neural Interview">
          <div className="space-y-6">
            {/* Agent Message */}
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-[#00ff88]/10 border border-[#00ff88]/30 flex items-center justify-center shrink-0">
                <Zap className="w-4 h-4 text-[#00ff88]" strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <p className="text-xs font-mono uppercase tracking-wider mb-1">
                  <GlowText color="#00ff88" intensity="low">System</GlowText>
                </p>
                <ChatMessageText content={message} role="assistant" />
              </div>
            </div>

            {/* Input */}
            {!complete && (
              <form onSubmit={sendMessage} className="flex gap-3">
                <div className="flex-1">
                  <CyberInput
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Your response..."
                    disabled={loading}
                    autoFocus
                  />
                </div>
                <CyberButton type="submit" variant="glitch" size="sm" disabled={loading || !input.trim()}>
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send"}
                </CyberButton>
              </form>
            )}

            {complete && (
              <div className="text-center py-4">
                <p className="text-sm font-mono">
                  <GlowText color="#00ff88" intensity="medium">Profile initialized.</GlowText>
                </p>
                <p className="text-xs font-mono mt-1">
                  <GlowText color="#6b7280" intensity="low">Redirecting to dashboard</GlowText>
                  <span className="animate-blink text-[#00ff88]">_</span>
                </p>
              </div>
            )}
          </div>
        </CyberCard>
      </div>
    </div>
  );
}
