"""
Scrape YouTube recommendations for 2 new real child profiles across 3 seeds.

Seeds (same as existing experiment):
  Male   : BNGjKDFAGTA
  Female : 18Fi6pNN8h4
  Neutral: YdiWTYkY1uY

Profiles:
  profile1 (female-leaning) — Chrome on port 9222
  profile2 (male-leaning)   — Chrome on port 9223

BEFORE RUNNING:
  Make sure both Chrome windows are open and signed in:
    Profile 1 (port 9222):
      Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"C:\chrome-debug-profile1`""
    Profile 2 (port 9223):
      Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9223 --user-data-dir=`"C:\chrome-debug-profile2`""

Run:
    cd C:/Users/tanuc/Downloads
    py scrape_new_profiles.py
"""

import csv, sys, time, re, random
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

sys.stdout.reconfigure(encoding='utf-8')

# ── CONFIG ───────────────────────────────────────────────────────────────────
SEEDS = {
    'male'   : 'BNGjKDFAGTA',
    'female' : '18Fi6pNN8h4',
    'neutral': 'YdiWTYkY1uY',
}

PROFILES = {
    'profile1': {'port': 9222, 'label': 'female_leaning'},
    'profile2': {'port': 9223, 'label': 'male_leaning'},
}

N_RUNS     = 10
SCROLL_TIMES = 8
OUTPUT_DIR = Path(r'C:/Users/tanuc/Downloads/new_profiles_experiment')
OUTPUT_DIR.mkdir(exist_ok=True)
# ─────────────────────────────────────────────────────────────────────────────

def get_ids(driver):
    ids = set()
    for script in [
        "return JSON.stringify(window.ytInitialData || null)",
        "return JSON.stringify(window.ytInitialPlayerResponse || null)",
    ]:
        try:
            result = driver.execute_script(script)
            if result and result != "null":
                ids.update(re.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_\-]{11})"', result))
        except:
            pass
    try:
        ids.update(re.findall(r'"videoId"\s*:\s*"([A-Za-z0-9_\-]{11})"', driver.page_source))
    except:
        pass
    try:
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='watch']"):
            href = a.get_attribute("href") or ""
            m = re.search(r'[?&]v=([A-Za-z0-9_\-]{11})', href)
            if m:
                ids.add(m.group(1))
    except:
        pass
    return ids

def scrape_condition(profile_key, seed_key):
    profile = PROFILES[profile_key]
    seed_id = SEEDS[seed_key]
    condition = f"{profile['label']}_{seed_key}_seed"
    output_csv = OUTPUT_DIR / f"condition_{condition}_recommendations.csv"

    # Check already done runs
    done_runs = set()
    if output_csv.exists():
        import pandas as pd
        existing = pd.read_csv(output_csv)
        done_runs = set(existing['run'].unique())
        print(f"  Already done runs: {sorted(done_runs)}")

    # Connect to Chrome
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{profile['port']}")
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        print(f"  ERROR: Could not connect to Chrome on port {profile['port']}: {e}")
        return

    write_header = not output_csv.exists()
    outfile = open(output_csv, 'a', newline='', encoding='utf-8')
    writer = csv.writer(outfile)
    if write_header:
        writer.writerow(['condition', 'profile', 'seed', 'run', 'seed_video_id', 'recommended_video_id'])

    for run in range(1, N_RUNS + 1):
        if run in done_runs:
            print(f"  Run {run}: already done, skipping.")
            continue
        try:
            driver.get("https://www.youtube.com")
            time.sleep(3)

            url = f"https://www.youtube.com/watch?v={seed_id}"
            driver.get(url)
            print(f"  Run {run}: loading seed video...")
            time.sleep(random.uniform(5, 7))

            ids = get_ids(driver)
            for _ in range(SCROLL_TIMES):
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(random.uniform(1.5, 2.5))
                ids.update(get_ids(driver))

            ids.discard(seed_id)
            print(f"  Run {run}: {len(ids)} unique recommended IDs")

            for vid_id in ids:
                writer.writerow([condition, profile_key, seed_key, run, seed_id, vid_id])
            outfile.flush()

        except Exception as e:
            print(f"  Run {run} error: {e}")

        if run < N_RUNS:
            time.sleep(random.uniform(5, 10))

    outfile.close()
    import pandas as pd
    result = pd.read_csv(output_csv)
    print(f"  Done! {result['recommended_video_id'].nunique()} unique videos across {N_RUNS} runs")

# ── Run all 6 conditions ─────────────────────────────────────────────────────
for profile_key in ['profile1', 'profile2']:
    for seed_key in ['male', 'female', 'neutral']:
        condition = f"{PROFILES[profile_key]['label']}_{seed_key}_seed"
        print(f"\n=== {condition} ===")
        scrape_condition(profile_key, seed_key)

print("\n\nAll 6 conditions scraped. Next: fetch transcripts and rate with Claude.")
