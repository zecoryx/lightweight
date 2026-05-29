import os
import sys
from pathlib import Path

# ─── ULTIMATE EXE PATH RESOLUTION ───────────────────────────
def setup_ultimate_environment():
    # PyInstaller vaqtinchalik papkasi
    bundle_dir = getattr(sys, '_MEIPASS', None)
    
    if bundle_dir:
        base_path = Path(bundle_dir)
        # Windows DLL Safety: llama_cpp-ni hamma yeridan qidiramiz
        if os.name == 'nt' and hasattr(os, 'add_dll_directory'):
            dll_locations = [
                base_path / "llama_cpp",
                base_path / "llama_cpp" / "lib",
                base_path / "cli" / "inference"
            ]
            for loc in dll_locations:
                if loc.exists():
                    try: os.add_dll_directory(str(loc))
                    except Exception: pass
        
        # EXE ichidagi 'cli' papkasini import qilinadigan qilish
        sys.path.insert(0, str(base_path))
        if (base_path / "cli").exists():
            sys.path.insert(0, str(base_path / "cli"))
    else:
        # Development rejimida
        current_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(current_dir.parent))
        sys.path.insert(0, str(current_dir))

setup_ultimate_environment()

# ─── RELATIVE IMPORTS FOR PACKAGE STABILITY ─────────────────
try:
    from hardware import Detector, HardwareReport
    from models import ModelManager
    from strategy import StrategyEngine
    from inference import InferenceEngine
    from runtime_probe import probe_gpu_layers
    from metadata import read_model_metadata
    from runtime_policy import apply_metadata, auto_profile_needed, choose_backend
except ImportError:
    from cli.hardware import Detector, HardwareReport
    from cli.models import ModelManager
    from cli.strategy import StrategyEngine
    from cli.inference import InferenceEngine
    from cli.runtime_probe import probe_gpu_layers
    from cli.metadata import read_model_metadata
    from cli.runtime_policy import apply_metadata, auto_profile_needed, choose_backend

# ─── CLI LOGIC ───────────────────────────────────────────────
import time
import inspect
import platform
import shlex
import shutil
import subprocess
from typing import Optional, List

try:
    import psutil
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TransferSpeedColumn
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.key_binding import KeyBindings
    import typer
except ModuleNotFoundError as exc:
    print(f"LightWeight dependency missing: {exc.name}. Reinstall with project dependencies or use the packaged binary.", file=sys.stderr)
    raise SystemExit(1)

__version__ = "0.1.0"
app = typer.Typer(no_args_is_help=True, help="LightWeight — 100% Reliable Local AI.")
squeeze_app = typer.Typer(no_args_is_help=True, help="Plan and verify exact-model squeeze profiles.")
app.add_typer(squeeze_app, name="squeeze")
console = Console()

def _is_windows_console_error(exc: Exception) -> bool:
    return exc.__class__.__name__ == "NoConsoleScreenBufferError"

def _create_prompt_session(toolbar, key_bindings):
    return PromptSession(
        bottom_toolbar=toolbar,
        multiline=True,
        key_bindings=key_bindings,
        style=PTStyle.from_dict({"prompt": "bg:#333333 fg:#ffffff bold", "": "bg:#333333 fg:#ffffff"})
    )

def _safe_open_browser(url: str):
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass

def _format_bytes(value: int) -> str:
    amount = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024

def _pull_with_progress(manager: ModelManager, model_id: str, **kwargs) -> str:
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    state = {"parts_task": None, "bytes_task": None}

    def on_progress(event: str, **payload):
        if event == "resolve_start":
            progress.console.print(f"[bold]Resolving[/bold] {payload.get('repo')}")
        elif event == "metadata_start":
            progress.console.print("[dim]Reading remote file sizes...[/dim]")
        elif event == "download_plan":
            total_files = int(payload.get("total_files") or 1)
            total_bytes = int(payload.get("total_bytes") or 0)
            state["parts_task"] = progress.add_task("Download parts", total=total_files)
            if total_bytes > 0:
                state["bytes_task"] = progress.add_task(f"Downloaded {_format_bytes(total_bytes)}", total=total_bytes)
        elif event == "file_start":
            filename = payload.get("filename", "model.gguf")
            index = payload.get("index")
            total = payload.get("total")
            size = int(payload.get("bytes") or 0)
            progress.console.print(f"[cyan]Part {index}/{total}[/cyan] {filename} ({_format_bytes(size) if size else 'size unknown'})")
        elif event == "file_done":
            size = int(payload.get("bytes") or 0)
            if state["parts_task"] is not None:
                progress.advance(state["parts_task"], 1)
            if state["bytes_task"] is not None and size:
                progress.advance(state["bytes_task"], size)

    with progress:
        return manager.pull(model_id, progress_callback=on_progress, **kwargs)

def _normalize_thermal(value: str) -> str:
    thermal = (value or "balanced").lower()
    if thermal not in {"cool", "balanced", "performance"}:
        console.print("[yellow]Unknown thermal mode; using balanced.[/yellow]")
        return "balanced"
    return thermal

def _print_plan(plan: dict):
    table = Table(title=f"Exact-model plan: {plan['model_id']}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Replacement", plan["replacement"])
    table.add_row("Repo", plan["repo"])
    table.add_row("Mode", plan["mode"])
    table.add_row("Verdict", plan["verdict"])
    table.add_row("Quant", plan["quant"])
    table.add_row("Context", str(plan["ctx"]))
    table.add_row("Estimated model size", f"{plan['estimated_gb']:.1f} GB")
    table.add_row("Usable memory estimate", f"{plan['usable_gb']:.1f} GB")
    table.add_row("Quality risk", plan["quality_risk"])
    table.add_row("MoE detected", "yes" if plan["moe"] else "no")
    table.add_row("Active-set policy", plan.get("active_set", "kv-cache"))
    table.add_row("Memory tier", plan.get("memory_tier", "VRAM/RAM"))
    console.print(table)
    if plan.get("core_optimizations"):
        console.print("[bold]Core optimizations[/bold]")
        for item in plan["core_optimizations"]:
            console.print(f"  - {item}")
    if plan.get("notes"):
        console.print("[bold]Notes[/bold]")
        for item in plan["notes"]:
            console.print(f"  - {item}")

def _resolve_local_model(manager: ModelManager, model: str):
    path = manager.get_model_path(model)
    registry_model = manager.registry.get(model)
    if not path:
        for local in manager.list_local_models():
            if model.lower() in local["name"].lower():
                return local["path"], local["name"], local
    return path, model, registry_model

def _apply_runtime_profile(strategy, profile: Optional[dict]):
    if not profile:
        return strategy
    if "n_gpu_layers" in profile:
        strategy.n_gpu_layers = max(0, int(profile["n_gpu_layers"]))
    if "n_batch" in profile:
        strategy.n_batch = max(1, int(profile["n_batch"]))
    if "n_ubatch" in profile:
        strategy.n_ubatch = max(1, int(profile["n_ubatch"]))
    if "n_threads" in profile:
        strategy.n_threads = max(1, int(profile["n_threads"]))
    if "n_threads_batch" in profile:
        strategy.n_threads_batch = max(1, int(profile["n_threads_batch"]))
    if "ctx" in profile:
        strategy.n_ctx = max(1, int(profile["ctx"]))
    if "kv_cache_type" in profile:
        strategy.kv_cache_type = str(profile["kv_cache_type"])
    if "moe_offload" in profile:
        strategy.moe_offload = str(profile["moe_offload"])
    if "n_cpu_moe" in profile and profile["n_cpu_moe"] is not None:
        strategy.n_cpu_moe = max(0, int(profile["n_cpu_moe"]))
    return strategy

