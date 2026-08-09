"""
kgiit analyze — Automated GitHub Issue Analyze & Incident Control.

This subcommand requires:
  - Internet access to reach api.github.com
  - Optional: GITHUB_TOKEN env var for authenticated requests (higher rate limits)
    Without a token, the GitHub API allows ~60 unauthenticated requests/hour.
    With a token, the limit is 5,000 requests/hour.

Write-back (--apply):
  - Requires --issue (single issue, not --all-open)
  - Requires GITHUB_TOKEN with write access (repo or public_repo scope)
  - Every attempt — applied, declined, failed — is logged to kgiit-action-log.jsonl
  - There is NO flag to bypass the confirmation prompt
  - Use 'kgiit log' to view the audit trail
"""
from __future__ import annotations

import sys

import click

from kgiit import __version__
from kgiit.analyze import (
    GitHubAPIError,
    GitHubAuthError,
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
    build_analyze_summary,
    classify_issue,
    detect_duplicates,
    print_banner,
    print_error,
    print_issues_table,
    rank_priorities,
    write_report,
)
from kgiit.analyze.action_log import DEFAULT_LOG_PATH
from kgiit.analyze.formatting import (
    print_priority_table,
    print_summary_panel,
    print_writeback_preview,
    print_writeback_result,
)
from kgiit.analyze.writeback import (
    apply_suggestion,
    build_suggestion_labels,
    decline_suggestion,
    resolve_identity,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@click.command(
    name="analyze",
    help=(
        "Analyze real GitHub issues in a repository.\n\n"
        "Requires internet access to reach api.github.com. "
        "Set GITHUB_TOKEN environment variable for authenticated requests "
        "(5,000 req/hr vs 60 req/hr unauthenticated). "
        "A missing GITHUB_TOKEN is not an error — the tool works without one "
        "for public repositories, just at lower rate limits.\n\n"
        "Add --apply to go beyond read-only: after analysis, a human explicitly "
        "approves the suggestion before it's written to the real GitHub issue. "
        "Every outcome (applied, declined, failed) is logged locally. "
        "Run 'kgiit log' to view the audit trail."
    ),
)
@click.version_option(version=__version__, prog_name="kgiit analyze")
@click.option("--repo",
              required=True,
              help="Target GitHub repository in owner/name format (e.g. octocat/Hello-World).",
              )
@click.option(
    "--issue",
    type=int,
    default=None,
    help="Specific issue number to analyze.",
)
@click.option(
    "--all-open",
    is_flag=True,
    default=False,
    help="Analyze all open issues in the repository.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default="analyze-report.md",
    show_default=True,
    help="Output file path for the Markdown report.",
)
@click.option(
    "--no-report",
    is_flag=True,
    default=False,
    help="Skip generating and writing the report file.",
)
@click.option(
    "--agent-skills/--no-agent-skills",
    default=True,
    show_default=True,
    help="Enable Agent Skill Layer (classification, priority ranking, duplicate detection, summary).",
)
@click.option(
    "--apply",
    "apply_writeback",
    is_flag=True,
    default=False,
    help=(
        "After analyzing, offer to write the suggested label(s) back to the real "
        "GitHub issue. Requires --issue (single-issue only — bulk write-back across "
        "--all-open is intentionally not supported, to keep the blast radius of any "
        "one confirmation small) and a GITHUB_TOKEN with write access. Nothing is "
        "ever written without an explicit interactive confirmation."
    ),
)
@click.option(
    "--confirmed-by",
    default=None,
    help=(
        "Name/login of the human approving this write-back. When a GITHUB_TOKEN is "
        "set, the tool auto-detects the verified GitHub login and uses that instead. "
        "Falls back to your OS username if neither is available."
    ),
)
@click.option(
    "--dual-approval",
    is_flag=True,
    default=False,
    hidden=False,
    help=(
        "Require a second independent confirmer before the label is applied. "
        "Stretch mode for high-risk repositories. Both approvers are logged."
    ),
)
def analyze_cmd(
    repo: str,
    issue: int | None,
    all_open: bool,
    output: str,
    no_report: bool,
    agent_skills: bool,
    apply_writeback: bool,
    confirmed_by: str | None,
    dual_approval: bool,
):
    """Main CLI entrypoint for kgiit analyze."""
    # 1. Validate options
    if issue is not None and all_open:
        print_error(
            "Cannot pass both --issue and --all-open. Please select only one.")
        sys.exit(1)

    if issue is None and not all_open:
        print_error("Must specify either --issue <number> or --all-open.")
        sys.exit(1)

    # --apply restrictions
    if apply_writeback and all_open:
        print_error(
            "--apply is not supported with --all-open.\n"
            "To keep the blast radius small, write-back is limited to one issue at a time.\n"
            "Use --issue <number> with --apply."
        )
        sys.exit(1)

    if apply_writeback and not agent_skills:
        print_error(
            "--apply requires --agent-skills (the default). "
            "Cannot write back without classifying the issue first."
        )
        sys.exit(1)

    # 2. Validate repo format
    if "/" not in repo or repo.count("/") != 1 or not repo.split("/")[
            0] or not repo.split("/")[1]:
        print_error(
            f"Invalid repository format '{repo}'. Expected format 'owner/name'.")
        sys.exit(1)

    owner, repo_name = repo.split("/")

    # 3. Print Banner (includes token/network notice)
    print_banner(f"{owner}/{repo_name}")

    # 4. Fetch and analyze issues
    try:
        client = GitHubClient()
        issues = []

        if issue is not None:
            click.echo(
                f"[*] Fetching issue #{issue} for {owner}/{repo_name}...")
            single_issue = client.get_issue(owner, repo_name, issue)
            issues = [single_issue]
        else:
            click.echo(
                f"[*] Fetching all open issues for {owner}/{repo_name}...")
            issues = client.list_open_issues(owner, repo_name)

        if not issues:
            click.echo(
                f"[+] No matching issues found for {owner}/{repo_name}.")
        else:
            print_issues_table(issues)

            # 5. Agent Skill Layer Integration
            if agent_skills:
                click.echo(
                    "[*] Executing Agent Skill Layer (issue-analyze, priority-ranker, duplicate-detector)...")
                classifications = {}
                classified_list = []
                duplicates = []

                for item in issues:
                    cls_res = classify_issue(item)
                    num_key = cls_res.get("issue_number")
                    classifications[num_key] = cls_res
                    classified_list.append(cls_res)

                    dup_res = detect_duplicates(item, issues)
                    duplicates.append(dup_res)

                ranked_list = rank_priorities(classified_list)
                print_priority_table(ranked_list, classifications)

                summary_text = build_analyze_summary(
                    classified_list, duplicates)
                print_summary_panel(summary_text)

                # 6. Write-Back Flow (--apply)
                if apply_writeback and issue is not None:
                    _run_writeback(
                        client=client,
                        repo=f"{owner}/{repo_name}",
                        issue_number=issue,
                        classification=classifications.get(issue, {}),
                        confirmed_by=confirmed_by,
                        dual_approval=dual_approval,
                    )

            if not no_report:
                report_path = write_report(
                    owner, repo_name, issues, output_path=output)
                click.echo(
                    f"[+] Report generated successfully at: {report_path}")

    except GitHubNotFoundError as e:
        print_error(f"Repository or issue not found: {e}")
        sys.exit(1)
    except GitHubAuthError as e:
        print_error(f"Authentication failed (check GITHUB_TOKEN): {e}")
        sys.exit(1)
    except GitHubRateLimitError:
        from rich.console import Console as _Console
        from rich.panel import Panel as _Panel
        _con = _Console()
        _con.print(_Panel(
            "[bold red]GitHub API rate limit exceeded.[/bold red]\n\n"
            "You are hitting the [bold]60 requests/hour[/bold] unauthenticated limit.\n\n"
            "Fix: set a [bold]GITHUB_TOKEN[/bold] environment variable:\n\n"
            "  [bold bright_cyan]Windows PowerShell:[/bold bright_cyan]\n"
            "    [dim]$env:GITHUB_TOKEN = \"ghp_your_token_here\"[/dim]\n\n"
            "  [bold bright_cyan]Linux / macOS:[/bold bright_cyan]\n"
            "    [dim]export GITHUB_TOKEN=ghp_your_token_here[/dim]\n\n"
            "Get a free token at: [link]https://github.com/settings/tokens[/link]\n"
            "(No special scopes needed for public repos — just click Generate)\n\n"
            "[dim]With a token: 5,000 requests/hour instead of 60.[/dim]",
            title="[bold red]Rate Limit Exceeded[/bold red]",
            border_style="red",
        ))
        sys.exit(1)
    except GitHubAPIError as e:
        print_error(f"GitHub API request failed: {e}")
        sys.exit(1)


def _run_writeback(
    client: GitHubClient,
    repo: str,
    issue_number: int,
    classification: dict,
    confirmed_by: str | None,
    dual_approval: bool,
) -> None:
    """
    Inner function: run the human-in-the-loop write-back flow.

    Steps:
      1. Build label suggestion from classification
      2. Resolve the confirmer's identity (GitHub-verified > explicit > OS)
      3. Preview what will be applied
      4. Ask for explicit confirmation (mandatory — no --yes bypass)
      5. If dual_approval: ask for a second confirmer
      6. Apply and log the result, or log the decline
    """
    from rich.console import Console
    console = Console()

    labels = build_suggestion_labels(classification)

    if not labels:
        console.print(
            "\n[bold yellow]⚠ No actionable labels generated.[/bold yellow] "
            "The classifier returned 'uncategorized'. Nothing to apply.\n"
        )
        return

    # Resolve identity
    approver_1 = resolve_identity(client, fallback=confirmed_by)

    print_writeback_preview(
        issue_number=issue_number,
        repo=repo,
        classification=classification,
        labels=labels,
        confirmed_by=approver_1,
    )

    # Primary confirmation — cannot be bypassed
    confirmed = click.confirm(
        "\nApply these labels to the real GitHub issue?",
        default=False,
    )

    if not confirmed:
        decline_suggestion(
            repo=repo,
            issue_number=issue_number,
            labels=labels,
            confirmed_by=approver_1,
        )
        print_writeback_result(
            status="declined",
            labels=labels,
            repo=repo,
            issue_number=issue_number,
        )
        return

    # Dual-approval stretch mode
    if dual_approval:
        console.print(
            "\n[bold cyan]Dual-approval mode:[/bold cyan] "
            "A second independent confirmer is required."
        )
        approver_2_name = click.prompt(
            "Enter the second approver's name/login",
            default="",
        ).strip()
        if not approver_2_name:
            console.print(
                "[bold red]Second approver name required for dual-approval. Aborting.[/bold red]\n"
            )
            decline_suggestion(
                repo=repo,
                issue_number=issue_number,
                labels=labels,
                confirmed_by=f"{approver_1}+dual-approval-aborted",
            )
            return

        confirmed_2 = click.confirm(
            f"Confirm as second approver '{approver_2_name}'?",
            default=False,
        )
        if not confirmed_2:
            console.print(
                "[bold yellow]⏹ Second approver declined. Write-back aborted.[/bold yellow]\n"
            )
            decline_suggestion(
                repo=repo,
                issue_number=issue_number,
                labels=labels,
                confirmed_by=f"{approver_1}+{approver_2_name}(declined)",
            )
            return

        # Both approved — combine identities in the log
        approver_1 = f"{approver_1}+{approver_2_name}"

    # Apply
    try:
        apply_suggestion(
            client=client,
            repo=repo,
            issue_number=issue_number,
            labels=labels,
            confirmed_by=approver_1,
        )
        print_writeback_result(
            status="applied",
            labels=labels,
            repo=repo,
            issue_number=issue_number,
        )
    except GitHubAPIError as exc:
        print_writeback_result(
            status="failed",
            labels=labels,
            repo=repo,
            issue_number=issue_number,
            error=str(exc),
        )
        # Exit with error so callers / CI can detect failure
        sys.exit(1)
