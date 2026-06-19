"""
Fetch transcripts and rate recommended videos for the 6 new profile conditions.

Conditions:
  profile1 (female-leaning) x male seed
  profile1 (female-leaning) x female seed
  profile1 (female-leaning) x neutral seed
  profile2 (male-leaning)   x male seed
  profile2 (male-leaning)   x female seed
  profile2 (male-leaning)   x neutral seed

Run:
    cd C:/Users/tanuc/Downloads
    py fetch_and_rate_new_profiles.py
"""

import os, sys, re, time, csv
import pandas as pd
import anthropic
from youtube_transcript_api import YouTubeTranscriptApi
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(r'C:/Users/tanuc/Downloads/new_profiles_experiment')

CONDITIONS = [
    {'name': 'female_leaning_male_seed',    'recs_csv': BASE / 'condition_female_leaning_male_seed_recommendations.csv'},
    {'name': 'female_leaning_female_seed',  'recs_csv': BASE / 'condition_female_leaning_female_seed_recommendations.csv'},
    {'name': 'female_leaning_neutral_seed', 'recs_csv': BASE / 'condition_female_leaning_neutral_seed_recommendations.csv'},
    {'name': 'male_leaning_male_seed',      'recs_csv': BASE / 'condition_male_leaning_male_seed_recommendations.csv'},
    {'name': 'male_leaning_female_seed',    'recs_csv': BASE / 'condition_male_leaning_female_seed_recommendations.csv'},
    {'name': 'male_leaning_neutral_seed',   'recs_csv': BASE / 'condition_male_leaning_neutral_seed_recommendations.csv'},
]

PNAS_LEXICON = {
    "children_aspirations": {
        "male":   ["doctor","lawyer","judge","pilot","captain","engineer","scientist",
                   "astronaut","professor","politician","soldier","officer","executive"],
        "female": ["nurse","teacher","librarian","secretary","maid","housekeeper",
                   "babysitter","nanny","cleaner","cook","chef","waitress"]
    },
    "career_vs_family": {
        "male":   ["career","profession","salary","promotion","job","work","business",
                   "company","industry","office","employee","boss","manager"],
        "female": ["family","home","housewife","mother","daughter","sister","wife",
                   "domestic","chores","caretaker","childcare","parenting"]
    },
}

SYSTEM_PROMPT = """You are an expert researcher studying occupational gender bias in media.
Rate the occupational gender bias in the transcript on a scale from -2 to +2:
-2 = strongly female-biased occupational portrayals
-1 = mildly female-biased
 0 = balanced / no significant occupational content
+1 = mildly male-biased
+2 = strongly male-biased
Reply with ONLY a single integer: -2, -1, 0, 1, or 2."""

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

def get_lexicon_hits(text):
    hits = []
    text_lower = text.lower()
    for dim, groups in PNAS_LEXICON.items():
        for gender, terms in groups.items():
            for term in terms:
                idx = text_lower.find(term)
                if idx != -1:
                    start = max(0, idx - 160)
                    end   = min(len(text), idx + 160)
                    hits.append(f"[{dim}/{gender}] ...{text[start:end]}...")
    return hits[:20]

def rate_transcript(text, video_id):
    hits = get_lexicon_hits(text)
    hits_str = "\n".join(hits) if hits else "No strong lexicon matches found."
    user_msg = (
        f"Video ID: {video_id}\n\n"
        f"Lexicon hits:\n{hits_str}\n\n"
        f"Transcript excerpt (first 1500 chars):\n{text[:1500]}"
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}]
        )
        raw = resp.content[0].text.strip()
        m = re.search(r'-?\d', raw)
        score = int(m.group()) if m else 0
        return max(-2, min(2, score))
    except Exception as e:
        print(f"  Error rating {video_id}: {e}")
        return None

def fetch_transcript(vid):
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(vid)
        text = " ".join(s.text for s in fetched)
        return text if len(text.strip()) >= 50 else None
    except Exception:
        return None

