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

__version__ = "0.1.0"

app = typer.Typer(no_args_is_help=True, help="LightWeight — Run massive LLMs on consumer hardware.")
console = Console()


class AgenticCLI:
    """Terminal chat — header top, messages scroll, input+bar always at bottom."""

    def __init__(self, model_name: str, path: str, n_ctx: int = 4096, n_threads: Optional[int] = None):
        # Lazy imports for faster startup
        from lightweight.hardware import Detector
        from lightweight.models import ModelManager
        from lightweight.strategy import StrategyEngine
        from lightweight.inference import InferenceEngine

        self.model_name = model_name
        self.path = path
        self.n_ctx = n_ctx
        self.n_threads = n_threads or psutil.cpu_count(logical=False) or 4

        self.detector = Detector()
        self.manager = ModelManager()
        self.process = psutil.Process(os.getpid())

        report = self.detector.get_report()
        model_size = os.path.getsize(path) // (1024 * 1024)
        strategy = StrategyEngine(report).determine_strategy(model_size)

        self.engine = InferenceEngine(path, strategy)
        self.engine.n_threads = self.n_threads

        self.is_running = True
        self.last_latency = 0.0
        self.token_count = 0

    # ─── Header ──────────────────────────────────────────────

    def _print_header(self):
        console.print()
        
        logo = (
            "[bold white]╔════╗[/bold white]\n"
            "[bold white]║ 🪶 ║[/bold white]\n"
            "[bold white]╚════╝[/bold white]"
        )
        
        welcome_text = (
            f"[bold white]Welcome to LightWeight! v{__version__}[/bold white]\n"
            f"[dim]/help for commands, /info for hardware status[/dim]\n"
            f"[dim]cwd: {os.getcwd()}[/dim]"
        )
        
        from rich.table import Table
        grid = Table.grid(padding=(0, 2))
        grid.add_column()
        grid.add_column()
        grid.add_row(logo, welcome_text)
        
        from rich.panel import Panel
        panel = Panel(
            grid,
            border_style="dim",
            padding=(1, 2),
            expand=False
        )
        console.print(panel)
        console.print()
        
        tips = (
            "[dim]Tips for getting started:[/dim]\n"
            "[dim]1. Run [white]/info[/white] to see your hardware limits.[/dim]\n"
            "[dim]2. Use [white]@filename.txt[/white] to include files in your prompt.[/dim]\n"
            "[dim]3. Use [white]Alt+Enter[/white] for multi-line inputs.[/dim]"
        )
        console.print(tips)
        console.print()

    def _toolbar(self):
        try:
            ram = self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            ram = 0
            
        ctx_percent = min(100, int((self.token_count / self.n_ctx) * 100)) if self.n_ctx else 0
        bar_len = 10
        filled = int((ctx_percent / 100) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        return HTML(
            f'<style fg="#888888">'
            f'  ? [Shift+Enter] Newline │ Model: {self.model_name} │ Ram: {ram:.0f}mb │ ctx [{bar} {ctx_percent}%]'
            f'</style>'
        )

    # ─── Slash Commands ──────────────────────────────────────

    def _handle_slash(self, text: str):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()

        if cmd in ["/exit", "/quit", "/q"]:
            self.is_running = False

        elif cmd == "/clear":
            console.clear()
            self._print_header()

        elif cmd == "/compact":
            self.engine.mem_manager.compact()
            console.print("[dim]  context cleared, memory optimized.[/dim]\n")

        elif cmd == "/info":
            from lightweight.hardware import Detector
            detector = Detector()
            report = detector.get_report(force=True)
            try:
                ram = self.process.memory_info().rss / (1024 * 1024)
            except Exception:
                ram = 0
            console.print()
            for label, val in [
                ("ai memory", f"{ram:.0f}mb"),
                ("system ram", f"{report.available_ram}/{report.total_ram}mb"),
                ("context", f"{self.n_ctx} tokens"),
                ("threads", str(self.n_threads)),
            ]:
                console.print(f"  [bold]{label}[/bold]  [dim]{val}[/dim]")
            if report.gpus:
                for g in report.gpus:
                    console.print(f"  [bold]gpu {g.index}[/bold]  [dim]{g.name} ({g.free_vram}/{g.total_vram}mb)[/dim]")
            console.print()

        elif cmd == "/system":
            if len(parts) > 1:
                self.engine.system_instruction = parts[1]
                console.print("[dim]  system instruction updated.[/dim]\n")
            else:
                current = self.engine.system_instruction or "(default)"
                console.print(f"[dim]  {current}[/dim]\n")

        elif cmd == "/help":
            console.print()
            for name, desc in [
                ("/compact", "clear context and free memory"),
                ("/info", "show system and model status"),
                ("/system", "set or view system instruction"),
                ("/clear", "clear the screen"),
                ("/exit", "end the session"),
            ]:
                console.print(f"  [bold]{name}[/bold]  [dim]{desc}[/dim]")
            console.print("[dim]\n  tip: use @path/to/file to inject file context[/dim]")
            console.print()

        else:
            console.print(f"[dim]  unknown: {cmd}[/dim]\n")

    # ─── Process Input & Streaming ───────────────────────────

    def _process_input(self, text: str):
        image_path = None
        if "@" in text:
            words = text.split()
            for word in words:
                if word.startswith("@"):
                    fpath = word[1:]
                    if os.path.exists(fpath):
                        if fpath.lower().endswith((".png", ".jpg", ".jpeg")):
                            image_path = fpath
                            console.print(f"[dim]  🔧 Attached image: {fpath}[/dim]")
                            text = text.replace(word, f"[attached image: {fpath}]")
                        else:
                            try:
                                with open(fpath, "r", encoding="utf-8") as f:
                                    content = f.read(8000)
                                console.print(f"[dim]  🔧 Read file: {fpath} ({len(content)} bytes)[/dim]")
                                text = text.replace(word, f"\n```\n# {fpath}\n{content}\n```\n")
                            except Exception:
                                pass

        console.print()
        full_response = ""
        
        # Use a single Live display to avoid flickering between status and streaming
        with Live(console=console, refresh_per_second=8, auto_refresh=True) as live:
            live.update("[dim]  thinking...[/dim]")
            
            generator = self.engine.generate(text, image_path=image_path, max_tokens=2048)
            try:
                first_chunk = next(generator)
                full_response += first_chunk["text"]
                self.last_latency = first_chunk.get("latency", {}).get("ttft", 0)
            except StopIteration:
                live.update("[dim]  no response[/dim]\n")
                return

            start_time = time.time()
            tokens_in_response = 0

            live.update(Markdown(full_response, code_theme="one-dark"))
            for chunk in generator:
                full_response += chunk["text"]
                self.last_latency = chunk.get("latency", {}).get("itl", 0)
                self.token_count += 1
                tokens_in_response += 1
                live.update(Markdown(full_response, code_theme="one-dark"))

        elapsed = time.time() - start_time
        tps = tokens_in_response / elapsed if elapsed > 0 else 0
        console.print(f"[dim]  {tokens_in_response} tokens • {tps:.1f} tok/s[/dim]\n")

    # ─── Main Loop ───────────────────────────────────────────

    def run(self):
        self._print_header()

        # Slash command autocompletion
        completer = WordCompleter([
            '/exit', '/quit', '/clear', '/compact', 
            '/info', '/system', '/help'
        ], sentence=True)

        # Multi-line input bindings
        kb = KeyBindings()
        
        @kb.add("enter")
        def _(event):
            event.current_buffer.validate_and_handle()
            
        @kb.add("escape", "enter") # Esc+Enter / Alt+Enter for newline
        @kb.add("escape", "[", "1", "3", ";", "2", "u") # Shift+Enter in modern terminals
        def _(event):
            event.current_buffer.insert_text("\n")

        session = PromptSession(
            completer=completer,
            key_bindings=kb,
            multiline=True,
            bottom_toolbar=self._toolbar,
            style=PTStyle.from_dict({
                "bottom-toolbar": "fg:#888888",
            }),
        )

        while self.is_running:
            try:
                # Use a safer width margin to prevent clipping and wrapping
                # console.width might be slightly inaccurate in some terminals
                w = max(20, console.width - 8)
                
                # Print the top border before the prompt
                console.print(f"[dim]╭{'─' * w}╮[/dim]")
                
                # The prompt is just the left wall and the arrow
                prompt_msg = HTML(f"<style fg='#888888'>│</style> <style fg='#ffffff'>></style> ")
                
                # The right wall is added via rprompt
                r_prompt = HTML("<style fg='#888888'>│</style>")
                
                try:
                    user_input = session.prompt(prompt_msg, rprompt=r_prompt)
                except Exception:
                    import builtins
                    user_input = builtins.input("> ")
                    
                # Print the bottom border after the prompt
                console.print(f"[dim]╰{'─' * w}╯[/dim]")

                if not user_input.strip():
                    continue

                if user_input.startswith("/"):
                    self._handle_slash(user_input)
                else:
                    self._process_input(user_input)

            except KeyboardInterrupt:
                console.print()
                continue
            except EOFError:
                break

        console.print("[dim]session ended[/dim]\n")


# ═══════════════════════════════════════════════════════════════
# Typer Commands
# ═══════════════════════════════════════════════════════════════

@app.command()
def chat(
    model: str = typer.Argument(..., help="Model name"),
    ctx: int = typer.Option(4096, "--ctx", "-c", help="Context window size"),
    threads: Optional[int] = typer.Option(None, "--threads", "-t", help="CPU threads"),
):
    """Start an interactive AI chat session."""
    from lightweight.models import ModelManager
    manager = ModelManager()
    path = manager.get_model_path(model)

    if not path:
        local = manager.list_local_models()
        for m in local:
            if model.lower() in m["name"].lower():
                path = m["path"]
                model = m["name"]
                break

    if not path:
        console.print(f"[bold red]error:[/bold red] [dim]model '{model}' not found. use 'lightweight pull <id>' first.[/dim]")
        raise typer.Exit(1)

    cli = AgenticCLI(model, path, n_ctx=ctx, n_threads=threads)
    cli.run()


@app.command()
def pull(model_id: str = typer.Argument(..., help="HuggingFace model ID")):
    """Download a model from HuggingFace."""
    from lightweight.hardware import Detector
    from lightweight.models import ModelManager
    
    console.print(f"\n[dim]pulling {model_id}...[/dim]")

    manager = ModelManager()
    detector = Detector()
    report = detector.get_report()

    try:
        path = manager.pull(model_id, hardware_report=report)
        console.print(f"[bold green]✓[/bold green] [dim]{path}[/dim]\n")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] [dim]{e}[/dim]\n")
        raise typer.Exit(1)


@app.command(name="list")
def list_models():
    """Show locally available models."""
    from lightweight.models import ModelManager
    manager = ModelManager()
    local = manager.list_local_models()

    if not local:
        console.print("\n[dim]no models found. use 'lightweight pull <model_id>' to download.[/dim]\n")
        return

    table = Table(box=None, show_header=True, header_style="bold dim", padding=(0, 2))
    table.add_column("MODEL", style="bold")
    table.add_column("QUANT", justify="center", style="dim")
    table.add_column("SIZE", justify="right", style="dim")

    for m in local:
        table.add_row(m["name"], m.get("quant", "auto"), f"{m['size']} MB")

    console.print()
    console.print(table)
    console.print()


@app.command()
def info():
    """Show hardware status."""
    from lightweight.hardware import Detector
    detector = Detector()
    report = detector.get_report(force=True)

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Resource", style="bold")
    table.add_column("Status", style="dim")

    table.add_row("RAM", f"{report.total_ram}MB (Available: {report.available_ram}MB)")
    if report.gpus:
        for g in report.gpus:
            table.add_row(f"GPU {g.index}", f"{g.name} ({g.total_vram}MB VRAM)")
    table.add_row("DISK", f"{report.disk_free // 1024}GB Free")

    console.print()
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
