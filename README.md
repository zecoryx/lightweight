<p align="center">
  <img src="frontend/public/logo.png" alt="LightWeight Logo" width="180">
</p>

<h1 align="center">LightWeight AI</h1>

<p align="center">
  <strong>The High-Performance Local LLM Engine for Consumer Hardware.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
</p>

---

**LightWeight** is an open-source inference ecosystem designed to run massive Large Language Models (like Qwen 72B, Llama 405B, or DeepSeek V3) on standard consumer laptops and PCs. By combining state-of-the-art quantization with intelligent hardware-aware strategies, LightWeight makes local AI accessible to everyone.

---

## 🚀 Quick Start

Get up and running in seconds with our one-liner installers.

### Windows (PowerShell)
```powershell
irm https://lightweight.zecoryx.uz/install.ps1 | iex
```

### macOS / Linux (Bash)
```bash
curl -fsSL https://lightweight.zecoryx.uz/install.sh | sh
```

---

## 🏗️ The Ecosystem

### 1. Terminal-Native Workspace (CLI)
A distraction-free, agentic terminal interface inspired by the best developer tools.
- **Interactive Chat**: High-speed markdown streaming with hardware telemetry.
- **Model Management**: One command to pull, list, or remove models from a library of 500+ curated LLMs.
- **Local API**: Host an OpenAI-compatible server on your machine with a single flag.

### 2. High-Fidelity Dashboard (Web)
A modern, cinematic Next.js dashboard to manage your AI library visually.
- **Performance Matrix**: Compare original vs. compressed performance across 500+ models.
- **Active User Stats**: Real-time telemetry of global deployments.
- **Command Palette**: Search and discover models using `Ctrl + .`.

---

## ✨ Key Features

- **Advanced 4-bit Quantization**: Reduce VRAM usage by up to 75% while maintaining 99%+ accuracy.
- **Smart Strategy Engine**: Automatically detects your GPU/RAM and decides the best layer offloading strategy.
- **Zero-Latency Streaming**: Optimized C++ core (llama.cpp) for immediate token response.
- **Enterprise Grade**: Support for massive MoE (Mixture of Experts) models via expert offloading.
- **Privacy First**: Everything runs 100% locally. No data ever leaves your machine.

---

## 💻 CLI Usage

Once installed, use the `lightweight` or `lw` command:

| Command | Description |
| :--- | :--- |
| `lw pull <id>` | Download a model optimized for your hardware. |
| `lw chat <id>` | Start an interactive agentic chat session. |
| `lw serve` | Start an OpenAI-compatible API server (port 8000). |
| `lw check <id>` | Simulate performance on your current hardware. |
| `lw list` | View your local model library. |
| `lw info` | Display detailed system & GPU telemetry. |
| `lw config` | Edit global configuration settings. |

---

## 🛠️ Technology Stack

### Backend (Python Core)
- **Engine**: [llama.cpp](https://github.com/ggerganov/llama.cpp) via `llama-cpp-python`.
- **CLI**: `Typer` & `Rich` for a premium terminal experience.
- **API**: `FastAPI` & `Uvicorn`.
- **Hardware**: `psutil` & `pynvml`.

### Frontend (Next.js Dashboard)
- **Framework**: Next.js 15 (App Router).
- **Styling**: Tailwind CSS v4.
- **Interactions**: Framer Motion & Lucide Icons.

---

## 📁 Project Structure

```text
lightweight/
├── lightweight/        # Python Source (CLI & Engine)
│   ├── cli.py          # Terminal Interface
│   ├── inference.py    # LLM Execution Logic
│   ├── hardware.py     # GPU/RAM Detection
│   └── strategy.py     # Offloading Algorithms
├── frontend/           # Next.js Web Dashboard
│   ├── src/app/        # Pages & API Routes
│   └── src/components/ # UI Components
├── .github/            # CI/CD Workflows (Auto-build)
├── install.ps1         # Windows Installer
└── install.sh          # Unix Installer
```

---

## 📋 Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **RAM** | 8 GB | 16 GB - 32 GB |
| **GPU** | Integrated | 8 GB+ VRAM (NVIDIA/Metal) |
| **Disk** | HDD | NVMe SSD (for fast model loading) |
| **OS** | Windows 10+ | macOS (M1/M2/M3) or Linux |

---

<p align="center">
  Built with ❤️ by the LightWeight Team.
</p>