def _apply_squeeze_profile(strategy, profile: Optional[dict], user_ctx: Optional[int] = None):
    if not profile:
        return strategy
    if user_ctx is None and profile.get("ctx"):
        strategy.n_ctx = max(128, int(profile["ctx"]))
    if profile.get("active_set"):
        strategy.active_set_policy = str(profile["active_set"])
    memory_tier = str(profile.get("memory_tier", "")).lower()
    if "ssd" in memory_tier:
        strategy.ssd_policy = "fallback-only"
    if "moe" in str(profile.get("active_set", "")).lower():
        strategy.use_expert_offloading = True
        if strategy.moe_offload == "off":
            strategy.moe_offload = "first-n"
    return strategy

def _maybe_auto_profile(
    manager: ModelManager,
    model: str,
    path: str,
    strategy,
    thermal: str,
    metadata,
    timeout: int = 90,
):
    if os.environ.get("LIGHTWEIGHT_AUTO_PROFILE", "1") == "0":
        return None
    profile = manager.get_runtime_profile(model, thermal)
    if _llama_capability("llama_supports_gpu_offload") is False:
        if profile and int(profile.get("n_gpu_layers", 0) or 0) == 0:
            return profile
        profile = {
            "thermal": thermal,
            "n_gpu_layers": 0,
            "n_batch": strategy.n_batch,
            "n_ubatch": strategy.n_ubatch,
            "n_threads": strategy.n_threads,
            "n_threads_batch": strategy.n_threads_batch,
            "kv_cache_type": strategy.kv_cache_type,
            "moe_offload": strategy.moe_offload,
            "n_cpu_moe": strategy.n_cpu_moe,
            "ctx": strategy.n_ctx,
            "model_size_mb": strategy.model_total_size_mb,
            "metadata": metadata.to_dict() if metadata else None,
            "attempts": [{"layers": 0, "ok": True, "reason": "llama-cpp-python GPU offload is not available"}],
            "created_at": int(time.time()),
            "auto": True,
        }
        manager.save_runtime_profile(model, profile)
        return profile
    if not auto_profile_needed(profile, metadata, strategy):
        return profile
    if strategy.n_gpu_layers <= 0:
        return profile
    if getattr(sys, "frozen", False) and os.environ.get("LIGHTWEIGHT_AUTO_PROFILE") != "1":
        return profile
    console.print(f"[dim]Auto-profiling {model} for this hardware...[/dim]")
    result = probe_gpu_layers(path, strategy, max_layers=strategy.n_gpu_layers, timeout=timeout)
    profile = {
        "thermal": thermal,
        "n_gpu_layers": int(result["best_n_gpu_layers"]),
        "n_batch": strategy.n_batch,
        "n_ubatch": strategy.n_ubatch,
        "n_threads": strategy.n_threads,
        "n_threads_batch": strategy.n_threads_batch,
        "kv_cache_type": strategy.kv_cache_type,
        "moe_offload": strategy.moe_offload,
        "n_cpu_moe": strategy.n_cpu_moe,
        "ctx": strategy.n_ctx,
        "model_size_mb": strategy.model_total_size_mb,
        "metadata": metadata.to_dict() if metadata else None,
        "attempts": result["attempts"],
        "created_at": int(time.time()),
        "auto": True,
    }
    manager.save_runtime_profile(model, profile)
    return profile

def _llama_capability(name: str):
    try:
        import llama_cpp
        fn = getattr(llama_cpp, name, None)
        return fn() if callable(fn) else None
    except Exception:
        return None

def _llama_init_supports(param: str) -> bool:
    try:
        from llama_cpp import Llama
        return param in inspect.signature(Llama.__init__).parameters
    except Exception:
        return False

_LLAMA_SERVER_HELP_CACHE: Optional[str] = None

def _find_llama_server() -> Optional[str]:
    configured = os.environ.get("LIGHTWEIGHT_LLAMA_SERVER")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return str(path)
        return configured
    return shutil.which("llama-server") or shutil.which("llama-server.exe")

