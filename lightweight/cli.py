import typer
import sys
import os
import logging
from rich.console import Console
from rich.table import Table
from typing import Optional

# Core imports
from lightweight.hardware import Detector
from lightweight.models import ModelManager
from lightweight.strategy import StrategyEngine
from lightweight.inference import InferenceEngine

app = typer.Typer(
    help="LightWeight — High-performance inference for massive LLMs.",
    no_args_is_help=True
)
console = Console()

@app.command()
def check():
    """Hardware resurslarini tekshirish"""
    try:
        detector = Detector()
        report = detector.get_report(force=True)
        
        console.print("\n[bold blue]LightWeight Hardware Status[/bold blue]\n")
        
        t = Table(show_header=True, header_style="bold magenta")
        t.add_column("Komponent")
        t.add_column("Holat / Hajm", justify="right")
        
        t.add_row("System RAM", f"{report.total_ram} MB (Free: {report.available_ram} MB)")
        for g in report.gpus:
            t.add_row(f"GPU {g.index}: {g.name}", f"{g.total_vram} MB (Free: {g.free_vram} MB)")
        t.add_row("Disk Space", f"{report.disk_free // 1024} GB Free")
        t.add_row("CUDA Support", "[green]Yes[/green]" if report.has_cuda else "[red]No[/red]")
        
        console.print(t)
    except Exception as e:
        console.print(f"[red]Xato:[/red] {str(e)}")

@app.command()
def pull(
    model_id: str = typer.Argument(..., help="HuggingFace Repo ID"),
    quant: Optional[str] = typer.Option(None, "--quant", "-q")
):
    """Modelni yuklab olish (Hardware-ga moslangan holda)"""
    try:
        detector = Detector()
        report = detector.get_report()
        manager = ModelManager()
        
        console.print(f"[bold blue]Analiz qilinmoqda:[/bold blue] {model_id}")
        path = manager.pull(model_id, hardware_report=report)
        console.print(f"[bold green]Muvaffaqiyatli yuklandi:[/bold green] {path}")
    except Exception as e:
        console.print(f"[bold red]Xato:[/bold red] {str(e)}")

@app.command()
def models():
    """Yuklangan modellar ro'yxati"""
    manager = ModelManager()
    local = manager.list_local_models()
    
    if not local:
        console.print("[yellow]Modellar topilmadi. 'pull' buyrug'ini ishlating.[/yellow]")
        return

    t = Table(title="Mahalliy Modellar")
    t.add_column("Nom", style="cyan")
    t.add_column("Format/Quant", style="green")
    t.add_column("Hajm (MB)", justify="right")
    
    for m in local:
        t.add_row(m['name'], m.get('quant', 'GGUF'), str(m['size']))
    console.print(t)

@app.command()
def chat(model: str):
    """Interaktiv suhbat rejimi"""
    manager = ModelManager()
    path = manager.get_model_path(model)
    
    if not path:
        console.print(f"[red]Xato:[/red] '{model}' topilmadi. Avval 'pull' qiling.")
        return

    detector = Detector()
    report = detector.get_report()
    model_info = manager.registry.get(model, {})
    is_moe = model_info.get("is_moe", False)
    model_size = os.path.getsize(path) // (1024 * 1024)
    
    strategy = StrategyEngine(report).determine_strategy(
        model_size, 
        model_name=model, 
        is_moe=is_moe
    )
    
    engine = InferenceEngine(path, strategy)
    
    console.print(f"\n[bold blue]Chat boshlandi: {model}[/bold blue]")
    console.print("[dim]Chiqish uchun 'exit' deb yozing.[/dim]\n")
    
    while True:
        prompt = console.input("[bold green]Siz:[/bold green] ")
        if prompt.lower() in ["exit", "quit", "q"]: break
        
        console.print("[bold blue]LightWeight Assistant:[/bold blue] ", end="")
        for chunk in engine.generate(prompt):
            console.print(chunk, end="")
        console.print("\n")

@app.command()
def serve(port: int = 8000, workers: int = 1):
    """Production darajasidagi API serverni ishga tushirish"""
    try:
        import uvicorn
        console.print(f"[bold green]API Server port {port} da ishga tushmoqda...[/bold green]")
        uvicorn.run("lightweight.api:app", port=port, host="0.0.0.0", workers=workers)
    except Exception as e:
        console.print(f"[red]Xato:[/red] {str(e)}")

if __name__ == "__main__":
    app()
