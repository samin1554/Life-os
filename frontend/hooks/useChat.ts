"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import type { ChatMessage } from "@/types";

const SESSION_KEY = "lifeos_chat_session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  needsApiKey: boolean;
}

export function useChat() {
  const { getToken } = useAuth();
  const [state, setState] = useState<ChatState>({
    messages: [],
    sessionId: null,
    isLoading: false,
    error: null,
    needsApiKey: false,
  });
  const abortRef = useRef<AbortController | null>(null);
  const hasLoaded = useRef(false);

  const loadHistory = useCallback(
    async (sessionId: string) => {
      try {
        const token = await getToken();
        const res = await fetch(
          `${API_BASE}/chat/history?session_id=${sessionId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (!res.ok) return;
        const data = await res.json();
        setState((prev) => ({
          ...prev,
          sessionId,
          messages: data.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            id: m.id,
            created_at: m.created_at,
          })),
        }));
      } catch {
        // silent
      }
    },
    [getToken]
  );

  // Load the latest session — check server first, fallback to localStorage
  useEffect(() => {
    if (hasLoaded.current) return;
    hasLoaded.current = true;

    const init = async () => {
      try {
        const token = await getToken();
        if (!token) return;

        // Try to get latest session from server (cross-device persistence)
        const res = await fetch(`${API_BASE}/chat/latest-session`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          if (data.session_id) {
            localStorage.setItem(SESSION_KEY, data.session_id);
            loadHistory(data.session_id);
            return;
          }
        }
      } catch {
        // Fallback to localStorage
      }

      // Fallback: use localStorage session
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        loadHistory(saved);
      }
    };

    init();
  }, [getToken, loadHistory]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();

      setState((prev) => ({
        ...prev,
        isLoading: true,
        error: null,
        messages: [...prev.messages, { role: "user", content: message }],
      }));

      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            message,
            session_id: state.sessionId,
          }),
          signal: abortRef.current.signal,
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();

        localStorage.setItem(SESSION_KEY, data.session_id);

        const apiKeyMissing =
          typeof data.response === "string" &&
          data.response.toLowerCase().includes("add your api key");

        setState((prev) => ({
          ...prev,
          isLoading: false,
          needsApiKey: apiKeyMissing || prev.needsApiKey,
          sessionId: data.session_id,
          messages: [
            ...prev.messages,
            {
              role: "assistant",
              content: data.response,
              agent_used: data.agent_used,
              agent_display_name: data.agent_display_name,
              download_url: data.download_url,
              agents_pipeline: data.agents_pipeline,
              suggested_actions: data.suggested_actions,
              email_draft: data.email_draft,
            },
          ],
        }));
      } catch (err: any) {
        if (err.name === "AbortError") return;
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: err.message || "Something went wrong",
        }));
      }
    },
    [getToken, state.sessionId]
  );

  const clearChat = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    localStorage.removeItem(SESSION_KEY);
    setState({
      messages: [],
      sessionId: null,
      isLoading: false,
      error: null,
      needsApiKey: false,
    });
  }, []);

  return { ...state, sendMessage, loadHistory, clearChat };
}