def _llama_server_help(binary: str) -> str:
    global _LLAMA_SERVER_HELP_CACHE
    if _LLAMA_SERVER_HELP_CACHE is not None:
        return _LLAMA_SERVER_HELP_CACHE
    try:
        result = subprocess.run(
            [binary, "--help"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        _LLAMA_SERVER_HELP_CACHE = f"{result.stdout}\n{result.stderr}"
    except Exception:
        _LLAMA_SERVER_HELP_CACHE = ""
    return _LLAMA_SERVER_HELP_CACHE

def _server_supports(binary: str, flag: str) -> bool:
    return flag in _llama_server_help(binary)

def _normalize_spec(spec: str) -> str:
    value = (spec or "off").strip().lower()
    allowed = {"off", "ngram-cache", "ngram-simple", "ngram-mod"}
    if value not in allowed:
        console.print("[yellow]Unknown speculative mode; using off.[/yellow]")
        return "off"
    return value

def _normalize_moe_offload(value: str) -> str:
    mode = (value or "auto").strip().lower()
    if mode not in {"auto", "off", "all", "first-n"}:
        console.print("[yellow]Unknown MoE offload mode; using auto.[/yellow]")
        return "auto"
    return mode

def _parse_gb(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().lower().replace(" ", "")
    if not text:
        return None
    multiplier = 1.0
    if text.endswith("mb"):
        multiplier = 1.0 / 1024
        text = text[:-2]
    elif text.endswith("gb"):
        text = text[:-2]
    elif text.endswith("g"):
        text = text[:-1]
    try:
        return max(0.0, float(text) * multiplier)
    except ValueError:
        raise typer.BadParameter("Use a size like 8gb, 16gb, or 6144mb.")

def _report_with_targets(report: HardwareReport, target_ram: Optional[str], target_vram: Optional[str]) -> HardwareReport:
    ram_gb = _parse_gb(target_ram)
    vram_gb = _parse_gb(target_vram)
    gpus = list(report.gpus)
    if vram_gb is not None and gpus:
        first = gpus[0]
        target_mb = int(vram_gb * 1024)
        gpus[0] = type(first)(
            name=f"{first.name} target",
            total_vram=max(first.total_vram, target_mb),
            free_vram=target_mb,
            index=first.index,
        )
    elif vram_gb is not None and vram_gb > 0:
        try:
            from cli.hardware import GPUInfo
        except Exception:
            from hardware import GPUInfo
        target_mb = int(vram_gb * 1024)
        gpus = [GPUInfo(name="Target GPU", total_vram=target_mb, free_vram=target_mb, index=0)]
    if ram_gb is None:
        return HardwareReport(
            total_ram=report.total_ram,
            available_ram=report.available_ram,
            gpus=gpus,
            disk_free=report.disk_free,
            has_cuda=bool(gpus) or report.has_cuda,
            timestamp=report.timestamp,
        )
    ram_mb = int(ram_gb * 1024)
    return HardwareReport(
        total_ram=max(report.total_ram, ram_mb),
        available_ram=ram_mb,
        gpus=gpus,
        disk_free=report.disk_free,
        has_cuda=bool(gpus) or report.has_cuda,
        timestamp=report.timestamp,
    )

def _profile_rank(verdict: str) -> int:
    return {"READY": 0, "TIGHT": 1, "SLOW_MODE": 2, "NOT_RECOMMENDED": 3}.get(verdict, 9)

def _recommend_squeeze_profile(plans: List[dict]) -> dict:
    acceptable = [p for p in plans if p["verdict"] in {"READY", "TIGHT"}]
    if acceptable:
        balanced = next((p for p in acceptable if p["mode"] == "balanced"), None)
        return balanced or sorted(acceptable, key=lambda p: (_profile_rank(p["verdict"]), p["estimated_gb"]))[0]
    slow = [p for p in plans if p["verdict"] == "SLOW_MODE"]
    if slow:
        return sorted(slow, key=lambda p: p["estimated_gb"])[0]
    return sorted(plans, key=lambda p: p["estimated_gb"])[0]

def _is_recommended_plan(plan: dict) -> bool:
    return plan.get("verdict") in {"READY", "TIGHT", "SLOW_MODE"}

def _resolve_ggml_backend_path(path_value: Optional[str]) -> Optional[str]:
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_file():
        return str(path)
    if not path.is_dir():
        return path_value
    preferred = [
        "ggml-cuda.dll",
        "ggml-vulkan.dll",
        "ggml-cpu.dll",
        "llama.dll",
        "libggml-cuda.so",
        "libggml-vulkan.so",
        "libggml-cpu-x64.so",
        "libggml-cpu.so",
        "libggml-base.so",
    ]
    for name in preferred:
        candidate = path / name
        if candidate.exists():
            return str(candidate)
    matches = sorted(path.glob("ggml-*.dll")) or sorted(path.glob("libggml-*.so")) or sorted(path.glob("*.dylib"))
    return str(matches[0]) if matches else str(path)

class AgenticCLI:
    def __init__(
        self,
        model_name: str,
        path: str,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        thermal: str = "balanced",
    ):
        self.model_name = model_name
        self.path = path
        self.n_ctx = n_ctx
        self.detector = Detector()
        self.manager = ModelManager()
        self.process = psutil.Process(os.getpid())
        report = self.detector.get_report()
        model_size = os.path.getsize(path) // (1024 * 1024)
        metadata = read_model_metadata(path)
        strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model_name, thermal_mode=thermal)
        squeeze_profile = self.manager.get_squeeze_profile(model_name)
        strategy = _apply_squeeze_profile(strategy, squeeze_profile, user_ctx=n_ctx)
        strategy = apply_metadata(strategy, metadata, user_ctx=n_ctx)
        profile = _maybe_auto_profile(self.manager, model_name, path, strategy, thermal, metadata)
        strategy = _apply_runtime_profile(strategy, profile)
        strategy.n_ctx = n_ctx
        if n_threads is not None:
            strategy.n_threads = max(1, n_threads)
        self.engine = InferenceEngine(
            path,
            strategy,
            system_instruction=(
                "You are LightWeight, a concise local AI assistant. "
                "Reply in the same language as the user. "
                "If the user greets you, greet them naturally and briefly."
            ),
        )
        self.n_threads = strategy.n_threads
        self.squeeze_profile = squeeze_profile
        self.strategy = strategy
        self.is_running = True

    def _print_header(self):
        console.print()
        logo = "[bold white]╔════╗\n║ 🪶 ║\n╚════╝[/bold white]"
        squeeze = ""
        if self.squeeze_profile:
            squeeze = f"\n[dim]Squeeze: {self.squeeze_profile.get('profile')} / {self.strategy.active_set_policy}[/dim]"
        welcome = f"[bold white]LightWeight v{__version__}[/bold white]\n[dim]The Ultimate Bulletproof Build[/dim]{squeeze}"
        grid = Table.grid(padding=(0, 2))
        grid.add_column(); grid.add_column()
        grid.add_row(logo, welcome)
        console.print(Panel(grid, border_style="dim", padding=(1, 2), expand=False))
        console.print()

    def _toolbar(self):
        try: ram = self.process.memory_info().rss / (1024 * 1024)
        except Exception: ram = 0
        return HTML(f'<style fg="#888888"> {self.model_name} · {ram:.0f}mb · ctx {self.strategy.n_ctx} · /help</style>')

    def _handle_slash(self, text: str):
        cmd = text.split()[0].lower()
        if cmd in ["/exit", "/quit", "/q"]: self.is_running = False
        elif cmd == "/info":
            report = self.detector.get_report(force=True)
            console.print(f"\n  [bold]RAM:[/bold] {report.available_ram}/{report.total_ram}MB")
            console.print(f"  [bold]Threads:[/bold] {self.n_threads}\n")
        elif cmd == "/storage":
            manager = self.manager
            local = manager.list_local_models()
            total_size = sum(m.get('size', 0) for m in local)
            console.print(f"\n  [bold]Disk Space:[/bold] {total_size / 1024:.2f} GB used\n")
        elif cmd == "/clear": console.clear(); self._print_header()
        elif cmd == "/compact":
            self.engine.mem_manager.compact(self.engine.model)
            console.print("[dim]  Memory compacted.[/dim]\n")

    def _markdown(self, text: str):
        return Markdown(
            text,
            code_theme="one-dark",
            inline_code_theme="one-dark",
            hyperlinks=True,
            style="default",
        )

    def run(self):
        self._print_header()
        kb = KeyBindings()
        @kb.add("enter")
        def _(event): event.current_buffer.validate_and_handle()
        @kb.add("escape", "enter")
        def _(event): event.current_buffer.insert_text("\n")

        try:
            session = _create_prompt_session(self._toolbar, kb)
        except Exception as exc:
            if not _is_windows_console_error(exc):
                raise
            console.print("[yellow]Windows interactive console unavailable; using plain input mode.[/yellow]")
            self._run_plain_input()
            return

        while self.is_running:
            try:
                try:
                    user_input = session.prompt(HTML("<style fg='#d97757'>›</style> "))
                except Exception as exc:
                    if not _is_windows_console_error(exc):
                        raise
                    console.print("[yellow]Windows interactive console unavailable; using plain input mode.[/yellow]")
                    self._run_plain_input()
                    return
                if not user_input.strip(): continue
                if user_input.startswith("/"): self._handle_slash(user_input)
                else:
                    with Live(console=console, refresh_per_second=10) as live:
                        full = ""
                        first_token = True
                        try:
                            for chunk in self.engine.generate(user_input):
                                full += chunk["text"]
                                if first_token:
                                    first_token = False
                                live.update(self._markdown(full or "Writing..."))
                            if first_token:
                                live.update(self._markdown("_No response._"))
                        except KeyboardInterrupt:
                            live.update(self._markdown("_Stopped._"))
                    console.print()
            except (KeyboardInterrupt, EOFError): break

    def _run_plain_input(self):
        while self.is_running:
            try:
                user_input = input("› ")
                if not user_input.strip():
                    continue
                if user_input.startswith("/"):
                    self._handle_slash(user_input)
                    continue
                with Live(console=console, refresh_per_second=10) as live:
                    full = ""
                    first_token = True
                    try:
                        for chunk in self.engine.generate(user_input):
                            full += chunk["text"]
                            first_token = False
                            live.update(self._markdown(full or "Writing..."))
                        if first_token:
                            live.update(self._markdown("_No response._"))
                    except KeyboardInterrupt:
                        live.update(self._markdown("_Stopped._"))
                console.print()
            except (KeyboardInterrupt, EOFError):
                break

@app.command()
def chat(model: str, ctx: int = 4096, threads: Optional[int] = None, thermal: str = "balanced"):
    thermal = _normalize_thermal(thermal)
    manager = ModelManager()
    path, model, registry_model = _resolve_local_model(manager, model)
    if not path: console.print(f"Error: Model '{model}' not found."); raise typer.Exit(1)
    squeeze_profile = manager.get_squeeze_profile(model)
    if squeeze_profile and ctx == 4096:
        ctx = int(squeeze_profile.get("ctx", ctx))
    elif registry_model and registry_model.get("plan") and ctx == 4096:
        ctx = int(registry_model["plan"].get("ctx", ctx))
    cli = AgenticCLI(model, path, n_ctx=ctx, n_threads=threads, thermal=thermal); cli.run()

@app.command()
def bench(
    model: str,
    tokens: int = 64,
    ctx: int = 2048,
    thermal: str = typer.Option("balanced", "--thermal", help="Runtime profile: cool, balanced, or performance."),
):
    thermal = _normalize_thermal(thermal)
    manager = ModelManager(); path = manager.get_model_path(model)
    if not path:
        for m in manager.list_local_models():
            if model.lower() in m["name"].lower():
                path, model = m["path"], m["name"]; break
    if not path:
        console.print(f"Error: Model '{model}' not found.")
        raise typer.Exit(1)

    detector = Detector(); report = detector.get_report(force=True)
    model_size = os.path.getsize(path) // (1024 * 1024)
    metadata = read_model_metadata(path)
    strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model, thermal_mode=thermal)
    squeeze_profile = manager.get_squeeze_profile(model)
    strategy = _apply_squeeze_profile(strategy, squeeze_profile, user_ctx=ctx)
    strategy = apply_metadata(strategy, metadata, user_ctx=ctx)
    profile = _maybe_auto_profile(manager, model, path, strategy, thermal, metadata)
    strategy = _apply_runtime_profile(strategy, profile)
    strategy.n_ctx = ctx
    engine = InferenceEngine(path, strategy)

    process = psutil.Process(os.getpid())
    ram_before = process.memory_info().rss / (1024 * 1024)
    started = time.perf_counter()
    generated = ""
    try:
        for chunk in engine.generate("Write one concise benchmark sentence.", max_tokens=tokens):
            generated += chunk["text"]
    except Exception as exc:
        console.print(f"✗ Benchmark failed: {exc}")
        raise typer.Exit(1)
    elapsed = max(time.perf_counter() - started, 0.001)
    ram_after = process.memory_info().rss / (1024 * 1024)
    token_estimate = max(1, len(generated.split()))

    table = Table(title=f"Benchmark: {model}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Elapsed", f"{elapsed:.2f}s")
    table.add_row("Approx throughput", f"{token_estimate / elapsed:.2f} word-tokens/s")
    table.add_row("RAM delta", f"{ram_after - ram_before:.0f} MB")
    table.add_row("GPU layers", str(strategy.n_gpu_layers))
    table.add_row("Threads", str(strategy.n_threads))
    table.add_row("Context", str(strategy.n_ctx))
    table.add_row("Batch / uBatch", f"{strategy.n_batch} / {strategy.n_ubatch}")
    table.add_row("KV cache", strategy.kv_cache_type)
    table.add_row("Flash attention", "on" if strategy.flash_attn else "off")
    table.add_row("KQV offload", "on" if strategy.offload_kqv else "off")
    table.add_row("Thermal", strategy.thermal_mode)
    if squeeze_profile:
        table.add_row("Squeeze profile", str(squeeze_profile.get("profile", "active")))
    console.print(table)
    manager.save_squeeze_benchmark(model, {
        "ok": True,
        "source": "bench",
        "thermal": thermal,
        "ctx": strategy.n_ctx,
        "generation_seconds": round(elapsed, 3),
        "chunks_per_second": round(token_estimate / elapsed, 3),
        "rss_delta_mb": round(ram_after - ram_before, 1),
        "sample": generated[:500],
        "created_at": int(time.time()),
    })

@app.command()
def doctor():
    detector = Detector()
    report = detector.get_report(force=True)

    try:
        import llama_cpp
        llama_version = getattr(llama_cpp, "__version__", "unknown")
    except Exception:
        llama_version = "not installed"

    table = Table(title="LightWeight Doctor", box=None)
    table.add_column("Check", style="bold dim")
    table.add_column("Value")
    table.add_row("OS", f"{platform.system()} {platform.release()} ({platform.machine()})")
    table.add_row("Python", sys.version.split()[0])
    table.add_row("llama-cpp-python", str(llama_version))
    server_binary = _find_llama_server()
    server_lib_path = os.environ.get("LIGHTWEIGHT_LLAMA_SERVER_LIB_PATH")
    table.add_row("llama-server binary", server_binary or "not found")
    table.add_row("llama-server lib path", server_lib_path or "system")
    table.add_row(
        "GGML backend path",
        os.environ.get("GGML_BACKEND_PATH") or _resolve_ggml_backend_path(server_lib_path) or "system",
    )
    table.add_row("RAM", f"{report.available_ram}/{report.total_ram} MB available")
    table.add_row(
        "GPU",
        ", ".join(f"{gpu.index}: {gpu.name} ({gpu.free_vram}/{gpu.total_vram} MB free)" for gpu in report.gpus)
        or "No NVIDIA GPU detected by NVML",
    )
    table.add_row("GPU offload support", str(_llama_capability("llama_supports_gpu_offload")))
    table.add_row("mmap support", str(_llama_capability("llama_supports_mmap")))
    table.add_row("mlock support", str(_llama_capability("llama_supports_mlock")))
    table.add_row("RPC support", str(_llama_capability("llama_supports_rpc")))
    table.add_row("flash_attn param", str(_llama_init_supports("flash_attn")))
    table.add_row("KV cache type params", str(_llama_init_supports("type_k") and _llama_init_supports("type_v")))
    table.add_row("n_batch/n_ubatch params", str(_llama_init_supports("n_batch") and _llama_init_supports("n_ubatch")))
    table.add_row("n_threads_batch param", str(_llama_init_supports("n_threads_batch")))
    table.add_row("RoPE/YaRN params", str(_llama_init_supports("rope_scaling_type") and _llama_init_supports("yarn_ext_factor")))
    table.add_row("draft_model param", str(_llama_init_supports("draft_model")))
    console.print(table)

@app.command()
def probe(
    model: str,
    ctx: int = 512,
    max_layers: Optional[int] = None,
    timeout: int = 120,
    thermal: str = typer.Option("balanced", "--thermal", help="Runtime profile: cool, balanced, or performance."),
):
    thermal = _normalize_thermal(thermal)
    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found.")
        raise typer.Exit(1)

    report = Detector().get_report(force=True)
    model_size = os.path.getsize(path) // (1024 * 1024)
    metadata = read_model_metadata(path)
    strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model, thermal_mode=thermal)
    squeeze_profile = manager.get_squeeze_profile(model)
    strategy = _apply_squeeze_profile(strategy, squeeze_profile, user_ctx=ctx)
    strategy = apply_metadata(strategy, metadata, user_ctx=ctx)
    strategy.n_ctx = ctx
    ceiling = max_layers if max_layers is not None else max(1, strategy.n_gpu_layers)
    if ceiling <= 0:
        console.print("No CUDA VRAM detected for probing. Keeping CPU mode.")
        raise typer.Exit(0)

    console.print(f"Probing GPU layers for {model} up to {ceiling} layers...")
    result = probe_gpu_layers(path, strategy, max_layers=ceiling, timeout=timeout)
    best = int(result["best_n_gpu_layers"])
    profile = {
        "thermal": thermal,
        "n_gpu_layers": best,
        "n_batch": strategy.n_batch,
        "n_ubatch": strategy.n_ubatch,
        "n_threads": strategy.n_threads,
        "n_threads_batch": strategy.n_threads_batch,
        "kv_cache_type": strategy.kv_cache_type,
        "ctx": ctx,
        "model_size_mb": model_size,
        "metadata": metadata.to_dict(),
        "attempts": result["attempts"],
        "created_at": int(time.time()),
    }
    manager.save_runtime_profile(model, profile)

    table = Table(title=f"Probe result: {model}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Best GPU layers", str(best))
    table.add_row("Thermal", thermal)
    table.add_row("Context used for probe", str(ctx))
    table.add_row("Attempts", ", ".join(str(a["layers"]) for a in result["attempts"]))
    table.add_row("Saved", "yes")
    console.print(table)

