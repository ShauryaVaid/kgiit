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
from kgiit import __version__

import click

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
        "ever written without an explicit interactive confirmation; there is no flag "
        "to bypass that prompt."
    ),
)
@click.option(
    "--confirmed-by",
    default=None,
    help=(
        "Name to attribute the write-back confirmation to, used only as a fallback "
        "when GITHUB_TOKEN's identity can't be resolved via the GitHub API."
    ),
)
@click.option(
    "--dual-approval",
    is_flag=True,
    default=False,
    help="Require two different confirmations (from two different names) before applying.",
)
@click.option(
    "--log-file",
    default=DEFAULT_LOG_PATH,
    show_default=True,
    help="Path to the local write-back audit log (JSON Lines). View with 'kgiit log'.",
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
    log_file: str,
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

    if apply_writeback and all_open:
        print_error(
            "--apply requires a single --issue <number>, not --all-open. "
            "Write-back is scoped to one confirmed issue at a time by design.")
        sys.exit(1)

    if apply_writeback and not agent_skills:
        print_error(
            "--apply requires the Agent Skill Layer to produce a suggestion "
            "to confirm. Remove --no-agent-skills.")
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

                # 5b. Confirmed write-back — human explicitly approves a
                # specific suggestion before it is applied to the real
                # GitHub issue. See kgiit.analyze.writeback for the
                # apply/decline logic itself; this block is only UI glue.
                if apply_writeback:
                    if not client.token:
                        print_error(
                            "--apply requires a GITHUB_TOKEN with write access to "
                            f"{owner}/{repo_name} (repo or public_repo scope). "
                            "No write was attempted.")
                        sys.exit(1)

                    target_issue = issues[0]
                    target_num = target_issue.get("number")
                    classification = classifications.get(f"#{target_num}", {})
                    proposed_labels = build_suggestion_labels(classification)

                    click.echo()
                    identity_1 = resolve_identity(
                        client, fallback=confirmed_by)
                    print_writeback_preview(
                        repo=f"{owner}/{repo_name}",
                        issue_number=target_num,
                        current_labels=target_issue.get("labels", []),
                        proposed_labels=proposed_labels,
                        confirmed_by=identity_1,
                        console=None,
                    )

                    approved = click.confirm(
                        f"Apply this suggestion to {owner}/{repo_name}#{target_num}?",
                        default=False,
                    )

                    if approved and dual_approval:
                        click.echo(
                            "[*] Dual approval enabled: a second, different "
                            "confirmer must also approve.")
                        identity_2 = click.prompt(
                            "Second approver name", default="", show_default=False
                        ).strip()
                        second_ok = bool(identity_2) and identity_2 != identity_1
                        if not second_ok:
                            click.echo(
                                "[!] Second approval missing or matched the first "
                                "approver — treating as declined.")
                            approved = False
                        else:
                            approved = click.confirm(
                                f"{identity_2}, confirm applying this suggestion?",
                                default=False,
                            )
                            identity_1 = f"{identity_1} + {identity_2}"

                    if not approved:
                        result = decline_suggestion(
                            owner=owner,
                            repo=repo_name,
                            issue_number=target_num,
                            classification=classification,
                            confirmed_by=identity_1,
                            log_path=log_file,
                        )
                        print_writeback_result(result)
                    else:
                        result = apply_suggestion(
                            client,
                            owner=owner,
                            repo=repo_name,
                            issue_number=target_num,
                            classification=classification,
                            confirmed_by=identity_1,
                            log_path=log_file,
                        )
                        print_writeback_result(result)
                        if not result["ok"]:
                            sys.exit(1)

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
