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
    <div className="relative group rounded-lg overflow-hidden border border-gray-100 shadow-sm my-4">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0d0d0d] border-b border-white/5">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-green-500/50"></div>
        </div>
      </div>

      {/* Commands */}
      <div
        className="bg-[#0d0d0d] px-4 py-4 font-mono text-sm space-y-1.5 cursor-pointer relative group/area"
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
            className="flex items-center gap-2 group/line cursor-pointer rounded px-2 py-1 hover:bg-white/5 transition-colors"
            title="Click to copy this line"
          >
            <span className="text-green-500 select-none text-xs">$</span>
            <code className="text-gray-100 flex-1 text-[13px]">{command}</code>
            <span
              className={`text-[10px] transition-all ${
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
