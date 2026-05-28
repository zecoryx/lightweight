import React, { useState } from "react";

interface TerminalProps {
  commands: string[];
}

const Terminal: React.FC<TerminalProps> = ({ commands }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  const copyLine = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch (err) {
      console.error("Copy failed", err);
    }
  };

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(commands.join("\n"));
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 1500);
    } catch (err) {
      console.error("Copy failed", err);
    }
  };

  return (
    <div className="relative group my-4 overflow-hidden rounded-lg border border-gray-200/80 bg-[#0d0d0d] shadow-sm">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-[#111111] px-3 py-2.5 sm:px-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex gap-1.5 shrink-0" aria-hidden="true">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/60"></div>
          </div>
          <span className="text-[11px] text-gray-400 font-mono truncate">
            terminal
          </span>
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            copyAll();
          }}
          className="h-7 shrink-0 rounded-md border border-white/10 px-2 text-[10px] font-mono text-gray-300 transition-colors hover:bg-white/5 hover:text-white sm:px-2.5 sm:text-[11px]"
        >
          {copiedAll ? "copied" : "copy all"}
        </button>
      </div>

      {/* Commands */}
      <div
        className="relative space-y-1.5 px-2.5 py-3 font-mono text-sm cursor-pointer group/area sm:px-3"
        onClick={(e) => {
          if (e.target === e.currentTarget) copyAll();
        }}
        title="Click to copy all"
      >
        {commands.map((command, index) => (
          <div
            key={index}
            onClick={(e) => {
              e.stopPropagation();
              copyLine(command, index);
            }}
            className="group/line flex cursor-pointer items-start gap-2 rounded-md px-1.5 py-1.5 transition-colors hover:bg-white/5 sm:px-2"
            title="Click to copy this line"
          >
            <span className="text-green-500 select-none text-xs leading-6">$</span>
            <code className="min-w-0 flex-1 break-all text-[12px] leading-6 text-gray-100 sm:text-[13px]">
              {command}
            </code>
            <span
              className={`hidden shrink-0 text-[10px] leading-6 transition-all min-[420px]:inline ${
                copiedIndex === index
                  ? "text-green-400 opacity-100"
                  : "text-gray-600 opacity-0 group-hover/line:opacity-100"
              }`}
            >
              {copiedIndex === index ? "✓" : "copy"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Terminal;