@app.command()
def pull(model_id: str, quant: Optional[str] = None, mode: str = "balanced", run_anyway: bool = False):
    manager = ModelManager(); detector = Detector()
    try:
        report = detector.get_report()
        plan = manager.build_fit_plan(model_id, hardware_report=report, mode=mode)
        _print_plan(plan)
        if plan["verdict"] == "NOT_RECOMMENDED" and not run_anyway:
            console.print("[yellow]This exact model is not recommended on this hardware. No smaller model will be substituted.[/yellow]")
            console.print("Use --run-anyway to download it anyway, or choose --mode extreme if you accept quality/speed tradeoffs.")
            raise typer.Exit(2)
        path = _pull_with_progress(manager, model_id, hardware_report=report, manual_quant=quant, mode=mode, plan=plan)
        console.print(f"✓ Ready: {path}")
    except Exception as e: console.print(f"✗ Error: {e}"); raise typer.Exit(1)

@app.command()
def check(model_id: str, mode: str = "balanced"):
    manager = ModelManager(); detector = Detector()
    report = detector.get_report(force=True)
    plan = manager.build_fit_plan(model_id, hardware_report=report, mode=mode)
    _print_plan(plan)
    console.print("RAM: " + f"{report.available_ram}/{report.total_ram} MB available")
    console.print("GPU: " + (", ".join(f"{g.name} ({g.free_vram}/{g.total_vram} MB)" for g in report.gpus) or "No CUDA GPU detected"))

