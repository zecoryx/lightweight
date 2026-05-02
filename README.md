<p align="center">
  <img src="asstes/images/logo.png" alt="LiteWeight Logo" width="250">
</p>

<h1 align="center">LiteWeight</h1>

---

LiteWeight — bu ochiq kodli (open-source) AI inference engine bo’lib, asosiy maqsadi og’ir large language model (LLM) larni — masalan Qwen 32B, Llama 70B, Mixtral 8x7B — kam xotirali (8–16 GB RAM, 4–8 GB VRAM) noutbuk va shaxsiy kompyuterlarda to’liq ishlata olishdir.

---

## 1. Muammo va Yechim

### 1.1. Muammo

Ochiq AI modellar katta hajmda parametrlar saqlaydi. Har bir parametr FP16 formatida 2 bayt oladi:

---

| Model | Parametrlar | FP16 hajmi | Minimum VRAM |
| :--- | :--- | :--- | :--- |
| Qwen 7B | 7 milliard | 14 GB | 14–16 GB |
| Qwen 14B | 14 milliard | 28 GB | 28–32 GB |
| Qwen 32B | 32 milliard | 64 GB | 64 GB+ |
| Mixtral 8x7B | 47 milliard | 94 GB | 80 GB+ |
| Llama 3.1 70B | 70 milliard | 140 GB | 8x A100 |

---

**Oddiy foydalanuvchi bu modellarni ishlatib bo’lmaydi. LiteRun ana shu muammoni hal qiladi.**

### 1.2. Yechim qisqacha

*   **Quantization** — model weights'ni 16-bit dan 4-bit ga siqish.
*   **Expert Offloading** — faqat faol qismlarni GPU'da saqlash.
*   **Speculative Decoding** — kichik model yordamida katta modelni tezlashtirish.
*   **Aqlli Memory Manager** — RAM, VRAM va SSD'ni birgalikda boshqarish.

---

## 2. Texnik Asoslar

### 2.1. Quantization

Quantization — bu matematik operatsiya. Model weights'lari FP16 (16-bit float) formatida saqlanadi. Quantization ularni INT4 (4-bit integer) yoki INT8 (8-bit integer) ga o’tkazadi.

#### 2.1.1. GGUF formati

LiteRun GGUF formatidan foydalanadi. Bu llama.cpp jamoasi tomonidan yaratilgan, bitta faylda model weights, metadata va tokenizer saqlaydigan binary formatdir. HuggingFace'dagi barcha modellar bu formatga o’tkazilgan.

Lite weight default sifatida **Q4_K_M** ishlatadi. Bu hajm va sifat o’rtasidagi eng optimal nuqta. Qwen 32B Q4_K_M ≈ 18 GB disk, lekin VRAM va RAM bo’yicha keyingi texnikalar yordamida yanada kamaytirish mumkin.

#### 2.1.2. Quantization matematik asosi

FP16 dan INT4 ga o’tish jarayoni:
`INT4_value = round( FP16_value / scale ) + zero_point`
`FP16_approx = (INT4_value - zero_point) * scale`

Bu yerda `scale` va `zero_point` har bir weight bloki uchun alohida hisoblanadi (K-quant uslubi). Shu sababli K-quant versiyalari (Q4_K_M) oddiy Q4 dan yaxshoreq sifat beradi.

### 2.2. Mixture of Experts (MoE)

Qwen 30B-A3B va Mixtral 8x7B kabi modellar MoE arxitekturasida qurilgan. Bu an’anaviy dense modeldan tubdan farqlanadi.

#### Expert Offloading mexanizmi

Expert Offloading quyidagicha ishlaydi:
1. Har bir token uchun Router qaysi expertlar kerakligini aniqlaydi.
2. Faqat o’sha expertlar GPU VRAM'ga ko’chiriladi.
3. Inference tugagach, ular RAM'ga qaytariladi.
4. Keyingi token uchun jarayon takrorlanadi.
5. **Prefetch**: Router keyingi token uchun ham taxmin qilib, parallel yuklab boshlaydi.

Bu jarayonda GPU VRAM'da faqat 2–4 expert turadi — barcha 8, 64 yoki 128 ta emas.

### 2.3. Speculative Decoding

An’anaviy inference: katta model har bir tokenni navbatma-navbat generatsiya qiladi. Bu sekin, chunki 32B parametrdan o’tish uchun ko’p vaqt kerak.

Speculative Decoding boshqacha ishlaydi:
1. Kichik “draft model” (masalan 1.5B) 5–7 tokenni tez generatsiya qiladi.
2. Katta “target model” (32B) bu tokenlarni parallel tekshiradi.
3. To’g’ri tokenlar qabul qilinadi — bir passda 5–7 token qo’shildi.
4. Xato token topilsa, o’sha joydan katta model to’g’rilaydi.

Natija: katta model sifati saqlanadi (100% deterministik), lekin tezlik 3–5x oshadi.

### 2.4. FloE Compression (ICML 2025)

FloE — bu MoE modellar uchun maxsus compression texnikasi. Expert'lar orasida o’xshash pattern'lar ko’p takrorlanishidan foydalanadi.

---

| Matrix | FloE texnikasi | Natija |
| :--- | :--- | :--- |
| Gate projection | Sparsifikatsiya (70% nol qilish) | 70% kichrayadi |
| Up projection | Ultra-low-bit quantization (1–2 bit) | 87% kichrayadi |
| Down projection | Qisman sparsifikatsiya | 50% kichrayadi |

---

## 3. LiteRun Arxitekturasi

LiteRun oltita mustaqil qatlamdan iborat:

