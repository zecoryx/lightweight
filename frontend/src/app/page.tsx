import Image from "next/image";
import Section from "@/components/Section";
import DataTable from "@/components/DataTable";
import Terminal from "@/components/Terminal";

export default function Home() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* 1. Header / Hero */}
      <header className="py-16 flex flex-col items-center border-b border-gray-100">
        <Image 
          src="/images/logo.png" 
          alt="LiteWeight Logo" 
          width={250} 
          height={100} 
          className="mb-8"
          priority
        />
        <h1 className="text-5xl font-black tracking-tight mb-4">LiteWeight</h1>
        <p className="text-xl text-gray-500 font-medium italic mb-8">
          Run 32B+ LLMs on 8GB RAM laptops
        </p>
        <div className="w-full max-w-md px-4">
          <Terminal commands={["pip install literun"]} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12 space-y-16 text-justify">
        {/* 2. Introduction */}
        <p className="text-lg leading-relaxed text-gray-700">
          LiteWeight — bu ochiq kodli (open-source) AI inference engine bo’lib, asosiy maqsadi og’ir large language model (LLM) larni — masalan Qwen 32B, Llama 70B, Mixtral 8x7B — kam xotirali (8–16 GB RAM, 4–8 GB VRAM) noutbuk va shaxsiy kompyuterlarda to’liq ishlata olishdir.
        </p>

        {/* 3. Why LiteWeight? (Muammo va Yechim) */}
        <Section title="1. Nega LiteWeight?">
          <h3 className="text-xl font-bold mb-4 text-center">Muammo: Katta modellar = Katta xotira</h3>
          <DataTable 
            headers={["Model", "Parametrlar", "FP16 hajmi", "Minimum VRAM"]}
            rows={[
              ["Qwen 7B", "7 milliard", "14 GB", "14–16 GB"],
              ["Qwen 14B", "14 milliard", "28 GB", "28–32 GB"],
              ["Qwen 32B", "32 milliard", "64 GB", "64 GB+"],
              ["Mixtral 8x7B", "47 milliard", "94 GB", "80 GB+"],
              ["Llama 3.1 70B", "70 milliard", "140 GB", "8x A100"],
            ]}
          />
          <p className="font-bold text-center my-8 text-lg text-blue-600">
            LiteWeight bilan bu modellar oddiy noutbukda ishlaydi.
          </p>
        </Section>

        {/* 4. Hardware & Performance (Talablar va Tezlik) */}
        <Section title="2. Talablar va Tezlik">
          <h3 className="text-xl font-bold mb-4">Hardware talablari</h3>
          <DataTable 
            headers={["Hardware", "Minimal", "Tavsiya etilgan", "Optimal"]}
            rows={[
              ["RAM", "8 GB", "16 GB", "32 GB"],
              ["GPU", "Yo’q (CPU)", "4 GB VRAM", "8 GB+ VRAM"],
              ["SSD", "HDD", "SATA SSD", "NVMe SSD"],
              ["CPU", "4 yadro", "8 yadro", "16+ yadro"],
            ]}
          />
          <h3 className="text-xl font-bold mt-12 mb-4">Tezlik kutilmalari (Real-world)</h3>
          <DataTable 
            headers={["Hardware", "Model", "Tezlik"]}
            rows={[
              ["CPU only (i7, 16GB)", "Qwen 7B Q4", "3–5 token/s"],
              ["GTX 1060 6GB", "Qwen 7B Q4", "15–25 token/s"],
              ["RTX 3060 12GB", "Qwen 14B Q4", "20–35 token/s"],
              ["RTX 3060 + Expert off.", "Qwen 32B Q4", "8–15 token/s"],
              ["RTX 4090 24GB", "Qwen 32B Q4", "40–60 token/s"],
            ]}
          />
        </Section>

        {/* 5. Quick Start (Foydalanish) */}
        <Section title="3. Tezkor Boshlash">
          <h3 className="text-xl font-bold mb-4">O‘rnatish</h3>
          <Terminal commands={["pip install literun"]} />
          
          <h3 className="text-xl font-bold mt-12 mb-4">Asosiy buyruqlar</h3>
          <Terminal commands={[
            "literun pull qwen:32b",
            "literun chat qwen:32b",
            "literun run qwen:32b \"Python'da quicksort yoz\"",
            "literun serve --model qwen:32b --port 8080",
            "literun info"
          ]} />
        </Section>
      </main>

      {/* 6. Footer */}
      <footer className="py-12 text-center border-t border-gray-100 text-gray-400 text-sm">
        © {new Date().getFullYear()} LiteWeight Project. Open Source.
      </footer>
    </div>
  );
}
