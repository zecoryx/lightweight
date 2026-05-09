import os
import sys
from pathlib import Path

# ─── BULLETPROOF PATH RESOLUTION ─────────────────────────────
# Bu qism dasturni EXE yoki paket sifatida har qanday noutbukda 
# va har qanday papkada ishlashini kafolatlaydi.

def setup_god_mode_paths():
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent

    potential_roots = [
        base_dir,
        base_dir / "cli",
        base_dir.parent,
    ]
    
    found_root = None
    for root in potential_roots:
        if (root / "hardware").exists() and (root / "models").exists():
            found_root = root
            break
    
    if found_root:
        root_str = str(found_root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        parent_str = str(found_root.parent)
        if parent_str not in sys.path:
            sys.path.insert(1, parent_str)
    else:
        sys.path.insert(0, str(base_dir))

setup_god_mode_paths()

# ─── SAFE IMPORTS ───────────────────────────────────────────
try:
    from hardware import Detector
    from models import ModelManager
    from strategy import StrategyEngine
    from inference import InferenceEngine
except ImportError:
    try:
        from cli.hardware import Detector
        from cli.models import ModelManager
        from cli.strategy import StrategyEngine
        from cli.inference import InferenceEngine
    except ImportError:
        try:
            from lightweight.hardware import Detector
            from lightweight.models import ModelManager
            from lightweight.strategy import StrategyEngine
            from lightweight.inference import InferenceEngine
        except ImportError as e:
            print(f"\n[Kritik Xato]: Modullarni topib bo'lmadi!")
            sys.exit(1)

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
app = typer.Typer(no_args_is_help=True, help="LightWeight — Total Private AI Engine.")
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
        welcome = f"[bold white]LightWeight v{__version__}[/bold white]\n[dim]Private AI Engine • Bulletproof Build[/dim]"
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
            console.print(f"\n  [bold]Diskdan foydalanish:[/bold]")
            console.print(f"  Papkada: {manager.base_path}")
            console.print(f"  Jami AI modellar: {total_size / 1024:.2f} GB")
            console.print(f"  Bo'sh joy (Disk): {self.detector.get_report().disk_free / 1024:.2f} GB\n")
        elif cmd == "/clear":
            console.clear()
            self._print_header()
        elif cmd == "/compact":
            self.engine.mem_manager.compact(self.engine.model)
            console.print("[dim]  Xotira tozalandi.[/dim]\n")
        elif cmd == "/help":
            console.print("\n  [bold]Mavjud buyruqlar:[/bold]")
            console.print("  [green]/exit[/green]    - Dasturdan chiqish")
            console.print("  [green]/info[/green]    - Tizim holatini ko'rish")
            console.print("  [green]/storage[/green] - Disk sarfini ko'rish")
            console.print("  [green]/clear[/green]   - Ekran tozash")
            console.print("  [green]/compact[/green] - Xotirani majburiy bo'shatish\n")
        else:
            console.print(f"[dim]  Noma'lum buyruq: {cmd}[/dim]\n")

    def run(self):
        self._print_header()
        commands = ['/exit', '/quit', '/info', '/clear', '/compact', '/help', '/storage']
        completer = WordCompleter(commands, ignore_case=True)
        kb = KeyBindings()
        @kb.add("enter")
        def _(event): event.current_buffer.validate_and_handle()
        @kb.add("escape", "enter")
        def _(event): event.current_buffer.insert_text("\n")

        session = PromptSession(
            completer=completer,
            bottom_toolbar=self._toolbar,
            multiline=True,
            key_bindings=kb,
            style=PTStyle.from_dict({
                "prompt": "bg:#333333 fg:#ffffff bold",
                "": "bg:#333333 fg:#ffffff",
                "bottom-toolbar": "bg:#222222 fg:#888888",
            })
        )

        while self.is_running:
            try:
                user_input = session.prompt(HTML("<style fg='#ffffff'> › </style>"))
                if not user_input.strip(): continue
                if user_input.startswith("/"): self._handle_slash(user_input)
                else:
                    console.print()
                    with Live(console=console) as live:
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
    if not path:
        console.print(f"Error: Model '{model}' not found."); raise typer.Exit(1)
    cli = AgenticCLI(model, path, n_ctx=ctx, n_threads=threads)
    cli.run()

@app.command()
def pull(model_id: str, quant: Optional[str] = None):
    manager = ModelManager(); detector = Detector()
    console.print(f"\n[dim]pulling {model_id}...[/dim]")
    try:
        path = manager.pull(model_id, hardware_report=detector.get_report(), manual_quant=quant)
        console.print(f"  [bold green]✓[/bold green] [dim]Ready: {path}[/dim]\n")
    except Exception as e:
        console.print(f"  [bold red]✗[/bold red] {e}\n"); raise typer.Exit(1)

@app.command()
def check(model_id: str):
    detector = Detector(); report = detector.get_report()
    est = StrategyEngine(report).estimate_performance(model_id)
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("Metric"); table.add_column("Standard", style="red"); table.add_column("LightWeight", style="green")
    table.add_row("Size", f"{est['original_gb']:.1f} GB", f"{est['compressed_gb']:.1f} GB")
    table.add_row("Speed", est['speed_before'], est['speed_after'])
    table.add_row("Logic", "100%", est['quality'])
    console.print(f"\n  [bold cyan]🔍 Hardware Analysis for: {model_id}[/bold cyan]")
    console.print(table); console.print()

@app.command()
def serve(port: int = 8000):
    import uvicorn
    console.print(f"\n  [bold green]✦ LightWeight Server[/bold green] on port {port}")
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")

@app.command(name="list")
def list_models():
    manager = ModelManager(); local = manager.list_local_models()
    if not local:
        console.print("\n[dim]No models found.[/dim]\n"); return
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("MODEL"); table.add_column("SIZE", justify="right")
    for m in local: table.add_row(m["name"], f"{m['size']} MB")
    console.print(); console.print(table); console.print()

if __name__ == "__main__": app()