---

| Qatlam | Nomi | Vazifasi | Til |
| :--- | :--- | :--- | :--- |
| 1 | CLI / API Layer | Foydalanuvchi interfeysi | Python (Typer, FastAPI) |
| 2 | Hardware Detector | GPU, RAM, SSD ni aniqlash | Python (psutil, pynvml) |
| 3 | Strategy Engine | Qaysi texnikani ishlatishni hal qilish | Python |
| 4 | Memory Manager | VRAM/RAM/SSD ni boshqarish | Python + C++ |
| 5 | Inference Engine | Asosiy AI hisoblash | C++ (llama.cpp) |
| 6 | Output Streamer | Token stream va API response | Python |

---

### 3.1. Data flow — foydalanuvchi so‘rovi qanday ishlaydi

1. Foydalanuvchi: `literun run qwen:32b "Savol"`
2. CLI Layer so‘rovni qabul qilib, Hardware Detector'ni ishga tushiradi.
3. Hardware Detector: GPU VRAM, RAM, SSD ni o’lchaydi.
4. Strategy Engine natijani oladi va strategiya qaror qiladi: (Q4_K_M, Expert Offloading, Speculative Decoding).
5. Memory Manager model faylini SSD'dan bo‘lib-bo‘lib yuklaydi.
6. Inference Engine (llama.cpp) first token generatsiya qiladi.
7. Output Streamer tokenlarni real-time foydalanuvchiga yuboradi.
8. Sessiya tugagach, Memory Manager xotirani tozalaydi.

### 3.2. Uch xotira zonasi

---

| Zona | Nima saqlanadi | O‘lchami | Kirish tezligi |
| :--- | :--- | :--- | :--- |
| GPU VRAM | Faol expertlar + KV cache + draft model | 4–8 GB | 900+ GB/s |
| CPU RAM | Nofaol expertlar + prefetch buffer | 8–16 GB | 50–80 GB/s |
| NVMe SSD | To’liq model fayli + ML cache | Model hajmi | 3–7 GB/s |

---

### 3.3. Xotira Boshqaruvi

*   **Prefetch mexanizmi**: Memory Manager token inputlariga qarab keyingi token uchun qaysi expertlar kerakligini taxmin qiladi. Token N generatsiya qilinayotganda, token N+1 uchun expertlar RAM'dan VRAM'ga parallel ko'chiriladi.
*   **LRU Cache policy**: Agar yangi expert kerak bo’lib, joy yo’q bo’lsa — LRU (Least Recently Used) algoritmi eng kam ishlatilgan expertni RAM'ga suradi va yangi expertga joy ochadi.

---

## 4. To’liq Tech Stack

---

| Komponent | Texnologiya | Sabab |
| :--- | :--- | :--- |
| Inference engine | llama.cpp (C++) | CUDA/Metal/CPU hybrid, eng tez open engine |
| Python binding | llama-cpp-python | llama.cpp ni Python'dan boshqarish |
| CLI framework | Typer (Python) | Oson CLI, avtomatik --help |
| API server | FastAPI (Python) | OpenAI-compatible endpoint |
| Hardware detection | psutil + pynvml | Cross-platform GPU/RAM o’lchash |
| Quantization | llama.cpp built-in | GGUF Q4_K_M standart |
| Expert scheduling | Custom Python scheduler | FloE + offloading logikasi |

---

## 5. Fayl Tuzilishi

```text
literun/
├── literun/
│   ├── cli.py            # CLI entry point
│   ├── api.py            # FastAPI server
│   ├── hardware/         # GPU/RAM/SSD aniqlash
│   ├── strategy/         # Qaysi texnikani tanlash
│   ├── memory/           # VRAM/RAM/SSD boshqarish
│   ├── inference/        # llama.cpp wrapper & FloE
│   └── models/           # Model registry & downloader
├── tests/
├── docs/
├── pyproject.toml
└── README.md
```

---

## 6. Foydalanish

### 6.1. O‘rnatish

`pip install literun`

### 6.2. Asosiy buyruqlar

*   **Model yuklab olish**: `literun pull qwen:32b` (Hardware'ga mos quantization versiyasini avtomatik tanlaydi).
*   **Suhbat rejimi**: `literun chat qwen:32b` (Interaktiv suhbat oynasi).
*   **Bitta so‘rov**: `literun run qwen:32b "Python'da quicksort yoz"`
*   **API server**: `literun serve --model qwen:32b --port 8080` (OpenAI SDK bilan mos ishlaydi).
*   **Hardware tekshirish**: `literun info`

---

## 7. Talablar va Tezlik

### 7.1. Hardware talablari

---

| Hardware | Minimal | Tavsiya etilgan | Optimal |
| :--- | :--- | :--- | :--- |
| RAM | 8 GB | 16 GB | 32 GB |
| GPU | Yo’q (CPU) | 4 GB VRAM | 8 GB+ VRAM |
| SSD | HDD | SATA SSD | NVMe SSD |
| CPU | 4 yadro | 8 yadro | 16+ yadro |

---

### 7.2. Tezlik kutilmalari

---

| Hardware | Model | Tezlik |
| :--- | :--- | :--- |
| CPU only (i7, 16GB) | Qwen 7B Q4 | 3–5 token/s |
| GTX 1060 6GB | Qwen 7B Q4 | 15–25 token/s |
| RTX 3060 12GB | Qwen 14B Q4 | 20–35 token/s |
| RTX 3060 + Expert off. | Qwen 32B Q4 | 8–15 token/s |
| RTX 4090 24GB | Qwen 32B Q4 | 40–60 token/s |

---