@squeeze_app.command(name="plan")
def squeeze_plan(
    model_id: str,
    target_ram: Optional[str] = typer.Option(None, "--target-ram", help="Plan as if this much RAM is available, for example 8gb or 16gb."),
    target_vram: Optional[str] = typer.Option(None, "--target-vram", help="Plan as if this much VRAM is available, for example 6gb."),
):
    manager = ModelManager()
    report = _report_with_targets(Detector().get_report(force=True), target_ram, target_vram)
    modes = ["quality", "balanced", "fit", "extreme"]
    plans = [manager.build_fit_plan(model_id, hardware_report=report, mode=mode) for mode in modes]
    recommended = _recommend_squeeze_profile(plans)

    table = Table(title=f"Squeeze plan: {model_id}", box=None)
    table.add_column("Profile", style="bold")
    table.add_column("Verdict")
    table.add_column("Quant")
    table.add_column("Ctx", justify="right")
    table.add_column("Est. GB", justify="right")
    table.add_column("Quality risk")
    table.add_column("Active-set")
    for plan in plans:
        marker = " <- recommended" if plan["mode"] == recommended["mode"] and _is_recommended_plan(recommended) else ""
        table.add_row(
            plan["mode"] + marker,
            plan["verdict"],
            plan["quant"],
            str(plan["ctx"]),
            f"{plan['estimated_gb']:.1f}",
            plan["quality_risk"],
            plan.get("active_set", "kv-cache"),
        )
    console.print(table)
    console.print(f"Usable memory estimate: {recommended['usable_gb']:.1f} GB")
    if _is_recommended_plan(recommended):
        console.print(f"Recommended command: lightweight squeeze build {model_id} --profile {recommended['mode']}")
    else:
        console.print("No recommended profile for this target. Use --run-anyway only if you accept slow/extreme behavior.")
    console.print("Core policy: exact model only; no silent replacement; SSD/NVMe is fallback, not the fast path.")
    if recommended.get("moe"):
        console.print("MoE policy: keep shared layers and hot experts in fast memory; use CPU/RAM for cold experts when needed.")
    else:
        console.print("Dense policy: quant + KV/cache/offload planning; dense weights are still needed every token.")

@squeeze_app.command(name="verify")
def squeeze_verify(
    model: str,
    thermal: str = typer.Option("balanced", "--thermal", help="Runtime profile: cool, balanced, or performance."),
    ctx: Optional[int] = typer.Option(None, "--ctx", help="Context size to verify."),
    prompt: str = typer.Option("Reply with one short sentence explaining what local AI is.", "--prompt", help="Small prompt used by --run verification."),
    tokens: int = typer.Option(64, "--tokens", help="Max tokens for --run verification."),
    run: bool = typer.Option(False, "--run", help="Run a small local load/generation check instead of printing the verification plan."),
):
    thermal = _normalize_thermal(thermal)
    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found locally. Pull it first, then run squeeze verify.")
        raise typer.Exit(1)
    report = Detector().get_report(force=True)
    model_size = os.path.getsize(path) // (1024 * 1024)
    metadata = read_model_metadata(path)
    strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model, thermal_mode=thermal)
    squeeze_profile = manager.get_squeeze_profile(model)
    strategy = _apply_squeeze_profile(strategy, squeeze_profile, user_ctx=ctx)
    strategy = apply_metadata(strategy, metadata, user_ctx=ctx)
    engine = InferenceEngine(path, strategy)

    table = Table(title=f"Squeeze verify: {model}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Path", path)
    table.add_row("Quant", str(metadata.quant or strategy.recommended_quant))
    table.add_row("Architecture", str(metadata.architecture or "unknown"))
    table.add_row("MoE", "yes" if metadata.is_moe else "no")
    if metadata.is_moe:
        table.add_row("Experts", str(metadata.expert_count or "unknown"))
        table.add_row("Active experts/token", str(metadata.expert_used_count or "unknown"))
    table.add_row("Context", str(strategy.n_ctx))
    table.add_row("GPU layers", str(strategy.n_gpu_layers))
    table.add_row("KV cache", strategy.kv_cache_type)
    table.add_row("Active-set policy", strategy.active_set_policy)
    table.add_row("MoE offload", f"{strategy.moe_offload} ({strategy.n_cpu_moe if strategy.n_cpu_moe is not None else 'auto'})")
    table.add_row("SSD policy", strategy.ssd_policy)
    console.print(table)

    if not run:
        console.print("Verification checklist:")
        console.print("  - load probe: lightweight probe " + model + f" --thermal {thermal}")
        console.print("  - speed check: lightweight bench " + model + f" --tokens 64 --thermal {thermal}")
        console.print("  - quality check: compare answers against the original or higher-quality quant on your task prompts")
        return

    try:
        process = psutil.Process(os.getpid())
        rss_before = process.memory_info().rss / (1024 * 1024)
        started = time.perf_counter()
        engine.load()
        load_elapsed = time.perf_counter() - started
        first_token_elapsed = None
        generated = ""
        token_count = 0
        gen_started = time.perf_counter()
        for chunk in engine.generate(prompt, max_tokens=max(1, tokens)):
            if first_token_elapsed is None:
                first_token_elapsed = time.perf_counter() - gen_started
            text = chunk.get("text", "")
            generated += text
            if text:
                token_count += 1
        gen_elapsed = max(time.perf_counter() - gen_started, 0.001)
        rss_after = process.memory_info().rss / (1024 * 1024)
        verification = {
            "ok": True,
            "thermal": thermal,
            "ctx": strategy.n_ctx,
            "load_seconds": round(load_elapsed, 3),
            "generation_seconds": round(gen_elapsed, 3),
            "first_token_seconds": round(first_token_elapsed or gen_elapsed, 3),
            "output_chunks": token_count,
            "chunks_per_second": round(token_count / gen_elapsed, 3),
            "rss_before_mb": round(rss_before, 1),
            "rss_after_mb": round(rss_after, 1),
            "rss_delta_mb": round(rss_after - rss_before, 1),
            "prompt": prompt,
            "sample": generated[:500],
            "created_at": int(time.time()),
        }
        saved = manager.save_squeeze_verification(model, verification)

        result = Table(title=f"Squeeze verification result: {model}", box=None)
        result.add_column("Metric", style="bold dim")
        result.add_column("Value")
        result.add_row("Load", f"{verification['load_seconds']}s")
        result.add_row("First token", f"{verification['first_token_seconds']}s")
        result.add_row("Generation", f"{verification['generation_seconds']}s")
        result.add_row("Output chunks/sec", str(verification["chunks_per_second"]))
        result.add_row("RSS delta", f"{verification['rss_delta_mb']} MB")
        result.add_row("Saved", "yes" if saved else "no (registry not writable)")
        console.print(result)
        if generated.strip():
            console.print(Panel(generated.strip(), title="Sample output", expand=False))
    except Exception as exc:
        console.print(f"✗ Load check failed: {exc}")
        manager.save_squeeze_verification(model, {
            "ok": False,
            "error": str(exc),
            "thermal": thermal,
            "ctx": strategy.n_ctx,
            "created_at": int(time.time()),
        })
        raise typer.Exit(1)

