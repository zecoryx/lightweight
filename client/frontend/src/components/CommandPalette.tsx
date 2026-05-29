"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Inline SVGs for Icons
const SearchIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </svg>
);

import { AI_MODELS, type AIModel } from "../data/models";

function createCustomModel(target: string): AIModel {
  return {
    id: `custom-${target}`,
    name: `Use exact target: ${target}`,
    description:
      "Build a workflow for this exact alias, local model name, or Hugging Face GGUF repo. LightWeight will check it before download.",
    target,
  };
}

function getPullTarget(model: AIModel): string {
  return model.target;
}

function hasRunnableTarget(model: AIModel): boolean {
  return !model.target.includes("<");
}

function getWorkflowCommands(model: AIModel): string[] {
  const target = getPullTarget(model);
  return [
    `lightweight squeeze plan ${target} --target-ram 8gb --target-vram 6gb`,
    `lightweight squeeze build ${target} --profile auto --target-ram 8gb --target-vram 6gb`,
    `lightweight squeeze verify ${target} --run`,
    `lightweight squeeze report ${target}`,
    `lightweight chat ${target} --thermal balanced`,
    `lightweight serve --backend python --port 8000`,
  ];
}

type ModelItemProps = {
  model: AIModel;
  isActive: boolean;
  onSelect: (model: AIModel) => void;
};

const ModelItem = React.memo(
  ({ model, isActive, onSelect }: ModelItemProps) => {
    return (
      <button
        className={`w-full flex items-center gap-4 px-4 py-2.5 rounded-lg group text-left ${
          isActive
            ? "bg-gray-50 text-gray-900 font-medium"
            : "text-gray-400 hover:bg-gray-50/50 hover:text-gray-700"
        }`}
        onClick={() => onSelect(model)}
      >
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm">{model.name}</div>
          <div className="mt-0.5 truncate font-mono text-[10px] text-gray-300">
            {model.target}
          </div>
        </div>
      </button>
    );
  },
  (prev, next) =>
    prev.isActive === next.isActive && prev.model.id === next.model.id,
);

