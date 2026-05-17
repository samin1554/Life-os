"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Mail, Send, Pencil, Check, X, Loader2, AlertCircle } from "lucide-react";
import { CyberButton } from "@/components/cyber/button";
import { useToast } from "@/components/toast";
import type { EmailDraft } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface EmailDraftCardProps {
  draft: EmailDraft;
  getToken: () => Promise<string | null>;
  onUpdate?: (updated: EmailDraft) => void;
}

export function EmailDraftCard({ draft, getToken, onUpdate }: EmailDraftCardProps) {
  const { addToast } = useToast();
  const [sending, setSending] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editBody, setEditBody] = useState(draft.body_preview || "");
  const [savingEdit, setSavingEdit] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSend = async () => {
    if (!confirm("Send this email?")) return;
    setSending(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/integrations/gmail/drafts/${draft.draft_id}/send`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSent(true);
        addToast("Email sent!", "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to send", "error");
      }
    } catch {
      addToast("Failed to send email", "error");
    } finally {
      setSending(false);
    }
  };


  const handleSaveEdit = async () => {
    setSavingEdit(true);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/integrations/gmail/drafts/${draft.draft_id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ body: editBody }),
      });
      if (res.ok) {
        addToast("Draft updated", "success");
        onUpdate?.({ ...draft, body_preview: editBody });
        setEditing(false);
      } else {
        addToast("Failed to update draft", "error");
      }
    } catch {
      addToast("Failed to update draft", "error");
    } finally {
      setSavingEdit(false);
    }
  };

  if (sent) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mt-3 p-3 bg-[#00ff88]/5 border border-[#00ff88]/30 cyber-chamfer-sm"
      >
        <div className="flex items-center gap-2">
          <Check className="w-4 h-4 text-[#00ff88]" />
          <p className="text-[11px] font-mono text-[#00ff88]">Email sent successfully</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="mt-3 relative"
    >
      {/* Rotating border wrapper */}
      <div className="relative overflow-hidden cyber-chamfer-sm" style={{ padding: "1.5px" }}>
        <div
          className="absolute inset-[-50%] w-[200%] h-[200%]"
          style={{
            background: "conic-gradient(from 0deg, transparent 0deg, #ff336620 60deg, #ff336650 120deg, #ff336620 180deg, transparent 240deg, #ff336615 300deg, transparent 360deg)",
            animation: "border-rotate 4s linear infinite",
          }}
        />
        <div className="relative bg-[#0d0d14] cyber-chamfer-sm">
          {/* Corner accents */}
          <span className="absolute top-0 left-0 w-3 h-3 border-t border-l border-[#ff336640] z-10" />
          <span className="absolute top-0 right-0 w-3 h-3 border-t border-r border-[#ff336640] z-10" />
          <span className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-[#ff336640] z-10" />
          <span className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-[#ff336640] z-10" />

          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[#2a2a3a]">
            <Mail className="w-3.5 h-3.5 text-[#ff3366]" />
            <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#ff3366]">
              Email Draft
            </span>
          </div>

          {/* Body */}
          <div className="px-3 py-2 space-y-1.5">
            {draft.to && (
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-mono text-[#6b7280] shrink-0">To:</span>
                <span className="text-[10px] font-mono text-[#e0e0e0] truncate">{draft.to}</span>
              </div>
            )}
            {draft.subject && (
              <div className="flex items-start gap-2">
                <span className="text-[10px] font-mono text-[#6b7280] shrink-0">Subject:</span>
                <span className="text-[10px] font-mono text-[#e0e0e0] truncate">{draft.subject}</span>
              </div>
            )}

            {editing ? (
              <div className="mt-2">
                <textarea
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                  className="w-full h-32 bg-[#0a0a0f] border border-[#2a2a3a] p-2 text-[11px] font-mono text-[#e0e0e0] resize-none focus:border-[#ff3366]/50 focus:outline-none cyber-chamfer-sm"
                  placeholder="Edit your draft..."
                />
                <div className="flex items-center gap-2 mt-2">
                  <CyberButton variant="default" size="sm" onClick={handleSaveEdit} disabled={savingEdit}>
                    {savingEdit ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                    Save
                  </CyberButton>
                  <CyberButton variant="ghost" size="sm" onClick={() => { setEditing(false); setEditBody(draft.body_preview || ""); }}>
                    <X className="w-3 h-3" />
                    Cancel
                  </CyberButton>
                </div>
              </div>
            ) : (
              <div className="mt-1 p-2 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm max-h-40 overflow-y-auto">
                <pre className="text-[11px] font-mono text-[#9ca3af] whitespace-pre-wrap leading-relaxed">
                  {draft.body_preview}
                </pre>
              </div>
            )}
          </div>

          {/* Actions */}
          {!editing && (
            <div className="px-3 py-2 border-t border-[#2a2a3a] flex items-center gap-2">
              <CyberButton variant="default" size="sm" onClick={handleSend} disabled={sending}>
                {sending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3" />}
                Send
              </CyberButton>
              <CyberButton variant="outline" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="w-3 h-3" />
                Edit
              </CyberButton>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
