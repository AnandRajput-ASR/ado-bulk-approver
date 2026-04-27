# ✅ Azure DevOps PR Approver

> **Bulk-approve Azure DevOps Pull Requests in seconds — no browser, no clicking, just Python.**

---

## 📋 Table of Contents

- [What It Does](#-what-it-does)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Setup](#-setup)
  - [1 — Clone / Download](#1--clone--download)
  - [2 — Create a Virtual Environment](#2--create-a-virtual-environment)
  - [3 — Install Dependencies](#3--install-dependencies)
  - [4 — Configure Your PAT](#4--configure-your-pat)
- [Usage](#-usage)
  - [Interactive Mode](#interactive-mode-default)
  - [File Mode](#file-mode----file)
  - [Clipboard Auto-Read](#clipboard-auto-read)
  - [Multi-Profile Auth](#multi-profile-auth----profile)
- [PR Status Behaviour](#-pr-status-behaviour)
- [URL Format](#-url-format)
- [Vote Reference](#-vote-reference)
- [Troubleshooting](#-troubleshooting)
- [Changelog](#-changelog)

---

## 🚀 What It Does

Provide Azure DevOps PR URLs via interactive prompt, a text file, or your clipboard — the script will:

1. Parse every URL to extract the **org / project / repo / PR ID**
2. Deduplicate and validate URLs
3. Show a confirmation list and ask `Approve all? [y/N]` before touching anything
4. Authenticate as **you** using your Personal Access Token (supports multiple profiles)
5. Check each PR's status — skip `completed` or `abandoned` PRs automatically
6. Detect PRs you've already approved and mark them `ALREADY APPROVED`
7. `PUT` an **Approved** vote (`10`) on every remaining active PR via the ADO REST API
8. Print a colour-coded summary table showing **PR ref / Title / Author / Status / Detail**

---

## 📁 Project Structure

```
pr-approver/
├── approve_prs.py      ← main script
├── requirements.txt    ← Python dependencies
├── .env.example        ← template — copy this to .env and fill in your PAT
└── .env                ← your secrets (never commit this!)
```

---

## 🔧 Prerequisites

| Requirement | Minimum Version |
|---|---|
| Python | 3.10 + |
| pip | any recent version |
| Azure DevOps access | Contributor / Reviewer role on the target repos |

---

## ⚙️ Setup

### 1 — Clone / Download

```bash
# If this is inside a larger repo
cd path/to/pr-approver
```

Or just place the folder anywhere on your machine.

---

### 2 — Create a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

> Tip: you'll see `(.venv)` in your prompt when it's active.

---

### 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

Packages installed:

| Package | Purpose |
|---|---|
| `requests` | HTTP calls to the ADO REST API |
| `python-dotenv` | Load secrets from `.env` without exposing them in code |
| `rich` | Beautiful terminal output — colours, tables, spinners |
| `pyperclip` | Read PR URLs directly from your clipboard |

---

### 4 — Configure Your PAT

#### a) Generate a Personal Access Token

1. Go to → `https://dev.azure.com/{your-org}/_usersSettings/tokens`
2. Click **+ New Token**
3. Set **Scopes** → **Code** → ✅ **Read & Write**
4. Set an expiry and click **Create**
5. **Copy the token** — you won't see it again

#### b) Create your `.env` file

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Then open `.env` and replace the placeholder:

```dotenv
# Default PAT (no --profile flag needed)
AZURE_DEVOPS_PAT=your_actual_token_here

# Optional named profiles — used with --profile flag
# AZURE_DEVOPS_PAT_WORK=your_work_token
# AZURE_DEVOPS_PAT_CLIENT=your_client_token
```

> ⚠️ **Never commit `.env` to version control.** Add it to `.gitignore`.

---

## ▶️ Usage

```bash
python approve_prs.py                          # interactive / clipboard
python approve_prs.py --file urls.txt          # load URLs from a file
python approve_prs.py --profile work           # use a named PAT profile
python approve_prs.py -f urls.txt -p work      # combine both
```

---

### Interactive Mode (default)

Run with no flags — paste URLs one per line, blank line to submit:

```
╭─────────────────────────────────────────────────╮
│ Azure DevOps PR Approver                        │
│                                                 │
│ Paste PR URLs one per line.                     │
│ Leave a blank line and press Enter when done.   │
╰─────────────────────────────────────────────────╯
  PR URL: https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/101
  PR URL: https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/102
  PR URL:              ← blank line + Enter to submit

Ready to approve 2 PR(s):
  • myorg/myproject → PR #101
  • myorg/myproject → PR #102

  Approve all? [y/N]: y
```

**Result table:**

```
╭────────────────────────────────┬──────────────────────┬────────────────┬──────────┬────────╮
│ Pull Request                   │ Title                │ Author         │  Status  │ Detail │
├────────────────────────────────┼──────────────────────┼────────────────┼──────────┼────────┤
│ myorg/myproject → PR #101      │ Fix login redirect   │ John Smith     │ APPROVED │        │
│ myorg/myproject → PR #102      │ Update deps          │ Jane Doe       │ APPROVED │        │
╰────────────────────────────────┴──────────────────────┴────────────────┴──────────┴────────╯

Done.  Approved: 2  Already approved: 0  Failed: 0  Skipped: 0
```

---

### File Mode — `--file`

Create a plain text file with one PR URL per line.
Lines starting with `#` are treated as comments and ignored.

```text
# Sprint 42 PRs
https://dev.azure.com/myorg/myproject/_git/backend/pullrequest/201
https://dev.azure.com/myorg/myproject/_git/frontend/pullrequest/202

# Hotfix
https://dev.azure.com/myorg/myproject/_git/backend/pullrequest/203
```

Run:

```bash
python approve_prs.py --file sprint42.txt
# or short form:
python approve_prs.py -f sprint42.txt
```

---

### Clipboard Auto-Read

When `CLIPBOARD_AUTO_READ = True` (default), the script scans your clipboard for ADO PR URLs at startup.

**Workflow:**
1. Copy one or more PR URLs from your browser (multi-line works too)
2. Run `python approve_prs.py`
3. You'll see: `📋 Clipboard has 3 PR URL(s) — press Enter on a blank line immediately to use them.`
4. Press **Enter** on a blank line immediately → clipboard URLs are loaded
5. Or start typing new URLs manually to ignore the clipboard

**To disable clipboard auto-read** — open `approve_prs.py` and change:

```python
CLIPBOARD_AUTO_READ = False
```

---

### Multi-Profile Auth — `--profile`

Useful when you work across **multiple Azure DevOps orgs** with different accounts/tokens.

**Step 1 — Add named profiles to `.env`:**

```dotenv
AZURE_DEVOPS_PAT=default_token
AZURE_DEVOPS_PAT_WORK=work_org_token
AZURE_DEVOPS_PAT_CLIENT=client_org_token
```

**Step 2 — Run with `--profile`:**

```bash
python approve_prs.py --profile work    # uses AZURE_DEVOPS_PAT_WORK
python approve_prs.py --profile client  # uses AZURE_DEVOPS_PAT_CLIENT
python approve_prs.py                   # uses AZURE_DEVOPS_PAT (default)
```

> Profile names are case-insensitive. `--profile Work` and `--profile work` both look up `AZURE_DEVOPS_PAT_WORK`.

---

## 🔄 PR Status Behaviour

Before voting, the script fetches each PR's current status and handles it automatically:

| PR Status | What happens |
|---|---|
| `active` | ✅ Proceeds to approve |
| `completed` | ⏭️ Skipped — `SKIPPED (PR is completed)` |
| `abandoned` | ⏭️ Skipped — `SKIPPED (PR is abandoned)` |
| Already approved by you | ⏭️ Skipped — `ALREADY APPROVED` |

No double-voting, no errors on closed PRs.

---

## 🔗 URL Format

The script accepts standard Azure DevOps PR URLs in this exact format:

```
https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
```

| Segment | Example |
|---|---|
| `org` | `contoso` |
| `project` | `my-project` |
| `repo` | `backend-api` |
| `id` | `1042` |

Full example:
```
https://dev.azure.com/contoso/my-project/_git/backend-api/pullrequest/1042
```

> URLs that don't match this pattern are automatically skipped with a warning.

---

## 🗳️ Vote Reference

The script currently sets vote = **`10` (Approved)**. For reference, ADO vote values are:

| Value | Meaning |
|---|---|
| `10` | ✅ Approved |
| `5` | 💬 Approved with suggestions |
| `0` | — No vote (reset) |
| `-5` | ⏳ Waiting for author |
| `-10` | ❌ Rejected |

To change the vote, edit `VOTE_APPROVED` at the top of `approve_prs.py`.

---

## 🛠️ Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `.env file not found` | `.env` doesn't exist | Run `Copy-Item .env.example .env` and fill in your PAT |
| `AZURE_DEVOPS_PAT is not set` | PAT placeholder wasn't replaced | Open `.env` and paste your real token |
| `AZURE_DEVOPS_PAT_WORK is not set` | Named profile key missing | Add `AZURE_DEVOPS_PAT_WORK=...` to your `.env` |
| `HTTP 401 — PAT may be expired` | PAT is invalid or expired | Regenerate your PAT with **Code → Read & Write** scope |
| `HTTP 403 Forbidden` | You don't have reviewer rights | Ask the repo admin to add you as a reviewer |
| `HTTP 404 Not Found` | Wrong org/project/repo/PR ID in URL | Double-check the URL is copied correctly |
| `Unrecognised URL format` | URL doesn't match the expected pattern | Ensure it's a `dev.azure.com` PR link, not a work item or branch link |
| `SKIPPED (PR is completed)` | PR was already merged | Nothing to do — PR is closed |
| Clipboard URLs not detected | `pyperclip` can't access clipboard | Try running in a terminal with clipboard access, or use `--file` instead |

---

## 📝 Changelog

### 2026-04-28 — v3: File input, Clipboard, Multi-Profile, PR Status check

| Feature | Details |
|---|---|
| `--file` / `-f` flag | Load URLs from a `.txt` file — one per line, `#` lines are comments. Great for recurring sprint batches. |
| `--profile` / `-p` flag | Use a named PAT profile. Add `AZURE_DEVOPS_PAT_{NAME}` to `.env` and pass `--profile name`. |
| Clipboard auto-read | At startup, scans clipboard for ADO PR URLs. Press blank Enter to load them. Toggle with `CLIPBOARD_AUTO_READ` at top of script. |
| PR status check | Fetches PR status before voting. `completed` and `abandoned` PRs are skipped automatically. |
| Author column | Results table now shows the PR creator's display name. |
| Token expiry hint | `401` auth errors now print `— PAT may be expired or missing Code scope.` |

### 2026-04-28 — v2: Confirmation, Deduplication, Titles, Already-Approved

| Feature | Details |
|---|---|
| Confirmation prompt | Shows list of parsed PRs and asks `Approve all? [y/N]` before any API call. |
| Duplicate deduplication | Same URL pasted twice → second silently skipped. |
| PR title in results | Fetches actual PR title from ADO and shows in summary table. |
| Already-approved detection | If you've already approved, shows `ALREADY APPROVED` instead of re-voting. |

### 2026-04-27 — v1: Initial Release

- Bulk approve via interactive prompt
- PAT auth via `.env`
- Rich colour-coded summary table

---

> Built with Python · `requests` · `python-dotenv` · `rich`
