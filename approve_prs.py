"""
Azure DevOps PR Approver
------------------------
Bulk-approve Azure DevOps Pull Requests from a file, clipboard, or
interactive prompt. Uses your Personal Access Token stored in .env.

Usage:
  python approve_prs.py                     # interactive / clipboard
  python approve_prs.py --file urls.txt     # from a text file
  python approve_prs.py --profile work      # use AZURE_DEVOPS_PAT_WORK

Supported URL format:
  https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    _PYPERCLIP_AVAILABLE = False

from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel

# ── Config toggles ─────────────────────────────────────────────────────────────
# Set to False to disable automatic clipboard pre-fill at startup.
CLIPBOARD_AUTO_READ = True

# ── Constants ──────────────────────────────────────────────────────────────────

ADO_API_VERSION = "7.1"
VOTE_APPROVED = 10          # Azure DevOps vote values: 10=Approved, 5=Approved w/ suggestions,
                            # 0=No vote, -5=Waiting for author, -10=Rejected
PR_ACTIVE_STATUS = "active" # PRs in any other status (completed, abandoned) will be skipped

PR_URL_PATTERN = re.compile(
    r"https://dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/]+)/pullrequest/(?P<pr_id>\d+)",
    re.IGNORECASE,
)

console = Console()

# ── Helpers ────────────────────────────────────────────────────────────────────


def load_pat(profile: str | None = None) -> str:
    """Load PAT from .env. Pass profile name to use AZURE_DEVOPS_PAT_{PROFILE}."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        console.print(
            f"[bold red]ERROR:[/] .env file not found.\n"
            f"Copy [cyan].env.example[/] \u2192 [cyan].env[/] and fill in your PAT.\n"
            f"Expected path: {env_path}",
            highlight=False,
        )
        sys.exit(1)
    load_dotenv(env_path)
    env_key = f"AZURE_DEVOPS_PAT_{profile.upper()}" if profile else "AZURE_DEVOPS_PAT"
    pat = os.getenv(env_key, "").strip()
    if not pat or pat == "your_personal_access_token_here":
        msg = f"[bold red]ERROR:[/] [cyan]{env_key}[/] is not set in your .env file."
        if profile:
            msg += f"\n[dim]Add it as: {env_key}=your_token[/]"
        console.print(msg)
        sys.exit(1)
    return pat


def parse_pr_url(url: str) -> dict:
    """Parse an Azure DevOps PR URL into its components."""
    match = PR_URL_PATTERN.match(url.strip())
    if not match:
        raise ValueError(f"Unrecognised URL format: {url}")
    return match.groupdict() | {"pr_id": int(match.group("pr_id"))}


def _extract_pr_urls(text: str) -> list[str]:
    """Pull every ADO PR URL out of an arbitrary block of text."""
    return [m.group(0) for m in PR_URL_PATTERN.finditer(text)]


def collect_pr_urls(file_path: str | None = None) -> list[str]:
    """Collect PR URLs from a --file, clipboard pre-fill, or interactive prompt."""

    # ── From file (─────────────────────────────────────────────────────
    if file_path:
        path = Path(file_path)
        if not path.exists():
            console.print(f"[bold red]ERROR:[/] File not found: {file_path}")
            sys.exit(1)
        urls = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        console.print(f"[dim]Loaded {len(urls)} URL(s) from [cyan]{file_path}[/][/]")
        return urls

    # ── Clipboard pre-fill ──────────────────────────────────────────────────
    clipboard_urls: list[str] = []
    if CLIPBOARD_AUTO_READ and _PYPERCLIP_AVAILABLE:
        try:
            clipboard_urls = _extract_pr_urls(pyperclip.paste())
            if clipboard_urls:
                console.print(
                    f"[dim]\U0001f4cb Clipboard has {len(clipboard_urls)} PR URL(s) — "
                    f"press [bold]Enter[/] on a blank line immediately to use them.[/]"
                )
        except Exception:  # noqa: BLE001
            pass

    # ── Interactive prompt ────────────────────────────────────────────────
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
            if clipboard_urls:
                return clipboard_urls  # blank Enter immediately → use clipboard
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


