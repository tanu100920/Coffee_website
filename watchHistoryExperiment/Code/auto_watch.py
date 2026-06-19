"""
Auto-watch training videos on a YouTube account to train the recommendation algorithm.

BEFORE RUNNING:
1. Kill existing Chrome:
      taskkill /F /IM chrome.exe /T
2. Open Chrome with your account + remote debugging:
      Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222 --user-data-dir=`"C:\chrome-debug-profile1`""
3. Sign into the correct YouTube account in that Chrome window
4. Run this script:
      cd C:/Users/tanuc/Downloads
      py auto_watch.py

Run once for Profile 1 (female account), then repeat for Profile 2 (male account)
changing PROFILE and CSV_PATH below.
"""

import csv, sys, time, random
sys.stdout.reconfigure(encoding='utf-8')

# ── CONFIG — change these per run ───────────────────────────────────────────
PROFILE   = "profile2"
CSV_PATH  = r"C:/Users/tanuc/Downloads/kid_videos_profile2_usable.csv"

WATCH_SECONDS_MIN = 40   # watch at least this many seconds per video
WATCH_SECONDS_MAX = 90   # watch at most this many seconds per video
MAX_VIDEOS        = 30   # stop after watching this many videos
DEBUG_PORT        = 9223
# ────────────────────────────────────────────────────────────────────────────

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'selenium'], check=True)
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

# ── Connect to existing Chrome ───────────────────────────────────────────────
options = Options()
options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
driver = webdriver.Chrome(options=options)
print(f"Connected to Chrome. Current URL: {driver.current_url}")

# ── Load videos ──────────────────────────────────────────────────────────────
with open(CSV_PATH, encoding='utf-8') as f:
    videos = list(csv.DictReader(f))

print(f"\nProfile: {PROFILE}")
print(f"Total videos to watch: {len(videos)}")
print(f"Watch duration per video: {WATCH_SECONDS_MIN}–{WATCH_SECONDS_MAX}s")
print(f"Estimated total time: {len(videos) * (WATCH_SECONDS_MIN + WATCH_SECONDS_MAX) // 2 // 60} minutes\n")

# ── Load progress (resume if interrupted) ───────────────────────────────────
progress_file = f"C:/Users/tanuc/Downloads/auto_watch_{PROFILE}_progress.txt"
try:
    with open(progress_file) as f:
        done_ids = set(f.read().splitlines())
    print(f"Resuming — {len(done_ids)} already watched\n")
except FileNotFoundError:
    done_ids = set()

# ── Watch loop ───────────────────────────────────────────────────────────────
watched, skipped, failed = 0, 0, 0

for i, row in enumerate(videos, 1):
    vid = row['video_id']
    title = row['title'][:60]
    url = row['url']

    if watched >= MAX_VIDEOS:
        break

    if vid in done_ids:
        skipped += 1
        continue

    watch_secs = random.randint(WATCH_SECONDS_MIN, WATCH_SECONDS_MAX)

    try:
        driver.get(url)
        time.sleep(3)  # wait for page load

        # Try to click play if paused
        try:
            play_btn = driver.find_element(By.CSS_SELECTOR, 'button.ytp-play-button')
            if 'Play' in play_btn.get_attribute('title'):
                play_btn.click()
        except:
            pass

        # Try to dismiss any overlays (ads, popups)
        try:
            skip_ad = driver.find_element(By.CSS_SELECTOR, '.ytp-skip-ad-button')
            time.sleep(5)
            skip_ad.click()
        except:
            pass

        print(f"[{i:3}/{len(videos)}] Watching {watch_secs}s | {title}")
        time.sleep(watch_secs)

        # Save progress
        with open(progress_file, 'a') as f:
            f.write(vid + '\n')
        done_ids.add(vid)
        watched += 1

    except Exception as e:
        print(f"[{i:3}/{len(videos)}] FAILED | {title} | {e}")
        failed += 1

    # Small random pause between videos (looks more human)
    time.sleep(random.uniform(2, 5))

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n=== DONE ===")
print(f"Watched: {watched} | Skipped (already done): {skipped} | Failed: {failed}")
print(f"Progress saved to: {progress_file}")
print(f"\nNext step: run the scraping script to get recommendations from this trained account.")
