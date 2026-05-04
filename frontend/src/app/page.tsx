"use client";

import DataTable from "@/components/DataTable";
import Terminal from "@/components/Terminal";
import Image from "next/image";
import { useLanguage } from "@/context/LanguageContext";

export default function Home() {
  const { t, language, setLanguage } = useLanguage();

  return (
    <div className="min-h-screen bg-white text-[#1a1a1a] font-sans selection:bg-gray-200">
      <main className="max-w-3xl mx-auto px-6 py-32 space-y-24">
        {/* Logo & Header */}
        <header className="space-y-12 relative">
          <div className="flex justify-between items-start">
            <Image
              src="/images/logo.png"
              alt="LightWeight Logo"
              width={100}
              height={100}
              className=""
            />

            {/* Language Switcher */}
            <div className="flex bg-gray-50/50 p-1 rounded-sm border border-gray-100 backdrop-blur-sm shadow-sm">
              {["en", "uz", "ru"].map((lang) => (
                <button
                  key={lang}
                  onClick={() => setLanguage(lang as any)}
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
                <span className="font-medium">10 {t("active_users")}</span>
              </div>
            </div>
          </div>
        </header>

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
                    <p className="text-2xl font-semibold">64GB+ VRAM</p>
                    <p className="text-xs text-gray-400">{t("price_tag")}</p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">16GB RAM</p>
                    <p className="text-xs text-gray-400">
                      {t("standard_laptop")}
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
                    <p className="text-2xl font-semibold">140GB+ VRAM</p>
                    <p className="text-xs text-gray-400">
                      {t("server_needed")}
                    </p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">32GB RAM</p>
                    <p className="text-xs text-gray-400">{t("personal_pc")}</p>
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
                    <p className="text-2xl font-semibold">300GB+ VRAM</p>
                    <p className="text-xs text-gray-400">
                      {t("server_needed")}
                    </p>
                  </div>
                  <div className="space-y-1 border-l border-gray-100 pl-8">
                    <span className="text-xs uppercase text-green-500 font-bold tracking-tighter">
                      {t("now_lightweight")}
                    </span>
                    <p className="text-2xl font-semibold">24-32GB RAM</p>
                    <p className="text-xs text-gray-400">{t("personal_pc")}</p>
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
              [t("perf_row1_hw"), "O'rtacha (7B-8B)", t("perf_row1_res")],
              [t("perf_row2_hw"), "Katta (14B-32B)", t("perf_row2_res")],
              [t("perf_row3_hw"), "Gigant (70B-671B)", t("perf_row3_res")],
            ]}
          />
        </section>

        {/* 4. Getting Started */}
        <section className="space-y-12">
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
            {t("usage_title")}
          </h2>

          <div className="space-y-8">
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("usage_install")}
              </h3>
              <Terminal commands={["pip install lightweight"]} />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("usage_check")}
              </h3>
              <p className="text-xs text-gray-400 italic">
                {t("usage_check_desc")}
              </p>
              <Terminal commands={["lightweight check"]} />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("usage_mgmt")}
              </h3>
              <p className="text-xs text-gray-400 italic">
                {t("usage_mgmt_desc")}
              </p>
              <Terminal
                commands={["lightweight pull qwen:32b", "lightweight models"]}
              />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("usage_chat")}
              </h3>
              <p className="text-xs text-gray-400 italic">
                {t("usage_chat_desc")}
              </p>
              <Terminal
                commands={[
                  "lightweight chat qwen:32b",
                  'lightweight run qwen:32b "Salom!"',
                ]}
              />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700">
                {t("usage_api")}
              </h3>
              <p className="text-xs text-gray-400 italic">
                {t("usage_api_desc")}
              </p>
              <Terminal commands={["lightweight serve --port 8000"]} />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
