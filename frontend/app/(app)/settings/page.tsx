"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import type { Memory } from "@/types";
import { Brain, Trash2, Shield, Loader2, Key, Plus, CheckCircle, XCircle, Eye, EyeOff, ChevronDown, Mail, Link2, Unlink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { SettingsSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal, FadeIn } from "@/components/motion";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";
import { CyberSelect } from "@/components/cyber/select";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const PROVIDERS = [
  { value: "groq", label: "Groq" },
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "together", label: "Together AI" },
  { value: "fireworks", label: "Fireworks AI" },
  { value: "mistral", label: "Mistral" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "perplexity", label: "Perplexity" },
  { value: "tavily", label: "Tavily (Search)" },
  { value: "custom", label: "Custom" },
];

const PROVIDER_BASE_URLS: Record<string, string> = {
  groq: "https://api.groq.com/openai/v1",
  openai: "https://api.openai.com/v1",
  openrouter: "https://openrouter.ai/api/v1",
  together: "https://api.together.xyz/v1",
  fireworks: "https://api.fireworks.ai/inference/v1",
  mistral: "https://api.mistral.ai/v1",
  deepseek: "https://api.deepseek.com/v1",
  perplexity: "https://api.perplexity.ai",
};

interface ApiKey {
  id: string;
  provider: string;
  label: string;
  key_suffix: string;
  base_url: string | null;
  is_primary: boolean;
  created_at: string | null;
}

