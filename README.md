# 🪶 LightWeight: The Ideal Local AI Engine

**LightWeight** is a high-performance, private-first CLI tool designed to run massive LLMs (like Llama-3.1 70B or Qwen-32B) on everyday consumer laptops without overheating or crashing.

## 🚀 Key "Painkillers" (Why LightWeight?)

- **iMatrix Quantization:** Preserves ~95% of model intelligence even at extreme compression.
- **Thermal Shield:** Intelligently caps CPU threads to keep your laptop cool and silent.
- **Smart Memory Manager:** Real-time RAM monitoring that prevents "Out of Memory" crashes by auto-compacting the KV-cache.
- **Bulletproof Portability:** A single self-contained binary that works on any Windows/Linux/Mac without extra drivers.

---

## 🛠️ Installation

### Windows (PowerShell)
```powershell
irm https://lightweight.zecoryx.uz/install.ps1 | iex
```

### Linux / macOS
```bash
curl -sSf https://lightweight.zecoryx.uz/install.sh | sh
```

---

## 📖 Commands

### 🔍 Check Hardware Compatibility
Analyze if your laptop can handle a model before you spend time downloading it.
```bash
lightweight check llama3:70b
```

### 📥 Download & Optimize
Automatically finds the smartest (iMatrix) and most efficient version for your RAM.
```bash
lightweight pull qwen:32b
```

### 💬 Private Chat
Start an optimized, private conversation. Use `@filename` to inject code/file context.
```bash
lightweight chat qwen:32b
```

### 🌐 Turn your PC into an AI Server
Host an OpenAI-compatible API to use with Cursor, VS Code, or other devices.
```bash
lightweight serve --port 8000
```

### 📂 Manage Storage
See exactly how much space your AI library is taking.
```bash
lightweight storage
```

---

## 🔮 Future Roadmap (v0.2.0)
Currently archived in the `/futures` directory:
- **Multimodal Support:** Native compressed Stable Diffusion and Whisper integration.
- **Text-to-Video:** SVD (Stable Video Diffusion) optimizations.
- **Speculative Decoding:** Blazing fast inference using tiny draft models.

## 📄 License
MIT © LightWeight Team
