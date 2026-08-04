import sys
from typing import Optional
import click

from triagectl import (
    __version__,
    GitHubClient,
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubAuthError,
    GitHubRateLimitError,
    print_banner,
    print_issues_table,
    print_error,
    write_report,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@click.command(name="triage", help="Automated GitHub Issue Triage & Incident Control CLI.")
@click.version_option(version=__version__, prog_name="triage")
@click.option(
    "--repo",
    required=True,
    help="Target GitHub repository in owner/name format (e.g. octocat/Hello-World).",
)
@click.option(
    "--issue",
    type=int,
    default=None,
    help="Specific issue number to triage.",
)
@click.option(
    "--all-open",
    is_flag=True,
    default=False,
    help="Triage all open issues in the repository.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default="triage-report.md",
    show_default=True,
    help="Output file path for the Markdown report.",
)
@click.option(
    "--no-report",
    is_flag=True,
    default=False,
    help="Skip generating and writing the report file.",
)
def main(
    repo: str,
    issue: Optional[int],
    all_open: bool,
    output: str,
    no_report: bool,
):
    """Main CLI entrypoint for triagectl."""
    # 1. Validate options: --issue and --all-open mutual exclusivity
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

    # 3. Print Banner
    print_banner(f"{owner}/{repo_name}")

    # 4. Fetch and triage issues
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


if __name__ == "__main__":
    main()