export default function SettingsPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [chromaConnected, setChromaConnected] = useState(true);
  const [loading, setLoading] = useState(true);
  const [deletingAll, setDeletingAll] = useState(false);

  // API Keys state
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [keysLoading, setKeysLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [addingKey, setAddingKey] = useState(false);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [newKey, setNewKey] = useState({
    provider: "groq",
    api_key: "",
    label: "default",
    base_url: "https://api.groq.com/openai/v1",
    is_primary: false,
  });
  const [showKeyInput, setShowKeyInput] = useState(false);

  // Connected Accounts state
  const [integrations, setIntegrations] = useState<{ provider: string; account_email: string; is_active: boolean; connected_at: string | null }[]>([]);
  const [integrationsLoading, setIntegrationsLoading] = useState(true);
  const [disconnecting, setDisconnecting] = useState(false);

  useEffect(() => {
    loadMemories();
    loadApiKeys();
    loadIntegrations();

    // Check if we just connected an account (redirect from OAuth callback)
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected") === "gmail") {
      addToast("Gmail connected successfully!", "success");
      window.history.replaceState({}, "", "/settings");
      loadIntegrations();
    } else if (params.get("error") === "gmail_failed") {
      addToast("Gmail connection failed. Please try again.", "error");
      window.history.replaceState({}, "", "/settings");
    }
  }, []);

  async function loadMemories() {
    try {
      const token = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/memory`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const json = await res.json();
        setMemories(json.memories);
        setChromaConnected(json.connected !== false);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load memories", "error");
    } finally {
      setLoading(false);
    }
  }

  async function deleteMemory(id: string) {
    try {
      const token = await getToken();
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/memory/${id}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      loadMemories();
    } catch (e) {
      console.error(e);
      addToast("Failed to delete memory", "error");
    }
  }

  async function deleteAllMemories() {
    if (!confirm("Delete all stored memories? This cannot be undone.")) return;
    setDeletingAll(true);
    try {
      const token = await getToken();
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/memory`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      loadMemories();
      addToast("All memories purged", "success");
    } catch (e) {
      console.error(e);
      addToast("Failed to purge memories", "error");
    } finally {
      setDeletingAll(false);
    }
  }

  // ── API Key functions ──────────────────────────────────────
  async function loadApiKeys() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/settings/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setApiKeys(json.api_keys);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setKeysLoading(false);
    }
  }

  async function addApiKey() {
    if (!newKey.api_key.trim()) {
      addToast("API key cannot be empty", "error");
      return;
    }
    setAddingKey(true);
    try {
      const token = await getToken();
      const body: Record<string, unknown> = {
        provider: newKey.provider,
        api_key: newKey.api_key,
        label: newKey.label || "default",
        is_primary: newKey.is_primary,
      };
      if (newKey.base_url) {
        body.base_url = newKey.base_url;
      }
      const res = await fetch(`${API_URL}/settings/api-keys`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        addToast("API key added", "success");
        setShowAddForm(false);
        setNewKey({ provider: "groq", api_key: "", label: "default", base_url: "https://api.groq.com/openai/v1", is_primary: false });
        setShowKeyInput(false);
        loadApiKeys();
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to add key", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to add key", "error");
    } finally {
      setAddingKey(false);
    }
  }

  async function deleteApiKey(id: string) {
    try {
      const token = await getToken();
      await fetch(`${API_URL}/settings/api-keys/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      addToast("Key removed", "success");
      loadApiKeys();
    } catch (e) {
      console.error(e);
      addToast("Failed to delete key", "error");
    }
  }

  async function verifyApiKey(id: string) {
    setVerifyingId(id);
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/settings/api-keys/${id}/verify`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (res.ok) {
        addToast(json.message || "Key verified!", "success");
      } else {
        addToast(json.detail || "Verification failed", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Verification failed", "error");
    } finally {
      setVerifyingId(null);
    }
  }

  async function setPrimaryKey(id: string) {
    try {
      const token = await getToken();
      await fetch(`${API_URL}/settings/api-keys/${id}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ is_primary: true }),
      });
      addToast("Primary key updated", "success");
      loadApiKeys();
    } catch (e) {
      console.error(e);
      addToast("Failed to update", "error");
    }
  }

  // ── Integration functions ──────────────────────────────────────
  async function loadIntegrations() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/integrations/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        setIntegrations(json.integrations);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIntegrationsLoading(false);
    }
  }

  async function connectGmail() {
    try {
      const token = await getToken();
      const res = await fetch(`${API_URL}/integrations/gmail/auth-url`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = await res.json();
        // Open OAuth consent in same window (will redirect back)
        window.location.href = json.auth_url;
      } else {
        addToast("Failed to start Gmail connection", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to connect Gmail", "error");
    }
  }

  async function disconnectGmail() {
    setDisconnecting(true);
    try {
      const token = await getToken();
      await fetch(`${API_URL}/integrations/gmail`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      addToast("Gmail disconnected", "success");
      loadIntegrations();
    } catch (e) {
      console.error(e);
      addToast("Failed to disconnect Gmail", "error");
    } finally {
      setDisconnecting(false);
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex flex-col bg-[#0a0a0f]">
        <TopBar title="Settings" />
        <SettingsSkeleton />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Settings" />

      <PageTransition className="p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
            <GradientText from="#00ff88" to="#00d4ff">System Config</GradientText>
          </h2>
          <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
            Privacy // Memory // Preferences
          </p>
        </div>

        {/* API Keys Section */}
        <CyberCard variant="terminal" header="API Keys">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Key className="w-5 h-5 text-[#00d4ff]" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-mono">
                  <GlowText color="#e0e0e0" intensity="low">Provider Keys</GlowText>
                </p>
                <CyberLabel>
                  Bring your own API keys for LLM providers
                </CyberLabel>
              </div>
            </div>
            <CyberButton
              variant="default"
              size="sm"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Add Key
            </CyberButton>
          </div>

          {/* Add Key Form */}
          <AnimatePresence>
            {showAddForm && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3, ease }}
                className="overflow-hidden"
              >
                <div className="p-4 border border-[#2a2a3a] bg-[#0a0a0f] cyber-chamfer-sm mb-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-wider text-[#6b7280] mb-1 block">Provider</label>
                      <CyberSelect
                        value={newKey.provider}
                        onChange={(value) => setNewKey({ ...newKey, provider: value, base_url: PROVIDER_BASE_URLS[value] || "" })}
                        glowColor="#00d4ff"
                        options={PROVIDERS}
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-mono uppercase tracking-wider text-[#6b7280] mb-1 block">Label</label>
                      <input
                        type="text"
                        value={newKey.label}
                        onChange={(e) => setNewKey({ ...newKey, label: e.target.value })}
                        placeholder="default"
                        className="w-full bg-[#111118] border border-[#2a2a3a] text-xs font-mono px-3 py-2 text-[#e0e0e0] placeholder:text-[#4a4a5a] focus:border-[#00d4ff] focus:outline-none transition-colors"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-wider text-[#6b7280] mb-1 block">Base URL <span className="text-[#4a4a5a]">(auto-filled for known providers)</span></label>
                    <input
                      type="url"
                      value={newKey.base_url}
                      onChange={(e) => setNewKey({ ...newKey, base_url: e.target.value })}
                      placeholder="https://api.example.com/v1"
                      className="w-full bg-[#111118] border border-[#2a2a3a] text-xs font-mono px-3 py-2 text-[#e0e0e0] placeholder:text-[#4a4a5a] focus:border-[#00d4ff] focus:outline-none transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-mono uppercase tracking-wider text-[#6b7280] mb-1 block">API Key</label>
                    <div className="relative">
                      <input
                        type={showKeyInput ? "text" : "password"}
                        value={newKey.api_key}
                        onChange={(e) => setNewKey({ ...newKey, api_key: e.target.value })}
                        placeholder="sk-..."
                        className="w-full bg-[#111118] border border-[#2a2a3a] text-xs font-mono px-3 py-2 pr-9 text-[#e0e0e0] placeholder:text-[#4a4a5a] focus:border-[#00d4ff] focus:outline-none transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeyInput(!showKeyInput)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[#6b7280] hover:text-[#e0e0e0] transition-colors"
                      >
                        {showKeyInput ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="is_primary"
                      checked={newKey.is_primary}
                      onChange={(e) => setNewKey({ ...newKey, is_primary: e.target.checked })}
                      className="accent-[#00ff88]"
                    />
                    <label htmlFor="is_primary" className="text-[10px] font-mono uppercase tracking-wider text-[#6b7280]">
                      Set as primary LLM key
                    </label>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <CyberButton variant="default" size="sm" onClick={addApiKey} disabled={addingKey}>
                      {addingKey ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
                      Save Key
                    </CyberButton>
                    <CyberButton variant="ghost" size="sm" onClick={() => setShowAddForm(false)}>
                      Cancel
                    </CyberButton>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Keys List */}
          {keysLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-[#6b7280]" />
            </div>
          ) : apiKeys.length === 0 ? (
            <FadeIn>
              <div className="text-center py-6 border border-dashed border-[#2a2a3a]">
                <Key className="w-6 h-6 text-[#6b7280] mx-auto mb-2" strokeWidth={1.5} />
                <p className="text-xs font-mono text-[#6b7280]">No API keys configured</p>
                <p className="text-[10px] font-mono text-[#4a4a5a] mt-1">System defaults will be used</p>
              </div>
            </FadeIn>
          ) : (
            <div className="space-y-2">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-[#e0e0e0] uppercase">{key.provider}</span>
                      {key.is_primary && (
                        <CyberBadge variant="default" className="text-[9px]">PRIMARY</CyberBadge>
                      )}
                      <span className="text-[10px] font-mono text-[#6b7280]">{key.label}</span>
                    </div>
                    <p className="text-[10px] font-mono text-[#4a4a5a] mt-0.5">
                      ****{key.key_suffix}
                      {key.base_url && <span className="ml-2 text-[#3a3a4a]">@ {key.base_url}</span>}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {!key.is_primary && (
                      <button
                        onClick={() => setPrimaryKey(key.id)}
                        className="text-[10px] font-mono text-[#6b7280] hover:text-[#00ff88] px-2 py-1 border border-[#2a2a3a] hover:border-[#00ff88] transition-colors"
                        title="Set as primary"
                      >
                        PRIMARY
                      </button>
                    )}
                    <button
                      onClick={() => verifyApiKey(key.id)}
                      disabled={verifyingId === key.id}
                      className="text-[#6b7280] hover:text-[#00d4ff] transition-colors p-1"
                      title="Verify key"
                    >
                      {verifyingId === key.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <CheckCircle className="w-3.5 h-3.5" />
                      )}
                    </button>
                    <button
                      onClick={() => deleteApiKey(key.id)}
                      className="text-[#6b7280] hover:text-[#ff3366] transition-colors p-1"
                      title="Delete key"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CyberCard>

        {/* Connected Accounts Section */}
        <CyberCard variant="terminal" header="Connected Accounts">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Link2 className="w-5 h-5 text-[#8b5cf6]" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-mono">
                  <GlowText color="#e0e0e0" intensity="low">Integrations</GlowText>
                </p>
                <CyberLabel>
                  Connect external services for agent access
                </CyberLabel>
              </div>
            </div>
          </div>

          {integrationsLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-[#6b7280]" />
            </div>
          ) : (
            <div className="space-y-3">
              {/* Gmail */}
              {(() => {
                const gmail = integrations.find((i) => i.provider === "gmail");
                return (
                  <div>
                    <div className="flex items-center gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm">
                      <div className="w-8 h-8 flex items-center justify-center border border-[#2a2a3a] bg-[#111118]">
                        <Mail className="w-4 h-4 text-[#ff3366]" strokeWidth={1.5} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-mono font-semibold text-[#e0e0e0]">Gmail</p>
                        {gmail ? (
                          <p className="text-[10px] font-mono text-[#00ff88]">
                            Connected: {gmail.account_email}
                          </p>
                        ) : (
                          <p className="text-[10px] font-mono text-[#6b7280]">
                            Not connected
                          </p>
                        )}
                      </div>
                      {gmail ? (
                        <CyberButton
                          variant="ghost"
                          size="sm"
                          onClick={disconnectGmail}
                          disabled={disconnecting}
                        >
                          {disconnecting ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" />
                          ) : (
                            <Unlink className="w-3.5 h-3.5 mr-1" />
                          )}
                          Disconnect
                        </CyberButton>
                      ) : (
                        <CyberButton
                          variant="default"
                          size="sm"
                          onClick={connectGmail}
                        >
                          <Link2 className="w-3.5 h-3.5 mr-1" />
                          Connect
                        </CyberButton>
                      )}
                    </div>
                    {!gmail && (
                      <p className="text-[10px] font-mono text-[#ff9900]/70 mt-1.5 ml-11">
                        Google OAuth verification in progress — available for test users only
                      </p>
                    )}
                  </div>
                );
              })()}
            </div>
          )}
        </CyberCard>

        {/* Memory Section */}
        <CyberCard variant="terminal" header="Memory Bank">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-[#00ff88]" strokeWidth={1.5} />
              <div>
                <p className="text-sm font-mono">
                  <GlowText color="#e0e0e0" intensity="low">Stored Memories</GlowText>
                </p>
                <CyberLabel>
                  {chromaConnected
                    ? `${memories.length} entries in semantic memory`
                    : "ChromaDB not connected"}
                </CyberLabel>
              </div>
            </div>
            <CyberButton
              variant="destructive"
              size="sm"
              onClick={deleteAllMemories}
              disabled={deletingAll || memories.length === 0}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Purge All
            </CyberButton>
          </div>

          {!chromaConnected ? (
            <FadeIn>
            <div className="text-center py-8 border border-dashed border-[#ff3366]/30 bg-[#ff3366]/5">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
                className="inline-block"
              >
                <Shield className="w-8 h-8 text-[#ff3366] mx-auto mb-2" strokeWidth={1.5} />
              </motion.div>
              <p className="text-xs font-mono">
                <GlowText color="#ff3366" intensity="low">ChromaDB disconnected</GlowText>
              </p>
              <p className="text-[10px] font-mono text-[#6b7280] mt-1">
                Vector memory service is unreachable
              </p>
            </div>
            </FadeIn>
          ) : memories.length === 0 ? (
            <FadeIn>
            <div className="text-center py-8 border border-dashed border-[#2a2a3a]">
              <motion.div
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 20, delay: 0.1 }}
                className="inline-block"
              >
                <Shield className="w-8 h-8 text-[#6b7280] mx-auto mb-2" strokeWidth={1.5} />
              </motion.div>
              <p className="text-xs font-mono">
                <GlowText color="#6b7280" intensity="low">Memory bank empty</GlowText>
              </p>
            </div>
            </FadeIn>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  className="flex items-start gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm group"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono leading-relaxed">
                      <GlowText color="#e0e0e0" intensity="low">{memory.content}</GlowText>
                    </p>
                    {memory.metadata && (
                      <div className="flex gap-2 mt-1">
                        {Object.entries(memory.metadata)
                          .filter(([k]) => k !== "user_id" && k !== "content")
                          .slice(0, 3)
                          .map(([k, v]) => (
                            <CyberBadge key={k} variant="outline" className="text-[9px]">
                              {k}: {String(v)}
                            </CyberBadge>
                          ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => deleteMemory(memory.id)}
                    className="text-[#6b7280] hover:text-[#ff3366] opacity-0 group-hover:opacity-100 transition-all shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CyberCard>

        {/* About */}
        <CyberCard header="System Info">
          <div className="space-y-3">
            <div className="flex justify-between text-xs font-mono">
              <CyberLabel>Version</CyberLabel>
              <GlowText color="#00ff88" intensity="low" className="text-xs font-mono">v0.1.0</GlowText>
            </div>
            <div className="flex justify-between text-xs font-mono">
              <CyberLabel>Architecture</CyberLabel>
              <GlowText color="#00d4ff" intensity="low" className="text-xs font-mono">Supervisor + 9 Domain Agents</GlowText>
            </div>
            <div className="flex justify-between text-xs font-mono">
              <CyberLabel>Memory</CyberLabel>
              <GlowText color="#ff00ff" intensity="low" className="text-xs font-mono">Chroma Vector DB</GlowText>
            </div>
            <div className="flex justify-between text-xs font-mono">
              <CyberLabel>Backend</CyberLabel>
              <GlowText color="#ffcc00" intensity="low" className="text-xs font-mono">FastAPI + Groq LLM</GlowText>
            </div>
          </div>
        </CyberCard>
      </PageTransition>
    </div>
  );
}
