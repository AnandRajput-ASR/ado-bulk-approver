"""
Azure DevOps PR Approver
------------------------
Paste one or more Azure DevOps Pull Request URLs at the prompt,
press Enter on a blank line, and the script will approve them all
using your Personal Access Token stored in .env.

Supported URL format:
  https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
"""

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt

# ── Constants ──────────────────────────────────────────────────────────────────

ADO_API_VERSION = "7.1"
VOTE_APPROVED = 10  # Azure DevOps vote values: 10=Approved, 5=Approved w/ suggestions,
                    # 0=No vote, -5=Waiting for author, -10=Rejected

PR_URL_PATTERN = re.compile(
    r"https://dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/]+)/pullrequest/(?P<pr_id>\d+)",
    re.IGNORECASE,
)

console = Console()

# ── Helpers ────────────────────────────────────────────────────────────────────


def load_pat() -> str:
    """Load PAT from .env file in the same directory as this script."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        example_path = Path(__file__).parent / ".env.example"
        console.print(
            f"[bold red]ERROR:[/] .env file not found.\n"
            f"Copy [cyan].env.example[/] → [cyan].env[/] and fill in your PAT.\n"
            f"Expected path: {env_path}",
            highlight=False,
        )
        sys.exit(1)
    load_dotenv(env_path)
    pat = os.getenv("AZURE_DEVOPS_PAT", "").strip()
    if not pat or pat == "your_personal_access_token_here":
        console.print(
            "[bold red]ERROR:[/] AZURE_DEVOPS_PAT is not set in your .env file."
        )
        sys.exit(1)
    return pat


def parse_pr_url(url: str) -> dict:
    """Parse an Azure DevOps PR URL into its components."""
    match = PR_URL_PATTERN.match(url.strip())
    if not match:
        raise ValueError(f"Unrecognised URL format: {url}")
    return match.groupdict() | {"pr_id": int(match.group("pr_id"))}


def collect_pr_urls() -> list[str]:
    """Interactively collect PR URLs from the user."""
    console.print(
        Panel(
            "[bold cyan]Azure DevOps PR Approver[/]\n\n"
            "Paste PR URLs one per line.\n"
            "Leave a blank line and press [bold]Enter[/] when done.",
            expand=False,
        )
    )
    urls: list[str] = []
    while True:
        try:
            line = input("  PR URL: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Interrupted.[/]")
            sys.exit(0)
        if not line:
            if urls:
                break
            console.print("[dim]  (enter at least one URL)[/]")
        else:
            urls.append(line)
    return urls


def get_current_user_id(org: str, auth: HTTPBasicAuth) -> str:
    """Return the object ID of the authenticated user for the given org."""
    url = f"https://vssps.dev.azure.com/{org}/_apis/profile/profiles/me?api-version={ADO_API_VERSION}"
    resp = requests.get(url, auth=auth, timeout=15)
    resp.raise_for_status()
    return resp.json()["id"]


def approve_pr(org: str, project: str, repo: str, pr_id: int,
               reviewer_id: str, auth: HTTPBasicAuth) -> dict:
    """
    Approve a single PR by PUTting a reviewer vote.
    Returns the response JSON on success.
    """
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/"
        f"{repo}/pullRequests/{pr_id}/reviewers/{reviewer_id}"
        f"?api-version={ADO_API_VERSION}"
    )
    payload = {"vote": VOTE_APPROVED}
    resp = requests.put(url, json=payload, auth=auth, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    pat = load_pat()
    auth = HTTPBasicAuth("", pat)  # ADO: username can be anything, password = PAT

    raw_urls = collect_pr_urls()

    # ── Parse & validate URLs ────────────────────────────────────────────────
    parsed: list[dict] = []
    for url in raw_urls:
        try:
            parsed.append(parse_pr_url(url) | {"url": url})
        except ValueError as exc:
            console.print(f"[yellow]SKIP[/] {exc}")

    if not parsed:
        console.print("[red]No valid PR URLs to process. Exiting.[/]")
        sys.exit(1)

    # ── Resolve reviewer IDs (once per unique org) ───────────────────────────
    orgs: set[str] = {p["org"] for p in parsed}
    user_ids: dict[str, str] = {}

    with console.status("[bold green]Authenticating…"):
        for org in orgs:
            try:
                user_ids[org] = get_current_user_id(org, auth)
            except requests.HTTPError as exc:
                console.print(
                    f"[bold red]AUTH FAILED[/] for org '{org}': {exc.response.status_code} "
                    f"{exc.response.reason}"
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[bold red]AUTH ERROR[/] for org '{org}': {exc}")

    if not user_ids:
        console.print("[red]Could not authenticate to any org. Check your PAT.[/]")
        sys.exit(1)

    # ── Approve each PR ──────────────────────────────────────────────────────
    results: list[tuple[str, str, str]] = []  # (pr_ref, status, detail)

    console.print()
    for item in parsed:
        org, project, repo, pr_id = item["org"], item["project"], item["repo"], item["pr_id"]
        pr_ref = f"{org}/{project} → PR #{pr_id}"

        if org not in user_ids:
            results.append((pr_ref, "SKIPPED", "Auth failed for org"))
            continue

        try:
            approve_pr(org, project, repo, pr_id, user_ids[org], auth)
            results.append((pr_ref, "APPROVED", ""))
        except requests.HTTPError as exc:
            status_code = exc.response.status_code
            try:
                detail = exc.response.json().get("message", exc.response.reason)
            except Exception:  # noqa: BLE001
                detail = exc.response.reason
            results.append((pr_ref, "FAILED", f"HTTP {status_code}: {detail}"))
        except Exception as exc:  # noqa: BLE001
            results.append((pr_ref, "FAILED", str(exc)))

    # ── Summary table ────────────────────────────────────────────────────────
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Pull Request", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    status_styles = {"APPROVED": "bold green", "SKIPPED": "yellow", "FAILED": "bold red"}

    for pr_ref, status, detail in results:
        style = status_styles.get(status, "white")
        table.add_row(pr_ref, f"[{style}]{status}[/]", detail)

    console.print()
    console.print(table)

    approved = sum(1 for _, s, _ in results if s == "APPROVED")
    failed = sum(1 for _, s, _ in results if s == "FAILED")
    skipped = sum(1 for _, s, _ in results if s == "SKIPPED")
    console.print(
        f"\n[bold]Done.[/]  "
        f"[green]Approved: {approved}[/]  "
        f"[red]Failed: {failed}[/]  "
        f"[yellow]Skipped: {skipped}[/]"
    )


if __name__ == "__main__":
    main()
