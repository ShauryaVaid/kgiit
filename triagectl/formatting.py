from datetime import datetime
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Pre-defined palette of colors for label chips
LABEL_COLORS = [
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "bright_red",
    "bright_magenta",
    "bright_cyan",
]


def format_labels(labels: List[str]) -> str:
    """Format a list of label strings as colored rich chips/badges."""
    if not labels:
        return "[dim]none[/dim]"

    chips = []
    for idx, label in enumerate(labels):
        color = LABEL_COLORS[idx % len(LABEL_COLORS)]
        chips.append(f"[bold black on {color}] {label} [/bold black on {color}]")
    
    return " ".join(chips)


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length with an ellipsis if exceeded."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def print_banner(repo: str, console: Optional[Console] = None) -> Panel:
    """
    Print a styled rich Panel/banner displaying the repo name and timestamp.
    """
    if console is None:
        console = Console()

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banner_content = (
        f"[bold white]Repository:[/] [bold cyan]{repo}[/bold cyan]\n"
        f"[bold white]Triage Time:[/] [dim]{timestamp_str}[/dim]"
    )

    panel = Panel(
        banner_content,
        title="[bold magenta]Triage Control Center[/bold magenta]",
        subtitle="[dim]GitHub Issue Overview[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    )

    console.print(panel)
    return panel


def print_issues_table(issues: List[Dict[str, Any]], console: Optional[Console] = None) -> Table:
    """
    Render and print a rich Table listing issues with columns:
    #, Title (truncated), Labels (as colored chips), Comments, URL.
    """
    if console is None:
        console = Console()

    table = Table(
        title="[bold green]GitHub Issues[/bold green]",
        show_header=True,
        header_style="bold yellow",
        border_style="dim",
    )

    table.add_column("#", style="bold cyan", justify="right", width=6)
    table.add_column("Title", style="bold white", min_width=25, max_width=45)
    table.add_column("Labels", style="none", min_width=15)
    table.add_column("Comments", style="bold magenta", justify="center", width=10)
    table.add_column("URL", style="underline blue", no_wrap=True)

    for issue in issues:
        num_str = f"#{issue.get('number', '')}"
        title = truncate_text(issue.get("title", ""), max_length=45)
        labels_chips = format_labels(issue.get("labels", []))
        comments_str = str(issue.get("comments", 0))
        url_str = issue.get("url", "")

        table.add_row(num_str, title, labels_chips, comments_str, url_str)

    console.print(table)
    return table


def print_error(message: str, console: Optional[Console] = None) -> None:
    """Print a styled error message using Rich."""
    if console is None:
        console = Console(stderr=True)

    console.print(f"[bold red]Error:[/] {message}")
