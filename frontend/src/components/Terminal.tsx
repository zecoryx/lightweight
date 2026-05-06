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
    <div className="group relative my-4 overflow-hidden rounded-2xl border border-[#262626] bg-[#0a0f14] shadow-[0_28px_90px_-42px_rgba(15,23,42,0.7)]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(56,189,248,0.14),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(34,197,94,0.12),transparent_28%)]" />

      <div className="relative flex items-center justify-between border-b border-white/8 bg-black/30 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
            <div className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
          </div>
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
            <span>LightWeight Shell</span>
            <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[9px] text-emerald-300">
              Ready
            </span>
          </div>
        </div>

        <button
          onClick={copyAll}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300 transition hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-cyan-100"
        >
          {copiedAll ? (
            <>
              <svg className="h-3 w-3 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Copied all
            </>
          ) : (
            <>
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2M16 8h2a2 2 0 012 2v8a2 2 0 01-2 2h-8a2 2 0 01-2-2v-2" />
              </svg>
              Copy block
            </>
          )}
        </button>
      </div>

      <div
        className="relative cursor-pointer space-y-2 bg-[linear-gradient(180deg,rgba(15,23,42,0.76),rgba(4,8,15,0.96))] px-4 py-4 font-mono text-sm"
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
            className="group/line flex items-start gap-3 rounded-xl border border-transparent px-3 py-2.5 transition hover:border-cyan-300/15 hover:bg-white/[0.04]"
            title="Click to copy this line"
          >
            <span className="select-none pt-0.5 text-xs font-bold text-emerald-400">$</span>
            <code className="flex-1 overflow-x-auto whitespace-pre-wrap break-all text-[13px] leading-6 text-slate-100">
              {command}
            </code>
            <span
              className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] transition ${
                copiedIndex === index
                  ? "bg-emerald-400/15 text-emerald-300 opacity-100"
                  : "bg-white/5 text-slate-500 opacity-0 group-hover/line:opacity-100"
              }`}
            >
              {copiedIndex === index ? "Copied" : "Copy"}
            </span>
          </div>
        ))}

        <div className="mt-3 flex items-center justify-between border-t border-white/6 pt-3 text-[10px] uppercase tracking-[0.18em] text-slate-500">
          <span>Click a line to copy</span>
          <span>Click the background to copy all</span>
        </div>
      </div>
    </div>
  );
};

export default Terminal;
