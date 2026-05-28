# LightWeight

LightWeight is a private local-AI CLI for running the exact model you choose with a hardware-aware fit plan. It does not silently replace a large model with a smaller one.

The workflow is:

```bash
lightweight doctor
lightweight check qwen:32b --mode fit
lightweight pull qwen:32b --mode fit
lightweight inspect-model qwen:32b
lightweight probe qwen:32b --thermal balanced
lightweight bench qwen:32b --tokens 64 --thermal balanced
lightweight chat qwen:32b --thermal balanced
```

## Why

- Exact-model planning: `quality`, `balanced`, `fit`, and `extreme` tune quant, context, offload, and thermals around the selected model.
- Runtime inspection: `inspect-model` reads GGUF metadata before you tune runtime settings.
- Local profiling: `probe` and `bench` measure memory pressure, GPU layer fit, and real tokens/sec on your machine.
- Active-set planning: MoE experts, KV cache, and dense layer placement are treated separately instead of using one generic offload rule.
- Recovery path: the engine can retry with safer runtime settings when a load hits memory limits.
- Local serving: `serve` opens the browser chat UI and exposes an OpenAI-compatible `/v1` API.

## Installation

### Windows PowerShell

```powershell
irm https://lightweight.zecoryx.uz/install.ps1 | iex
```

### Linux / macOS

```bash
curl -fsSL https://lightweight.zecoryx.uz/install.sh | sh
```

## Commands

### Check the Machine

```bash
lightweight doctor
lightweight check llama3:70b --mode fit
```

`doctor` checks backend support, RAM, VRAM, disk, mmap/mlock, and llama-server availability. `check` builds a plan before you download.

### Pull an Exact Model

```bash
lightweight pull qwen:32b --mode fit
```

You can use a built-in alias such as `qwen:14b`, `qwen:32b`, `llama3:70b`, `deepseek-r1:32b`, or pass an exact Hugging Face GGUF repo ID.

### Squeeze Planning

```bash
lightweight squeeze plan deepseek-r1:14b --target-ram 8gb --target-vram 6gb
lightweight squeeze build deepseek-r1:14b --profile auto --target-ram 8gb --target-vram 6gb
lightweight squeeze verify deepseek-r1:14b
lightweight squeeze report deepseek-r1:14b
lightweight squeeze profiles deepseek-r1:14b
lightweight squeeze use deepseek-r1:14b balanced
```

`squeeze plan` compares `quality`, `balanced`, `fit`, and `extreme` profiles for the exact model. It shows the quant, context, active-set policy, estimated size, and whether the model is ready, tight, slow, or not recommended on the target memory budget.

`squeeze build` downloads the selected exact-model GGUF quant and stores the chosen squeeze profile in the local registry.

`squeeze verify` reads the local model metadata and prints the runtime policy that will be used before you rely on it. Use `--run` when you want a small local load and generation check; the result is saved back into the local registry.

`squeeze report` summarizes the active squeeze profile, runtime profile, metadata, and last verification result.

`squeeze profiles` lists saved profiles for a local model. `squeeze use` switches the active profile used by `chat`, `serve`, and the browser/API backend.

### Inspect, Probe, and Benchmark

```bash
lightweight inspect-model qwen:32b
lightweight probe qwen:32b --thermal balanced
lightweight bench qwen:32b --tokens 64 --thermal balanced
```

Use these before daily use so the runtime profile is based on your actual device, not a generic claim.

### Chat

```bash
lightweight chat qwen:32b --thermal balanced
```

Terminal chat supports local private inference and stop/retry behavior.

### Browser Chat and API Server

```bash
lightweight serve --backend auto --port 8000
```

Then open `http://localhost:8000` for the browser chat UI, or call:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen:32b","messages":[{"role":"user","content":"Hello"}]}'
```

If native `llama-server` is installed:

```bash
lightweight serve --backend llama-server --model qwen:32b --spec ngram-cache
```

For MoE models, LightWeight can use llama-server expert placement when the installed binary supports it:

```bash
lightweight serve --backend llama-server --model mixtral:8x7b --moe-offload auto
lightweight serve --backend llama-server --model qwen-moe --moe-offload first-n --n-cpu-moe 18
```

The intended memory tier is:

```text
VRAM: shared layers, hot experts, active KV cache
RAM: cold experts, quantized model pages, older KV cache
SSD: storage/mmap and last-resort fallback, not the fast path
```

Advanced tensor placement can be passed through only when you know the target llama-server build supports it:

```bash
lightweight serve --backend llama-server --model qwen-moe --override-tensor "blk.*.ffn_.*=CPU"
```

## Manage Storage

```bash
lightweight list
lightweight rm qwen:32b
lightweight storage
```

## Notes

LightWeight can reduce memory pressure with quant selection, mmap, GPU layer offload, MoE expert placement, KV cache options, prompt cache, and backend routing. It cannot make every huge dense model fast on every small laptop without tradeoffs. SSD/NVMe paging is treated as a fallback, not as a promise of interactive speed. When the model is too large, `check`, `probe`, and `bench` make that visible before you rely on it.

## License

MIT © LightWeight Team
