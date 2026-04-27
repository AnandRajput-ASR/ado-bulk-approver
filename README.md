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
- [URL Format](#-url-format)
- [Vote Reference](#-vote-reference)
- [Troubleshooting](#-troubleshooting)
- [Changelog](#-changelog)

---

## 🚀 What It Does

Paste one or more Azure DevOps PR URLs interactively at the terminal prompt — the script will:

1. Parse every URL to extract the **org / project / repo / PR ID**
2. Authenticate as **you** using your Personal Access Token
3. Resolve your reviewer identity (once per unique org)
4. `PUT` an **Approved** vote (`10`) on every PR via the ADO REST API
5. Print a colour-coded summary table showing **APPROVED / FAILED / SKIPPED** for each PR

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
AZURE_DEVOPS_PAT=your_actual_token_here
```

> ⚠️ **Never commit `.env` to version control.** Add it to `.gitignore`.

---

## ▶️ Usage

```bash
python approve_prs.py
```

You'll see an interactive prompt:

```
╭─────────────────────────────────────────────────╮
│ Azure DevOps PR Approver                        │
│                                                 │
│ Paste PR URLs one per line.                     │
│ Leave a blank line and press Enter when done.   │
╰─────────────────────────────────────────────────╯
  PR URL: https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/101
  PR URL: https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/102
  PR URL: https://dev.azure.com/otherorg/proj/_git/repo/pullrequest/55
  PR URL:              ← blank line → press Enter to submit
```

**Result table:**

```
╭────────────────────────────────┬──────────┬────────╮
│ Pull Request                   │ Status   │ Detail │
├────────────────────────────────┼──────────┼────────┤
│ myorg/myproject → PR #101      │ APPROVED │        │
│ myorg/myproject → PR #102      │ APPROVED │        │
│ otherorg/proj → PR #55         │ APPROVED │        │
╰────────────────────────────────┴──────────┴────────╯

Done.  Approved: 3  Failed: 0  Skipped: 0
```

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
| `HTTP 401 Unauthorized` | PAT is invalid or expired | Regenerate your PAT with **Code → Read & Write** scope |
| `HTTP 403 Forbidden` | You don't have reviewer rights | Ask the repo admin to add you as a reviewer |
| `HTTP 404 Not Found` | Wrong org/project/repo/PR ID in URL | Double-check the URL is copied correctly |
| `Unrecognised URL format` | URL doesn't match the expected pattern | Ensure it's a `dev.azure.com` PR link, not a work item or branch link |

---

## 📝 Changelog

| Date | Change |
|---|---|
| 2026-04-27 | Initial version — bulk approve via interactive prompt, PAT auth, rich summary table |

---

> Built with Python · `requests` · `python-dotenv` · `rich`
