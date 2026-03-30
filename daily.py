#!/usr/bin/env python3
"""
GitHub Contribution Date Display — Daily Script

Two-phase operation:
  python3 daily.py prepare              # Generates tomorrow's date repo locally
  python3 daily.py push                 # Pushes to GitHub (deletes old, creates new)
  python3 daily.py now                  # Prepare + push for today's date
  python3 daily.py preview              # ASCII preview of tomorrow's date
  python3 daily.py preview --today      # ASCII preview of today's date

Custom date (DD/MM/YYYY, today, tomorrow, yesterday):
  python3 daily.py prepare 20/03/2026   # Prepare a specific date
  python3 daily.py now yesterday        # Prepare + push yesterday's date
  python3 daily.py preview 04/07/2026   # Preview a specific date
"""

import subprocess
import os
import sys
import shutil
from datetime import datetime, timedelta, date, timezone

# ── Configuration ──────────────────────────────────────────────────────
TIMEZONE = timezone(timedelta(hours=-7))  # US Pacific (PDT). Change to -8 for PST.
COMMITS_PER_PIXEL = 40    # Must be high enough to outshine organic contributions
BG_COMMITS = 2            # Background: light green
REPO_PREFIX = 'gigilo-'   # Daily repos named gigilo-MMDD (unique name each day to avoid GitHub caching)
GITHUB_USER = 'ipogodin'
WORK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.date-staging')
DATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.date-staging-target')

# ── Digit font (5 rows tall, variable width) ──────────────────────────
FONT = {
    '0': ['.##.', '#..#', '#..#', '#..#', '.##.'],
    '1': ['..#.', '.##.', '..#.', '..#.', '.###'],
    '2': ['.##.', '#..#', '..#.', '.#..', '####'],
    '3': ['###.', '...#', '.##.', '...#', '###.'],
    '4': ['#..#', '#..#', '####', '...#', '...#'],
    '5': ['####', '#...', '###.', '...#', '###.'],
    '6': ['.##.', '#...', '###.', '#..#', '.##.'],
    '7': ['####', '...#', '..#.', '.#..', '.#..'],
    '8': ['.##.', '#..#', '.##.', '#..#', '.##.'],
    '9': ['.##.', '#..#', '.###', '...#', '.##.'],
    '/': ['..#', '.#.', '.#.', '#..', '#..'],
}


def render_date(month, day, year):
    """Render MM/DD/YYYY as a 5-row bitmap."""
    text = f'{month:02d}/{day:02d}/{year:04d}'
    rows = [''] * 5
    for i, ch in enumerate(text):
        glyph = FONT[ch]
        for r in range(5):
            if i > 0:
                rows[r] += '.'
            rows[r] += glyph[r]
    return rows


