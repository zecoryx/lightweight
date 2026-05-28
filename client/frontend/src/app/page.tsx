"use client";

import React, { type ReactNode, useState } from "react";
import DataTable from "@/components/DataTable";
import Terminal from "@/components/Terminal";
import Image from "next/image";
import { useLanguage } from "@/context/LanguageContext";
import Creators from "@/components/Creators";

type Language = "en" | "uz" | "ru";

export default function Home() {
  const { t, language, setLanguage } = useLanguage();
  const [activeUsers, setActiveUsers] = useState(0);

  React.useEffect(() => {
    const getSessionId = () => {
      const key = "lightweight_session_id";
      const existing = sessionStorage.getItem(key);
      if (existing) return existing;

      const sessionId =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

      sessionStorage.setItem(key, sessionId);
      return sessionId;
    };

    const trackUser = async () => {
      try {
        const res = await fetch("/api/stats", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sessionId: getSessionId() }),
        });
        const data = await res.json();
        if (data.success) setActiveUsers(data.count);
      } catch (e) {
        console.error("Stats tracking failed", e);
      }
    };

    trackUser();

    // Refresh count every 30s
    const interval = setInterval(async () => {
      const res = await fetch(`/api/stats?t=${Date.now()}`, {
        cache: "no-store",
      });
      const data = await res.json();
      setActiveUsers(data.count);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-white text-[#1a1a1a] font-sans selection:bg-gray-200">
      <main className="relative z-10 max-w-3xl mx-auto px-6 py-32 space-y-24">
        {/* Logo & Header */}
        <header className="space-y-12 relative animate-fade-up">
          <div className="hero-motion-field" aria-hidden="true">
            <span className="hero-motion-line hero-motion-line-a" />
            <span className="hero-motion-line hero-motion-line-b" />
            <span className="hero-motion-line hero-motion-line-c" />
          </div>

          <div className="flex justify-between items-start">
            <Image
              src="/images/logo-light.png"
              alt="LightWeight Logo"
              width={90}
              height={90}
              className=""
            />

            <div className="flex flex-col items-end gap-2">
              {/* Language Switcher */}
              <div className="flex bg-gray-50/50 p-1 rounded-md border border-gray-100 shadow-sm">
                {(["en", "uz", "ru"] satisfies Language[]).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setLanguage(lang)}
                    className={`px-4 py-1.5 rounded-sm text-[10px] cursor-pointer font-bold uppercase tracking-widest transition-all duration-300 ${
                      language === lang
                        ? "bg-white text-black shadow-[0_2px_10px_-3px_rgba(0,0,0,0.07)]"
                        : "text-gray-400 hover:text-gray-600 hover:bg-white/50"
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>

              {/* Explore Workflows Hint */}
              <button
                onClick={() =>
                  window.dispatchEvent(
                    new KeyboardEvent("keydown", { key: ".", ctrlKey: true }),
                  )
                }
                className="flex items-center text-[13px] font-medium text-gray-600 bg-white px-3 py-1.5 rounded-md border border-gray-200 hover:bg-gray-50 hover:text-black transition-colors shadow-sm w-full justify-center sm:w-auto"
              >
                <svg
                  className="w-3.5 h-3.5 mr-1.5 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                Explore Workflows
                <div className="ml-2 flex items-center gap-0.5">
                  <kbd className="bg-gray-50 text-gray-500 border border-gray-200 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold">
                    Ctrl
                  </kbd>
                  <kbd className="bg-gray-50 text-gray-500 border border-gray-200 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold">
                    .
                  </kbd>
                </div>
              </button>
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-4">
              <h1 className="text-4xl font-semibold tracking-tight">
                {t("hero_title")}
              </h1>
              <p className="text-xl text-gray-500 leading-relaxed max-w-2xl">
                {t("hero_subtitle")}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              {/* GitHub Star */}
              <a
                href="https://github.com/zecoryx/lightweight"
                target="_blank"
                className="flex items-center border border-gray-200 rounded-md overflow-hidden text-[13px] font-medium hover:bg-gray-50 transition-colors"
              >
                <div className="bg-gray-50/50 px-3 py-1.5 flex items-center border-r border-gray-200">
                  <svg
                    className="w-4 h-4 mr-1.5"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                  </svg>
                  Star
                </div>
                <div className="bg-white px-3 py-1.5 font-semibold">0</div>
              </a>

              {/* Buy Me a Coffee */}
              <a
                href="#"
                className="flex items-center bg-[#FFDD00] text-black px-4 py-1.5 rounded-md text-[13px] font-medium hover:bg-[#ffdf1e] transition-colors shadow-sm"
              >
                <Image
                  src="https://cdn.buymeacoffee.com/buttons/bmc-new-btn-logo.svg"
                  alt="BMC"
                  width={15}
                  height={15}
                  className="mr-2"
                />
                Buy me a coffee
              </a>

              {/* Active Users */}
              <div className="flex items-center text-[13px] text-gray-500 bg-gray-50/50 px-3 py-1.5 rounded-md border border-gray-100">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                <svg
                  className="w-3.5 h-3.5 mr-1.5 text-gray-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span className="font-medium">
                  {activeUsers} {t("active_users")}
                </span>
              </div>
            </div>

          </div>
        </header>

        <Creators />

        {/* 1. The Result: Before vs After */}
        <section className="space-y-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
            {t("problem_title")}
          </h2>
          <div className="space-y-8">
            <p className="text-gray-700 leading-relaxed">{t("problem_desc")}</p>

            <div className="grid gap-4">
              <div className="border border-gray-100 p-6 rounded-lg space-y-4 shadow-sm hover:border-gray-200 transition-colors">
                <h3 className="text-xs font-bold text-gray-400 uppercase">
                  {t("example_qwen")}
                </h3>
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-1">
                    <span className="text-xs uppercase text-red-400 font-bold tracking-tighter">
                      {t("needed_before")}
                    </span>
                    <p className="text-2xl font-semibold">Manual fit math</p>
                    <p className="text-xs text-gray-400">Guess quant and context</p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">squeeze plan</p>
                    <p className="text-xs text-gray-400">
                      Profile before download
                    </p>
                  </div>
                </div>
              </div>

              <div className="border border-gray-100 p-6 rounded-lg space-y-4 shadow-sm hover:border-gray-200 transition-colors">
                <h3 className="text-sm font-bold text-gray-400 uppercase">
                  {t("example_llama")}
                </h3>
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-1">
                    <span className="text-xs uppercase text-red-400 font-bold tracking-tighter">
                      {t("needed_before")}
                    </span>
                    <p className="text-2xl font-semibold">Crash on load</p>
                    <p className="text-xs text-gray-400">No recovery path</p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">verify + report</p>
                    <p className="text-xs text-gray-400">Measured on your PC</p>
                  </div>
                </div>
              </div>

              <div className="border border-gray-100 p-6 rounded-lg space-y-4 shadow-sm hover:border-gray-200 transition-colors">
                <h3 className="text-sm font-bold text-gray-400 uppercase">
                  {t("example_kimi")}
                </h3>
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-1">
                    <span className="text-xs uppercase text-red-400 font-bold tracking-tighter">
                      {t("needed_before")}
                    </span>
                    <p className="text-2xl font-semibold">Custom API work</p>
                    <p className="text-xs text-gray-400">Glue code required</p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">active profile</p>
                    <p className="text-xs text-gray-400">Chat + /v1 use the same squeeze profile</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Engineering Architecture */}
        <section className="space-y-12">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
            {t("tech_title")}
          </h2>
          <div className="grid gap-12 sm:grid-cols-2 text-justify">
            <div className="space-y-4">
              <h3 className="text-lg font-medium italic text-gray-800">
                {t("tech_01_title")}
              </h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                {t("tech_01_desc")}
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium italic text-gray-800">
                {t("tech_02_title")}
              </h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                {t("tech_02_desc")}
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium italic text-gray-800">
                {t("tech_03_title")}
              </h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                {t("tech_03_desc")}
              </p>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-medium italic text-gray-800">
                {t("tech_04_title")}
              </h3>
              <p className="text-gray-500 text-sm leading-relaxed">
                {t("tech_04_desc")}
              </p>
            </div>
          </div>
        </section>

        {/* 3. Performance Matrix */}
        <section className="space-y-8">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
            {t("perf_title")}
          </h2>
          <DataTable
            headers={[
              t("perf_col_hw"),
              t("perf_col_model"),
              t("perf_col_speed"),
            ]}
            rows={[
              [t("perf_row1_hw"), "doctor / check", t("perf_row1_res")],
              [t("perf_row2_hw"), "inspect / probe", t("perf_row2_res")],
              [t("perf_row3_hw"), "bench / chat", t("perf_row3_res")],
            ]}
          />
        </section>

        {/* 4. Getting Started */}
        <section className="space-y-12">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
            {t("usage_title")}
          </h2>

          <div className="space-y-6">
            <AccordionItem id="01" title="Install" defaultOpen={true}>
              <p className="text-xs text-gray-400 mb-4">
                Windows (PowerShell):
              </p>
              <Terminal
                commands={[
                  "irm https://lightweight.zecoryx.uz/install.ps1 | iex",
                ]}
              />
              <p className="text-xs text-gray-400 mb-4 mt-6">macOS / Linux:</p>
              <Terminal
                commands={[
                  "curl -fsSL https://lightweight.zecoryx.uz/install.sh | sh",
                ]}
              />
            </AccordionItem>

            <AccordionItem id="02" title="Download & Chat" defaultOpen={true}>
              <p className="text-xs text-gray-400 mb-4">
                Plan the exact model, build the squeeze profile, then verify it locally:
              </p>
              <Terminal
                commands={[
                  "lightweight doctor",
                  "lightweight squeeze plan qwen:32b --target-ram 16gb --target-vram 6gb",
                  "lightweight squeeze build qwen:32b --profile auto --target-ram 16gb --target-vram 6gb",
                  "lightweight squeeze verify qwen:32b --run",
                  "lightweight squeeze report qwen:32b",
                  "lightweight chat qwen:32b --thermal balanced",
                ]}
              />
            </AccordionItem>

            <AccordionItem id="03" title="Manage Local Library">
              <p className="text-xs text-gray-400 mb-4">
                View all downloaded models on your machine:
              </p>
              <Terminal commands={["lightweight list"]} />
              <p className="text-xs text-gray-400 mb-4 mt-6">
                Remove a model to free up disk space:
              </p>
              <Terminal commands={["lightweight rm llama3:8b"]} />
            </AccordionItem>

            <AccordionItem id="04" title="Local API Server">
              <p className="text-xs text-gray-400 mb-4">
                Turn your machine into an OpenAI-compatible local API endpoint:
              </p>
              <Terminal
                commands={[
                    "lightweight serve --backend llama-server --model qwen:32b --port 8000",
                    "# Uses the active squeeze profile and serves http://localhost:8000/v1",
                ]}
              />
              <div className="mt-6 space-y-3">
                <p className="text-xs text-gray-500 font-medium">
                  Send a request from any app:
                </p>
                <Terminal
                  commands={[
                    `curl http://localhost:8000/v1/chat/completions \\`,
                    `  -H "Content-Type: application/json" \\`,
                    `  -d '{"model": "qwen:32b", "messages": [{"role": "user", "content": "Hello!"}]}'`,
                  ]}
                />
                <div className="grid grid-cols-2 gap-4 text-xs text-gray-400 mt-4">
                  <div className="space-y-1">
                    <p className="font-semibold text-gray-600">Endpoints</p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        POST /v1/chat/completions
                      </code>
                    </p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        GET /v1/models
                      </code>
                    </p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        GET /v1/health
                      </code>
                    </p>
                  </div>
                  <div className="space-y-1">
                    <p className="font-semibold text-gray-600">Options</p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        --backend auto
                      </code>{" "}
                      — choose python or llama-server
                    </p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        --thermal balanced
                      </code>{" "}
                      — laptop-friendly limits
                    </p>
                    <p>
                      <code className="bg-gray-50 px-1 rounded text-[11px]">
                        --moe-offload auto
                      </code>{" "}
                      — active expert placement for MoE models
                    </p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 font-medium mt-6">
                  Use native llama-server when it is installed:
                </p>
                <Terminal
                  commands={[
                    "lightweight serve --backend llama-server --model qwen:32b --spec ngram-cache",
                  ]}
                />
              </div>
            </AccordionItem>

            <AccordionItem id="05" title="Advanced Tools">
              <div className="space-y-6">
                <div>
                  <p className="text-xs text-gray-400 mb-4">
                    Compare squeeze profiles for a specific hardware target:
                  </p>
                  <Terminal commands={["lightweight squeeze plan llama3:70b --target-ram 16gb --target-vram 6gb"]} />
                </div>

                <div>
                  <p className="text-xs text-gray-400 mb-4">
                    Switch the active squeeze profile used by chat and serve:
                  </p>
                  <Terminal
                    commands={[
                      "lightweight squeeze profiles qwen:32b",
                      "lightweight squeeze use qwen:32b balanced",
                    ]}
                  />
                </div>

                <div>
                  <p className="text-xs text-gray-400 mb-4">
                    Read GGUF metadata and benchmark real token speed:
                  </p>
                  <Terminal
                    commands={[
                      "lightweight inspect-model qwen:32b",
                      "lightweight probe qwen:32b --thermal balanced",
                      "lightweight bench qwen:32b --tokens 64 --thermal balanced",
                    ]}
                  />
                </div>

                <div>
                  <p className="text-xs text-gray-400 mb-4">
                    Configure global CLI settings:
                  </p>
                  <Terminal commands={["lightweight config --edit"]} />
                </div>
              </div>
            </AccordionItem>
          </div>
        </section>

        <section className="pt-20 border-t border-gray-100">
          <div className="flex flex-col md:flex-row items-baseline gap-12 md:gap-24">
            <div className="shrink-0">
              <h2 className="text-5xl font-black uppercase tracking-tighter text-gray-900 leading-[0.8]">
                Coming
                <br />
                <span className="text-gray-200">Soon</span>
              </h2>
            </div>

            <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-y-10 gap-x-8">
              {[
                { id: "01", label: "Voice Tasks" },
                { id: "02", label: "Image to Text" },
                { id: "03", label: "Image to Video" },
                { id: "04", label: "Better CLI" },
                { id: "05", label: "Improve Performance" },
              ].map((feat) => (
                <div
                  key={feat.id}
                  className="pt-4 border-t border-gray-900/5 space-y-3"
                >
                  <span className="text-[10px] font-bold text-gray-300 tabular-nums">
                    {feat.id}
                  </span>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-gray-900">
                    {feat.label}
                  </h3>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

type AccordionItemProps = {
  id: string;
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

function AccordionItem({ id, title, children, defaultOpen = false }: AccordionItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={`border-t border-gray-50 pt-6 transition-all ${isOpen ? "pb-6" : "pb-0"}`}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full group text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-bold text-gray-300 tabular-nums">
            {id}
          </span>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-700 group-hover:text-black transition-colors">
            {title}
          </h3>
        </div>
        <div
          className={`transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}
        >
          <svg
            className="w-4 h-4 text-gray-300 group-hover:text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>

      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? "max-h-[2000px] opacity-100 mt-6 pl-6" : "max-h-0 opacity-0"}`}
      >
        {children}
      </div>
    </div>
  );
}
