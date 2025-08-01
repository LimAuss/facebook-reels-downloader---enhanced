#!/usr/bin/env python3
import os
import sys
import csv
import json
import re
import logging
import subprocess
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

def safe_fname(s):
    return re.sub(r'[\\/*?:"<>|]', "-", s)

def scrape_video_urls(driver, max_count=None):
    seen = set()
    prev_pos = -1
    MAX_SCROLLS, SCROLL_DELAY = 25, 4

    for i in range(MAX_SCROLLS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(SCROLL_DELAY)
        elems = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
        for e in elems:
            href = e.get_attribute("href").split('?')[0]
            seen.add(href)
        logging.info(f"Scroll #{i+1} → {len(seen)} videos")
        if max_count and len(seen) >= max_count:
            logging.info("✅ Hit max_count, stopping scroll")
            break
        pos = driver.execute_script("return window.pageYOffset;")
        if pos == prev_pos:
            logging.info("⚠️ No more new content, stopping early")
            break
        prev_pos = pos

    urls = list(seen)
    return urls[:max_count] if max_count else urls

def download_videos(urls, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    # dump URLs
    with open(os.path.join(out_dir, "urls.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for u in urls:
            writer.writerow([u])

    for url in urls:
        logging.info(f"⬇️ Downloading {url}")
        base = [
            "yt-dlp", url,
            "--output", os.path.join(out_dir, "%(id)s.%(ext)s"),
            "--write-info-json", "--no-playlist", "--ignore-errors",
            "--retries", "8", "--fragment-retries", "5",
        ]
        res = subprocess.run(base, capture_output=True, text=True)
        if res.returncode != 0:
            logging.warning("   primary failed, trying fallback")
            fb = subprocess.run(
                base + ["--format", "bestvideo+bestaudio/best", "--verbose"],
                capture_output=True, text=True
            )
            if fb.returncode != 0:
                logging.error(f"   both attempts failed for {url}")
                with open("failed.txt","a",encoding="utf-8") as flog:
                    flog.write(url + "\n")



def rename_by_engagement(out_dir):
    for fn in os.listdir(out_dir):
        if not fn.endswith(".info.json"):
            continue
        vid = fn[:-10]  # strip .info.json
        info_path = os.path.join(out_dir, fn)
        mp4_path = os.path.join(out_dir, vid + ".mp4")
        if not os.path.exists(mp4_path):
            continue

        data = json.load(open(info_path, encoding="utf-8"))
        
        likes = data.get("like_count") or data.get("stats", {}).get("diggCount", 0) or 0
        views = data.get("view_count") or data.get("stats", {}).get("playCount", 0) or 0
        rate = likes / views if views else 0

        title = data.get("title") or vid
        safe = safe_fname(title)

        # format engagement rate as percent with two decimals
        er_str = f"{rate:.2%}"

        # Format upload date
        raw_date = data.get("upload_date")  # "20250730"
        if raw_date and len(raw_date) == 8:
            date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
        else:
            date_str = "unknown-date"

        # Combine all parts into the new filename
        new_mp4  = f"[{er_str} ER] [{date_str}] {safe} [{vid}].mp4"
        new_json = new_mp4.replace(".mp4", ".info.json")

        os.rename(mp4_path, os.path.join(out_dir, new_mp4))
        os.rename(info_path, os.path.join(out_dir, new_json))
        logging.info(f"🔄 Renamed → {new_mp4}")

        # remove JSON if you don’t need it
        os.remove(os.path.join(out_dir, new_json))


def main():
    if len(sys.argv) < 3:
        print("Usage: python reels.py <folder_name> <tiktok_url> [max_count]")
        sys.exit(1)

    folder = sys.argv[1]
    url = sys.argv[2]
    max_count = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None

    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(url)
    sleep(5)
    input("⚠️ CAPTCHA detected? Solve it in the browser, then press Enter here to resume scraping…")

    urls = scrape_video_urls(driver, max_count)
    driver.quit()

    logging.info(f"🎉 Found {len(urls)} videos, starting download...")
    out_dir = os.path.join("output", folder)
    download_videos(urls, out_dir)
    # rename_by_likes(out_dir)
    rename_by_engagement(out_dir)

    logging.info("✅ All done!")

if __name__ == "__main__":
    main()
