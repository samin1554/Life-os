"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import type { AgentEvent } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export function useAgentEvents() {
  const { getToken } = useAuth();
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const connect = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/agents/events`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortRef.current.signal,
      });

      if (!res.ok) return;
      setConnected(true);

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const chunk of lines) {
          const dataLine = chunk
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (dataLine) {
            try {
              const event: AgentEvent = JSON.parse(
                dataLine.replace("data: ", "")
              );
              setEvents((prev) => [event, ...prev].slice(0, 50));
            } catch {
              // ignore
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") return;
    } finally {
      setConnected(false);
    }
  }, [getToken]);

  const disconnect = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    setConnected(false);
  }, []);

  return { events, connected, connect, disconnect };
}
