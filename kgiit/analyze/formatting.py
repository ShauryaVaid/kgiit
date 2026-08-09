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
    repo: str,
    issue_number: int,
    current_labels: list[str],
    proposed_labels: list[str],
    confirmed_by: str,
    console: Console | None = None,
) -> Panel:
    """
    Show exactly what a write-back would change, and who is about to
    confirm it, BEFORE the confirmation prompt is shown. This is the
    "human explicitly approves a specific suggestion" moment made visible.

    HowToAlgo ADLC: human in the loop is always visible, never implicit.
    """
    if console is None:
        console = Console()

    current_str = ", ".join(f"`{lbl}`" for lbl in current_labels) or "*none*"
    proposed_str = ", ".join(f"`{lbl}`" for lbl in proposed_labels) or "*none*"

    body = (
        f"[bold white]Target:[/] {repo}#{issue_number}\n"
        f"[bold white]Current labels:[/] {current_str}\n"
        f"[bold white]Will add:[/] [bold green]{proposed_str}[/bold green]\n"
        f"[bold white]Confirming as:[/] [bold cyan]{confirmed_by}[/bold cyan]\n\n"
        f"[dim]This writes to the real GitHub issue via the API. "
        f"Nothing is sent until you explicitly confirm below.[/dim]\n"
        f"[dim]Powered by HowToAlgo ADLC — AI suggests, human decides.[/dim]"
    )

    panel = Panel(
        body,
        title="[bold yellow]Write-Back Preview — Human Approval Required[/bold yellow]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)
    return panel


def print_writeback_result(
        result: dict[str, Any], console: Console | None = None) -> Panel:
    """Print the outcome of an apply_suggestion()/decline_suggestion() call."""
    if console is None:
        console = Console()

    entry = result.get("entry", {})
    status = entry.get("status", "unknown")

    if status == "applied":
        labels = ", ".join(
            f"`{lbl}`" for lbl in result.get(
                "labels_now_on_issue", [])) or "*none*"
        body = (
            f"[bold green]Applied.[/bold green] Issue now has: {labels}\n"
            f"[dim]Confirmed by {entry.get('confirmed_by')} at {entry.get('timestamp')}. "
            f"See the local action log for the full audit entry.[/dim]"
        )
        style = "green"
        title = "[bold green]Write-Back Applied[/bold green]"
    elif status == "declined":
        body = (
            "[bold yellow]Declined.[/bold yellow] No changes were sent to GitHub.\n"
            f"[dim]Decline recorded for {entry.get('confirmed_by')} at {entry.get('timestamp')}.[/dim]"
        )
        style = "yellow"
        title = "[bold yellow]Write-Back Declined[/bold yellow]"
    else:
        body = (
            f"[bold red]Failed.[/bold red] {entry.get('error') or result.get('error') or 'Unknown error.'}\n"
            f"[dim]Failure recorded for {entry.get('confirmed_by')} at {entry.get('timestamp')}. "
            f"No partial changes were made to the issue.[/dim]"
        )
        style = "red"
        title = "[bold red]Write-Back Failed[/bold red]"

    panel = Panel(body, title=title, border_style=style, padding=(1, 2))
    console.print(panel)
    return panel


def print_action_log_table(
        entries: list[dict[str, Any]], console: Console | None = None) -> Table:
    """Render the local write-back audit log as a Rich table, newest first."""
    if console is None:
        console = Console()

    table = Table(
        title="[bold magenta]kgiit Write-Back Audit Log[/bold magenta]",
        show_header=True,
        header_style="bold yellow",
        border_style="dim",
    )
    table.add_column("Time (UTC)", style="dim", no_wrap=True)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Repo#Issue", style="bold cyan", no_wrap=True)
    table.add_column("Confirmed By", style="bold white")
    table.add_column("Suggestion", style="none")

    status_styles = {
        "applied": "[bold black on green] APPLIED [/bold black on green]",
        "declined": "[bold black on yellow] DECLINED [/bold black on yellow]",
        "failed": "[bold white on red] FAILED [/bold white on red]",
        "skipped": "[bold black on grey70] SKIPPED [/bold black on grey70]",
    }

    for entry in reversed(entries):
        status = entry.get("status", "unknown")
        status_chip = status_styles.get(status, status)
        target = f"{entry.get('repo', '?')}#{entry.get('issue_number', '?')}"
        suggestion = entry.get("suggestion", {}) or {}
        labels = (
            suggestion.get("labels_applied")
            or suggestion.get("labels_attempted")
            or suggestion.get("labels_proposed")
            or []
        )
        suggestion_str = ", ".join(labels) if labels else (
            entry.get("error") or "-")

        table.add_row(
            entry.get("timestamp", "?"),
            status_chip,
            target,
            entry.get("confirmed_by", "?"),
            suggestion_str,
        )

    console.print(table)
    return table
