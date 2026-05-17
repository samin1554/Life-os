"use client";

import { useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import type { ChatMessage } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface SSEState {
  messages: ChatMessage[];
  currentAgent: string | null;
  isStreaming: boolean;
  error: string | null;
  agentsUsed: string[];
}

export function useSSE() {
  const { getToken } = useAuth();
  const [state, setState] = useState<SSEState>({
    messages: [],
    currentAgent: null,
    isStreaming: false,
    error: null,
    agentsUsed: [],
  });
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (message: string) => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
      abortRef.current = new AbortController();

      setState((prev) => ({
        ...prev,
        isStreaming: true,
        error: null,
        currentAgent: null,
        messages: [...prev.messages, { role: "user", content: message }],
      }));

      try {
        const token = await getToken();
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message }),
          signal: abortRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let finalResponse = "";
        const agentsUsed: string[] = [];

        while (true) {
          const { done, value } = await reader!.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              const eventName = line.replace("event: ", "").trim();
              // Next line should be data:
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.replace("data: ", ""));

                if (data.agent) {
                  setState((prev) => ({ ...prev, currentAgent: data.agent }));
                }

                if (data.agents) {
                  agentsUsed.push(...data.agents);
                }

                if (data.response) {
                  finalResponse = data.response;
                }
              } catch {
                // ignore malformed JSON
              }
            }
          }
        }

        setState((prev) => ({
          ...prev,
          isStreaming: false,
          currentAgent: null,
          agentsUsed: [...new Set([...prev.agentsUsed, ...agentsUsed])],
          messages: [
            ...prev.messages,
            { role: "assistant", content: finalResponse || "..." },
          ],
        }));
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: err.message || "Something went wrong",
        }));
      }
    },
    [getToken]
  );

  const clearChat = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    setState({
      messages: [],
      currentAgent: null,
      isStreaming: false,
      error: null,
      agentsUsed: [],
    });
  }, []);

  return { ...state, sendMessage, clearChat };
}