def get_contribution_grid(target_date):
    """
    Map (col, row) -> date for GitHub's contribution grid.
    """
    github_weekday = (target_date.weekday() + 1) % 7
    this_sunday = target_date - timedelta(days=github_weekday)
    grid_start = this_sunday - timedelta(weeks=52)

    grid = {}
    d = grid_start
    while d <= target_date:
        day_offset = (d - grid_start).days
        grid[(day_offset // 7, day_offset % 7)] = d
        d += timedelta(days=1)
    return grid


def get_date_pixels(month, day, year, target_date):
    """Returns set of dates that should be 'on' for the date display."""
    grid = get_contribution_grid(target_date)
    total_cols = max(c for c, r in grid.keys()) + 1

    bitmap = render_date(month, day, year)
    text_width = len(bitmap[0])
    col_offset = (total_cols - text_width) // 2
    row_offset = 1

    on_dates = set()
    for r in range(5):
        for c in range(text_width):
            if bitmap[r][c] == '#':
                d = grid.get((col_offset + c, row_offset + r))
                if d is not None:
                    on_dates.add(d)
    return on_dates


def make_commit(date_str, label, env):
    """Append to file and commit."""
    with open(os.path.join(WORK_DIR, 'contributions.txt'), 'a') as f:
        f.write(f'{date_str} {label}\n')
    subprocess.run(['git', 'add', '.'], check=True, capture_output=True, cwd=WORK_DIR)
    subprocess.run(
        ['git', 'commit', '-m', f'{date_str} {label}'],
        env=env, check=True, capture_output=True, cwd=WORK_DIR,
    )


def prepare(target_date):
    """Phase 1: Generate all commits locally for the target date."""
    month, day, year = target_date.month, target_date.day, target_date.year
    print(f'Preparing {month:02d}/{day:02d}/{year}...')

    # Clean staging area
    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR)

    # Init fresh repo
    subprocess.run(['git', 'init'], check=True, capture_output=True, cwd=WORK_DIR)
    subprocess.run(['git', 'branch', '-M', 'main'], check=True, capture_output=True, cwd=WORK_DIR)
    with open(os.path.join(WORK_DIR, 'contributions.txt'), 'w') as f:
        f.write('')

    # Calculate grid and pixels
    grid = get_contribution_grid(target_date)
    on_dates = get_date_pixels(month, day, year, target_date)
    all_dates = sorted(set(grid.values()))

    total_commits = 0
    for i, d in enumerate(all_dates):
        date_str = d.isoformat()
        env = {
            **os.environ,
            'GIT_AUTHOR_DATE': f'{date_str}T12:00:00',
            'GIT_COMMITTER_DATE': f'{date_str}T12:00:00',
        }

        if d in on_dates:
            count = BG_COMMITS + COMMITS_PER_PIXEL
        else:
            count = BG_COMMITS

        for c in range(count):
            make_commit(date_str, f'[{c+1}/{count}]', env)
        total_commits += count

        pct = (i + 1) * 100 // len(all_dates)
        bar = '█' * (pct // 2) + '░' * (50 - pct // 2)
        print(f'\r  [{bar}] {pct}% ({i+1}/{len(all_dates)} days)', end='', flush=True)

    print()  # newline after progress bar

    # Save target date so push() knows the repo name
    with open(DATE_FILE, 'w') as f:
        f.write(target_date.isoformat())

    print(f'  Prepared: {len(all_dates)} days, {total_commits} commits')
    return total_commits


def get_repo_name(target_date):
    """Generate unique repo name for a given date: gigilo-MMDD"""
    return f'{REPO_PREFIX}{target_date.month:02d}{target_date.day:02d}'


def delete_old_repos():
    """Delete all old gigilo-MMDD repos from GitHub."""
    result = subprocess.run(
        ['gh', 'repo', 'list', GITHUB_USER, '--limit', '200', '--json', 'name', '-q', '.[].name'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return
    for name in result.stdout.strip().split('\n'):
        if name.startswith(REPO_PREFIX) and name != 'gigilo-history':
            print(f'  Deleting old repo: {name}')
            subprocess.run(
                ['gh', 'repo', 'delete', f'{GITHUB_USER}/{name}', '--yes'],
                capture_output=True,
            )


def push():
    """Phase 2: Delete old repos on GitHub, create new one with unique name, push."""
    print(f'Pushing to GitHub...')

    if not os.path.exists(os.path.join(WORK_DIR, '.git')):
        print('ERROR: No prepared repo found. Run "daily.py prepare" first.')
        sys.exit(1)

    # Read target date to determine repo name
    if not os.path.exists(DATE_FILE):
        print('ERROR: No target date found. Run "daily.py prepare" first.')
        sys.exit(1)
    with open(DATE_FILE) as f:
        target_date = date.fromisoformat(f.read().strip())
    repo_name = get_repo_name(target_date)

    # Delete all old gigilo-* repos
    delete_old_repos()

    # Create new repo with unique name and push
    result = subprocess.run(
        ['gh', 'repo', 'create', repo_name, '--public'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f'  Create failed: {result.stderr}')
        sys.exit(1)

    # Add remote and push
    subprocess.run(
        ['git', 'remote', 'add', 'origin', f'git@github.com:{GITHUB_USER}/{repo_name}.git'],
        capture_output=True, cwd=WORK_DIR,
    )
    result = subprocess.run(
        ['git', 'push', '-u', 'origin', 'main'],
        capture_output=True, text=True, cwd=WORK_DIR,
        timeout=600,
    )
    if result.returncode == 0:
        print(f'  Done! Pushed to {GITHUB_USER}/{repo_name}')
    else:
        print(f'  Push failed: {result.stderr}')
        sys.exit(1)


def preview(target_date):
    """Show ASCII preview of the date display."""
    month, day, year = target_date.month, target_date.day, target_date.year
    grid = get_contribution_grid(target_date)
    total_cols = max(c for c, r in grid.keys()) + 1
    on_dates = get_date_pixels(month, day, year, target_date)

    print(f'\nDate preview: {month:02d}/{day:02d}/{year}')
    print('─' * (total_cols + 4))
    for row in range(7):
        line = '  '
        for col in range(total_cols):
            d = grid.get((col, row))
            if d is None:
                line += ' '
            elif d in on_dates:
                line += '█'
            else:
                line += '░'
        print(line)
    print('─' * (total_cols + 4))
    print(f'  Pixels: {len(on_dates)}')


def parse_date(s):
    """Parse date from 'today', 'tomorrow', 'yesterday', or DD/MM/YYYY."""
    now = datetime.now(TIMEZONE)
    s = s.lower().strip()
    if s == 'today':
        return now.date()
    if s == 'tomorrow':
        return (now + timedelta(days=1)).date()
    if s == 'yesterday':
        return (now - timedelta(days=1)).date()
    try:
        return datetime.strptime(s, '%d/%m/%Y').date()
    except ValueError:
        print(f'Invalid date: {s}  (use DD/MM/YYYY, today, tomorrow, or yesterday)')
        sys.exit(1)


def main():
    now = datetime.now(TIMEZONE)
    tomorrow = (now + timedelta(days=1)).date()
    today = now.date()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    # Optional date argument (last arg): DD/MM/YYYY, today, tomorrow, yesterday
    custom_date = None
    if len(sys.argv) >= 3 and sys.argv[-1] not in ('--today',):
        custom_date = parse_date(sys.argv[-1])

    if cmd == 'prepare':
        prepare(custom_date or tomorrow)
    elif cmd == 'push':
        push()
    elif cmd == 'now':
        prepare(custom_date or today)
        push()
    elif cmd == 'preview':
        if custom_date:
            target = custom_date
        else:
            target = today if '--today' in sys.argv else tomorrow
        preview(target)
    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
