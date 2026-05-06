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

const DownloadIcon = () => (
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
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" x2="12" y1="15" y2="3" />
  </svg>
);

import { AI_MODELS, type AIModel } from "../data/models";

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedModel, setSelectedModel] = useState<AIModel | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
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
    if (!search) return AI_MODELS;
    return AI_MODELS.filter(
      (m) =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.description.toLowerCase().includes(search.toLowerCase()),
    );
  }, [search]);

  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % filteredModels.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(
        (prev) => (prev - 1 + filteredModels.length) % filteredModels.length,
      );
    } else if (e.key === "Enter") {
      if (filteredModels[activeIndex]) {
        setSelectedModel(filteredModels[activeIndex]);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] px-4 bg-gray-900/5 backdrop-blur-[2px] animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-white rounded-xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.12)] border border-gray-100 overflow-hidden flex flex-col"
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
                placeholder="Search AI models..."
                className="flex-1 bg-transparent border-none outline-none text-base text-gray-800 placeholder:text-gray-300 font-light"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
              />
            </>
          ) : (
            <button
              onClick={() => setSelectedModel(null)}
              className="flex-1 flex items-center gap-3 text-gray-500 hover:text-gray-800 transition-colors group text-left"
            >
              <div className="w-6 h-6 flex items-center justify-center rounded-full bg-gray-50 group-hover:bg-gray-100 transition-colors">
                <span className="text-sm font-bold">&larr;</span>
              </div>
              <span className="text-sm font-medium">Back to models</span>
            </button>
          )}
          <kbd className="hidden sm:inline-flex px-1.5 py-0.5 text-[10px] font-medium text-gray-400 bg-gray-50 border border-gray-100 rounded shadow-sm uppercase tracking-tighter">
            ESC
          </kbd>
        </div>

        {/* Content Area */}
        <div className="max-h-[50vh] overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
          {!selectedModel ? (
            <div className="space-y-0.5">
              {filteredModels.length > 0 ? (
                filteredModels.map((model, index) => (
                  <button
                    key={model.id}
                    className={cn(
                      "w-full flex items-center gap-4 px-4 py-2.5 rounded-lg transition-all duration-150 group text-left",
                      activeIndex === index
                        ? "bg-gray-50 text-gray-900 font-medium"
                        : "hover:bg-gray-50/50 text-gray-400",
                    )}
                    onClick={() => setSelectedModel(model)}
                    onMouseEnter={() => setActiveIndex(index)}
                  >
                    <div className="flex-1 text-sm">{model.name}</div>
                  </button>
                ))
              ) : (
                <div className="py-10 text-center text-gray-400 text-sm font-light italic">
                  No models matching "{search}"
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
                        Parameter
                      </th>
                      <th className="px-4 py-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                        Original
                      </th>
                      <th className="px-4 py-2.5 text-[10px] font-bold text-gray-400 uppercase tracking-widest text-right">
                        Optimized
                      </th>
                    </tr>
                  </thead>
                  <tbody className="text-sm font-mono text-gray-600">
                    <tr className="border-b border-gray-50">
                      <td className="px-4 py-3 text-gray-400">Model Size</td>
                      <td className="px-4 py-3 line-through opacity-50">
                        {selectedModel.originalSize}
                      </td>
                      <td className="px-4 py-3 text-blue-600 font-bold text-right">
                        {selectedModel.compressedSize}
                      </td>
                    </tr>
                    <tr className="border-b border-gray-50">
                      <td className="px-4 py-3 text-gray-400">
                        Inference Speed
                      </td>
                      <td className="px-4 py-3 opacity-50">
                        {selectedModel.originalSpeed}
                      </td>
                      <td className="px-4 py-3 text-green-600 font-bold text-right">
                        {selectedModel.compressedSpeed}
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-gray-400">Hardware Req.</td>
                      <td className="px-4 py-3 opacity-50">High-end GPU</td>
                      <td className="px-4 py-3 text-gray-900 text-right">
                        Consumer Laptop
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="space-y-2">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest px-1">
                  Device Performance
                </div>
                <div className="border border-gray-100 rounded-lg overflow-hidden">
                  <table className="w-full text-left border-collapse text-[11px] font-mono">
                    <tbody className="text-gray-600">
                      <tr className="border-b border-gray-50 hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          Old Office Laptop
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          Readable speed
                        </td>
                      </tr>
                      <tr className="border-b border-gray-50 hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          Standard Laptop
                        </td>
                        <td className="px-4 py-2.5 text-right italic">
                          Fast as a human
                        </td>
                      </tr>
                      <tr className="hover:bg-gray-50/30 transition-colors">
                        <td className="px-4 py-2.5 text-gray-400 uppercase">
                          Gaming PC / Mac
                        </td>
                        <td className="px-4 py-2.5 text-right font-bold text-blue-500">
                          Instant response
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => {
                    const command = `lightweight pull ${selectedModel.id}`;
                    navigator.clipboard.writeText(command);
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
                        lightweight pull
                      </span>
                      <span>{selectedModel.id}</span>
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
