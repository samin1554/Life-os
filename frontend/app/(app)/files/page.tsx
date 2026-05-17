"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { TopBar } from "@/components/layout/topbar";
import { CyberCard } from "@/components/cyber/card";
import { CyberButton } from "@/components/cyber/button";
import { CyberBadge } from "@/components/cyber/badge";
import { UploadDropzone } from "@/components/uploads/upload-dropzone";
import { downloadFile } from "@/lib/download";
import type { GeneratedFile } from "@/types";
import {
  FileText,
  Table2,
  Image,
  Upload,
  Download,
  Trash2,
  Loader2,
  FileUp,
} from "lucide-react";
import { motion } from "framer-motion";
import { PageTransition, ScrollReveal, FadeIn } from "@/components/motion";
import { GlowText, GradientText, CyberLabel } from "@/components/typography";
import { useToast } from "@/components/toast";

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface UploadedFileItem {
  id: string;
  original_name: string;
  mime_type: string;
  file_size_bytes: number;
  purpose: string;
  has_extracted_text: boolean;
  created_at: string | null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(mime: string) {
  if (mime.startsWith("image/")) return <Image className="w-4 h-4 text-[#ff00ff]" />;
  if (mime.includes("pdf")) return <FileText className="w-4 h-4 text-[#ff3366]" />;
  if (mime.includes("spreadsheet") || mime.includes("csv")) return <Table2 className="w-4 h-4 text-[#00ff88]" />;
  return <FileText className="w-4 h-4 text-[#00d4ff]" />;
}

export default function FilesPage() {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [tab, setTab] = useState<"uploaded" | "generated">("uploaded");
  const [uploads, setUploads] = useState<UploadedFileItem[]>([]);
  const [generated, setGenerated] = useState<GeneratedFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFiles();
  }, []);

  async function loadFiles() {
    setLoading(true);
    try {
      const token = await getToken();
      const headers = { Authorization: `Bearer ${token}` };

      const [uploadsRes, generatedRes] = await Promise.all([
        fetch(`${API_URL}/uploads`, { headers }),
        fetch(`${API_URL}/files`, { headers }),
      ]);

      if (uploadsRes.ok) {
        const data = await uploadsRes.json();
        setUploads(data.files || []);
      }
      if (generatedRes.ok) {
        const data = await generatedRes.json();
        setGenerated(data.files || []);
      }
    } catch (e) {
      console.error(e);
      addToast("Failed to load files", "error");
    } finally {
      setLoading(false);
    }
  }

  async function deleteUpload(id: string) {
    try {
      const token = await getToken();
      await fetch(`${API_URL}/uploads/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      addToast("File deleted", "success");
      loadFiles();
    } catch (e) {
      console.error(e);
      addToast("Delete failed", "error");
    }
  }

  async function handleDownload(file: GeneratedFile) {
    try {
      await downloadFile(`/files/${file.id}/download`, getToken, file.filename);
    } catch (e) {
      console.error(e);
      addToast("Download failed", "error");
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <TopBar title="Files" />

      <PageTransition className="p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-[var(--font-orbitron)] font-bold uppercase tracking-widest">
            <GradientText from="#00d4ff" to="#ff00ff">File Manager</GradientText>
          </h2>
          <p className="text-xs font-mono text-[#6b7280] mt-1 uppercase tracking-wider">
            Uploads // Documents // Generated Files
          </p>
        </div>

        {/* Upload Zone */}
        <CyberCard header="Upload">
          <UploadDropzone onUploadComplete={loadFiles} />
        </CyberCard>

        {/* Tab Selector */}
        <div className="flex gap-2">
          <button
            onClick={() => setTab("uploaded")}
            className={`px-4 py-2 text-xs font-mono uppercase tracking-wider border transition-colors ${
              tab === "uploaded"
                ? "border-[#00d4ff] text-[#00d4ff] bg-[#00d4ff]/5"
                : "border-[#2a2a3a] text-[#6b7280] hover:border-[#4a4a5a]"
            }`}
          >
            <FileUp className="w-3.5 h-3.5 inline mr-1.5" />
            Uploaded ({uploads.length})
          </button>
          <button
            onClick={() => setTab("generated")}
            className={`px-4 py-2 text-xs font-mono uppercase tracking-wider border transition-colors ${
              tab === "generated"
                ? "border-[#00ff88] text-[#00ff88] bg-[#00ff88]/5"
                : "border-[#2a2a3a] text-[#6b7280] hover:border-[#4a4a5a]"
            }`}
          >
            <Download className="w-3.5 h-3.5 inline mr-1.5" />
            Generated ({generated.length})
          </button>
        </div>

        {/* File List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-[#6b7280]" />
          </div>
        ) : tab === "uploaded" ? (
          <div className="space-y-2">
            {uploads.length === 0 ? (
              <FadeIn>
                <div className="text-center py-12 border border-dashed border-[#2a2a3a]">
                  <Upload className="w-8 h-8 text-[#6b7280] mx-auto mb-3" strokeWidth={1.5} />
                  <p className="text-xs font-mono text-[#6b7280]">No uploaded files yet</p>
                  <p className="text-[10px] font-mono text-[#4a4a5a] mt-1">
                    Upload PDFs, docs, or images for AI analysis
                  </p>
                </div>
              </FadeIn>
            ) : (
              uploads.map((file, i) => (
                <ScrollReveal key={file.id} delay={i * 0.05}>
                  <div className="flex items-center gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm group hover:border-[#3a3a4a] transition-colors">
                    {getFileIcon(file.mime_type)}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-[#e0e0e0] truncate">{file.original_name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] font-mono text-[#4a4a5a]">{formatSize(file.file_size_bytes)}</span>
                        {file.has_extracted_text && (
                          <CyberBadge variant="outline" className="text-[9px]">TEXT</CyberBadge>
                        )}
                        <span className="text-[10px] font-mono text-[#3a3a4a]">{file.purpose}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => deleteUpload(file.id)}
                      className="text-[#6b7280] hover:text-[#ff3366] opacity-0 group-hover:opacity-100 transition-all p-1"
                      title="Delete"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </ScrollReveal>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {generated.length === 0 ? (
              <FadeIn>
                <div className="text-center py-12 border border-dashed border-[#2a2a3a]">
                  <Download className="w-8 h-8 text-[#6b7280] mx-auto mb-3" strokeWidth={1.5} />
                  <p className="text-xs font-mono text-[#6b7280]">No generated files yet</p>
                  <p className="text-[10px] font-mono text-[#4a4a5a] mt-1">
                    Ask the Worker Agent to create documents for you
                  </p>
                </div>
              </FadeIn>
            ) : (
              generated.map((file, i) => (
                <ScrollReveal key={file.id} delay={i * 0.05}>
                  <div className="flex items-center gap-3 p-3 bg-[#0a0a0f] border border-[#2a2a3a] cyber-chamfer-sm group hover:border-[#3a3a4a] transition-colors">
                    <FileText className="w-4 h-4 text-[#00ff88]" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-[#e0e0e0] truncate">{file.filename}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] font-mono text-[#4a4a5a]">
                          {file.created_at ? new Date(file.created_at).toLocaleDateString() : ""}
                        </span>
                        <CyberBadge variant="outline" className="text-[9px]">{file.file_format?.toUpperCase()}</CyberBadge>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownload(file)}
                      className="text-[#6b7280] hover:text-[#00ff88] opacity-0 group-hover:opacity-100 transition-all p-1"
                      title="Download"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </ScrollReveal>
              ))
            )}
          </div>
        )}
      </PageTransition>
    </div>
  );
}
