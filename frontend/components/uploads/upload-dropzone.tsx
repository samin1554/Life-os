"use client";

import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, X } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { useToast } from "@/components/toast";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const MAX_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
  "text/csv",
  "image/png",
  "image/jpeg",
];

interface UploadDropzoneProps {
  onUploadComplete?: () => void;
  purpose?: string;
  compact?: boolean;
}

export function UploadDropzone({ onUploadComplete, purpose = "general", compact = false }: UploadDropzoneProps) {
  const { getToken } = useAuth();
  const { addToast } = useToast();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    for (const file of fileArray) {
      if (file.size > MAX_SIZE) {
        addToast(`${file.name} exceeds 10MB limit`, "error");
        continue;
      }
      if (!ALLOWED_TYPES.includes(file.type) && file.type !== "") {
        addToast(`${file.name}: unsupported file type`, "error");
        continue;
      }

      setUploading(true);
      setProgress(0);

      try {
        const token = await getToken();
        const formData = new FormData();
        formData.append("file", file);
        formData.append("purpose", purpose);

        const res = await fetch(`${API_URL}/uploads?purpose=${encodeURIComponent(purpose)}`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });

        if (res.ok) {
          addToast(`${file.name} uploaded`, "success");
          onUploadComplete?.();
        } else {
          const err = await res.json();
          addToast(err.detail || `Failed to upload ${file.name}`, "error");
        }
      } catch (e) {
        console.error(e);
        addToast(`Upload failed: ${file.name}`, "error");
      } finally {
        setUploading(false);
        setProgress(0);
      }
    }
  }, [getToken, addToast, onUploadComplete, purpose]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  return (
    <motion.div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onClick={() => inputRef.current?.click()}
      animate={{
        borderColor: isDragging ? "#00ff88" : "#2a2a3a",
        backgroundColor: isDragging ? "rgba(0, 255, 136, 0.03)" : "transparent",
      }}
      transition={{ duration: 0.2 }}
      className={`
        border-2 border-dashed cursor-pointer transition-colors
        flex flex-col items-center justify-center gap-2
        ${compact ? "py-4 px-6" : "py-8 px-6"}
        hover:border-[#00d4ff]/50
      `}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => e.target.files && handleFiles(e.target.files)}
      />

      {uploading ? (
        <>
          <Loader2 className="w-5 h-5 text-[#00ff88] animate-spin" />
          <p className="text-xs font-mono text-[#6b7280]">Uploading...</p>
        </>
      ) : (
        <>
          <Upload className={`${compact ? "w-4 h-4" : "w-6 h-6"} text-[#6b7280]`} strokeWidth={1.5} />
          <p className="text-xs font-mono text-[#6b7280] text-center">
            {compact ? "Drop files or click" : "Drop files here or click to browse"}
          </p>
          {!compact && (
            <p className="text-[10px] font-mono text-[#4a4a5a]">
              PDF, DOCX, TXT, PNG, JPG (max 10MB)
            </p>
          )}
        </>
      )}
    </motion.div>
  );
}
