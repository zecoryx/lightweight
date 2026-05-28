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
    <div className="relative group rounded-lg overflow-hidden border border-gray-200/80 shadow-sm my-4 bg-[#0d0d0d]">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 bg-[#111111] border-b border-white/10">
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
          className="h-7 rounded-md border border-white/10 px-2.5 text-[11px] font-mono text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
        >
          {copiedAll ? "copied" : "copy all"}
        </button>
      </div>

      {/* Commands */}
      <div
        className="px-3 py-3 font-mono text-sm space-y-1.5 cursor-pointer relative group/area"
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
            className="flex items-start gap-2 group/line cursor-pointer rounded-md px-2 py-1.5 hover:bg-white/5 transition-colors"
            title="Click to copy this line"
          >
            <span className="text-green-500 select-none text-xs leading-6">$</span>
            <code className="text-gray-100 flex-1 text-[13px] leading-6 break-all sm:break-words">
              {command}
            </code>
            <span
              className={`shrink-0 text-[10px] leading-6 transition-all ${
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
