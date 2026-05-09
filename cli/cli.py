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
    from hardware import Detector
    from models import ModelManager
    from strategy import StrategyEngine
    from inference import InferenceEngine
except ImportError:
    from cli.hardware import Detector
    from cli.models import ModelManager
    from cli.strategy import StrategyEngine
    from cli.inference import InferenceEngine

# ─── CLI LOGIC ───────────────────────────────────────────────
import psutil
import time
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

import typer

__version__ = "0.1.0"
app = typer.Typer(no_args_is_help=True, help="LightWeight — 100% Reliable Local AI.")
console = Console()

class AgenticCLI:
    def __init__(self, model_name: str, path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        self.model_name = model_name
        self.path = path
        self.n_ctx = n_ctx
        self.detector = Detector()
        self.manager = ModelManager()
        self.process = psutil.Process(os.getpid())
        report = self.detector.get_report()
        model_size = os.path.getsize(path) // (1024 * 1024)
        strategy = StrategyEngine(report).determine_strategy(model_size, model_name=model_name)
        self.engine = InferenceEngine(path, strategy)
        self.n_threads = strategy.n_threads
        self.is_running = True

    def _print_header(self):
        console.print()
        logo = "[bold white]╔════╗\n║ 🪶 ║\n╚════╝[/bold white]"
        welcome = f"[bold white]LightWeight v{__version__}[/bold white]\n[dim]The Ultimate Bulletproof Build[/dim]"
        grid = Table.grid(padding=(0, 2))
        grid.add_column(); grid.add_column()
        grid.add_row(logo, welcome)
        console.print(Panel(grid, border_style="dim", padding=(1, 2), expand=False))
        console.print()

    def _toolbar(self):
        try: ram = self.process.memory_info().rss / (1024 * 1024)
        except Exception: ram = 0
        return HTML(f'<style fg="#888888"> Model: {self.model_name} │ Ram: {ram:.0f}mb │ Threads: {self.n_threads} │ /help</style>')

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

    def run(self):
        self._print_header()
        kb = KeyBindings()
        @kb.add("enter")
        def _(event): event.current_buffer.validate_and_handle()
        @kb.add("escape", "enter")
        def _(event): event.current_buffer.insert_text("\n")

        session = PromptSession(
            bottom_toolbar=self._toolbar,
            multiline=True,
            key_bindings=kb,
            style=PTStyle.from_dict({"prompt": "bg:#333333 fg:#ffffff bold", "": "bg:#333333 fg:#ffffff"})
        )

        while self.is_running:
            try:
                user_input = session.prompt(HTML("<style fg='#ffffff'> › </style>"))
                if not user_input.strip(): continue
                if user_input.startswith("/"): self._handle_slash(user_input)
                else:
                    console.print()
                    with Live(console=console, refresh_per_second=10) as live:
                        full = ""
                        for chunk in self.engine.generate(user_input):
                            full += chunk["text"]
                            live.update(Markdown(full, code_theme="one-dark"))
                    console.print()
            except (KeyboardInterrupt, EOFError): break

@app.command()
def chat(model: str, ctx: int = 4096, threads: Optional[int] = None):
    manager = ModelManager(); path = manager.get_model_path(model)
    if not path:
        for m in manager.list_local_models():
            if model.lower() in m["name"].lower():
                path, model = m["path"], m["name"]; break
    if not path: console.print(f"Error: Model '{model}' not found."); raise typer.Exit(1)
    cli = AgenticCLI(model, path, n_ctx=ctx, n_threads=threads); cli.run()

@app.command()
def pull(model_id: str, quant: Optional[str] = None):
    manager = ModelManager(); detector = Detector()
    try:
        path = manager.pull(model_id, hardware_report=detector.get_report(), manual_quant=quant)
        console.print(f"✓ Ready: {path}")
    except Exception as e: console.print(f"✗ Error: {e}"); raise typer.Exit(1)

@app.command()
def serve(port: int = 8000):
    import uvicorn
    # EXE Compatibility: Load app from direct instance
    try:
        from cli.api import app as fast_app
    except ImportError:
        from api import app as fast_app
    console.print(f"✦ LightWeight Server on port {port}")
    uvicorn.run(fast_app, host="0.0.0.0", port=port)

@app.command(name="list")
def list_models():
    manager = ModelManager(); local = manager.list_local_models()
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("MODEL"); table.add_column("SIZE", justify="right")
    for m in local: table.add_row(m["name"], f"{m['size']} MB")
    console.print(); console.print(table); console.print()

if __name__ == "__main__": app()