def get_pr_info(org: str, project: str, repo: str, pr_id: int,
                reviewer_id: str, auth: HTTPBasicAuth) -> tuple[str, bool, str, str]:
    """Fetch PR title, already-approved flag, PR status, and author display name."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/"
        f"{repo}/pullRequests/{pr_id}?api-version={ADO_API_VERSION}"
    )
    resp = requests.get(url, auth=auth, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    title = data.get("title", f"PR #{pr_id}")
    pr_status = data.get("status", PR_ACTIVE_STATUS).lower()
    author_name = data.get("createdBy", {}).get("displayName", "\u2014")
    already_approved = any(
        r.get("id") == reviewer_id and r.get("vote") == VOTE_APPROVED
        for r in data.get("reviewers", [])
    )
    return title, already_approved, pr_status, author_name


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
    # ── CLI arguments ────────────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="Bulk-approve Azure DevOps Pull Requests.")
    parser.add_argument(
        "--file", "-f",
        metavar="PATH",
        help="Path to a .txt file with one PR URL per line (lines starting with # are ignored).",
    )
    parser.add_argument(
        "--profile", "-p",
        metavar="NAME",
        help="PAT profile to use. Reads AZURE_DEVOPS_PAT_{NAME} from .env (e.g. --profile work).",
    )
    args = parser.parse_args()

    pat = load_pat(args.profile)
    auth = HTTPBasicAuth("", pat)  # ADO: username can be anything, password = PAT

    raw_urls = collect_pr_urls(args.file)

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

    # ── Deduplicate URLs ─────────────────────────────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for item in parsed:
        key = item["url"].lower().rstrip("/")
        if key in seen:
            console.print(f"[dim]DUPLICATE skipped:[/] {item['url']}")
        else:
            seen.add(key)
            unique.append(item)
    parsed = unique

    # ── Confirm before approving ─────────────────────────────────────────────
    console.print(f"\n[bold]Ready to approve {len(parsed)} PR(s):[/]")
    for item in parsed:
        console.print(f"  [cyan]•[/] {item['org']}/{item['project']} → PR #{item['pr_id']}")
    console.print()
    try:
        confirm = input("  Approve all? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled.[/]")
        sys.exit(0)
    if confirm != "y":
        console.print("[yellow]Aborted.[/]")
        sys.exit(0)

    # ── Resolve reviewer IDs (once per unique org) ───────────────────────────
    orgs: set[str] = {p["org"] for p in parsed}
    user_ids: dict[str, str] = {}

    with console.status("[bold green]Authenticating…"):
        for org in orgs:
            try:
                user_ids[org] = get_current_user_id(org, auth)
            except requests.HTTPError as exc:
                status_code = exc.response.status_code
                reason = exc.response.reason
                hint = " \u2014 PAT may be expired or missing Code scope." if status_code == 401 else ""
                console.print(
                    f"[bold red]AUTH FAILED[/] for org '{org}': {status_code} {reason}{hint}"
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[bold red]AUTH ERROR[/] for org '{org}': {exc}")

    if not user_ids:
        console.print("[red]Could not authenticate to any org. Check your PAT.[/]")
        sys.exit(1)

    # ── Approve each PR ──────────────────────────────────────────────────────
    results: list[tuple[str, str, str, str, str]] = []  # (pr_ref, title, author, status, detail)

    console.print()
    for item in parsed:
        org, project, repo, pr_id = item["org"], item["project"], item["repo"], item["pr_id"]
        pr_ref = f"{org}/{project} → PR #{pr_id}"
        title = f"PR #{pr_id}"
        author = "—"

        if org not in user_ids:
            results.append((pr_ref, title, author, "SKIPPED", "Auth failed for org"))
            continue

        # Fetch PR info: title, already-approved, PR status, author
        try:
            title, already_approved, pr_status, author = get_pr_info(
                org, project, repo, pr_id, user_ids[org], auth
            )
            if pr_status != PR_ACTIVE_STATUS:
                results.append((pr_ref, title, author, "SKIPPED", f"PR is {pr_status}"))
                continue
            if already_approved:
                results.append((pr_ref, title, author, "ALREADY APPROVED", ""))
                continue
        except Exception:  # noqa: BLE001
            pass  # non-fatal — proceed with approve attempt

        try:
            approve_pr(org, project, repo, pr_id, user_ids[org], auth)
            results.append((pr_ref, title, author, "APPROVED", ""))
        except requests.HTTPError as exc:
            status_code = exc.response.status_code
            try:
                detail = exc.response.json().get("message", exc.response.reason)
            except Exception:  # noqa: BLE001
                detail = exc.response.reason
            results.append((pr_ref, title, author, "FAILED", f"HTTP {status_code}: {detail}"))
        except Exception as exc:  # noqa: BLE001
            results.append((pr_ref, title, author, "FAILED", str(exc)))

    # ── Summary table ────────────────────────────────────────────────────────
    status_styles = {
        "APPROVED": "bold green",
        "ALREADY APPROVED": "dim green",
        "SKIPPED": "yellow",
        "FAILED": "bold red",
    }

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Pull Request", style="cyan", no_wrap=True)
    table.add_column("Title", style="white", max_width=40)
    table.add_column("Author", style="dim", max_width=22)
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    for pr_ref, title, author, status, detail in results:
        style = status_styles.get(status, "white")
        table.add_row(pr_ref, title, author, f"[{style}]{status}[/]", detail)

    console.print()
    console.print(table)

    approved = sum(1 for _, _, _, s, _ in results if s == "APPROVED")
    already  = sum(1 for _, _, _, s, _ in results if s == "ALREADY APPROVED")
    failed   = sum(1 for _, _, _, s, _ in results if s == "FAILED")
    skipped  = sum(1 for _, _, _, s, _ in results if s == "SKIPPED")
    console.print(
        f"\n[bold]Done.[/]  "
        f"[green]Approved: {approved}[/]  "
        f"[dim green]Already approved: {already}[/]  "
        f"[red]Failed: {failed}[/]  "
        f"[yellow]Skipped: {skipped}[/]"
    )


if __name__ == "__main__":
    main()
