from __future__ import annotations

from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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


def format_labels(labels: list[str]) -> str:
    """Format a list of label strings as colored rich chips/badges."""
    if not labels:
        return "[dim]none[/dim]"

    chips = []
    for idx, label in enumerate(labels):
        color = LABEL_COLORS[idx % len(LABEL_COLORS)]
        chips.append(
            f"[bold black on {color}] {label} [/bold black on {color}]")

    return " ".join(chips)


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length with an ellipsis if exceeded."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def print_banner(repo: str, console: Console | None = None) -> Panel:
    """
    Print a styled rich Panel/banner displaying the repo name and timestamp.
    """
    if console is None:
        console = Console()

    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    banner_content = (
        f"[bold white]Repository:[/] [bold cyan]{repo}[/bold cyan]\n"
        f"[bold white]Analyze Time:[/] [dim]{timestamp_str}[/dim]\n"
        f"[dim]Note: kgiit analyze requires internet access. "
        f"Set GITHUB_TOKEN env var for higher rate limits (optional but recommended).[/dim]"
    )

    panel = Panel(
        banner_content,
        title="[bold magenta]kgiit — Analyze Control Center[/bold magenta]",
        subtitle="[dim]Agent Skill Layer Enabled[/dim]",
        border_style="bright_blue",
        padding=(1, 2),
    )

    console.print(panel)
    return panel


def print_issues_table(
        issues: list[dict[str, Any]], console: Console | None = None) -> Table:
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
    table.add_column(
        "Comments",
        style="bold magenta",
        justify="center",
        width=10)
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


def print_priority_table(ranked_issues: list[dict[str,
                                                  Any]],
                         classifications: dict[str,
                                               dict[str,
                                                    Any]],
                         console: Console | None = None) -> Table:
    """
    Render agent skill priority ranking & severity classification table.
    """
    if console is None:
        console = Console()

    table = Table(
        title="[bold yellow]Agent Skill Layer: Issue Priority & Severity Ranking[/bold yellow]",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
    )

    table.add_column("Rank", style="bold yellow", justify="center", width=6)
    table.add_column("Issue", style="bold cyan", justify="right", width=8)
    table.add_column("Severity", justify="center", width=10)
    table.add_column("Category", style="bold magenta", min_width=15)
    table.add_column("Assignee", style="bold white", width=12)
    table.add_column("Rationale", style="dim white")

    for item in ranked_issues:
        rank_str = f"#{item.get('rank')}"
        num_str = item.get("issue_number")

        info = classifications.get(num_str, {})
        sev = info.get("severity", "LOW")
        if sev == "HIGH":
            sev_styled = "[bold black on bright_red] HIGH [/bold black on bright_red]"
        elif sev == "MEDIUM":
            sev_styled = "[bold black on yellow] MEDIUM [/bold black on yellow]"
        else:
            sev_styled = "[bold black on green] LOW [/bold black on green]"

        label_str = info.get("label", "uncategorized")
        owner_str = info.get("owner", "unassigned")
        reason_str = item.get("reason", "")

        table.add_row(
            rank_str,
            num_str,
            sev_styled,
            label_str,
            owner_str,
            reason_str)

    console.print(table)
    return table


def print_summary_panel(
        summary_text: str,
        console: Console | None = None) -> Panel:
    """Print an agent skill summary panel."""
    if console is None:
        console = Console()

    panel = Panel(
        f"[bold white]{summary_text}[/bold white]",
        title="[bold green]Agent Analyze Summary[/bold green]",
        border_style="bold green",
        padding=(1, 2),
    )
    console.print(panel)
    return panel


def print_error(message: str, console: Console | None = None) -> None:
    """Print a styled error message using Rich."""
    if console is None:
        console = Console(stderr=True)

    console.print(f"[bold red]Error:[/] {message}")