@squeeze_app.command(name="build")
def squeeze_build(
    model_id: str,
    profile: str = typer.Option("auto", "--profile", help="Squeeze profile: auto, quality, balanced, fit, or extreme."),
    target_ram: Optional[str] = typer.Option(None, "--target-ram", help="Plan as if this much RAM is available, for example 8gb or 16gb."),
    target_vram: Optional[str] = typer.Option(None, "--target-vram", help="Plan as if this much VRAM is available, for example 6gb."),
    quant: Optional[str] = typer.Option(None, "--quant", help="Force a GGUF quant name when pulling."),
    run_anyway: bool = typer.Option(False, "--run-anyway", help="Download even when the selected profile is not recommended."),
):
    manager = ModelManager()
    report = _report_with_targets(Detector().get_report(force=True), target_ram, target_vram)
    modes = ["quality", "balanced", "fit", "extreme"]
    plans = [manager.build_fit_plan(model_id, hardware_report=report, mode=mode) for mode in modes]
    selected = _recommend_squeeze_profile(plans) if profile == "auto" else next((p for p in plans if p["mode"] == profile), None)
    if not selected:
        console.print("✗ Unknown profile. Use: auto, quality, balanced, fit, or extreme.")
        raise typer.Exit(1)

    _print_plan(selected)
    if selected["verdict"] == "NOT_RECOMMENDED" and not run_anyway:
        console.print("[yellow]Selected profile is not recommended on this target. No model was downloaded.[/yellow]")
        console.print("Use --run-anyway if you want to keep this exact model despite speed/memory risk.")
        raise typer.Exit(2)

    try:
        path = _pull_with_progress(manager, model_id, hardware_report=report, manual_quant=quant, mode=selected["mode"], plan=selected)
    except Exception as exc:
        console.print(f"✗ Build failed: {exc}")
        raise typer.Exit(1)

    local_name = model_id.split("/")[-1]
    squeeze_profile = {
        "profile": selected["mode"],
        "model_id": model_id,
        "repo": selected["repo"],
        "quant": quant.upper() if quant else selected["quant"],
        "ctx": selected["ctx"],
        "verdict": selected["verdict"],
        "quality_risk": selected["quality_risk"],
        "active_set": selected.get("active_set", "kv-cache"),
        "memory_tier": selected.get("memory_tier", "VRAM/RAM"),
        "target_ram": target_ram,
        "target_vram": target_vram,
        "path": path,
        "created_at": int(time.time()),
    }
    manager.save_squeeze_profile(local_name, squeeze_profile)

    table = Table(title=f"Squeeze build ready: {local_name}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Path", path)
    table.add_row("Profile", squeeze_profile["profile"])
    table.add_row("Quant", squeeze_profile["quant"])
    table.add_row("Context", str(squeeze_profile["ctx"]))
    table.add_row("Active-set", squeeze_profile["active_set"])
    table.add_row("Next verify", f"lightweight squeeze verify {local_name}")
    table.add_row("Next serve", "lightweight serve --backend python --port 8000")
    console.print(table)

@squeeze_app.command(name="report")
def squeeze_report(
    model: str,
    profile: str = typer.Option("active", "--profile", help="Profile to report: active, quality, balanced, fit, or extreme."),
):
    manager = ModelManager()
    path, model, registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found locally.")
        raise typer.Exit(1)

    squeeze_profile = manager.get_squeeze_profile(model, profile=profile)
    runtime_profile = manager.get_runtime_profile(model)
    metadata = read_model_metadata(path)
    size_mb = os.path.getsize(path) // (1024 * 1024)

    table = Table(title=f"Squeeze report: {model}", box=None)
    table.add_column("Metric", style="bold dim")
    table.add_column("Value")
    table.add_row("Path", path)
    table.add_row("Repo", str((registry_model or {}).get("repo", "unknown")))
    table.add_row("File size", f"{size_mb} MB")
    table.add_row("Metadata quant", str(metadata.quant or (registry_model or {}).get("quant", "unknown")))
    table.add_row("Architecture", str(metadata.architecture or "unknown"))
    table.add_row("MoE", "yes" if metadata.is_moe else "no")
    if metadata.is_moe:
        table.add_row("Experts", str(metadata.expert_count or "unknown"))
        table.add_row("Active experts/token", str(metadata.expert_used_count or "unknown"))
    if squeeze_profile:
        table.add_row("Squeeze profile", str(squeeze_profile.get("profile", "unknown")))
        table.add_row("Squeeze verdict", str(squeeze_profile.get("verdict", "unknown")))
        table.add_row("Squeeze quant", str(squeeze_profile.get("quant", "unknown")))
        table.add_row("Squeeze ctx", str(squeeze_profile.get("ctx", "unknown")))
        table.add_row("Active-set", str(squeeze_profile.get("active_set", "unknown")))
        table.add_row("Memory tier", str(squeeze_profile.get("memory_tier", "unknown")))
    else:
        table.add_row("Squeeze profile", "not built")
    if runtime_profile:
        table.add_row("Runtime thermal", str(runtime_profile.get("thermal", "balanced")))
        table.add_row("Runtime GPU layers", str(runtime_profile.get("n_gpu_layers", "unknown")))
        table.add_row("Runtime KV", str(runtime_profile.get("kv_cache_type", "unknown")))
    else:
        table.add_row("Runtime profile", "not probed")

    verification = None
    if squeeze_profile:
        verification = squeeze_profile.get("verification")
    if not verification and registry_model:
        verification = registry_model.get("last_squeeze_verification")
    if verification:
        table.add_row("Verify status", "ok" if verification.get("ok") else "failed")
        if verification.get("ok"):
            if verification.get("load_seconds") is not None:
                table.add_row("Verify load", f"{verification.get('load_seconds')}s")
            if verification.get("first_token_seconds") is not None:
                table.add_row("Verify first token", f"{verification.get('first_token_seconds')}s")
            table.add_row("Verify chunks/sec", str(verification.get("chunks_per_second")))
            table.add_row("Verify RSS delta", f"{verification.get('rss_delta_mb')} MB")
        else:
            table.add_row("Verify error", str(verification.get("error", "unknown")))
    else:
        table.add_row("Verification", "not run")
    benchmark = None
    if squeeze_profile:
        benchmark = squeeze_profile.get("benchmark")
    if not benchmark and registry_model:
        benchmark = registry_model.get("last_squeeze_benchmark")
    if benchmark:
        table.add_row("Bench chunks/sec", str(benchmark.get("chunks_per_second")))
        table.add_row("Bench RSS delta", f"{benchmark.get('rss_delta_mb')} MB")
    console.print(table)

    if not squeeze_profile:
        console.print(f"Next: lightweight squeeze build {model} --profile auto")
    elif not verification:
        console.print(f"Next: lightweight squeeze verify {model} --run")
    elif verification.get("ok"):
        console.print("Next: lightweight serve --backend python --port 8000")
    else:
        console.print(f"Next: lightweight squeeze plan {model} --target-ram 16gb")

