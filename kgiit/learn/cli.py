"""
kgiit.learn.cli — Learn subcommand CLI and activation flow.

Handles:
  - Track selection menu
  - Terminal vs GUI mode choice
  - Headless mode for CI smoke-testing
  - Sandbox purge
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kgiit.learn.curriculum import ALL_TRACKS, Track, get_track
from kgiit.learn.sandbox import list_sessions, purge_all_sessions

console = Console()


def _detect_display() -> bool:
    """Check if a graphical display is available (for Electron GUI launch)."""
    if sys.platform == "win32":
        return True  # Windows always has display
    # Unix: check DISPLAY or WAYLAND_DISPLAY
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _print_track_menu() -> None:
    """Display the track selection table."""
    table = Table(
        title="[bold bright_cyan]Available Tracks[/bold bright_cyan]",
        show_header=True,
        header_style="bold yellow",
        border_style="bright_blue",
        box=box.ROUNDED,
    )
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Track", style="bold white", min_width=22)
    table.add_column("Description", style="dim white")
    table.add_column("Lessons", style="bold magenta", width=8, justify="center")

    for idx, track in enumerate(ALL_TRACKS, start=1):
        table.add_row(
            str(idx),
            track.title,
            track.description,
            str(len(track.lessons)),
        )

    console.print()
    console.print(table)
    console.print()


def _select_track() -> Track | None:
    """Interactively select a track."""
    _print_track_menu()
    console.print(f"[bold bright_white]Choose a track (1–{len(ALL_TRACKS)}) or [q]uit:[/bold bright_white] ", end="")

    try:
        choice = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice in ("q", "quit", "exit", ""):
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(ALL_TRACKS):
            return ALL_TRACKS[idx]
        else:
            console.print(f"[red]Invalid choice '{choice}'[/red]")
            return None
    except ValueError:
        # Try matching by ID or name
        for track in ALL_TRACKS:
            if choice in track.id or choice in track.title.lower():
                return track
        console.print(f"[red]Unknown track '{choice}'[/red]")
        return None


def _select_mode() -> str:
    """Ask: terminal TUI or GUI? Returns 'terminal' or 'gui'."""
    has_display = _detect_display()

    console.print(
        "\n[bold bright_white]How would you like to practice?[/bold bright_white]\n"
    )
    console.print("  [bold bright_green][1][/bold bright_green]  Terminal (Textual TUI) [bold]— recommended[/bold]")
    console.print("  [bold bright_blue][2][/bold bright_blue]  Graphical window (Electron app)")
    if not has_display:
        console.print(
            "\n  [dim]Note: No display detected (SSH/headless). "
            "Auto-selecting terminal mode.[/dim]"
        )

    if not has_display:
        return "terminal"

    console.print()
    try:
        choice = console.input("[bold bright_cyan]Enter choice (1/2, default=1): [/bold bright_cyan]").strip()
    except (EOFError, KeyboardInterrupt):
        return "terminal"

    if choice == "2":
        return "gui"
    return "terminal"


def _launch_tui(track: Track, headless: bool = False) -> None:
    """Launch the Textual TUI for a given track."""
    from kgiit.learn.tui import LearnApp
    app = LearnApp(track=track, headless=headless)
    if headless:
        # In headless mode, run auto-pilot through the first lesson
        console.print(f"[dim]Headless mode: running track '{track.title}'...[/dim]")
        # Textual's headless mode via run(headless=True)
        app.run(headless=True)
    else:
        app.run()


def _launch_gui(track: Track) -> None:
    """Launch the FastAPI bridge and Electron GUI."""
    console.print("[dim]Starting local backend for GUI...[/dim]")
    
    # Set track ID in env for the renderer process
    env = os.environ.copy()
    env["TRACK_ID"] = track.id

    import urllib.request
    import urllib.error

    # Start FastAPI server
    uvicorn_cmd = [sys.executable, "-m", "uvicorn", "kgiit.learn.server:app", "--port", "8000", "--host", "127.0.0.1"]
    server_proc = subprocess.Popen(uvicorn_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Fast polling loop instead of sleeping for 1.5s
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=0.05)
            break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.05)
    
    gui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "gui")
    console.print("[dim]Launching Electron GUI...[/dim]")
    # Use npx electron directly to skip npm parsing overhead
    npm_cmd = ["npx", "electron", "."] if sys.platform != "win32" else ["npx.cmd", "electron", "."]
    
    electron_proc = subprocess.Popen(npm_cmd, cwd=gui_dir, env=env)
    
    try:
        electron_proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        console.print("[dim]Shutting down GUI backend...[/dim]")
        server_proc.terminate()
        server_proc.wait()


def launch_learn_interactive() -> None:
    """
    Full interactive learn activation flow:
    1. Track selection
    2. Mode selection (terminal / GUI)
    3. Launch TUI or GUI
    """
    console.print(
        Panel(
            "[bold bright_cyan]kgiit learn[/bold bright_cyan]\n\n"
            "[white]Practice real git commands in a safe offline sandbox.\n"
            "No LLM. No external API. Fully offline.[/white]\n\n"
            "[dim]Each session runs in an isolated directory with its own\n"
            "git config — never touches your real ~/.gitconfig[/dim]",
            border_style="bright_cyan",
            box=box.ROUNDED,
        )
    )

    track = _select_track()
    if track is None:
        console.print("[dim]No track selected. Exiting.[/dim]")
        return

    console.print(
        f"\n[bold bright_green]Selected:[/bold bright_green] [bold]{track.title}[/bold] "
        f"([dim]{len(track.lessons)} lessons[/dim])"
    )

    mode = _select_mode()

    console.print(f"\n[dim]Launching {mode} mode...[/dim]")
    if mode == "gui":
        _launch_gui(track)
    else:
        _launch_tui(track, headless=False)


@click.group(
    name="learn",
    invoke_without_command=True,
    help="Practice git commands in a safe offline sandbox (fully offline, no LLM).",
)
@click.option(
    "--track",
    "track_id",
    default=None,
    help="Track ID to start directly (e.g. git-basics, branching).",
)
@click.option(
    "--headless",
    is_flag=True,
    default=False,
    help="Run in headless mode (for CI smoke-testing, no interactive terminal needed).",
)
@click.option(
    "--list-tracks",
    is_flag=True,
    default=False,
    help="List available learning tracks and exit.",
)
@click.pass_context
def learn_cmd(ctx: click.Context, track_id: str | None, headless: bool, list_tracks: bool) -> None:
    """
    kgiit learn — Interactive git practice in an isolated offline sandbox.

    \b
    Safety guarantee: commands run ONLY inside ~/.kgiit/sandboxes/<session-id>/.
    Your real ~/.gitconfig and repositories are never touched.

    \b
    Examples:
      kgiit learn                          Interactive track selection
      kgiit learn --track git-basics       Start a specific track directly
      kgiit learn --headless               CI smoke-test mode
      kgiit learn reset --purge            Remove all sandbox sessions
    """
    if ctx.invoked_subcommand is not None:
        return

    if list_tracks:
        _print_track_menu()
        return

    if headless:
        # Headless: auto-run first track, first lesson
        track = get_track(track_id) if track_id else ALL_TRACKS[0]
        if track is None:
            console.print(f"[red]Unknown track: {track_id}[/red]")
            sys.exit(1)
        console.print(f"[dim]Headless: running '{track.title}'...[/dim]")
        _launch_tui(track, headless=True)
        return

    if track_id:
        track = get_track(track_id)
        if track is None:
            console.print(f"[red]Unknown track '{track_id}'. Use --list-tracks to see options.[/red]")
            sys.exit(1)
        mode = _select_mode()
        if mode == "gui":
            _launch_gui(track)
        else:
            _launch_tui(track, headless=False)
    else:
        launch_learn_interactive()


@learn_cmd.command(name="demo", help="Automated walkthrough of a lesson (hackathon demo mode).")
def demo_cmd() -> None:
    """Run a hands-free deterministic walkthrough of git basics."""
    import time

    from rich.panel import Panel

    from kgiit.learn.curriculum import ALL_TRACKS
    from kgiit.learn.ml.classifier import classify_mistake
    from kgiit.learn.sandbox import SandboxSession

    track = ALL_TRACKS[0]  # git-basics
    lesson = track.lessons[1]  # 'git status' lesson

    console.print(Panel(f"[bold bright_cyan]kgiit demo[/bold bright_cyan]\nAutomated Walkthrough: {track.title} - {lesson.title}", box=box.ROUNDED, border_style="cyan"))
    
    session = SandboxSession(lesson.fixture)
    console.print(f"[dim]Started sandbox session: {session.session_id}[/dim]\n")
    
    console.print(f"[bold yellow]Prompt:[/bold yellow] {lesson.instructions}\n")
    time.sleep(1.5)
    
    # 1. Deliberate Mistake
    mistake = "git statu"
    console.print(f"[bold bright_green]~/sandbox $[/bold bright_green] [white]{mistake}[/white]")
    time.sleep(1)
    
    proc = session.run(mistake)
    if proc.stdout: console.print(proc.stdout, end="")
    if proc.stderr: console.print(f"[red]{proc.stderr}[/red]", end="")
    
    # Get ML Hint
    label, conf, hint = classify_mistake(mistake, lesson.target_command, context=session.get_state())
    time.sleep(1)
    console.print(f"[bold magenta]Hint ({label} - {conf*100:.0f}% confidence):[/bold magenta] [italic]{hint}[/italic]\n")
    time.sleep(2)
    
    # 2. Correct command
    correct = "git status"
    console.print(f"[bold bright_green]~/sandbox $[/bold bright_green] [white]{correct}[/white]")
    time.sleep(1)
    
    proc = session.run(correct)
    if proc.stdout: console.print(proc.stdout, end="")
    
    # Verify
    result = lesson.verify(session, proc)
    time.sleep(0.5)
    if result.passed:
        console.print(f"\n[bold bright_green][SUCCESS][/bold bright_green] {result.message}")
    
    time.sleep(1)
    session.purge()
    console.print("\n[dim]Sandbox cleaned up. Demo complete.[/dim]")


@learn_cmd.command(name="reset", help="Clean up sandbox sessions.")
@click.option(
    "--purge",
    is_flag=True,
    default=False,
    help="Remove ALL sandbox sessions (cannot be undone).",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    default=False,
    help="List existing sandbox sessions without deleting.",
)
def reset_cmd(purge: bool, list_only: bool) -> None:
    """Manage sandbox session cleanup."""
    sessions = list_sessions()

    if list_only or (not purge):
        if not sessions:
            console.print("[dim]No sandbox sessions found.[/dim]")
        else:
            console.print(f"[bold]Sandbox sessions ({len(sessions)}):[/bold]")
            from kgiit.learn.sandbox import SANDBOX_ROOT
            for sid in sessions:
                path = SANDBOX_ROOT / sid
                size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                console.print(f"  [cyan]{sid}[/cyan]  [dim]{size // 1024} KB — {path}[/dim]")
        return

    if purge:
        if not sessions:
            console.print("[dim]No sessions to remove.[/dim]")
            return
        n = purge_all_sessions()
        console.print(f"[bold green]Removed {n} sandbox session(s).[/bold green]")
