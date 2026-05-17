"use client";

import { cn } from "@/lib/utils";
import { AgentBadge } from "./agent-badge";
import type { ChatMessage } from "@/types";

interface AgentStreamProps {
  messages: ChatMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
}

function ThinkingDots() {
  return (
    <span className="inline-flex gap-1">
      <span className="w-1.5 h-1.5 bg-[#00ff88] animate-pulse" />
      <span className="w-1.5 h-1.5 bg-[#00ff88] animate-pulse [animation-delay:0.2s]" />
      <span className="w-1.5 h-1.5 bg-[#00ff88] animate-pulse [animation-delay:0.4s]" />
    </span>
  );
}

export function AgentStream({ messages, currentAgent, isStreaming }: AgentStreamProps) {
  return (
    <div className="flex flex-col gap-4">
      {isStreaming && currentAgent && (
        <div className="flex items-center gap-3 text-sm text-[#6b7280]">
          <ThinkingDots />
          <AgentBadge agent={currentAgent} />
          <span className="font-mono text-xs uppercase tracking-wider">Processing...</span>
        </div>
      )}

      {messages.map((msg, i) => (
        <div
          key={i}
          className={cn(
            "flex",
            msg.role === "user" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "max-w-[85%] cyber-chamfer-sm",
              msg.role === "user"
                ? "bg-[#00ff88]/10 border border-[#00ff88]/30 px-5 py-3"
                : "bg-[#12121a] border border-[#2a2a3a] px-5 py-4"
            )}
          >
            {msg.role === "assistant" && (
              <div className="mb-2">
                <AgentBadge agent="coach" />
              </div>
            )}
            <p className="text-sm leading-relaxed whitespace-pre-wrap font-mono text-[#e0e0e0]">
              {msg.content}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
