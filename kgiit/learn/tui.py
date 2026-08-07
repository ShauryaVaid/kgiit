"""
kgiit.learn.tui — Textual TUI for interactive git practice.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  Header: lesson title + track                       │
  ├────────────────────────┬────────────────────────────┤
  │  Scrollback Pane       │  Status Pane               │
  │  (lesson + history)    │  (branch, staged, last     │
  │                        │   commit — live refresh)   │
  ├────────────────────────┴────────────────────────────┤
  │  Input line (bottom)                                │
  └─────────────────────────────────────────────────────┘

Meta-commands (always available):
  next        — skip to the next lesson
  hint        — show the ML-selected hint
  reset step  — reset sandbox to fixture state
  quit        — exit the practice session
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, Static

from kgiit.learn.curriculum import Track
from kgiit.learn.ml.classifier import classify_mistake
from kgiit.learn.sandbox import SandboxEscapeError, SandboxSession

# ---------------------------------------------------------------------------
# Status Pane
# ---------------------------------------------------------------------------


class StatusPane(Static):
    """Live git status display, refreshed after every command."""

    DEFAULT_CSS = """
    StatusPane {
        width: 32;
        min-width: 28;
        background: $panel;
        border: solid $primary;
        padding: 1 2;
        color: $text;
    }
    """

    sandbox: SandboxSession | None = None

    def refresh_state(self, sandbox: SandboxSession) -> None:
        """Refresh displayed state from current sandbox."""
        self.sandbox = sandbox
        state = sandbox.get_state()

        if not state.get("is_repo"):
            self.update(
                "[bold yellow]Sandbox State[/bold yellow]\n\n"
                "[dim]No git repository yet.[/dim]\n"
                f"[dim]Path: {sandbox.repo_dir.name}[/dim]"
            )
            return

        branch = state.get("branch") or "(unknown)"
        staged = state.get("staged", [])
        unstaged = state.get("unstaged", [])
        untracked = state.get("untracked", [])
        last = state.get("last_commit")

        lines = [
            "[bold yellow]Sandbox State[/bold yellow]\n",
            f"[bold cyan]Branch:[/bold cyan] [green]{branch}[/green]",
            "",
        ]

        if staged:
            lines.append("[bold green]Staged:[/bold green]")
            for f in staged[:4]:
                lines.append(f"  [green]+ {f}[/green]")
            if len(staged) > 4:
                lines.append(f"  [dim]... +{len(staged) - 4} more[/dim]")
        else:
            lines.append("[dim]Staged: (none)[/dim]")

        lines.append("")
        if unstaged:
            lines.append("[bold yellow]Modified:[/bold yellow]")
            for f in unstaged[:3]:
                lines.append(f"  [yellow]~ {f}[/yellow]")
        elif untracked:
            lines.append("[bold red]Untracked:[/bold red]")
            for f in untracked[:3]:
                lines.append(f"  [red]? {f}[/red]")
        else:
            lines.append("[dim]Working tree clean[/dim]")

        lines.append("")
        if last:
            lines.append("[bold magenta]Last commit:[/bold magenta]")
            # Truncate long messages
            short = last if len(last) <= 28 else last[:25] + "..."
            lines.append(f"  [magenta]{short}[/magenta]")
        else:
            lines.append("[dim]No commits yet[/dim]")

        lines.append(f"\n[dim]Sandbox: {sandbox.repo_dir.name}[/dim]")

        self.update("\n".join(lines))


# ---------------------------------------------------------------------------
# Main TUI App
# ---------------------------------------------------------------------------

class LearnApp(App):
    """
    Interactive git practice TUI.

    Handles a single track's worth of lessons sequentially.
    """

    CSS = """
    Screen {
        background: #0d1117;
    }

    Header {
        background: #161b22;
        color: #58a6ff;
    }

    Footer {
        background: #161b22;
    }

    #scrollback {
        background: #0d1117;
        border: solid #30363d;
        padding: 0 1;
        height: 1fr;
        scrollbar-color: #30363d #0d1117;
    }

    #main-layout {
        height: 1fr;
    }

    #left-panel {
        width: 1fr;
        height: 1fr;
    }

    #status-pane {
        width: 34;
        height: 1fr;
        background: #161b22;
        border: solid #21262d;
        padding: 1 2;
        color: #c9d1d9;
    }

    #input-bar {
        dock: bottom;
        background: #161b22;
        border-top: solid #30363d;
        padding: 0 1;
        height: 3;
    }

    Input {
        background: #0d1117;
        color: #c9d1d9;
        border: none;
    }

    Input:focus {
        border: none;
        background: #161b22;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+r", "reset_step", "Reset Step"),
        Binding("ctrl+n", "next_lesson", "Next Lesson"),
        Binding("ctrl+h", "show_hint", "Hint"),
    ]

    TITLE = "kgiit learn — git practice sandbox"

    current_lesson_idx: reactive[int] = reactive(0)

    def __init__(self, track: Track, headless: bool = False):
        super().__init__()
        self.track = track
        self.lessons = track.lessons
        self._headless = headless
        self.sandbox: SandboxSession | None = None
        self._lesson_passed = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-layout"):
            with Vertical(id="left-panel"):
                yield RichLog(
                    id="scrollback",
                    highlight=True,
                    markup=True,
                    wrap=True,
                )
            yield StatusPane(id="status-pane")
        yield Input(
            placeholder="Type a git command and press Enter... (hint: type 'skip', 'tracks', 'hint', 'reset', or 'quit')",
            id="input-bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Start the first lesson on mount."""
        self._start_lesson(0)
        self.query_one("#input-bar", Input).focus()

    # ------------------------------------------------------------------
    # Lesson management
    # ------------------------------------------------------------------

    def _start_lesson(self, idx: int) -> None:
        """Initialize and display a lesson."""
        if idx >= len(self.lessons):
            self._show_completion()
            return

        self.current_lesson_idx = idx
        lesson = self.lessons[idx]
        self._lesson_passed = False

        log = self.query_one("#scrollback", RichLog)
        log.clear()

        # Create sandbox for this lesson
        self.sandbox = SandboxSession(fixture=lesson.fixture)

        # Run setup steps (e.g. create files before staging lesson)
        for step_fn in lesson.setup_steps:
            try:
                step_fn(self.sandbox)
            except Exception as e:
                log.write(f"[red]Setup error: {e}[/red]")

        # Update status pane
        self._refresh_status()

        # Display lesson info
        lesson_num = idx + 1
        total = len(self.lessons)
        log.write(
            f"[bold bright_magenta]━━━ Lesson {lesson_num}/{total}: {lesson.title} ━━━[/bold bright_magenta]\n")
        log.write(
            f"[bold bright_yellow]Concept:[/bold bright_yellow] "
            f"[white]{lesson.concept}[/white]\n"
        )
        log.write(f"[dim]{'─' * 60}[/dim]\n")

        # Split instructions into lines and display
        for line in lesson.instructions.strip().split("\n"):
            if line.startswith("  git ") or line.strip().startswith("git "):
                log.write(f"[bold #a371f7]{line}[/bold #a371f7]")
            else:
                log.write(f"[white]{line}[/white]")

        log.write(f"\n[dim]{'─' * 60}[/dim]")
        log.write(
            "[dim]Meta-commands: [bold]hint[/bold] | [bold]skip[/bold] | "
            "[bold]tracks[/bold] | [bold]reset[/bold] | [bold]quit[/bold][/dim]\n")

    def _show_completion(self) -> None:
        """Show track completion message."""
        log = self.query_one("#scrollback", RichLog)
        log.clear()
        log.write(
            "\n[bold #a371f7]=========================================[/bold #a371f7]\n"
            "[bold #a371f7]   TRACK COMPLETION CERTIFICATE   [/bold #a371f7]\n"
            "[bold #a371f7]=========================================[/bold #a371f7]\n\n"
            f"[white]Track:    [bold]{self.track.title}[/bold][/white]\n"
            f"[white]Lessons:  {len(self.lessons)} / {len(self.lessons)}[/white]\n"
            f"[white]Status:   [bold #a371f7]PASSED[/bold #a371f7][/white]\n\n"
            "[bold bright_magenta]Ready to try this on a real repository?[/bold bright_magenta]\n"
            "[white]Run: [bold yellow]kgiit analyze --repo <owner/name>[/bold yellow][/white]\n\n"
            "[dim]Press Ctrl+Q to exit, or type 'quit'.[/dim]"
        )
        status = self.query_one("#status-pane", StatusPane)
        status.update(
            "[bold #a371f7]Track Complete![/bold #a371f7]\n\n"
            "[white]All lessons done.[/white]"
        )

    def _refresh_status(self) -> None:
        """Refresh the status pane from current sandbox state."""
        if self.sandbox is None:
            return
        status = self.query_one("#status-pane", StatusPane)
        status.refresh_state(self.sandbox)

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the user pressing Enter in the input bar."""
        command = event.value.strip()
        if not command:
            return

        # Clear input
        event.input.value = ""

        log = self.query_one("#scrollback", RichLog)
        log.write(
            f"\n[bold bright_magenta]$[/bold bright_magenta] [bold white]{command}[/bold white]")

        # Handle meta-commands
        cmd_lower = command.lower()
        if cmd_lower == "quit" or cmd_lower == "exit":
            self.action_quit()
            return
        elif cmd_lower == "hint":
            self.action_show_hint()
            return
        elif cmd_lower in ("next", "skip"):
            self.action_next_lesson()
            return
        elif cmd_lower in ("reset step", "reset"):
            self.action_reset_step()
            return
        elif cmd_lower in ("tracks", "list", "courses"):
            from kgiit.learn.curriculum import ALL_TRACKS
            log.write("\n[bold cyan]Available Tracks:[/bold cyan]")
            for t in ALL_TRACKS:
                log.write(
                    f"  • [bold]{t.title}[/bold] ({len(t.lessons)} lessons)")
            log.write(
                "[dim]To switch tracks, type 'quit' and run 'kgiit learn' again to select a new one.[/dim]")
            return

        # Execute the command in the sandbox
        if self.sandbox is None or self.current_lesson_idx >= len(
                self.lessons):
            log.write("[red]No active lesson sandbox.[/red]")
            return

        lesson = self.lessons[self.current_lesson_idx]

        try:
            result = self.sandbox.run_user_command(command)
        except SandboxEscapeError as e:
            log.write(
                f"[bold red]⚠ SAFETY VIOLATION:[/bold red] "
                f"[red]{e}[/red]\n"
                "[dim]Commands must run inside the sandbox. This attempt was refused.[/dim]"
            )
            return
        except Exception as e:
            log.write(f"[red]Error executing command: {e}[/red]")
            return

        # Show command output
        if result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                log.write(f"[dim]{line}[/dim]")
        if result.stderr.strip():
            for line in result.stderr.strip().split("\n"):
                log.write(f"[yellow]{line}[/yellow]")

        # Refresh status pane
        self._refresh_status()

        # Deterministic verification
        verify_result = lesson.verify(self.sandbox, result)

        if verify_result.passed and not self._lesson_passed:
            self._lesson_passed = True
            log.write("\n[bold #a371f7]✓ CORRECT![/bold #a371f7]")
            for line in verify_result.message.split("\n"):
                log.write(f"[green]{line}[/green]")
            log.write(
                "\n[dim]Type [bold]skip[/bold] or [bold]next[/bold] to continue to the next lesson.[/dim]"
            )
        elif not verify_result.passed:
            # Call ML classifier for a hint
            context = {
                "has_staged": len(
                    self.sandbox.get_state().get(
                        "staged", [])) > 0, "has_unstaged": len(
                    self.sandbox.get_state().get(
                        "unstaged", [])) > 0, "is_init": self.sandbox.get_state().get(
                    "is_repo", False), }
            ml_label, confidence, hint_text = classify_mistake(
                typed=command,
                expected=lesson.target_command,
                context=context,
            )
            conf_str = f"(ML: {ml_label}, {confidence:.0%})" if confidence > 0 else f"(Rule: {ml_label})"
            log.write(
                f"\n[bold yellow]✗ Not quite... {conf_str}[/bold yellow]")
            log.write("\n[bold yellow]Hint:[/bold yellow]")
            for line in hint_text.split("\n"):
                log.write(f"[yellow]{line}[/yellow]")
            if verify_result.message:
                log.write(f"\n[dim]{verify_result.message}[/dim]")

    # ------------------------------------------------------------------
    # Actions (keyboard bindings + meta-commands)
    # ------------------------------------------------------------------

    def action_quit(self) -> None:
        """Quit the practice session."""
        if self.sandbox:
            # Clean up temp sandbox dir? Keep it for now — user might want to
            # inspect
            pass
        self.exit()

    def action_next_lesson(self) -> None:
        """Advance to the next lesson."""
        log = self.query_one("#scrollback", RichLog)
        next_idx = self.current_lesson_idx + 1
        if next_idx >= len(self.lessons):
            self._show_completion()
        else:
            log.write(f"\n[dim]Moving to lesson {next_idx + 1}...[/dim]")
            self._start_lesson(next_idx)

    def action_reset_step(self) -> None:
        """Reset the sandbox to the current lesson's fixture state."""
        if self.sandbox is None:
            return
        log = self.query_one("#scrollback", RichLog)
        log.write("\n[dim]Resetting sandbox to fixture state...[/dim]")
        self.sandbox.reset()
        lesson = self.lessons[self.current_lesson_idx]
        for step_fn in lesson.setup_steps:
            try:
                step_fn(self.sandbox)
            except Exception as e:
                log.write(f"[red]Setup error: {e}[/red]")
        self._refresh_status()
        self._lesson_passed = False
        log.write("[dim]Sandbox reset. Try the lesson again.[/dim]")

    def action_show_hint(self) -> None:
        """Show the lesson's fallback hint (no ML — just the pre-written hint)."""
        if self.current_lesson_idx >= len(self.lessons):
            return
        lesson = self.lessons[self.current_lesson_idx]
        log = self.query_one("#scrollback", RichLog)
        log.write("\n[bold yellow]💡 Hint:[/bold yellow]")
        for line in lesson.hint.split("\n"):
            log.write(f"[yellow]{line}[/yellow]")
        log.write(
            f"\n[dim]Target command: [bold]{lesson.target_command}[/bold][/dim]")
