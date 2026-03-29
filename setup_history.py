#!/usr/bin/env python3
"""
Generate static history repo with word art for 2013-2024.
Run once, push once, never touch again.
"""

import subprocess
import os
from datetime import date, timedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Pixel font ────────────────────────────────────────────────────────
FONT = {
    'A': ['.##.', '#..#', '####', '#..#', '#..#'],
    'B': ['###.', '#..#', '###.', '#..#', '###.'],
    'C': ['.###', '#...', '#...', '#...', '.###'],
    'D': ['##..', '#.#.', '#..#', '#.#.', '##..'],
    'E': ['###', '#..', '##.', '#..', '###'],
    'F': ['###', '#..', '##.', '#..', '#..'],
    'G': ['.##.', '#...', '#.##', '#..#', '.##.'],
    'H': ['#..#', '#..#', '####', '#..#', '#..#'],
    'I': ['###', '.#.', '.#.', '.#.', '###'],
    'J': ['.###', '..#.', '..#.', '#.#.', '.#..'],
    'K': ['#..#', '#.#.', '##..', '#.#.', '#..#'],
    'L': ['#..', '#..', '#..', '#..', '###'],
    'M': ['#...#', '##.##', '#.#.#', '#...#', '#...#'],
    'N': ['#..#', '##.#', '#.##', '#..#', '#..#'],
    'O': ['.##.', '#..#', '#..#', '#..#', '.##.'],
    'P': ['###.', '#..#', '###.', '#...', '#...'],
    'R': ['###.', '#..#', '###.', '#.#.', '#..#'],
    'S': ['.##', '#..', '.#.', '..#', '##.'],
    'T': ['#####', '..#..', '..#..', '..#..', '..#..'],
    'U': ['#..#', '#..#', '#..#', '#..#', '.##.'],
    'V': ['#..#', '#..#', '#..#', '.##.', '..#.'],
    'W': ['#...#', '#...#', '#.#.#', '##.##', '#...#'],
    ' ': ['..', '..', '..', '..', '..'],
}

YEAR_WORDS = {
    2013: 'I LOVE DICKS',
    2014: 'WAR',
    2015: 'POLAND',
    2016: 'USA',
    2017: 'LEETCODE',
    2018: 'NEW JOB',
    2019: 'COVID',
    2020: 'WFH',
    2021: 'HOUSE',
    2022: 'BIG WAR',
    2023: 'REUNITE',
    2024: 'WAKESURF',
}

BG_COMMITS = 2
FG_COMMITS = 10


def text_to_bitmap(text):
    rows = [''] * 5
    for i, ch in enumerate(text):
        glyph = FONT.get(ch, FONT[' '])
        for r in range(5):
            if i > 0:
                rows[r] += '.'
            rows[r] += glyph[r]
    return rows


def github_weekday(d):
    return (d.weekday() + 1) % 7


def year_grid(year):
    jan1 = date(year, 1, 1)
    dec31 = date(year, 12, 31)
    start_weekday = github_weekday(jan1)
    total_days = (dec31 - jan1).days + 1

    grid_to_date = {}
    for day_offset in range(total_days):
        d = jan1 + timedelta(days=day_offset)
        pos = start_weekday + day_offset
        grid_to_date[(pos // 7, pos % 7)] = d

    total_cols = max(c for c, r in grid_to_date.keys()) + 1
    targets = {d.isoformat(): BG_COMMITS for d in grid_to_date.values()}

    if year in YEAR_WORDS:
        bitmap = text_to_bitmap(YEAR_WORDS[year])
        text_width = len(bitmap[0])
        col_offset = (total_cols - text_width) // 2
        row_offset = 1
        for r in range(5):
            for c in range(text_width):
                grid_col = col_offset + c
                grid_row = row_offset + r
                if (grid_col, grid_row) in grid_to_date:
                    d = grid_to_date[(grid_col, grid_row)]
                    if bitmap[r][c] == '#':
                        targets[d.isoformat()] = FG_COMMITS
    return targets


def make_commits(date_str, count):
    env = {**os.environ, 'GIT_AUTHOR_DATE': f'{date_str}T12:00:00', 'GIT_COMMITTER_DATE': f'{date_str}T12:00:00'}
    for i in range(count):
        with open('contributions.txt', 'a') as f:
            f.write(f'{date_str} [{i+1}/{count}]\n')
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'{date_str} [{i+1}/{count}]'], env=env, check=True, capture_output=True)


def main():
    print('=== HISTORY REPO SETUP (2013-2024) ===\n')

    # Reset git
    subprocess.run(['rm', '-rf', '.git'], check=True)
    with open('contributions.txt', 'w') as f:
        f.write('')
    subprocess.run(['git', 'init'], check=True, capture_output=True)
    subprocess.run(['git', 'branch', '-M', 'main'], check=True, capture_output=True)

    for year in range(2013, 2025):
        word = YEAR_WORDS.get(year, '')
        print(f'{year}: "{word}"')
        targets = year_grid(year)
        days_done = 0
        for date_str, target in sorted(targets.items()):
            make_commits(date_str, target)
            days_done += 1
            if days_done % 60 == 0:
                print(f'  {days_done}/{len(targets)} days')
        print(f'  Done: {len(targets)} days')

    total = subprocess.run(['git', 'log', '--oneline'], capture_output=True, text=True)
    total_commits = len(total.stdout.strip().split('\n'))
    print(f'\nHistory complete! {total_commits} commits.')
    print('Now create repo and push:')
    print('  gh repo create gigilo-history --public --source=. --push')


if __name__ == '__main__':
    main()
