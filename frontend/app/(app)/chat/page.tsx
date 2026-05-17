"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberButton } from "@/components/cyber/button";
import { CyberInput } from "@/components/cyber/input";
import { useChat } from "@/hooks/useChat";
import { downloadFile } from "@/lib/download";
import { Send, Trash2, Bot, User, Zap, Download, FileText, Table2, AlertCircle, Loader2, Search, Target, Flag, Heart, PenTool, Users, BarChart3, ChevronRight, Paperclip, X } from "lucide-react";
import { motion } from "framer-motion";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { GlowText, GradientText, ChatMessageText } from "@/components/typography";
import { useToast } from "@/components/toast";
import { ApiKeyDisclaimer } from "@/components/api-key-disclaimer";
import { EmailDraftCard } from "@/components/chat/email-draft-card";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const AGENT_COLORS: Record<string, string> = {
  focus: "#00ff88",
  health: "#00d4ff",
  execution: "#ff00ff",
  chaos_triage: "#ff3366",
  goals: "#ffcc00",
  delegate: "#8b5cf6",
  research: "#00aaff",
  worker: "#ff5500",
};

const QUICK_PROMPTS = [
  "What should I focus on today?",
  "How am I doing this week?",
  "Help me plan my day",
  "Research best laptops under $1000",
  "Create a budget spreadsheet for my Japan trip",
  "Plan a trip and make a travel guide",
];

const EXPORT_PROMPTS: Record<string, string> = {
  spreadsheet: "Turn this into a comparison spreadsheet",
  pdf: "Turn this into a PDF report",
};

const SUGGESTION_ICONS: Record<string, React.ReactNode> = {
  search: <Search className="w-3 h-3" />,
  "file-text": <FileText className="w-3 h-3" />,
  target: <Target className="w-3 h-3" />,
  flag: <Flag className="w-3 h-3" />,
  heart: <Heart className="w-3 h-3" />,
  "pen-tool": <PenTool className="w-3 h-3" />,
  users: <Users className="w-3 h-3" />,
  "bar-chart": <BarChart3 className="w-3 h-3" />,
  zap: <Zap className="w-3 h-3" />,
};

