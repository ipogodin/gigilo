# GitHub Contribution Date Display

Displays the current date (MM/DD/YYYY) on the GitHub contribution graph using pixel art.

Two repos work together:
- **`gigilo-history`** — Static repo with word art on years 2013-2024. Push once, never changes.
- **`gigilo-date`** — Recreated fresh every night. Shows today's date on the current year view.

GitHub counts contributions across all repos, so both appear on the same profile.

---

## Mac Setup Guide (from scratch)

### 1. Install prerequisites

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install GitHub CLI
brew install gh

# Authenticate (select GitHub.com, SSH, authorize in browser)
gh auth login

# Grant repo deletion permission (needed for daily date refresh)
gh auth refresh -h github.com -s delete_repo

# Verify
gh auth status
```

### 2. Clone this repo

```bash
cd ~
git clone git@github.com:ipogodin/gigilo.git
cd gigilo
```

### 3. Configure git identity

```bash
git config --global user.email "$(gh api user -q .email)"
git config --global user.name "$(gh api user -q .login)"
```

### 4. Set up the history repo (one time only)

This generates word art commits for 2013-2024 and pushes to `gigilo-history`. Takes ~15 minutes.

```bash
python3 setup_history.py
gh repo create gigilo-history --public --source=. --push
```

Verify: go to your GitHub profile, click year tabs 2013-2024. Words should appear within 24 hours.

### 5. Test the daily date display

```bash
# Preview tomorrow's date
python3 daily.py preview

# Preview today's date
python3 daily.py preview --today

# Run the full cycle for today (prepare + push)
python3 daily.py now
```

Verify: check your GitHub profile's current year contribution graph.

### 6. Set up the daily cron job

Create the cron scripts:

```bash
# Prepare script (runs at 23:50 — generates tomorrow's commits locally)
cat << 'SCRIPT' > ~/gigilo-prepare.sh
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
cd ~/gigilo
python3 daily.py prepare >> /tmp/gigilo-cron.log 2>&1
SCRIPT
chmod +x ~/gigilo-prepare.sh

# Push script (runs at 00:01 — deletes old repo, creates new, pushes)
cat << 'SCRIPT' > ~/gigilo-push.sh
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
cd ~/gigilo
python3 daily.py push >> /tmp/gigilo-cron.log 2>&1
SCRIPT
chmod +x ~/gigilo-push.sh
```

Add both cron jobs:

```bash
(crontab -l 2>/dev/null | grep -v gigilo; echo "50 23 * * * \$HOME/gigilo-prepare.sh"; echo "1 0 * * * \$HOME/gigilo-push.sh") | crontab -
```

### 7. Verify cron

```bash
# Check cron is registered
crontab -l

# Expected output:
# 50 23 * * * $HOME/gigilo-prepare.sh
# 1 0 * * * $HOME/gigilo-push.sh

# After the first run, check logs:
cat /tmp/gigilo-cron.log
```

---

## How it works

### Daily cycle

| Time | What happens |
|------|-------------|
| **23:50** | `daily.py prepare` — calculates tomorrow's date, generates ~2,000 commits in a local staging directory (`.date-staging/`) |
| **00:01** | `daily.py push` — deletes `gigilo-date` on GitHub, creates it fresh, pushes the pre-built commits |

The push is a clean first push to a brand-new repo, so GitHub indexes it immediately.

### Why two repos?

- `gigilo-history` is static — 2013-2024 word art never changes, so it's pushed once
- `gigilo-date` is recreated daily — avoids ghost data, force push issues, and GitHub caching problems
- GitHub counts contributions across all repos, so both show on the same profile

### File overview

| File | Purpose |
|------|---------|
| `daily.py` | Daily date display — prepare commits + push to GitHub |
| `setup_history.py` | One-time setup — generate 2013-2024 word art |
| `contributions.txt` | Scratch file for commit content |

---

## Commands

```bash
python3 daily.py prepare      # Generate tomorrow's date locally (run at 23:50)
python3 daily.py push          # Delete old repo, create new, push (run at 00:01)
python3 daily.py now           # Do both for today's date (manual/test)
python3 daily.py preview       # ASCII preview of tomorrow's date
python3 daily.py preview --today  # ASCII preview of today's date
python3 setup_history.py       # One-time: generate 2013-2024 history
```

## Configuration

Edit the top of `daily.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEZONE` | UTC-7 (PDT) | Display timezone. Change to UTC-8 for PST. |
| `COMMITS_PER_PIXEL` | 15 | Commits per "on" pixel. Increase if ghost data visible. |
| `BG_COMMITS` | 2 | Background commits per day (light green). |
| `REPO_NAME` | `gigilo-date` | Name of the daily repo on GitHub. |
| `GITHUB_USER` | `ipogodin` | GitHub username. |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Date not showing | GitHub may take minutes to index. Wait and refresh. |
| `gh repo delete` fails | Run `gh auth refresh -h github.com -s delete_repo` |
| Cron not running | Check `crontab -l` and `/tmp/gigilo-cron.log` |
| `gh` not found in cron | Verify PATH in the shell scripts includes `gh` location |
| History words missing | Run `setup_history.py` and push to `gigilo-history` |
| Wrong date shown | Check `TIMEZONE` in `daily.py` matches your target timezone |
