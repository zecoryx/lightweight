import Image from "next/image";

const TEAM = [
  {
    name: "Abdullayev L",
    username: "@zecoryx",
    image: "https://github.com/zecoryx.png",
    description:
      "LightWeight focuses on exact-model local inference: hardware checks, GGUF metadata inspection, runtime planning, backend routing, and browser or OpenAI-compatible serving without silently replacing the model you chose.",
  },
  {
    name: "Abu Bakr",
    username: "@nafderlin",
    image: "/creator.png",
    description:
      "The workflow includes doctor, inspect-model, probe, and bench so users can see memory pressure, GPU layer fit, and real tokens-per-second before settling on a thermal profile for private local chat.",
  },
];

const Creators = () => {
  return (
    <section className="pb-2">
      <div className="space-y-12">
        <div className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 sm:flex sm:items-center sm:justify-start sm:gap-2">
          {TEAM.map((member, index) => (
            <div
              key={index}
              className="group relative flex min-w-0 items-center gap-4 rounded-lg border border-transparent p-3 transition-all duration-500 hover:border-gray-100 hover:bg-gray-50/30 sm:gap-5 sm:p-4"
            >
              {/* Premium Tooltip */}
              <div className="pointer-events-none invisible absolute bottom-full left-0 z-50 mb-4 w-[min(20rem,calc(100vw-2rem))] rounded-2xl border border-gray-100 bg-white/95 p-5 opacity-0 backdrop-blur-xl transition-all duration-500 translate-y-2 scale-95 origin-bottom-left group-hover:visible group-hover:translate-y-0 group-hover:scale-100 group-hover:opacity-100 sm:mb-6 sm:w-80">
                <div className="flex flex-col space-y-4">
                  <div className="flex items-center gap-3 border-b border-gray-50 pb-3">
                    <div className="relative w-10 h-10 rounded-full overflow-hidden border border-gray-100">
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
                    &quot;{member.description}&quot;
                  </p>
                </div>
                {/* Decorative Arrow */}
                <div className="absolute -bottom-1.5 left-8 w-3 h-3 bg-white border-r border-b border-gray-100 rotate-45" />
              </div>

              <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full border border-gray-100 bg-gray-50 transition-all duration-700 group-hover:grayscale-0 sm:h-14 sm:w-14">
                <Image
                  src={member.image}
                  alt={member.name}
                  fill
                  className="object-cover"
                  sizes="56px"
                />
              </div>
              <div className="flex min-w-0 flex-col space-y-0.5">
                <span className="truncate text-sm font-bold tracking-tight text-[#1a1a1a] transition-colors group-hover:text-black">
                  {member.name}
                </span>
                <span className="truncate text-[10px] font-mono lowercase text-gray-400 opacity-70 transition-opacity group-hover:opacity-100">
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