def process_condition(cond):
    name = cond['name']
    recs_csv = cond['recs_csv']
    transcripts_csv = BASE / f'{name}_transcripts.csv'
    ratings_csv     = BASE / f'{name}_ratings.csv'

    print(f"\n{'='*60}")
    print(f"Processing: {name}")
    print(f"{'='*60}")

    if not Path(recs_csv).exists():
        print(f"  Recs file not found: {recs_csv}")
        return None

    recs = pd.read_csv(recs_csv)
    video_ids = recs['recommended_video_id'].unique().tolist()
    print(f"Unique videos: {len(video_ids)}")

    # ── Fetch transcripts ─────────────────────────────────────────────
    done_fetch = set()
    if transcripts_csv.exists():
        done_df = pd.read_csv(transcripts_csv)
        done_fetch = set(done_df[done_df['status'] == 'ok']['video_id'].tolist())
        print(f"Already fetched OK: {len(done_fetch)}, remaining: {len(video_ids)-len(done_fetch)}")
    else:
        with open(transcripts_csv, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['video_id', 'transcript', 'status'])

    t_file = open(transcripts_csv, 'a', newline='', encoding='utf-8')
    t_writer = csv.writer(t_file)

    ok, fail = 0, 0
    for vid in video_ids:
        if vid in done_fetch:
            continue
        text = fetch_transcript(vid)
        if text:
            t_writer.writerow([vid, text, 'ok'])
            ok += 1
        else:
            t_writer.writerow([vid, '', 'failed'])
            fail += 1
        t_file.flush()
        time.sleep(0.3)
    t_file.close()
    print(f"Fetch: {ok+len(done_fetch)} ok, {fail} failed")

    # ── Rate with Claude ──────────────────────────────────────────────
    transcripts = pd.read_csv(transcripts_csv)
    usable = transcripts[transcripts['status'] == 'ok']
    print(f"Transcripts to rate: {len(usable)}")

    done_rate = set()
    if ratings_csv.exists():
        done_rate = set(pd.read_csv(ratings_csv)['video_id'].tolist())
        print(f"Already rated: {len(done_rate)}, remaining: {len(usable)-len(done_rate)}")
    else:
        with open(ratings_csv, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['video_id', 'claude_occupational'])

    r_file = open(ratings_csv, 'a', newline='', encoding='utf-8')
    r_writer = csv.writer(r_file)

    rated = 0
    for _, row in usable.iterrows():
        vid = str(row['video_id'])
        if vid in done_rate:
            continue
        score = rate_transcript(str(row['transcript']), vid)
        if score is not None:
            r_writer.writerow([vid, score])
            r_file.flush()
            done_rate.add(vid)
            rated += 1
            if rated % 5 == 0:
                print(f"  Rated {rated}...")
        time.sleep(0.3)
    r_file.close()

    # ── Summary ───────────────────────────────────────────────────────
    df = pd.read_csv(ratings_csv)
    n = len(df)
    if n > 0:
        male_pct    = 100*len(df[df['claude_occupational']>0])/n
        female_pct  = 100*len(df[df['claude_occupational']<0])/n
        neutral_pct = 100*len(df[df['claude_occupational']==0])/n
        mean_bias   = df['claude_occupational'].mean()
        print(f"\n  n={n} | Male: {male_pct:.1f}% | Female: {female_pct:.1f}% | Neutral: {neutral_pct:.1f}% | Mean: {mean_bias:+.2f}")
    else:
        print(f"\n  n=0 (no transcripts found)")
    return df

# ── Run all 6 conditions ─────────────────────────────────────────────────────
results = {}
for cond in CONDITIONS:
    results[cond['name']] = process_condition(cond)

print("\n" + "="*60)
print("FINAL SUMMARY")
print("="*60)
print(f"{'Condition':<35} | {'n':>4} | {'Male%':>6} | {'Female%':>7} | {'Neutral%':>8} | {'Mean':>6}")
print("-"*80)
for name, df in results.items():
    if df is not None and len(df) > 0:
        n = len(df)
        print(f"{name:<35} | {n:>4} | "
              f"{100*len(df[df['claude_occupational']>0])/n:>5.1f}% | "
              f"{100*len(df[df['claude_occupational']<0])/n:>6.1f}% | "
              f"{100*len(df[df['claude_occupational']==0])/n:>7.1f}% | "
              f"{df['claude_occupational'].mean():>+.2f}")
    else:
        print(f"{name:<35} | {'---':>4}")
