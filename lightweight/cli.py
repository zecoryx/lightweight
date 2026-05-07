import os
import sys
import psutil
import time
from typing import Optional
from pathlib import Path

# ─── ROBUST PATH RESOLUTION ──────────────────────────────────
# Har qanday papkadan va EXE ichidan modullarni topishni ta'minlaydi.
def setup_environment():
    bundle_dir = getattr(sys, '_MEIPASS', None)
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    
    # Qidirish uchun yo'llar ro'yxati
    paths = []
    if bundle_dir: paths.append(bundle_dir)
    
    # Agar biz paket ichida bo'lsak (lightweight/cli.py)
    if current_dir.name == "lightweight":
        paths.append(str(current_dir.parent)) # Loyiha root
        paths.append(str(current_dir))        # Paket ichi
    # Agar biz alohida cli papkasida bo'lsak (cli/cli.py)
    elif current_dir.name == "cli":
        paths.append(str(current_dir.parent)) # Loyiha root
        paths.append(str(current_dir.parent / "lightweight"))
    
    for p in paths:
        if p not in sys.path:
            sys.path.insert(0, p)

setup_environment()

# Importlarni har xil nomlar bilan sinab ko'rish
try:
    from lightweight.hardware import Detector
    from lightweight.models import ModelManager
    from lightweight.strategy import StrategyEngine
    from lightweight.inference import InferenceEngine
except ImportError:
    try:
        from hardware import Detector
        from models import ModelManager
        from strategy import StrategyEngine
        from inference import InferenceEngine
    except ImportError as e:
        print(f"Error: Could not load internal modules. Path: {sys.path}")
        print(f"Detail: {e}")
        sys.exit(1)

# ─── CLI LOGIC ───────────────────────────────────────────────
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.key_binding import KeyBindings

import typer

__version__ = "0.1.0"
app = typer.Typer(no_args_is_help=True, help="LightWeight — Local AI Engine.")
console = Console()

class AgenticCLI:
    def __init__(self, model_name: str, path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        self.model_name = model_name
        self.path = path
        self.n_ctx = n_ctx
        self.detector = Detector()
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
        welcome = f"[bold white]LightWeight v{__version__}[/bold white]\n[dim]Ready for private inference[/dim]"
        grid = Table.grid(padding=(0, 2))
        grid.add_column(); grid.add_column()
        grid.add_row(logo, welcome)
        console.print(Panel(grid, border_style="dim", padding=(1, 2), expand=False))
        console.print()

    def _toolbar(self):
        try: ram = self.process.memory_info().rss / (1024 * 1024)
        except Exception: ram = 0
        return HTML(f'<style fg="#888888"> Model: {self.model_name} │ Ram: {ram:.0f}mb │ Threads: {self.n_threads}</style>')

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
            style=PTStyle.from_dict({
                "prompt": "bg:#333333 fg:#ffffff bold",
                "": "bg:#333333 fg:#ffffff",
            })
        )

        while self.is_running:
            try:
                user_input = session.prompt(HTML("<style fg='#ffffff'> › </style>"))
                if not user_input.strip(): continue
                if user_input.startswith("/"):
                    cmd = user_input.split()[0].lower()
                    if cmd in ["/exit", "/quit", "/q"]: self.is_running = False
                    elif cmd == "/clear": console.clear(); self._print_header()
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
def list():
    manager = ModelManager(); local = manager.list_local_models()
    if not local:
        console.print("\n[dim]No models found.[/dim]\n"); return
    table = Table(box=None, show_header=True, header_style="bold dim")
    table.add_column("MODEL"); table.add_column("SIZE", justify="right")
    for m in local: table.add_row(m["name"], f"{m['size']} MB")
    console.print(); console.print(table); console.print()

@app.command()
def serve(port: int = 8000):
    import uvicorn
    console.print(f"\n  [bold green]✦ LightWeight Server[/bold green] on port {port}")
    uvicorn.run("lightweight.api:app", host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__": app()
