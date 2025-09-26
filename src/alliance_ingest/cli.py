"""
Generic CLI for alliance-ingest project.
Discovers and runs all ingests, downloads, and tests dynamically.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    name="ingest",
    help="Generic ingest CLI - discovers and runs all downloads, transforms, and tests"
)
console = Console()


def discover_transform_configs(base_path: Path = Path(".")) -> List[Path]:
    """Discover all transform YAML files in src/ directory."""
    transform_configs = []
    
    # Look for .yaml files in src/ subdirectories (excluding download.yaml)
    for yaml_file in base_path.glob("src/**/*.yaml"):
        if yaml_file.name != "download.yaml" and "transform" in yaml_file.name:
            transform_configs.append(yaml_file)
    
    return sorted(transform_configs)


def discover_download_configs(base_path: Path = Path(".")) -> List[Path]:
    """Discover download.yaml files."""
    download_configs = []
    
    # Look for download.yaml files
    for yaml_file in base_path.glob("src/**/download.yaml"):
        download_configs.append(yaml_file)
    
    return sorted(download_configs)


def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status."""
    console.print(f"[bold blue]Running:[/bold blue] {description}")
    console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        console.print(f"[green]✓ {description} completed successfully[/green]\n")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ {description} failed with exit code {e.returncode}[/red]\n")
        return False
    except FileNotFoundError:
        console.print(f"[red]✗ Command not found: {cmd[0]}[/red]\n")
        return False


def run_downloads(
    output_dir: str = ".",
    ignore_cache: bool = False,
    verbose: bool = False
) -> int:
    """Download all data sources. Returns number of successful downloads."""
    download_configs = discover_download_configs()
    
    if not download_configs:
        console.print("[yellow]No download.yaml files found[/yellow]")
        return 0
    
    console.print(Panel(f"[bold]Downloading data from {len(download_configs)} sources[/bold]"))
    
    success_count = 0
    for config in download_configs:
        cmd = ["uv", "run", "downloader", str(config)]
        if output_dir != ".":
            cmd.extend(["--output-dir", output_dir])
        if ignore_cache:
            cmd.append("--ignore-cache")
        if verbose:
            cmd.append("--verbose")
            
        if run_command(cmd, f"Download from {config.parent.name}"):
            success_count += 1
    
    console.print(f"[bold]Downloads completed: {success_count}/{len(download_configs)} successful[/bold]")
    return success_count


@app.command()
def download(
    output_dir: str = typer.Option(".", help="Output directory for downloaded data"),
    ignore_cache: bool = typer.Option(False, help="Force download of data, even if it exists"),
    verbose: bool = typer.Option(False, help="Verbose output")
):
    """Download all data sources."""
    run_downloads(output_dir, ignore_cache, verbose)


def run_transforms(
    output_dir: str = "output",
    output_format: str = "tsv", 
    limit: Optional[int] = None,
    progress: bool = False,
) -> int:
    """Run all discovered transforms. Returns number of successful transforms."""
    transform_configs = discover_transform_configs()
    
    if not transform_configs:
        console.print("[yellow]No transform configs found[/yellow]")
        return 0
    
    console.print(Panel(f"[bold]Running {len(transform_configs)} transforms[/bold]"))
    
    success_count = 0
    for config in transform_configs:
        cmd = ["uv", "run", "koza", "transform", str(config)]
        cmd.extend(["--output-dir", output_dir])
        cmd.extend(["--output-format", output_format])
        if limit:
            cmd.extend(["--limit", str(limit)])
        if progress:
            cmd.append("--progress")
            
        transform_name = config.parent.name
        if run_command(cmd, f"Transform {transform_name}"):
            success_count += 1
    
    console.print(f"[bold]Transforms completed: {success_count}/{len(transform_configs)} successful[/bold]")
    return success_count


@app.command()
def transform(
    output_dir: str = typer.Option("output", help="Output directory for transformed data"),
    output_format: str = typer.Option("tsv", help="Output format (tsv, jsonl, kgx)"),
    limit: Optional[int] = typer.Option(None, help="Number of rows to process per transform"),
    progress: bool = typer.Option(False, help="Show progress bars"),
):
    """Run all discovered transforms."""
    run_transforms(output_dir, output_format, limit, progress)


@app.command()
def test(
    verbose: bool = typer.Option(False, help="Verbose test output"),
    pattern: str = typer.Option("test_", help="Test file pattern"),
):
    """Run all tests."""
    cmd = ["uv", "run", "pytest", "tests/"]
    if verbose:
        cmd.append("-v")
    
    console.print(Panel("[bold]Running all tests[/bold]"))
    
    if run_command(cmd, "Test suite"):
        console.print("[green]All tests completed[/green]")
    else:
        console.print("[red]Some tests failed[/red]")
        sys.exit(1)


@app.command() 
def run(
    output_dir: str = typer.Option("output", help="Output directory"),
    download_first: bool = typer.Option(True, help="Download data before transforming"),
    run_tests: bool = typer.Option(False, help="Run tests after transforms"),
):
    """Run the complete ingest pipeline: download → transform → (optionally test)."""
    console.print(Panel("[bold green]Starting complete ingest pipeline[/bold green]"))
    
    success = True
    
    # Download phase
    if download_first:
        try:
            success_count = run_downloads(output_dir=output_dir)
            if success_count == 0:
                success = False
        except Exception as e:
            console.print(f"[red]Download phase failed: {e}[/red]")
            success = False
    
    # Transform phase
    if success:
        try:
            success_count = run_transforms(output_dir=output_dir)
            if success_count == 0:
                success = False
        except Exception as e:
            console.print(f"[red]Transform phase failed: {e}[/red]")
            success = False
    
    # Test phase (optional)
    if success and run_tests:
        try:
            test()
        except Exception as e:
            console.print(f"[red]Test phase failed: {e}[/red]")
            success = False
    
    if success:
        console.print(Panel("[bold green]Pipeline completed successfully![/bold green]"))
    else:
        console.print(Panel("[bold red]Pipeline failed - see errors above[/bold red]"))
        sys.exit(1)


@app.command()
def discover(
):
    """Show what configs and files would be discovered and run."""
    console.print(Panel("[bold]Discovery Report[/bold]"))
    
    download_configs = discover_download_configs()
    transform_configs = discover_transform_configs()
    
    console.print(f"[bold]Download configs found:[/bold] {len(download_configs)}")
    for config in download_configs:
        console.print(f"  • {config}")
    
    console.print(f"\n[bold]Transform configs found:[/bold] {len(transform_configs)}")  
    for config in transform_configs:
        console.print(f"  • {config}")
    
    test_dir = Path("tests")
    if test_dir.exists():
        test_files = list(test_dir.glob("**/test_*.py"))
        console.print(f"\n[bold]Test files found:[/bold] {len(test_files)}")
        for test_file in test_files[:5]:  # Show first 5
            console.print(f"  • {test_file}")
        if len(test_files) > 5:
            console.print(f"  ... and {len(test_files) - 5} more")
    else:
        console.print("\n[yellow]No tests directory found[/yellow]")


if __name__ == "__main__":
    app()