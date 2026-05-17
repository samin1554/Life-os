"use client";

import { AlertTriangle } from "lucide-react";

interface ChaosTriggerProps {
  onTrigger: () => void;
  disabled?: boolean;
}

export function ChaosTrigger({ onTrigger, disabled }: ChaosTriggerProps) {
  return (
    <button
      onClick={onTrigger}
      disabled={disabled}
      className="w-full cyber-chamfer-sm border-2 border-[#ff3366]/40 bg-[#ff3366]/5 p-5 text-left
        hover:bg-[#ff3366]/10 hover:border-[#ff3366] hover:shadow-[0_0_10px_#ff336630]
        transition-all duration-300 disabled:opacity-40 disabled:pointer-events-none"
    >
      <div className="flex items-start gap-4">
        <AlertTriangle className="w-6 h-6 text-[#ff3366] shrink-0 mt-0.5" strokeWidth={1.5} />
        <div>
          <p className="text-sm font-mono uppercase tracking-wider text-[#ff3366] font-semibold">
            System Overload Detected
          </p>
          <p className="text-xs font-mono text-[#ff3366]/70 mt-1 uppercase tracking-wide">
            Initiate chaos triage protocol — reduce to 3 critical objectives
          </p>
        </div>
      </div>
    </button>
  );
}
