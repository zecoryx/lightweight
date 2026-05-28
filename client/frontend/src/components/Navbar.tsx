"use client";

import { useLanguage } from "@/context/LanguageContext";

export default function Navbar() {
  const { language, setLanguage } = useLanguage();

  return (
    <nav className="fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-md border-b border-gray-100 z-50">
      <div className="max-w-3xl mx-auto px-6 h-16 flex items-center justify-between">
        <span className="font-semibold tracking-tight text-sm uppercase">LightWeight</span>
        
        <div className="flex gap-4 text-xs font-medium uppercase tracking-widest text-gray-400">
          <button 
            onClick={() => setLanguage("en")}
            className={`hover:text-[#1a1a1a] transition-colors ${language === "en" ? "text-[#1a1a1a] border-b border-[#1a1a1a]" : ""}`}
          >
            EN
          </button>
          <button 
            onClick={() => setLanguage("uz")}
            className={`hover:text-[#1a1a1a] transition-colors ${language === "uz" ? "text-[#1a1a1a] border-b border-[#1a1a1a]" : ""}`}
          >
            UZ
          </button>
          <button 
            onClick={() => setLanguage("ru")}
            className={`hover:text-[#1a1a1a] transition-colors ${language === "ru" ? "text-[#1a1a1a] border-b border-[#1a1a1a]" : ""}`}
          >
            RU
          </button>
        </div>
      </div>
    </nav>
  );
}
