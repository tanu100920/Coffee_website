"""
From the usable kid videos, find the 100 most recent ones that have transcripts.

Run:
    cd C:/Users/tanuc/Downloads
    py get_100_with_transcripts.py
"""
import csv, sys, time
sys.stdout.reconfigure(encoding='utf-8')

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'youtube-transcript-api'], check=True)
    from youtube_transcript_api import YouTubeTranscriptApi

def check_transcript(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = transcripts.find_transcript(['en'])
            return 'en', t.fetch()
        except:
            pass
        for t in transcripts:
            try:
                return t.language_code, t.fetch()
            except:
                continue
        return None, None
    except:
        return None, None

for label, path in [
    ('profile1', r'C:/Users/tanuc/Downloads/kid_videos_profile1_usable.csv'),
    ('profile2', r'C:/Users/tanuc/Downloads/kid_videos_profile2_usable.csv'),
]:
    print(f'\n=== {label} ===')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    found, checked = [], 0
    for row in rows:
        if len(found) >= 100:
            break
        checked += 1
        lang, transcript = check_transcript(row['video_id'])
        if lang:
            found.append({**row, 'lang': lang})
            print(f'  [{checked:3} checked | {len(found):3} found] OK  ({lang}) | {row["title"][:55]}')
        else:
            print(f'  [{checked:3} checked | {len(found):3} found] FAIL     | {row["title"][:55]}')
        time.sleep(0.3)

    print(f'\n{label}: checked {checked} videos, found {len(found)} with transcripts')

    out = path.replace('_usable.csv', '_train100.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(found[0].keys()))
        w.writeheader()
        w.writerows(found)
    print(f'Saved: {out}')