ModelItem.displayName = "ModelItem";

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [visibleCount, setVisibleCount] = useState(20);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === ".") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        setSelectedModel(null);
        setSearch("");
      }
      if (e.key === "Escape") {
        setIsOpen(false);
        setSelectedModel(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [isOpen]);

  const filteredModels = useMemo(() => {
    const query = search.trim();
    const runnableModels = AI_MODELS.filter(hasRunnableTarget);
    if (!query) return runnableModels;

    const matches = runnableModels.filter(
      (m) =>
        m.name.toLowerCase().includes(query.toLowerCase()) ||
        m.target.toLowerCase().includes(query.toLowerCase()) ||
        m.description.toLowerCase().includes(query.toLowerCase()),
    );

    const hasExactTarget = matches.some(
      (model) => model.target.toLowerCase() === query.toLowerCase(),
    );
    return hasExactTarget ? matches : [createCustomModel(query), ...matches];
  }, [search]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setActiveIndex(0);
    setVisibleCount(20);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => {
        const nextIndex = (prev + 1) % filteredModels.length;
        if (nextIndex >= visibleCount - 5) {
          setVisibleCount((c) => Math.min(c + 20, filteredModels.length));
        }
        return nextIndex;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => {
        const nextIndex =
          (prev - 1 + filteredModels.length) % filteredModels.length;
        if (nextIndex >= visibleCount - 5) {
          setVisibleCount((c) =>
            Math.min(Math.max(c, nextIndex + 10), filteredModels.length),
          );
        }
        return nextIndex;
      });
    } else if (e.key === "Enter") {
      if (filteredModels[activeIndex]) {
        setSelectedModel(filteredModels[activeIndex]);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] px-4 bg-gray-900/20 animate-in fade-in duration-200 cursor-default"
      onClick={() => setIsOpen(false)}
    >
      <div
        className="w-full max-w-xl bg-white rounded-xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.12)] border border-gray-100 overflow-hidden flex flex-col cursor-default"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search / Back Bar */}
        <div className="flex items-center px-5 py-4 border-b border-gray-50">
          {!selectedModel ? (
            <>
              <div className="text-gray-300 mr-3">
                <SearchIcon />
              </div>
              <input
                ref={inputRef}
                type="text"
                placeholder="Search models and exact-run workflows..."
                className="flex-1 bg-transparent border-none outline-none text-base text-gray-800 placeholder:text-gray-300 font-light"
                value={search}
                onChange={(e) => handleSearchChange(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </>
          ) : (
            <button
              onClick={() => setSelectedModel(null)}
              className="flex-1 flex items-center gap-3 text-gray-500 hover:text-gray-800 transition-colors group text-left"
            >
              <span className="text-sm font-medium">Back to models</span>
            </button>
          )}
          <kbd className="hidden sm:inline-flex px-1.5 py-0.5 text-[10px] font-medium text-gray-400 bg-gray-50 border border-gray-100 rounded shadow-sm uppercase tracking-tighter">
            ESC
          </kbd>
        </div>

        {/* Content Area */}
        <div
          className="max-h-[50vh] overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent"
          onScroll={(e) => {
            const bottom =
              e.currentTarget.scrollHeight - e.currentTarget.scrollTop <=
              e.currentTarget.clientHeight + 50;
            if (bottom && visibleCount < filteredModels.length) {
              setVisibleCount((prev) =>
                Math.min(prev + 20, filteredModels.length),
              );
            }
          }}
        >
          {!selectedModel ? (
            <div className="space-y-0.5">
              {filteredModels.length > 0 ? (
                filteredModels
                  .slice(0, visibleCount)
                  .map((model, index) => (
                    <ModelItem
                      key={model.id}
                      model={model}
                      isActive={activeIndex === index}
                      onSelect={setSelectedModel}
                    />
                  ))
              ) : (
                <div className="py-10 text-center text-gray-400 text-sm font-light italic">
                  No models matching &quot;{search}&quot;
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-6 animate-in slide-in-from-bottom-1 duration-200">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-medium text-gray-900">
                    {selectedModel.name}
                  </h2>
                  <p className="text-sm text-gray-400 font-light mt-1">
                    {selectedModel.description}
                  </p>
                </div>
              </div>

              <div className="border border-gray-100 rounded-lg overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-50/50 border-b border-gray-100">
                      <th className="px-4 py-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                        Step
                      </th>
                      <th className="px-4 py-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                        Command
                      </th>
                      <th className="px-4 py-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest text-right">
                        Result
                      </th>
                    </tr>
                  </thead>
                  <tbody className="text-sm font-mono text-gray-600">
                    <tr className="border-b border-gray-50">
                      <td className="px-4 py-3 text-gray-400">Plan</td>
                      <td className="px-4 py-3">check --mode fit</td>
                      <td className="px-4 py-3 text-gray-900 text-right">
                        exact model
                      </td>
                    </tr>
                    <tr className="border-b border-gray-50">
                      <td className="px-4 py-3 text-gray-400">Inspect</td>
                      <td className="px-4 py-3">inspect-model</td>
                      <td className="px-4 py-3 text-gray-900 text-right">
                        GGUF metadata
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-400">Run</td>
                      <td className="px-4 py-3">probe / bench / chat</td>
                      <td className="px-4 py-3 text-gray-900 text-right">
                        measured locally
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="space-y-2">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
                  Runtime Checks
                </div>
                <div className="border border-gray-100 rounded-lg overflow-hidden">
                  <table className="w-full text-left border-collapse text-[11px] font-mono">
                    <tbody className="text-gray-600">
                      <tr className="border-b border-gray-50 hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          doctor
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          backend, RAM, VRAM, disk
                        </td>
                      </tr>
                      <tr className="border-b border-gray-50 hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          probe
                        </td>
                        <td className="px-4 py-2.5 text-right italic">
                          GPU layers and memory pressure
                        </td>
                      </tr>
                      <tr className="hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          bench
                        </td>
                        <td className="px-4 py-2.5 text-right font-bold text-blue-500">
                          tokens/sec on this device
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="rounded-lg border border-gray-100 bg-gray-950 p-4 text-[11px] font-mono text-gray-200 overflow-x-auto">
                {getWorkflowCommands(selectedModel).map((command) => (
                  <div key={command} className="whitespace-nowrap py-0.5">
                    <span className="text-gray-500">$ </span>
                    {command}
                  </div>
                ))}
              </div>

              <div className="pt-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      getWorkflowCommands(selectedModel).join("\n"),
                    );
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                  className={cn(
                    "w-full py-3.5 rounded-lg text-xs font-mono font-bold transition-all flex items-center justify-center gap-3 shadow-sm border transition-all duration-300",
                    copied
                      ? "bg-green-50 border-green-200 text-green-700"
                      : "bg-gray-900 border-gray-900 text-white hover:bg-black",
                  )}
                >
                  {copied ? (
                    <>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      Copied to clipboard!
                    </>
                  ) : (
                    <>
                      <span className="opacity-50 font-normal">
                        Copy exact-run
                      </span>
                      <span>{getPullTarget(selectedModel)}</span>
                      <span className="opacity-50 font-normal">workflow</span>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="ml-1 opacity-50"
                      >
                        <rect
                          x="9"
                          y="9"
                          width="13"
                          height="13"
                          rx="2"
                          ry="2"
                        />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-gray-50/50 border-t border-gray-50 flex items-center justify-between text-[10px] text-gray-400 font-medium uppercase tracking-[0.1em]">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              Navigate <span className="text-gray-300">(&uarr;&darr;)</span>
            </span>
            <span className="flex items-center gap-1">
              Select <span className="text-gray-300">(Enter)</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
