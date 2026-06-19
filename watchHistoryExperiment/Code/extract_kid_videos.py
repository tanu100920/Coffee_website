"""
Extract the last 100 video IDs watched by the kid from YouTube watch history.

Strategy:
- Combines both watch-history files
- Filters using kid-content keywords (titles + channels)
- Excludes clear parent/adult content
- Returns 100 most recent kid video IDs

Run:
    cd C:/Users/tanuc/Downloads
    py extract_kid_videos.py
"""

import json, re, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# ── Load both files ─────────────────────────────────────────────────────────
files = [
    r"C:/Users/tanuc/Downloads/watch-history.json",
    r"C:/Users/tanuc/Downloads/watch-history (1).json",
]
all_entries = []
for path in files:
    with open(path, encoding='utf-8') as f:
        all_entries.extend(json.load(f))

# Sort by time descending (newest first)
all_entries.sort(key=lambda x: x.get('time', ''), reverse=True)
print(f"Total entries across both files: {len(all_entries)}")

# ── Keyword lists ────────────────────────────────────────────────────────────
KIDS_TITLE_KW = [
    # Platforms/games kids use
    'roblox', 'minecraft', 'pokemon', 'lego', 'among us', 'fortnite',
    # Cartoons / animated shows
    'cartoon', 'animation', 'animated', 'anime', 'sonic', 'spiderman',
    'spider-man', 'teen titans', 'batman', 'superhero', 'avengers', 'ironman',
    'peppa', 'bluey', 'cocomelon', 'paw patrol', 'frozen', 'elsa', 'moana',
    'toy story', 'finding nemo', 'encanto', 'minions', 'despicable',
    # Toys / kids products
    'toy', 'doll', 'barbie', 'princess', 'hot wheels', 'playdoh', 'play doh',
    'unboxing', 'slime', 'fidget',
    # Kids content descriptors
    'kids choice', 'for kids', 'children', 'nursery rhyme', 'abc song',
    'learn colors', 'learn numbers', 'kindergarten',
    # Family/child-friendly shorts often tagged
    '#roblox', '#animation', '#cartoon', '#sonic', '#minecraft', '#lego',
    '#kids', '#pokemon', '#spiderman',
]

KIDS_CHANNEL_KW = [
    'roblox', 'cartoon', 'animation', 'kids', 'children', 'nursery',
    'toy', 'sonic', 'pokemon', 'minecraft', 'lego', 'bluey', 'peppa',
    'cocomelon', 'paw patrol', 'disney junior', 'nickelodeon',
]

# Adult content — if title strongly matches these, skip even if kids kw also matches
ADULT_TITLE_KW = [
    'trump', 'iran', 'invest in', 'stock market', 'prompt engineering',
    'chanakya dialogue', 'malala', 'modi', 'pakistan', 'israel', 'arnab',
    'skincare product', 'instamart', 'platinumrx', 'google ads',
    'from google ads',  # ad entries
    'ai अनुवाद', 'भाषा कौशल',
]

def extract_video_id(url):
    if not url:
        return None
    m = re.search(r'[?&]v=([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else None

def is_ad(entry):
    details = entry.get('details', [])
    return any('google ads' in d.get('name','').lower() for d in details)

def is_kids(entry):
    if is_ad(entry):
        return False

    title = entry.get('title', '').lower()
    channel = ' '.join(
        s.get('name', '') for s in entry.get('subtitles', [])
    ).lower()

    # Exclude strong adult matches
    if any(kw in title for kw in ADULT_TITLE_KW):
        return False

    # Match kids keywords in title or channel
    if any(kw in title for kw in KIDS_TITLE_KW):
        return True
    if any(kw in channel for kw in KIDS_CHANNEL_KW):
        return True

    return False

# ── Filter and collect ───────────────────────────────────────────────────────
kid_videos = []
seen_ids = set()

for entry in all_entries:
    if not is_kids(entry):
        continue
    vid_id = extract_video_id(entry.get('titleUrl', ''))
    if not vid_id or vid_id in seen_ids:
        continue
    seen_ids.add(vid_id)
    kid_videos.append({
        'video_id': vid_id,
        'title': entry.get('title', '').replace('Watched ', '', 1),
        'channel': entry.get('subtitles', [{}])[0].get('name', '') if entry.get('subtitles') else '',
        'time': entry.get('time', ''),
        'url': f"https://www.youtube.com/watch?v={vid_id}",
    })
    if len(kid_videos) >= 100:
        break

print(f"\nKid videos found (deduped, newest first): {len(kid_videos)}")
print("\n=== Last 100 Kid Video IDs ===")
for i, v in enumerate(kid_videos, 1):
    print(f"{i:3}. {v['video_id']}  | {v['time'][:10]} | {v['channel'][:30]:<30} | {v['title'][:55]}")

# Save to CSV
import csv
out_path = r"C:/Users/tanuc/Downloads/kid_video_ids.csv"
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['video_id','title','channel','time','url'])
    writer.writeheader()
    writer.writerows(kid_videos)

print(f"\nSaved to: {out_path}")

# Print just the IDs for easy copy-paste
print("\n=== Video IDs only ===")
print('\n'.join(v['video_id'] for v in kid_videos))
