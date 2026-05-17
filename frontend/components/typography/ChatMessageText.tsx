"use client";

import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface ChatMessageTextProps {
  content: string;
  role?: "user" | "assistant" | "system";
  className?: string;
}

/**
 * Renders chat message text with:
 * - Role-based tinting
 * - Inline code highlighting (`code`)
 * - Bold emphasis (**text**)
 */
export function ChatMessageText({
  content,
  role = "assistant",
  className,
}: ChatMessageTextProps) {
  const roleColor =
    role === "user"
      ? "#00ff88"
      : role === "system"
      ? "#6b7280"
      : "#e0e0e0";

  // Simple markdown-lite parser for inline formatting
  const segments = parseContent(content);

  return (
    <div
      className={cn(
        "text-sm font-mono whitespace-pre-wrap leading-relaxed",
        className
      )}
      style={{ color: roleColor }}
    >
      {segments.map((seg, i) => {
        if (seg.type === "code") {
          return (
            <code
              key={i}
              className="px-1.5 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff] text-xs font-mono border border-[#00d4ff]/20"
            >
              {seg.content}
            </code>
          );
        }
        if (seg.type === "bold") {
          return (
            <strong
              key={i}
              className="font-bold"
              style={{ color: "#ffffff" }}
            >
              {seg.content}
            </strong>
          );
        }
        return <span key={i}>{seg.content}</span>;
      })}
    </div>
  );
}

type Segment = { type: "text" | "code" | "bold"; content: string };

function parseContent(text: string): Segment[] {
  const segments: Segment[] = [];
  // Match inline code `...` or **bold**
  const regex = /(`([^`]+)`|\*\*([^*]+)\*\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Push preceding text
    if (match.index > lastIndex) {
      segments.push({
        type: "text",
        content: text.slice(lastIndex, match.index),
      });
    }

    if (match[1].startsWith("`")) {
      segments.push({ type: "code", content: match[2] });
    } else {
      segments.push({ type: "bold", content: match[3] });
    }

    lastIndex = match.index + match[0].length;
  }

  // Push remaining text
  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }

  if (segments.length === 0) {
    segments.push({ type: "text", content: text });
  }

  return segments;
}
