"""
kgiit — Two doors, one CLI.

Usage:
    kgiit                   Interactive mode (Rich menu)
    kgiit analyze [OPTIONS]  Analyze real GitHub issues (needs internet + optional GITHUB_TOKEN)
                             Add --apply to confirm and write a suggestion back to a real issue.
    kgiit learn  [OPTIONS]  Practice git commands in a safe offline sandbox
    kgiit log    [OPTIONS]  View the local write-back audit log (who confirmed what, when)
"""
from rich.table import Table
import os
import subprocess
import sys

# Force UTF-8 output on Windows so Rich box/unicode characters
# never crash the cp1252 codec (happens on older Windows terminals)
if sys.platform == "win32" and sys.stdout.encoding.lower() != "utf-8":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from kgiit import __version__
from kgiit.analyze.cli import analyze_cmd
from kgiit.analyze.log_cli import log_cmd
from kgiit.learn.cli import learn_cmd

console = Console()


def _print_kgiit_banner() -> None:
    """Print the main kgiit welcome banner matching the premium aesthetic."""
    # UTF-8 reconfigure is handled at module import level (top of this file)

    # The exact block chunks for KGiit to allow vertical column coloring
    chunks = [
        (" ██╗  ██╗ ", " ██████╗ ", " ██╗", "██╗", "████████╗"),
        (" ██║ ██╔╝ ", "██╔════╝ ", " ██║", "██║", "╚══██╔══╝"),
        (" █████╔╝  ", "██║  ███╗", " ██║", "██║", "   ██║   "),
        (" ██╔═██╗  ", "██║   ██║", " ██║", "██║", "   ██║   "),
        (" ██║  ██╗ ", "╚██████╔╝", " ██║", "██║", "   ██║   "),
        (" ╚═╝  ╚═╝ ", " ╚═════╝ ", " ╚═╝", "╚═╝", "   ╚═╝   ")
    ]
    colors = ["#00f2fe", "#4facfe", "#b15eff", "#ff007f", "#ff4b91"]

    banner = Text(justify="center")

    # 1) Colorful Gradient ASCII Art
    for row in chunks:
        for i, chunk in enumerate(row):
            banner.append(chunk, style=f"bold {colors[i]}")
        banner.append("\n")

    # 2) Subtitles
    banner.append("\nTwo doors. One CLI.\n", style="bold #fdfbfb")
    banner.append("github.com/ShauryaVaid/kgiit", style="dim #a0a5b5")

    # 3) Enclose in a massive full-width double-lined purple box
    logo_panel = Panel(
        banner,
        border_style="#00f2fe",
        box=box.DOUBLE,
        padding=(2, 2),
        expand=True
    )
    console.print(logo_panel)
    console.print()

    # 4) Modes / Doors (Cleanly listed under the banner)
    console.print(
        "[bold #ff007f]Door 1 →[/bold #ff007f] [bold white]KGiit analyze[/bold white]"
        " — Apply git/GitHub skills on real repos",
        justify="center"
    )
    console.print(
        "[dim #a0a5b5]Needs internet + optional GITHUB_TOKEN[/dim #a0a5b5]",
        justify="center"
    )
    console.print()
    console.print(
        "[bold #00f2fe]Door 2 →[/bold #00f2fe] [bold white]KGiit learn[/bold white]"
        "   — Practice git commands in a safe sandbox",
        justify="center"
    )
    console.print(
        "[dim #a0a5b5]Fully offline. No LLM. No external API.[/dim #a0a5b5]",
        justify="center"
    )
    console.print()


