import { useLanguage } from "@/context/LanguageContext";
import Image from "next/image";

const TEAM = [
  {
    name: "Abdullayev L",
    username: "@zecoryx",
    image: "https://github.com/zecoryx.png",
    description:
      "Lightweight AI leverages advanced 4-bit quantization and GGUF-based inference to run large-scale language models locally on consumer-grade hardware. Pull optimized weights from our registry and serve them via a minimalist CLI that bypasses the need for high-end GPUs or cloud dependencies.",
  },
  {
    name: "Abu Bakr",
    username: "@nafderlin",
    image: "/creator.png",
    description:
      "Our platform streamlines the AI lifecycle with performance monitoring tools that track token-per-second (TPS) and VRAM usage in real-time. Integrate compressed models into your local workspace with zero-config setup, ensuring full data privacy and low-latency inference across all your devices.",
  },
];

const Creators = () => {
  const { t } = useLanguage();

  return (
    <section className="pb-2">
      <div className="space-y-12">
        <div className="flex items-center justify-start gap-2">
          {TEAM.map((member, index) => (
            <div
              key={index}
              className="group relative flex items-center gap-5 p-4 rounded-lg border border-transparent hover:border-gray-100 hover:bg-gray-50/30 transition-all duration-500 cursor-help"
            >
              {/* Premium Tooltip */}
              <div className="pointer-events-none invisible group-hover:visible absolute bottom-full left-0 mb-6 w-80 p-5 bg-white/95 backdrop-blur-xl border border-gray-100 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.1)] z-50 transition-all duration-500 opacity-0 group-hover:opacity-100 translate-y-2 group-hover:translate-y-0 scale-95 group-hover:scale-100 origin-bottom-left">
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center gap-3 border-b border-gray-50 pb-3">
                    <div className="relative w-10 h-10 rounded-full overflow-hidden border border-gray-100 shadow-sm">
                      <Image
                        src={member.image}
                        alt={member.name}
                        fill
                        className="object-cover"
                        sizes="40px"
                      />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[12px] font-bold text-black tracking-tight">
                        {member.name}
                      </span>
                      <span className="text-[10px] text-gray-400 font-mono">
                        {member.username}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] leading-relaxed text-gray-500 font-medium italic">
                    "{member.description}"
                  </p>
                </div>
                {/* Decorative Arrow */}
                <div className="absolute -bottom-1.5 left-8 w-3 h-3 bg-white border-r border-b border-gray-100 rotate-45" />
              </div>

              <div className="relative w-14 h-14 shrink-0 rounded-full overflow-hidden bg-gray-50 border border-gray-100 group-hover:grayscale-0 transition-all duration-700 shadow-sm">
                <Image
                  src={member.image}
                  alt={member.name}
                  fill
                  className="object-cover"
                  sizes="56px"
                />
              </div>
              <div className="flex flex-col space-y-0.5">
                <span className="text-sm font-bold text-[#1a1a1a] tracking-tight group-hover:text-black transition-colors">
                  {member.name}
                </span>
                <span className="text-[10px] font-mono text-gray-400 lowercase opacity-70 group-hover:opacity-100 transition-opacity">
                  {member.username}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default Creators;
