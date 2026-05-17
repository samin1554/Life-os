"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { downloadFile } from "@/lib/download";
import type { GeneratedFile } from "@/types";
import {
  FileText,
  Table2,
  FileSpreadsheet,
  Download,
  Trash2,
  Loader2,
  Filter,
} from "lucide-react";
import { motion } from "framer-motion";
import { DownloadsSkeleton } from "@/components/cyber/skeleton";
import { PageTransition, ScrollReveal } from "@/components/motion";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  docx: <FileText className="w-5 h-5 text-[#00aaff]" />,
  pdf: <FileText className="w-5 h-5 text-[#ff3366]" />,
  xlsx: <Table2 className="w-5 h-5 text-[#00ff88]" />,
};

const FORMAT_COLORS: Record<string, string> = {
  docx: "#00aaff",
  pdf: "#ff3366",
  xlsx: "#00ff88",
};

const FORMAT_LABELS: Record<string, string> = {
  docx: "Word",
  pdf: "PDF",
  xlsx: "Excel",
};

const TEMPLATE_LABELS: Record<string, string> = {
  travel_guide: "Travel Guide",
  budget_tracker: "Budget Tracker",
  research_report: "Research Report",
  project_plan: "Project Plan",
  comparison_sheet: "Comparison",
  modern_report: "Report",
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export default function DownloadsPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [files, setFiles] = useState<GeneratedFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    loadFiles();
  }, [filter]);

  async function loadFiles() {
    setLoading(true);
    try {
      const token = await getToken();
      const url =
        filter === "all"
          ? `${API_BASE}/files?limit=100`
          : `${API_BASE}/files?format=${filter}&limit=100`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load files", "error");
    } finally {
      setLoading(false);
    }
  }

  async function deleteFile(id: string) {
    setDeleting(id);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/files/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setFiles((prev) => prev.filter((f) => f.id !== id));
        addToast("File deleted", "success");
      } else {
        addToast("Failed to delete file", "error");
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to delete file", "error");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Downloads" />

      <PageTransition className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
              <GradientText from="#00aaff" to="#00ff88">Generated Files</GradientText>
            </h2>
            <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
              {files.length} files // Download or manage your documents
            </p>
          </div>

          {/* Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-[#6b7280]" />
            {["all", "docx", "xlsx", "pdf"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 text-[10px] font-mono uppercase tracking-wider border transition-all cyber-chamfer-sm ${
                  filter === f
                    ? "border-[#00ff88] text-[#00ff88] bg-[#00ff88]/10"
                    : "border-[#2a2a3a] text-[#6b7280] hover:border-[#6b7280]"
                }`}
              >
                {f === "all" ? "All" : FORMAT_LABELS[f] || f}
              </button>
            ))}
          </div>
        </div>

        {/* File List */}
        {loading ? (
          <DownloadsSkeleton />
        ) : files.length === 0 ? (
          <CyberCard variant="terminal">
            <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
              <FileSpreadsheet className="w-10 h-10 text-[#6b7280]/40" />
              <p className="text-sm font-mono">
                <GlowText color="#6b7280" intensity="low">No generated files yet.</GlowText>
              </p>
              <p className="text-xs font-mono text-[#6b7280]/60 max-w-md">
                Ask your coach to create documents, spreadsheets, or reports.
                They will appear here for download.
              </p>
            </div>
          </CyberCard>
        ) : (
          <div className="space-y-3">
            {files.map((file, idx) => {
              const color = FORMAT_COLORS[file.file_format] || "#6b7280";
              return (
                <motion.div
                  key={file.id}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, ease, delay: 0.04 * idx }}
                  whileHover={{ x: 4 }}
                >
                <CyberCard
                  hoverEffect
                  className="flex items-center gap-4"
                >
                  {/* Icon */}
                  <div
                    className="w-10 h-10 flex items-center justify-center border cyber-chamfer-sm shrink-0"
                    style={{
                      borderColor: `${color}40`,
                      backgroundColor: `${color}10`,
                    }}
                  >
                    {FORMAT_ICONS[file.file_format] || (
                      <FileText className="w-5 h-5 text-[#6b7280]" />
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-mono truncate">
                        <GlowText color="#e0e0e0" intensity="low">{file.original_name}</GlowText>
                      </h3>
                      <CyberBadge
                        variant="outline"
                        className="text-[10px] shrink-0"
                        style={{ borderColor: `${color}40`, color }}
                      >
                        {FORMAT_LABELS[file.file_format] || file.file_format}
                      </CyberBadge>
                      {file.template_used && (
                        <CyberBadge
                          variant="outline"
                          className="text-[10px] shrink-0"
                        >
                          {TEMPLATE_LABELS[file.template_used] ||
                            file.template_used}
                        </CyberBadge>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <CyberLabel>{formatBytes(file.file_size_bytes)}</CyberLabel>
                      <CyberLabel>//</CyberLabel>
                      <CyberLabel>
                        {new Date(file.created_at).toLocaleDateString()}
                      </CyberLabel>
                      {file.task_description && (
                        <>
                          <CyberLabel>//</CyberLabel>
                          <CyberLabel className="truncate max-w-[300px]">
                            {file.task_description}
                          </CyberLabel>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <CyberButton
                      variant="default"
                      size="sm"
                      disabled={downloadingId === file.id}
                      onClick={async () => {
                        setDownloadingId(file.id);
                        try {
                          await downloadFile(
                            `/files/${file.id}/download`,
                            getToken,
                            file.original_name
                          );
                        } catch (e) {
                          console.error("Download failed:", e);
                        } finally {
                          setDownloadingId(null);
                        }
                      }}
                    >
                      {downloadingId === file.id ? (
                        <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5 mr-1.5" />
                      )}
                      {downloadingId === file.id ? "Downloading..." : "Download"}
                    </CyberButton>
                    <CyberButton
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteFile(file.id)}
                      disabled={deleting === file.id}
                    >
                      {deleting === file.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="w-3.5 h-3.5 text-[#ff3366]" />
                      )}
                    </CyberButton>
                  </div>
                </CyberCard>
                </motion.div>
              );
            })}
          </div>
        )}
      </PageTransition>
    </div>
  );
}
