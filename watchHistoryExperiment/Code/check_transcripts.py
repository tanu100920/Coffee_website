"""
Check transcript availability for kid video IDs from both profiles.

Run:
    cd C:/Users/tanuc/Downloads
    py check_transcripts.py
"""
import csv, sys, time
sys.stdout.reconfigure(encoding='utf-8')

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("Installing youtube_transcript_api...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'youtube-transcript-api'], check=True)
    from youtube_transcript_api import YouTubeTranscriptApi

def check_transcript(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        # Try English first, then any language
        try:
            t = transcripts.find_transcript(['en'])
            return 'en', len(t.fetch())
        except:
            pass
        # Try any available
        for t in transcripts:
            try:
                fetched = t.fetch()
                return t.language_code, len(fetched)
            except:
                continue
        return None, 0
    except Exception as e:
        return None, 0

results = {}

for label, path in [
    ('profile1', r'C:/Users/tanuc/Downloads/kid_videos_profile1.csv'),
    ('profile2', r'C:/Users/tanuc/Downloads/kid_videos_profile2.csv'),
]:
    print(f'\n=== {label} ===')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    ok, failed = [], []
    for i, row in enumerate(rows, 1):
        vid = row['video_id']
        lang, count = check_transcript(vid)
        status = 'OK' if lang else 'FAIL'
        if lang:
            ok.append({**row, 'lang': lang, 'segments': count})
            print(f'  [{i:3}/100] OK  ({lang}, {count} seg) | {row["title"][:50]}')
        else:
            failed.append(row)
            print(f'  [{i:3}/100] FAIL              | {row["title"][:50]}')
        time.sleep(0.3)

    print(f'\n{label} summary: {len(ok)} OK / {len(failed)} failed out of 100')
    results[label] = {'ok': ok, 'failed': failed}

    # Save OK videos
    out = path.replace('.csv', '_with_transcripts.csv')
    if ok:
        with open(out, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(ok[0].keys()))
            writer.writeheader()
            writer.writerows(ok)
        print(f'Saved: {out}')

print('\n=== FINAL SUMMARY ===')
for label, r in results.items():
    print(f'{label}: {len(r["ok"])}/100 have transcripts')
