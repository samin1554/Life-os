"use client";

import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

export interface CyberInputProps extends InputHTMLAttributes<HTMLInputElement> {
  prefix?: string;
  chamfer?: "sm" | "default";
}

const CyberInput = forwardRef<HTMLInputElement, CyberInputProps>(
  ({ className, prefix = ">", chamfer = "sm", ...props }, ref) => {
    const chamferClass = chamfer === "sm" ? "cyber-chamfer-sm" : "cyber-chamfer";

    return (
      <div className={cn("relative", chamferClass)}>
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#00ff88] font-mono text-sm font-bold">
            {prefix}
          </span>
        )}
        <input
          ref={ref}
          className={cn(
            "w-full bg-[#12121a] border border-[#2a2a3a] text-[#00ff88] font-mono text-sm",
            "placeholder:text-[#6b7280]/60 placeholder:font-mono",
            "focus:border-[#00ff88] focus:shadow-[0_0_5px_#00ff88,0_0_10px_#00ff8840] focus:outline-none",
            "transition-all duration-200",
            prefix ? "pl-7 pr-4 py-2.5" : "px-4 py-2.5",
            className
          )}
          {...props}
        />
      </div>
    );
  }
);
CyberInput.displayName = "CyberInput";

export { CyberInput };