def _interactive_menu() -> None:
    """Show an interactive Rich menu when kgiit is run with no subcommand."""
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        _print_kgiit_banner()

        console.print("  [bold white]Choose a mode:[/bold white]\n")

        # Menu Options Table (No Box)
        menu_table = Table.grid(padding=(0, 2))
        menu_table.add_column(justify="right")
        menu_table.add_column(justify="left", style="white")
        menu_table.add_row(
            "  [bold #ff007f][1][/bold #ff007f]",
            "Apply git/GitHub skills — analyze real issues in a repository")
        menu_table.add_row(
            "", "[dim #a0a5b5](needs internet, optional GITHUB_TOKEN)[/dim #a0a5b5]\n")
        menu_table.add_row(
            "  [bold #00f2fe][2][/bold #00f2fe]",
            "Learn git — practice commands in a safe offline sandbox")
        menu_table.add_row(
            "", "[dim #a0a5b5](fully offline, no LLM, no external API)[/dim #a0a5b5]\n")
        menu_table.add_row(
            "  [bold #b15eff][3][/bold #b15eff]",
            "Write-back — approve & apply an AI suggestion to a real GitHub issue\n")
        menu_table.add_row(
            "", "[dim #a0a5b5](requires GITHUB_TOKEN with write scope)[/dim #a0a5b5]\n")
        menu_table.add_row(
            "  [bold #ffa500][4][/bold #ffa500]",
            "View audit log — see who confirmed what, and when\n")
        menu_table.add_row(
            "  [bold #6c757d]\\[/bye, q][/bold #6c757d]",
            "[dim]Quit[/dim]\n")

        console.print(menu_table)

        try:
            choice = console.input(
                "[bold #ff69b4]Enter choice (1/2/3/4/q): [/bold #ff69b4]").strip().lower()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting.[/dim]")
            sys.exit(0)

        if choice == "1":
            console.print()
            repo = console.input(
                "[bold #ff69b4]Enter GitHub repo (e.g. octocat/Hello-World): [/bold #ff69b4]").strip()
            if repo:
                console.print(f"\n[dim]Running analyze for {repo}...[/dim]\n")
                cmd = ["kgiit"] if sys.platform != "win32" else ["kgiit.exe"]
                subprocess.run(
                    cmd + ["analyze", "--repo", repo, "--all-open"], check=False)
            else:
                console.print("[red]No repository entered.[/red]")
                import time
                time.sleep(1)
        elif choice == "2":
            console.print()
            # Import here to avoid circular startup cost
            from kgiit.learn.cli import launch_learn_interactive
            launch_learn_interactive()
        elif choice == "3":
            # Write-back flow: ask for repo + issue then --apply
            console.print()
            repo = console.input(
                "[bold #ff69b4]Enter GitHub repo (e.g. octocat/Hello-World): [/bold #ff69b4]").strip()
            issue_str = console.input(
                "[bold #ff69b4]Enter issue number to analyze and approve: [/bold #ff69b4]").strip()
            if repo and issue_str.isdigit():
                console.print(
                    f"\n[dim]Running write-back flow for {repo}#{issue_str}...[/dim]\n"
                    f"[dim]You will be shown the AI suggestion and asked to approve or decline.[/dim]\n"
                )
                cmd = ["kgiit"] if sys.platform != "win32" else ["kgiit.exe"]
                subprocess.run(
                    cmd + ["analyze", "--repo", repo, "--issue", issue_str, "--apply"],
                    check=False
                )
            else:
                console.print("[red]Invalid repo or issue number.[/red]")
                import time
                time.sleep(1)
        elif choice == "4":
            console.print()
            cmd = ["kgiit"] if sys.platform != "win32" else ["kgiit.exe"]
            subprocess.run(cmd + ["log"], check=False)
        elif choice in ("q", "quit", "exit", "/bye", ""):
            console.print(
                "\n[bold bright_magenta]Goodbye![/bold bright_magenta]")
            sys.exit(0)
        else:
            console.print(
                f"\n[bold red]Invalid choice:[/] '{choice}'. Please enter 1, 2, 3, 4, or /bye.")
            import time
            time.sleep(1)

        # After command runs, pause to let user see output if they want, then
        # loop
        console.print("\n[dim]Press Enter to return to the main menu...[/dim]")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting.[/dim]")
            sys.exit(0)


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version=__version__, prog_name="kgiit")
@click.pass_context
def main(ctx: click.Context) -> None:
    """
    kgiit — Two doors, one CLI.

    \b
    Door 1: kgiit analyze — Apply git/GitHub skills on real repositories
            (needs internet, optional GITHUB_TOKEN)
            Add --apply to confirm and write AI suggestions to real issues.

    \b
    Door 2: kgiit learn  — Practice git commands in a safe offline sandbox
            (fully offline, no LLM, no external API)

    \b
    kgiit log — View the local write-back audit log
            (who confirmed which suggestion, what was applied, and when)

    Run with no subcommand for an interactive menu.
    """
    if ctx.invoked_subcommand is None:
        _interactive_menu()


# Register subcommands
main.add_command(analyze_cmd, name="analyze")
main.add_command(learn_cmd, name="learn")
main.add_command(log_cmd, name="log")


if __name__ == "__main__":
    main()
