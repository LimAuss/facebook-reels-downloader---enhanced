from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
import os, subprocess, csv, sys, json, re, logging

def load_cookies(driver, cookie_path):
    with open(cookie_path, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    for c in cookies:
        # drop unsupported keys
        for k in ('sameSite','storeId','hostOnly','session'):
            c.pop(k, None)
        driver.add_cookie(c)

# ─── 1) BOOT UP SELENIUM + LOGIN ─────────────────────────────────────────────
driver = webdriver.Chrome()
driver.maximize_window()

# hit IG to set cookie domain, then load yours
driver.get("https://www.instagram.com")
sleep(3)
try:
    load_cookies(driver, "ig_cookies.json")
except Exception as e:
    print(f"❌ Failed to load cookies: {e}")
    driver.quit()
    sys.exit(1)
driver.refresh()
sleep(3)

# ─── 2) NAVIGATE TO TARGET PROFILE/REELS PAGE ────────────────────────────────
chanel = sys.argv[1]         # folder name
url     = sys.argv[2]        # https://www.instagram.com/reel/ABC123/
max_count  = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None # optional max reels to download
driver.get(url)
sleep(5)                     # let initial content load

# ─── 3) INFINITE SCROLL (if needed) ──────────────────────────────────────────
MAX_SCROLLS   = 25      # absolute cap so we don't infinite loop
SCROLL_DELAY  = 4       # seconds between scrolls
seen_urls     = set()
prev_pos      = -1

for i in range(MAX_SCROLLS):
    # 1) scroll
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    sleep(SCROLL_DELAY)

    # 2) grab all reel links so far
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/reel/']")
    for a in anchors:
        href = a.get_attribute('href').split('?')[0]
        seen_urls.add(href)

    print(f"Scroll #{i+1}: collected {len(seen_urls)} reels")

    # 3) if we have enough, stop
    if max_count is not None and len(seen_urls) >= max_count:
        print(f"✅ Reached target of {max_count} reels—stopping scroll.")
        break

    # 4) also stop if can’t scroll anymore
    pos = driver.execute_script("return window.pageYOffset")
    if pos == prev_pos:
        print("⚠️ No more new content, stopping early.")
        break
    prev_pos = pos

# finally, build your URLs list (and cap it if needed)
urls = list(seen_urls)
if max_count is not None:
    urls = urls[:max_count]

print(f"▶️  Ready to download {len(urls)} reels")

# ─── 4) COLLECT REEL LINKS ────────────────────────────────────────────────────
anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/reel/']")
urls = []


for a in anchors:
    href = a.get_attribute('href')
    if href and ('/reel/' in href or '/reels/' in href):
        urls.append(href.split('?')[0])

if max_count is not None:
    urls = urls[:max_count]

driver.quit()

# make sure folder exists
output_dir = os.path.join("output", chanel)
os.makedirs(output_dir, exist_ok=True)

# dump URLs to CSV in case you want it
csv_path = os.path.join(output_dir, f"{chanel}.csv")
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    for u in urls:
        w.writerow([u])

# ─── 5) DOWNLOAD EACH WITH FALLBACK ──────────────────────────────────────────
success_count = 0
total_count = len(urls)

for url in urls:
    print(f"📥 Downloading {url}")
    base_args = [
        "yt-dlp", url,
        "--output", os.path.join(output_dir, "%(id)s.%(ext)s"),
        "--write-info-json",
        "--no-playlist",
        "--ignore-errors",
        "--retries", "8",
        "--fragment-retries", "5",
    ]

    # 1st try
    res = subprocess.run(base_args, capture_output=True, text=True)
    if res.returncode == 0:
        print("   ✅ downloaded")
        success_count += 1
    else:
        print("   ⚠️ primary failed, retrying fallback…")
        print(res.stderr)
        fb = subprocess.run(
            base_args + ["--format", "bestvideo+bestaudio/best", "--verbose"],
            capture_output=True, text=True
        )
        if fb.returncode == 0:
            print("   ✅ fallback worked")
            success_count += 1
        else:
            print("   ❌ both attempts failed — logging")
            with open("failed.txt","a",encoding="utf-8") as flog:
                flog.write(url+"\n")

print(f"\nDownload summary: {success_count}/{total_count} reels downloaded successfully.")

# ─── 6) RENAME BY ENGAGEMENT (views/likes from .info.json) ───────────────────
def safe_fname(s, max_len=120):
    # 1) replace any whitespace-control (newline/tab) with a space
    s = re.sub(r'[\r\n\t]+', ' ', s)

    # 2) replace Windows-illegal chars with dash
    s = re.sub(r'[\\/*?:"<>|]', '-', s)

    # 3) collapse multiple spaces, trim ends
    s = re.sub(r'\s{2,}', ' ', s).strip()

    # 4) truncate to a safe length so path <260 chars
    return s[:max_len]

renamed_titles = []

for fname in os.listdir(output_dir):
    if not fname.endswith(".info.json"):
        continue
    vid = fname[:-10]  # strip .info.json
    info_path = os.path.join(output_dir, fname)
    mp4_path  = os.path.join(output_dir, vid + ".mp4")
    if not os.path.exists(mp4_path):
        continue

    data = json.load(open(info_path, encoding="utf-8"))
    views = None  # not available
    likes = data.get("like_count", 0) or 0
    date = data.get("upload_date", "unknown")
    if date and date != "unknown" and len(date) == 8:
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    else:
        date = "unknown"

    title = data.get("description", vid) or vid
    safe = safe_fname(title)

    new_mp4 = f"[{likes:,} likes] [{date}] {safe} [{vid}].mp4"
    new_json = new_mp4.replace(".mp4", ".info.json")
    
    os.rename(mp4_path, os.path.join(output_dir, new_mp4))
    os.rename(info_path, os.path.join(output_dir, new_json))

    print(f"🔄 Renamed to: {new_mp4}")

    renamed_titles.append(new_mp4)

    # remove the info.json file if you don't need it
    os.remove(os.path.join(output_dir, new_json))

# Write all renamed titles to a text file
titles_txt_path = os.path.join(output_dir, "renamed_titles.txt")
with open(titles_txt_path, "w", encoding="utf-8") as f:
    for title in renamed_titles:
        f.write(title + "\n")