def print_writeback_preview(
    issue_number: int,
    repo: str,
    classification: dict[str, Any],
    labels: list[str],
    confirmed_by: str,
    console: Console | None = None,
) -> None:
    """
    Print a clear preview of what will be written to GitHub before confirmation.

    Shows the human exactly:
    - Which repo and issue will be modified
    - What labels will be applied
    - Who will be credited as the confirmer
    - A warning that this is irreversible
    """
    if console is None:
        console = Console()

    sev = classification.get("severity", "?")
    lbl = classification.get("label", "?")
    owner_field = classification.get("owner", "unassigned")

    if sev == "HIGH":
        sev_styled = "[bold black on bright_red] HIGH [/bold black on bright_red]"
    elif sev == "MEDIUM":
        sev_styled = "[bold black on yellow] MEDIUM [/bold black on yellow]"
    else:
        sev_styled = "[bold black on green] LOW [/bold black on green]"

    labels_str = "  " + "\n  ".join(f"[bold magenta]{lb}[/bold magenta]" for lb in labels)

    panel_content = (
        f"[bold white]Repository:[/] [cyan]{repo}[/cyan]\n"
        f"[bold white]Issue:[/] [cyan]#{issue_number}[/cyan]\n\n"
        f"[bold white]AI Classification:[/]\n"
        f"  Severity: {sev_styled}\n"
        f"  Category: [bold magenta]{lbl}[/bold magenta]\n"
        f"  Assignee: [bold white]{owner_field}[/bold white]\n\n"
        f"[bold white]Labels to Apply:[/]\n"
        f"{labels_str}\n\n"
        f"[bold white]Confirming As:[/] [bold green]{confirmed_by}[/bold green]\n\n"
        "[dim]This will POST labels to the real GitHub issue.[/dim]\n"
        "[dim]Existing labels are preserved (additive only).[/dim]"
    )

    console.print(
        Panel(
            panel_content,
            title="[bold yellow]\u26a0 Write-Back Preview[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
    )


def print_writeback_result(
    status: str,
    labels: list[str],
    repo: str,
    issue_number: int,
    error: str | None = None,
    console: Console | None = None,
) -> None:
    """
    Print the result of a write-back attempt (applied, declined, or failed).
    """
    if console is None:
        console = Console()

    if status == "applied":
        labels_str = ", ".join(f"[bold magenta]{lb}[/bold magenta]" for lb in labels)
        console.print(
            f"\n[bold green]\u2705 Labels applied successfully![/bold green]\n"
            f"  Repo:   [cyan]{repo}[/cyan]\n"
            f"  Issue:  [cyan]#{issue_number}[/cyan]\n"
            f"  Labels: {labels_str}\n"
            f"\n[dim]Logged to kgiit-action-log.jsonl. View with: kgiit log[/dim]\n"
        )
    elif status == "declined":
        console.print(
            f"\n[bold yellow]\u23f9 Write-back declined.[/bold yellow] "
            "No changes made to GitHub. Outcome recorded in the audit log.\n"
        )
    elif status == "failed":
        console.print(
            f"\n[bold red]\u274c Write-back failed.[/bold red]\n"
            f"  Error: [red]{error}[/red]\n"
            "  No labels were applied. Failure recorded in the audit log.\n"
            "  Run [bold]kgiit log[/bold] to review.\n"
        )


def print_action_log_table(
    entries: list[dict[str, Any]],
    console: Console | None = None,
) -> Table:
    """
    Render a list of audit log entries as a Rich table.
    Reusable from both log_cli.py and tests.
    """
    if console is None:
        console = Console()

    from rich import box as _box
    table = Table(
        title="[bold yellow]kgiit — Write-Back Audit Log[/bold yellow]",
        show_header=True,
        header_style="bold cyan",
        border_style="bright_blue",
        box=_box.ROUNDED,
        expand=True,
    )
    table.add_column("Timestamp (UTC)", style="dim", min_width=19, no_wrap=True)
    table.add_column("Repo", style="bold white", min_width=12)
    table.add_column("Issue", style="bold cyan", justify="right", width=7)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Labels", style="bold magenta", min_width=16)
    table.add_column("By", style="bold green", min_width=14)

    status_styles = {
        "applied": "[bold green]applied[/bold green]",
        "declined": "[bold yellow]declined[/bold yellow]",
        "failed": "[bold red]failed[/bold red]",
        "skipped": "[dim]skipped[/dim]",
    }

    for entry in entries:
        ts = entry.get("timestamp", "")
        if "T" in ts:
            ts = ts[:19].replace("T", " ")

        status = entry.get("status", "unknown")
        labels = entry.get("suggestion", {}).get("labels", [])
        labels_str = ", ".join(labels) if labels else "-"
        if status == "failed":
            err = entry.get("error", "")[:35]
            labels_str = f"[red]ERR: {err}[/red]"

        table.add_row(
            ts,
            entry.get("repo", "-"),
            f"#{entry.get('issue_number', '?')}",
            status_styles.get(status, f"[dim]{status}[/dim]"),
            labels_str,
            entry.get("confirmed_by", "-"),
        )

    console.print(table)
    return table