export default function ChatPage() {
  const { getToken, userId } = useAuth();
  const { addToast } = useToast();
  const { messages, sessionId, isLoading, error, needsApiKey, sendMessage, clearChat } =
    useChat();
  const [input, setInput] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [attachedFile, setAttachedFile] = useState<{ id: string; name: string } | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    let message = input.trim();
    if (attachedFile) {
      message = `[Attached: ${attachedFile.name}]\n\n${message}`;
      setAttachedFile(null);
    }
    sendMessage(message);
    setInput("");
  };

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      addToast("File too large (max 10MB)", "error");
      return;
    }
    setUploadingFile(true);
    try {
      const token = await getToken();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("purpose", "chat");
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
      const res = await fetch(`${API_URL}/uploads?purpose=chat`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setAttachedFile({ id: data.id, name: file.name });
        addToast(`${file.name} attached`, "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Upload failed", "error");
      }
    } catch (err) {
      console.error(err);
      addToast("Upload failed", "error");
    } finally {
      setUploadingFile(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f]">
      <TopBar title="AI Coach" />
      {needsApiKey && <ApiKeyDisclaimer />}

      <PageTransition className="flex-1 flex flex-col max-w-5xl mx-auto w-full">
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-[#2a2a3a] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-5 h-5 text-[#00ff88]" strokeWidth={1.5} />
            <div>
              <h2 className="text-sm font-[var(--font-orbitron)] uppercase tracking-wider">
                <GradientText from="#00ff88" to="#00d4ff">Life Coach</GradientText>
              </h2>
              <p className="text-[10px] font-mono text-[#6b7280] uppercase tracking-wider">
                Auto-dispatches specialist agents when needed
              </p>
            </div>
          </div>
          <CyberButton variant="ghost" size="sm" onClick={clearChat}>
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            Clear
          </CyberButton>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
              <Bot className="w-12 h-12 text-[#00ff88]/30" strokeWidth={1} />
              <div>
                <p className="text-sm font-mono mb-1">
                  <GlowText color="#00ff88" intensity="low">Your AI Life Coach</GlowText>
                </p>
                <p className="text-xs font-mono text-[#6b7280]/60">
                  Chat naturally — specialist agents are dispatched automatically
                  when needed.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <motion.button
                    key={prompt}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                    whileHover={{ x: 4 }}
                    onClick={() => setInput(prompt)}
                    className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider
                      bg-[#12121a] border border-[#2a2a3a] text-[#6b7280]
                      hover:border-[#00ff88]/40 hover:text-[#00ff88]
                      transition-all duration-150 cyber-chamfer-sm"
                  >
                    {prompt}
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg, i) => {
                const delayIndex = Math.max(0, i - (messages.length - 5));
                return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, ease, delay: 0.04 * delayIndex }}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] p-4 cyber-chamfer-sm ${
                      msg.role === "user"
                        ? "bg-[#00ff88]/10 border border-[#00ff88]/20"
                        : "bg-[#12121a] border border-[#2a2a3a]"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      {msg.role === "user" ? (
                        <User className="w-3.5 h-3.5 text-[#00ff88]" />
                      ) : (
                        <Bot className="w-3.5 h-3.5 text-[#00d4ff]" />
                      )}
                      <span className="text-[10px] font-mono uppercase tracking-wider">
                        {msg.role === "user" ? (
                          <GlowText color="#00ff88" intensity="low">You</GlowText>
                        ) : (
                          <GlowText color="#00d4ff" intensity="low">Coach</GlowText>
                        )}
                      </span>
                    </div>
                    {msg.role === "assistant" && msg.agents_pipeline && msg.agents_pipeline.length > 1 && (
                      <div className="flex items-center gap-1.5 mb-2 text-[10px] font-mono text-[#6b7280]">
                        {msg.agents_pipeline.map((agent, i) => (
                          <span key={agent} className="flex items-center gap-1">
                            {i > 0 && <span>→</span>}
                            <span style={{ color: AGENT_COLORS[agent] || "#6b7280" }}>{agent}</span>
                          </span>
                        ))}
                      </div>
                    )}
                    {msg.role === "assistant" && msg.agent_used && (
                      <div
                        className="flex items-center gap-1.5 mb-2 text-[10px] font-mono uppercase tracking-wider"
                        style={{ color: AGENT_COLORS[msg.agent_used] || "#6b7280" }}
                      >
                        <Zap className="w-3 h-3" />
                        <span>Powered by {msg.agent_display_name || msg.agent_used}</span>
                      </div>
                    )}
                    <ChatMessageText content={msg.content} role={msg.role as "user" | "assistant"} />
                    {/* Download button when file was generated */}
                    {msg.role === "assistant" && msg.download_url && (
                      <button
                        onClick={async () => {
                          setDownloading(true);
                          try {
                            await downloadFile(msg.download_url!, getToken);
                          } catch (e) {
                            console.error("Download failed:", e);
                            addToast("Download failed", "error");
                          } finally {
                            setDownloading(false);
                          }
                        }}
                        disabled={downloading}
                        className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#00ff88]/10
                          border border-[#00ff88]/30 text-[#00ff88] text-xs font-mono uppercase
                          tracking-wider hover:bg-[#00ff88]/20 transition-all cyber-chamfer-sm
                          disabled:opacity-50"
                      >
                        {downloading ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Download className="w-3.5 h-3.5" />
                        )}
                        {downloading ? "Downloading..." : "Download Document"}
                      </button>
                    )}
                    {/* Worker ran but no file — show help */}
                    {msg.role === "assistant" && msg.agent_used === "worker" && !msg.download_url && (
                      <div className="mt-3 flex items-center gap-2 text-[10px] font-mono text-[#ffcc00]">
                        <AlertCircle className="w-3 h-3" />
                        <span>No file was generated. Try being more specific, e.g. "Create a spreadsheet..."</span>
                      </div>
                    )}
                    {/* Research-only message — offer export */}
                    {msg.role === "assistant" && msg.agent_used === "research" && !msg.download_url && (
                      <motion.div
                        className="mt-3 flex items-center gap-2"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, ease, delay: 0.15 }}
                      >
                        <motion.button
                          whileTap={{ scale: 0.95 }}
                          onClick={() => sendMessage(EXPORT_PROMPTS.spreadsheet)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#00aaff]/10
                            border border-[#00aaff]/30 text-[#00aaff] text-[10px] font-mono uppercase
                            tracking-wider hover:bg-[#00aaff]/20 transition-all cyber-chamfer-sm"
                        >
                          <Table2 className="w-3 h-3" />
                          Export as Spreadsheet
                        </motion.button>
                        <motion.button
                          whileTap={{ scale: 0.95 }}
                          onClick={() => sendMessage(EXPORT_PROMPTS.pdf)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#ff3366]/10
                            border border-[#ff3366]/30 text-[#ff3366] text-[10px] font-mono uppercase
                            tracking-wider hover:bg-[#ff3366]/20 transition-all cyber-chamfer-sm"
                        >
                          <FileText className="w-3 h-3" />
                          Export as PDF
                        </motion.button>
                      </motion.div>
                    )}
                    {/* Email draft card */}
                    {msg.role === "assistant" && msg.email_draft && (
                      <EmailDraftCard
                        draft={msg.email_draft}
                        getToken={getToken}
                      />
                    )}
                    {/* Suggested next actions from agent collaboration */}
                    {msg.role === "assistant" && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-[#6b7280]">
                          <ChevronRight className="w-3 h-3" />
                          <GlowText color="#ffcc00" intensity="low">Suggested next</GlowText>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {msg.suggested_actions.map((action, idx) => {
                            const hintColor = AGENT_COLORS[action.agent_hint || ""] || "#6b7280";
                            return (
                              <motion.button
                                key={idx}
                                initial={{ opacity: 0, x: -8 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.3, ease, delay: 0.1 + 0.06 * idx }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => sendMessage(action.message)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5
                                  bg-[#1a1a2e] border text-[10px] font-mono uppercase
                                  tracking-wider transition-all cyber-chamfer-sm"
                                style={{
                                  borderColor: `${hintColor}30`,
                                  color: `${hintColor}cc`,
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.borderColor = `${hintColor}60`;
                                  e.currentTarget.style.color = hintColor;
                                  e.currentTarget.style.backgroundColor = `${hintColor}10`;
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.borderColor = `${hintColor}30`;
                                  e.currentTarget.style.color = `${hintColor}cc`;
                                  e.currentTarget.style.backgroundColor = "#1a1a2e";
                                }}
                              >
                                {SUGGESTION_ICONS[action.icon || "zap"] || <Zap className="w-3 h-3" />}
                                {action.label}
                              </motion.button>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
                );
              })}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-[#12121a] border border-[#2a2a3a] p-4 cyber-chamfer-sm">
                    <div className="flex items-center gap-2">
                      <Bot className="w-3.5 h-3.5 text-[#00d4ff]" />
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-[#00d4ff] rounded-full animate-bounce" />
                        <span
                          className="w-1.5 h-1.5 bg-[#00d4ff] rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        />
                        <span
                          className="w-1.5 h-1.5 bg-[#00d4ff] rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="p-4 bg-[#ff3366]/10 border border-[#ff3366]/30 cyber-chamfer-sm">
              <p className="text-xs font-mono">
                <GlowText color="#ff3366" intensity="medium">Error: {error}</GlowText>
              </p>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-6 py-4 border-t border-[#2a2a3a]">
          {/* Attached file chip */}
          {attachedFile && (
            <div className="flex items-center gap-2 mb-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#00d4ff]/10 border border-[#00d4ff]/30 text-[10px] font-mono text-[#00d4ff]">
                <FileText className="w-3 h-3" />
                {attachedFile.name}
                <button onClick={() => setAttachedFile(null)} className="ml-1 hover:text-white">
                  <X className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex items-end gap-3">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.txt,.md,.csv,.png,.jpg,.jpeg"
              onChange={handleFileAttach}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingFile || isLoading}
              className="p-2 text-[#6b7280] hover:text-[#00d4ff] transition-colors disabled:opacity-50"
              title="Attach file"
            >
              {uploadingFile ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Paperclip className="w-4 h-4" />
              )}
            </button>
            <div className="flex-1">
              <CyberInput
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Talk to your coach..."
                disabled={isLoading}
                className="w-full"
              />
            </div>
            <CyberButton
              type="submit"
              variant="glitch"
              size="icon"
              disabled={!input.trim() || isLoading}
            >
              <Send className="w-4 h-4" />
            </CyberButton>
          </form>
        </div>
      </PageTransition>
    </div>
  );
}