@squeeze_app.command(name="profiles")
def squeeze_profiles(model: str):
    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found locally.")
        raise typer.Exit(1)
    data = manager.list_squeeze_profiles(model)
    profiles = data.get("profiles", {})
    active = data.get("active")
    if not profiles:
        console.print(f"No squeeze profiles found for {model}.")
        console.print(f"Next: lightweight squeeze build {model} --profile auto")
        return

    table = Table(title=f"Squeeze profiles: {model}", box=None)
    table.add_column("Profile", style="bold")
    table.add_column("Active")
    table.add_column("Verdict")
    table.add_column("Quant")
    table.add_column("Ctx", justify="right")
    table.add_column("Verified")
    for name, item in profiles.items():
        verification = item.get("verification")
        if verification:
            verified = "ok" if verification.get("ok") else "failed"
        else:
            verified = "no"
        table.add_row(
            name,
            "yes" if name == active else "",
            str(item.get("verdict", "unknown")),
            str(item.get("quant", "unknown")),
            str(item.get("ctx", "unknown")),
            verified,
        )
    console.print(table)

@squeeze_app.command(name="use")
def squeeze_use(model: str, profile: str):
    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found locally.")
        raise typer.Exit(1)
    if not manager.set_active_squeeze_profile(model, profile):
        console.print(f"✗ Profile '{profile}' not found for {model}.")
        console.print(f"Run: lightweight squeeze profiles {model}")
        raise typer.Exit(1)
    console.print(f"✓ Active squeeze profile for {model}: {profile}")

@app.command()
def info(model_id: str, mode: str = "balanced"):
    manager = ModelManager(); detector = Detector()
    report = detector.get_report()
    plan = manager.build_fit_plan(model_id, hardware_report=report, mode=mode)
    console.print(Panel.fit(
        f"[bold]Model:[/bold] {model_id}\n"
        f"[bold]Repo:[/bold] {plan['repo']}\n"
        f"[bold]Estimated params:[/bold] {plan['params_b']}B\n"
        f"[bold]Replacement:[/bold] {plan['replacement']}\n"
        f"[bold]Recommended quant:[/bold] {plan['quant']}\n"
        f"[bold]Verdict:[/bold] {plan['verdict']}",
        title="LightWeight Model Info"
    ))

@app.command()
def inspect_model(model: str):
    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found.")
        raise typer.Exit(1)
    metadata = read_model_metadata(path)
    table = Table(title=f"Model metadata: {model}", box=None)
    table.add_column("Field", style="bold dim")
    table.add_column("Value")
    for key, value in metadata.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)

@app.command()
def storage():
    manager = ModelManager(); local = manager.list_local_models()
    total = sum(model.get("size", 0) for model in local)
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("MODEL"); table.add_column("SIZE", justify="right"); table.add_column("REPO")
    for model in local:
        table.add_row(model["name"], f"{model.get('size', 0)} MB", model.get("repo", ""))
    console.print(table)
    console.print(f"\nTotal: {total / 1024:.2f} GB")

@app.command(name="rm")
def remove(model: str, keep_files: bool = False):
    manager = ModelManager()
    if manager.remove_model(model, delete_files=not keep_files):
        console.print(f"✓ Removed: {model}")
    else:
        console.print(f"✗ Model not found: {model}")
        raise typer.Exit(1)

@app.command()
def config(edit: bool = False):
    config_path = Path.home() / ".config" / "lightweight" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text("{\n  \"model_dir\": null,\n  \"default_ctx\": 4096\n}\n", encoding="utf-8")
    if edit:
        editor = os.environ.get("EDITOR")
        if editor:
            try:
                subprocess.call([*shlex.split(editor), str(config_path)])
            except Exception as exc:
                console.print(f"Could not open editor: {exc}")
        else:
            console.print(f"Set EDITOR or edit manually: {config_path}")
    else:
        console.print(config_path.read_text(encoding="utf-8"))

def _run_llama_server(
    model: str,
    port: int,
    host: str,
    open_browser: bool,
    thermal: str,
    parallel: int,
    cache_reuse: int,
    spec: str,
    moe_offload: str,
    n_cpu_moe: Optional[int],
    override_tensor: Optional[List[str]],
):
    import threading

    binary = _find_llama_server()
    if not binary:
        console.print("✗ llama-server binary not found.")
        console.print("  Install llama.cpp server and set LIGHTWEIGHT_LLAMA_SERVER, or use:")
        console.print("  lightweight serve --backend python --model {model} --port {port}".format(model=model, port=port))
        raise typer.Exit(1)

    manager = ModelManager()
    path, model, _registry_model = _resolve_local_model(manager, model)
    if not path:
        console.print(f"Error: Model '{model}' not found.")
        raise typer.Exit(1)

    report = Detector().get_report(force=True)
    model_size = os.path.getsize(path) // (1024 * 1024)
    metadata = read_model_metadata(path)
    strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model, thermal_mode=thermal)
    squeeze_profile = manager.get_squeeze_profile(model)
    strategy = _apply_squeeze_profile(strategy, squeeze_profile)
    strategy = apply_metadata(strategy, metadata)
    requested_moe = _normalize_moe_offload(moe_offload)
    if requested_moe != "auto":
        strategy.moe_offload = requested_moe
    if n_cpu_moe is not None:
        strategy.n_cpu_moe = max(0, n_cpu_moe)
        if strategy.moe_offload in {"auto", "off"}:
            strategy.moe_offload = "first-n"
    if override_tensor:
        strategy.override_tensors = list(override_tensor)
    profile = _maybe_auto_profile(manager, model, path, strategy, thermal, metadata)
    strategy = _apply_runtime_profile(strategy, profile)
    spec = _normalize_spec(spec)
    browser_host = "localhost" if host in {"0.0.0.0", "::"} else host
    browser_url = f"http://{browser_host}:{port}"

    command = [
        binary,
        "-m",
        path,
        "--host",
        host,
        "--port",
        str(port),
        "--ctx-size",
        str(strategy.n_ctx),
        "--threads",
        str(strategy.n_threads),
        "--threads-batch",
        str(strategy.n_threads_batch or strategy.n_threads),
        "--batch-size",
        str(strategy.n_batch),
        "--ubatch-size",
        str(strategy.n_ubatch),
        "--n-gpu-layers",
        str(strategy.n_gpu_layers),
        "--parallel",
        str(max(1, parallel)),
        "--cache-type-k",
        strategy.kv_cache_type,
        "--cache-type-v",
        strategy.kv_cache_type,
    ]
    if cache_reuse > 0:
        command.extend(["--cache-reuse", str(cache_reuse)])
    if strategy.cache_prompt:
        command.append("--cache-prompt")
    if spec != "off":
        if _server_supports(binary, "--spec-type"):
            command.extend(["--spec-type", spec])
        else:
            console.print("[yellow]llama-server does not expose --spec-type; speculative decoding skipped.[/yellow]")
    if strategy.flash_attn and _server_supports(binary, "--flash-attn"):
        command.extend(["--flash-attn", "auto"])
    if strategy.native_fit and _server_supports(binary, "--fit"):
        command.extend(["--fit", "on", "--fit-ctx", str(strategy.n_ctx)])
        if _server_supports(binary, "--fit-target"):
            command.extend(["--fit-target", "768" if thermal != "cool" else "1024"])
    if metadata and metadata.is_moe and strategy.use_expert_offloading:
        if strategy.moe_offload == "all" and _server_supports(binary, "--cpu-moe"):
            command.append("--cpu-moe")
        elif strategy.moe_offload in {"auto", "first-n"} and strategy.n_cpu_moe:
            if _server_supports(binary, "--n-cpu-moe"):
                command.extend(["--n-cpu-moe", str(strategy.n_cpu_moe)])
            elif _server_supports(binary, "--cpu-moe"):
                command.append("--cpu-moe")
        for override in strategy.override_tensors or []:
            if _server_supports(binary, "--override-tensor"):
                command.extend(["--override-tensor", override])

    console.print(f"✦ LightWeight llama-server backend on {host}:{port}")
    console.print(f"  Model: {model}")
    console.print(f"  Chat/API: {browser_url}")
    console.print(f"  GPU layers: {strategy.n_gpu_layers}")
    console.print(f"  Parallel slots: {max(1, parallel)}")
    console.print(f"  Cache reuse: {cache_reuse}")
    console.print(f"  Speculative: {spec}")
    if squeeze_profile:
        console.print(f"  Squeeze profile: {squeeze_profile.get('profile')} ({squeeze_profile.get('verdict')})")
    console.print(f"  Active-set: {strategy.active_set_policy}")
    console.print(f"  SSD policy: {strategy.ssd_policy}")
    if metadata and metadata.is_moe:
        expert_text = f"{metadata.expert_count or '?'} experts"
        if metadata.expert_used_count:
            expert_text += f", {metadata.expert_used_count} active per token"
        console.print(f"  MoE: {expert_text}")
        console.print(f"  MoE offload: {strategy.moe_offload} ({strategy.n_cpu_moe if strategy.n_cpu_moe is not None else 'auto'})")
    if open_browser:
        threading.Timer(0.8, lambda: _safe_open_browser(browser_url)).start()
    env = os.environ.copy()
    server_lib_path = env.get("LIGHTWEIGHT_LLAMA_SERVER_LIB_PATH")
    if server_lib_path:
        if os.name == "nt":
            current = env.get("PATH")
            env["PATH"] = f"{server_lib_path};{current}" if current else server_lib_path
        else:
            current = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = f"{server_lib_path}:{current}" if current else server_lib_path
        env.setdefault("GGML_BACKEND_PATH", _resolve_ggml_backend_path(server_lib_path) or server_lib_path)
    raise typer.Exit(subprocess.call(command, env=env))

