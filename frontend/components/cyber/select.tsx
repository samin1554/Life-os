"use client";

import { cn } from "@/lib/utils";
import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Check } from "lucide-react";

export interface CyberSelectOption {
  value: string;
  label: string;
}

export interface CyberSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CyberSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  chamfer?: "sm" | "default";
  glowColor?: string;
}

const ease = [0.16, 1, 0.3, 1] as [number, number, number, number];

export function CyberSelect({
  value,
  onChange,
  options,
  placeholder = "Select...",
  disabled = false,
  className,
  chamfer = "sm",
  glowColor = "#00ff88",
}: CyberSelectProps) {
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value);
  const selectedIndex = options.findIndex((o) => o.value === value);

  const toggle = useCallback(() => {
    if (!disabled) setOpen((prev) => !prev);
  }, [disabled]);

  const selectOption = useCallback(
    (optionValue: string) => {
      onChange(optionValue);
      setOpen(false);
    },
    [onChange]
  );

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      switch (e.key) {
        case "Escape":
          setOpen(false);
          break;
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev + 1) % options.length);
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev - 1 + options.length) % options.length);
          break;
        case "Enter":
          e.preventDefault();
          if (options[highlightedIndex]) {
            selectOption(options[highlightedIndex].value);
          }
          break;
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, highlightedIndex, options, selectOption]);

  // Reset highlight when opening
  useEffect(() => {
    if (open) {
      setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
    }
  }, [open, selectedIndex]);

  const chamferClass = chamfer === "sm" ? "cyber-chamfer-sm" : "cyber-chamfer";

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Trigger */}
      <motion.button
        type="button"
        onClick={toggle}
        disabled={disabled}
        className={cn(
          "w-full bg-[#0d0d14] border border-[#2a2a3a] text-[#e0e0e0] font-mono text-xs",
          "pl-3 pr-8 py-2.5 text-left cursor-pointer flex items-center justify-between",
          "hover:border-[#3a3a4a] hover:bg-[#111118]",
          "focus:outline-none",
          "transition-all duration-200",
          "disabled:opacity-40 disabled:cursor-not-allowed",
          chamferClass
        )}
        style={{
          borderColor: open ? glowColor : undefined,
          boxShadow: open ? `0 0 8px ${glowColor}30, 0 0 16px ${glowColor}15` : undefined,
        }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
      >
        <span className={cn(!selectedOption && "text-[#6b7280]")}>
          {selectedOption?.label || placeholder}
        </span>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2, ease }}
          className="absolute right-2.5 top-1/2 -translate-y-1/2"
        >
          <ChevronDown
            className="w-3.5 h-3.5 text-[#4a4a5a]"
            strokeWidth={2}
          />
        </motion.span>
      </motion.button>

      {/* Dropdown Panel — rendered via portal to escape clip-path */}
      <AnimatePresence>
        {open && (
          <DropdownPortal
            containerRef={containerRef}
            chamferClass={chamferClass}
            glowColor={glowColor}
            options={options}
            value={value}
            highlightedIndex={highlightedIndex}
            setHighlightedIndex={setHighlightedIndex}
            selectOption={selectOption}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Portal Component ─── */

function DropdownPortal({
  containerRef,
  chamferClass,
  glowColor,
  options,
  value,
  highlightedIndex,
  setHighlightedIndex,
  selectOption,
}: {
  containerRef: React.RefObject<HTMLDivElement | null>;
  chamferClass: string;
  glowColor: string;
  options: CyberSelectOption[];
  value: string;
  highlightedIndex: number;
  setHighlightedIndex: (i: number) => void;
  selectOption: (v: string) => void;
}) {
  const [style, setStyle] = useState<React.CSSProperties>({});

  useEffect(() => {
    function position() {
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) {
        setStyle({
          position: "fixed",
          top: rect.bottom + 4,
          left: rect.left,
          width: rect.width,
          zIndex: 9999,
        });
      }
    }
    position();
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    return () => {
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
    };
  }, [containerRef]);

  const content = (
    <motion.div
      initial={{ opacity: 0, y: -8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "bg-[#0d0d14] border border-[#2a2a3a]",
        "shadow-[0_8px_30px_rgba(0,0,0,0.5)] overflow-hidden",
        chamferClass
      )}
      style={{
        ...style,
        borderColor: `${glowColor}40`,
        boxShadow: `0 8px 30px rgba(0,0,0,0.5), 0 0 20px ${glowColor}10`,
      }}
    >
      <div className="max-h-60 overflow-y-auto py-1">
        {options.map((option, index) => {
          const isSelected = option.value === value;
          const isHighlighted = index === highlightedIndex;
          return (
            <motion.button
              key={option.value}
              type="button"
              onClick={() => selectOption(option.value)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={cn(
                "w-full px-3 py-2 text-left font-mono text-xs flex items-center justify-between",
                "transition-colors duration-150",
                isSelected
                  ? "text-[#e0e0e0]"
                  : isHighlighted
                  ? "text-[#e0e0e0] bg-[#1a1a2e]"
                  : "text-[#6b7280] hover:text-[#e0e0e0] hover:bg-[#1a1a2e]"
              )}
              style={isSelected ? { backgroundColor: `${glowColor}10` } : undefined}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15, delay: index * 0.03 }}
            >
              <span>{option.label}</span>
              {isSelected && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 17 }}
                >
                  <Check
                    className="w-3.5 h-3.5"
                    style={{ color: glowColor }}
                    strokeWidth={2}
                  />
                </motion.span>
              )}
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );

  if (typeof document === "undefined") return null;
  return createPortal(content, document.body);
}
