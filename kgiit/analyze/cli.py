"""
kgiit analyze — Automated GitHub Issue Analyze & Incident Control.

This subcommand requires:
  - Internet access to reach api.github.com
  - Optional: GITHUB_TOKEN env var for authenticated requests (higher rate limits)
    Without a token, the GitHub API allows ~60 unauthenticated requests/hour.
    With a token, the limit is 5,000 requests/hour.
"""
from __future__ import annotations

import sys

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
from kgiit.analyze.formatting import (
    print_priority_table,
    print_summary_panel,
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
        "for public repositories, just at lower rate limits."
    ),
)
@click.version_option(version="1.0.0", prog_name="kgiit analyze")
@click.option(
    "--repo",
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
def analyze_cmd(
    repo: str,
    issue: int | None,
    all_open: bool,
    output: str,
    no_report: bool,
    agent_skills: bool,
):
    """Main CLI entrypoint for kgiit analyze."""
    # 1. Validate options
    if issue is not None and all_open:
        print_error("Cannot pass both --issue and --all-open. Please select only one.")
        sys.exit(1)

    if issue is None and not all_open:
        print_error("Must specify either --issue <number> or --all-open.")
        sys.exit(1)

    # 2. Validate repo format
    if "/" not in repo or repo.count("/") != 1 or not repo.split("/")[0] or not repo.split("/")[1]:
        print_error(f"Invalid repository format '{repo}'. Expected format 'owner/name'.")
        sys.exit(1)

    owner, repo_name = repo.split("/")

    # 3. Print Banner (includes token/network notice)
    print_banner(f"{owner}/{repo_name}")

    # 4. Fetch and analyze issues
    try:
        client = GitHubClient()
        issues = []

        if issue is not None:
            click.echo(f"[*] Fetching issue #{issue} for {owner}/{repo_name}...")
            single_issue = client.get_issue(owner, repo_name, issue)
            issues = [single_issue]
        else:
            click.echo(f"[*] Fetching all open issues for {owner}/{repo_name}...")
            issues = client.list_open_issues(owner, repo_name)

        if not issues:
            click.echo(f"[+] No matching issues found for {owner}/{repo_name}.")
        else:
            print_issues_table(issues)

            # 5. Agent Skill Layer Integration
            if agent_skills:
                click.echo("[*] Executing Agent Skill Layer (issue-analyze, priority-ranker, duplicate-detector)...")
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

                summary_text = build_analyze_summary(classified_list, duplicates)
                print_summary_panel(summary_text)

            if not no_report:
                report_path = write_report(owner, repo_name, issues, output_path=output)
                click.echo(f"[+] Report generated successfully at: {report_path}")

    except GitHubNotFoundError as e:
        print_error(f"Repository or issue not found: {e}")
        sys.exit(1)
    except GitHubAuthError as e:
        print_error(f"Authentication failed (check GITHUB_TOKEN): {e}")
        sys.exit(1)
    except GitHubRateLimitError as e:
        print_error(f"GitHub API rate limit exceeded: {e}")
        sys.exit(1)
    except GitHubAPIError as e:
        print_error(f"GitHub API request failed: {e}")
        sys.exit(1)