def _run_server(
    port: int,
    host: str,
    open_browser: bool,
    thermal: str,
    backend: str,
    model: Optional[str],
    parallel: int,
    cache_reuse: int,
    spec: str,
    moe_offload: str,
    n_cpu_moe: Optional[int],
    override_tensor: Optional[List[str]],
):
    import threading
    try:
        import uvicorn
    except ImportError:
        console.print("✗ uvicorn is not installed. Reinstall LightWeight with its Python dependencies.")
        raise typer.Exit(1)
    thermal = _normalize_thermal(thermal)
    if (backend or "").lower() == "auto" and not model:
        backend = "python"
    else:
        backend = choose_backend(
            backend,
            has_server=bool(_find_llama_server()),
            cache_reuse=cache_reuse,
            parallel=parallel,
        )
    if backend == "llama-server":
        if not model:
            console.print("✗ --model is required when using --backend llama-server.")
            raise typer.Exit(1)
        _run_llama_server(
            model=model,
            port=port,
            host=host,
            open_browser=open_browser,
            thermal=thermal,
            parallel=parallel,
            cache_reuse=cache_reuse,
            spec=spec,
            moe_offload=moe_offload,
            n_cpu_moe=n_cpu_moe,
            override_tensor=override_tensor,
        )
        return
    if backend != "python":
        console.print("✗ Unknown backend. Use: python or llama-server.")
        raise typer.Exit(1)

    # EXE Compatibility: Load app from direct instance
    try:
        from cli.api import app as fast_app
    except ImportError as first_error:
        try:
            from api import app as fast_app
        except ImportError as second_error:
            console.print(f"✗ API backend could not be imported: {second_error or first_error}")
            raise typer.Exit(1)
    browser_host = "localhost" if host in {"0.0.0.0", "::"} else host
    browser_url = f"http://{browser_host}:{port}"
    os.environ["LIGHTWEIGHT_THERMAL"] = thermal
    console.print(f"✦ LightWeight Server on {host}:{port}")
    console.print(f"  Chat UI: {browser_url}")
    console.print(f"  Thermal mode: {thermal}")
    console.print(f"  Backend: {backend}")
    if open_browser:
        threading.Timer(0.8, lambda: _safe_open_browser(browser_url)).start()
    try:
        uvicorn.run(fast_app, host=host, port=port)
    except OSError as exc:
        console.print(f"✗ Server could not start on {host}:{port}: {exc}")
        raise typer.Exit(1)

@app.command()
def serve(
    port: int = 8000,
    host: str = "0.0.0.0",
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the browser chat UI."),
    thermal: str = typer.Option("balanced", "--thermal", help="Runtime profile: cool, balanced, or performance."),
    backend: str = typer.Option("python", "--backend", help="Serving backend: auto, python, or llama-server."),
    model: Optional[str] = typer.Option(None, "--model", help="Local model name for llama-server backend."),
    parallel: int = typer.Option(1, "--parallel", help="llama-server parallel slots."),
    cache_reuse: int = typer.Option(256, "--cache-reuse", help="llama-server minimum cache reuse chunk size."),
    spec: str = typer.Option("off", "--spec", help="Speculative decoding for llama-server: off, ngram-cache, ngram-simple."),
    moe_offload: str = typer.Option("auto", "--moe-offload", help="MoE expert placement: auto, off, all, or first-n."),
    n_cpu_moe: Optional[int] = typer.Option(None, "--n-cpu-moe", help="Keep MoE expert weights for the first N layers on CPU."),
    override_tensor: Optional[List[str]] = typer.Option(None, "--override-tensor", help="Advanced llama-server tensor placement override PATTERN=BUFFER."),
):
    _run_server(
        port=port,
        host=host,
        open_browser=open_browser,
        thermal=thermal,
        backend=backend,
        model=model,
        parallel=parallel,
        cache_reuse=cache_reuse,
        spec=spec,
        moe_offload=moe_offload,
        n_cpu_moe=n_cpu_moe,
        override_tensor=override_tensor,
    )

@app.command(name="server")
def server_alias(
    port: int = 8000,
    host: str = "0.0.0.0",
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open the browser chat UI."),
    thermal: str = typer.Option("balanced", "--thermal", help="Runtime profile: cool, balanced, or performance."),
    backend: str = typer.Option("python", "--backend", help="Serving backend: auto, python, or llama-server."),
    model: Optional[str] = typer.Option(None, "--model", help="Local model name for llama-server backend."),
    parallel: int = typer.Option(1, "--parallel", help="llama-server parallel slots."),
    cache_reuse: int = typer.Option(256, "--cache-reuse", help="llama-server minimum cache reuse chunk size."),
    spec: str = typer.Option("off", "--spec", help="Speculative decoding for llama-server: off, ngram-cache, ngram-simple."),
    moe_offload: str = typer.Option("auto", "--moe-offload", help="MoE expert placement: auto, off, all, or first-n."),
    n_cpu_moe: Optional[int] = typer.Option(None, "--n-cpu-moe", help="Keep MoE expert weights for the first N layers on CPU."),
    override_tensor: Optional[List[str]] = typer.Option(None, "--override-tensor", help="Advanced llama-server tensor placement override PATTERN=BUFFER."),
):
    _run_server(
        port=port,
        host=host,
        open_browser=open_browser,
        thermal=thermal,
        backend=backend,
        model=model,
        parallel=parallel,
        cache_reuse=cache_reuse,
        spec=spec,
        moe_offload=moe_offload,
        n_cpu_moe=n_cpu_moe,
        override_tensor=override_tensor,
    )

@app.command(name="list")
def list_models():
    manager = ModelManager(); local = manager.list_local_models()
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("MODEL"); table.add_column("SIZE", justify="right")
    for m in local: table.add_row(m["name"], f"{m['size']} MB")
    console.print(); console.print(table); console.print()

if __name__ == "__main__": app()
