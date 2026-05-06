import os
import psutil
import time
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings

import typer

# Global imports
from lightweight.hardware import Detector
from lightweight.models import ModelManager
from lightweight.strategy import StrategyEngine
from lightweight.inference import InferenceEngine

__version__ = "0.1.0"
app = typer.Typer(no_args_is_help=True, help="LightWeight — Ideal Local LLM Engine.")
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
        self.token_count = 0

    def _toolbar(self):
        try: ram = self.process.memory_info().rss / (1024 * 1024)
        except Exception: ram = 0
        return HTML(f'<style fg="#888888"> │ Model: {self.model_name} │ Ram: {ram:.0f}mb │ Threads: {self.n_threads}</style>')

    def _handle_slash(self, text: str):
        cmd = text.split()[0].lower()
        if cmd in ["/exit", "/quit", "/q"]: self.is_running = False
        elif cmd == "/info":
            report = self.detector.get_report(force=True)
            console.print(f"\n  [bold]RAM:[/bold] {report.available_ram}/{report.total_ram}MB")
            console.print(f"  [bold]Threads:[/bold] {self.n_threads}\n")
        elif cmd == "/help":
            console.print("\n  /info, /compact, /exit\n")

    def run(self):
        session = PromptSession(bottom_toolbar=self._toolbar)
        console.print("[bold white]LightWeight Chat Initialized.[/bold white]")
        while self.is_running:
            try:
                user_input = session.prompt(HTML("<style fg='#ffffff'> › </style>"))
                if not user_input.strip(): continue
                if user_input.startswith("/"): self._handle_slash(user_input)
                else:
                    with Live(console=console) as live:
                        full = ""
                        for chunk in self.engine.generate(user_input):
                            full += chunk["text"]
                            live.update(Markdown(full))
            except (KeyboardInterrupt, EOFError): break

@app.command()
def chat(model: str, ctx: int = 4096, threads: Optional[int] = None):
    manager = ModelManager()
    path = manager.get_model_path(model)
    if not path:
        console.print(f"Error: Model '{model}' not found."); raise typer.Exit(1)
    cli = AgenticCLI(model, path, n_ctx=ctx, n_threads=threads)
    cli.run()

@app.command()
def pull(model_id: str, quant: Optional[str] = None):
    manager = ModelManager(); detector = Detector()
    report = detector.get_report()
    path = manager.pull(model_id, hardware_report=report, manual_quant=quant)
    console.print(f"✓ Downloaded: {path}")

@app.command()
def check(model_id: str):
    detector = Detector(); report = detector.get_report()
    est = StrategyEngine(report).estimate_performance(model_id)
    table = Table(title=f"Check: {model_id}")
    table.add_column("Metric"); table.add_column("Value")
    table.add_row("Compressed Size", f"{est['compressed_gb']:.1f} GB")
    table.add_row("Est. Speed", est['speed_after'])
    console.print(table)

@app.command()
def serve(port: int = 8000):
    import uvicorn
    console.print(f"Starting API Server on port {port}...")
    uvicorn.run("lightweight.api:app", host="0.0.0.0", port=port)

if __name__ == "__main__": app()
