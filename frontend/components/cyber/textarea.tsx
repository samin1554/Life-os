"use client";

import { cn } from "@/lib/utils";
import { TextareaHTMLAttributes, forwardRef } from "react";

export interface CyberTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  prefix?: string;
  chamfer?: "sm" | "default";
}

const CyberTextarea = forwardRef<HTMLTextAreaElement, CyberTextareaProps>(
  ({ className, prefix = ">", chamfer = "sm", ...props }, ref) => {
    const chamferClass = chamfer === "sm" ? "cyber-chamfer-sm" : "cyber-chamfer";

    return (
      <div className={cn("relative", chamferClass)}>
        {prefix && (
          <span className="absolute left-3 top-3 text-[#00ff88] font-mono text-sm font-bold">
            {prefix}
          </span>
        )}
        <textarea
          ref={ref}
          className={cn(
            "w-full bg-[#12121a] border border-[#2a2a3a] text-[#00ff88] font-mono text-sm",
            "placeholder:text-[#6b7280]/60 placeholder:font-mono",
            "focus:border-[#00ff88] focus:shadow-[0_0_5px_#00ff88,0_0_10px_#00ff8840] focus:outline-none",
            "transition-all duration-200 resize-none",
            prefix ? "pl-7 pr-4 py-2.5" : "px-4 py-2.5",
            className
          )}
          rows={3}
          {...props}
        />
      </div>
    );
  }
);
CyberTextarea.displayName = "CyberTextarea";

export { CyberTextarea };
