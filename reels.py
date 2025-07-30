from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
import os
import subprocess
import csv
import sys
import json

def load_cookies(driver, cookie_path):
    with open(cookie_path, 'r') as file:
        cookies = json.load(file)
    for cookie in cookies:
        # Selenium requires the domain to be excluded sometimes
        cookie.pop('sameSite', None)  # Remove unsupported fields
        cookie.pop('storeId', None)
        cookie.pop('hostOnly', None)
        cookie.pop('session', None)
        driver.add_cookie(cookie)

# Initialize the WebDriver
# Ensure the chromedriver is in the system path or provide the absolute path
driver = webdriver.Chrome()  # Update if needed, e.g., webdriver.Chrome(executable_path='/path/to/chromedriver')
driver.maximize_window()

driver.get("https://facebook.com")  # go to FB first to set domain
sleep(3)
load_cookies(driver, "fb_cookie.json")
driver.refresh()  # this will log you in

# Open the webpage
chanel = sys.argv[1]
url = sys.argv[2]
driver.get(url)

# Close pop-up login
sleep(5)
# element = driver.find_element(By.XPATH, "//div[@aria-label='Close']")
# element.click()

# Define the number of scrolling steps and scroll interval
scroll_steps = 100  # Adjust as needed
scroll_interval = 6  # Adjust as needed

# Set an initial scroll position
prev_scroll_position = 0

# Scroll to the bottom multiple times
for _ in range(scroll_steps):
    # Scroll down
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    # Wait for the page to load new content (you may need to adjust the time)
    sleep(scroll_interval)

    # Get the current scroll position
    curr_scroll_position = driver.execute_script("return window.pageYOffset;")

    # If the scroll position remains the same, you've likely reached the bottom
    if curr_scroll_position == prev_scroll_position:
        print("Reached the bottom of the page.")
        break

    prev_scroll_position = curr_scroll_position

# Extract reel URLs
a_elements = driver.find_elements(By.CSS_SELECTOR, 'a')

# Create a chanel output directory (cross-platform)
output_dir = os.path.join("output", chanel)
os.makedirs(output_dir, exist_ok=True)

# Save the extracted URLs to a CSV file
csv_path = os.path.join("output", f"{chanel}.csv")
with open(csv_path, "w") as f:
    writer = csv.writer(f)
    for element in a_elements:
        href = element.get_attribute('href')
        if href and '/reel/' in href:
            writer.writerow([href.split('/?s=')[0]])

f.close()
driver.quit()

# Bulk download reels with yt-dlp
with open(csv_path, "r", encoding="utf-8") as file:
    urls = [line.strip() for line in file if line.strip()]

# 🔁 More reliable per-video downloader
for url in urls:
    args = [
        "yt-dlp",
        url,
        "--output", os.path.join(output_dir, "%(title).100s [%(id)s].%(ext)s"),
        "--no-playlist",
        "--ignore-errors",
        "--retries", "10",
        "--fragment-retries", "10",
        "--sleep-interval", "2",
        "--max-sleep-interval", "5"
    ]
    if os.path.exists("cookies.txt"):
        args += ["--cookies", "cookies.txt"]

    
    
    print(f"📥 Downloading: {url}")
    result = subprocess.run(args, capture_output=True, text=True)

    if result.returncode == 0:
        print("   ✅ success")
        continue


    # If we get here, the first attempt failed:
    print(f"   ⚠️ normal download failed, retrying with fallback…")
    print(result.stderr)

    # Fallback command—whatever flags you used manually
    fallback_args = [
        "yt-dlp",
        url,
        "--format", "bestvideo+bestaudio/best",
        "--output", os.path.join(output_dir, "%(title).100s [%(id)s].%(ext)s"),
        "--no-playlist",
        "--ignore-errors",
        "--verbose",
    ]
    if os.path.exists("cookies.txt"):
        fallback_args += ["--cookies", "cookies.txt"]

    
    fb_result = subprocess.run(fallback_args, capture_output=True, text=True)
    if fb_result.returncode == 0:
        print("   ✅ fallback success!")
    else:
        print("   ❌ fallback also failed. Logged for later.")
        print(fb_result.stderr)
        with open("failed.txt", "a", encoding="utf-8") as log:
            log.write(url + "\n")
import re
import os

def parse_number(text):
    match = re.search(r'([\d.]+)([KM]?)', text)
    if not match:
        return 0
    num, suffix = match.groups()
    num = float(num)
    return int(num * 1_000_000 if suffix == 'M' else num * 1_000 if suffix == 'K' else num)

for filename in os.listdir(output_dir):
    if not filename.endswith(".mp4"):
        continue

    views_match = re.search(r'(\d+[\.\d]*[KM]?) views', filename)
    likes_match = re.search(r'(\d+[\.\d]*[KM]?) reactions', filename)

    if not views_match or not likes_match:
        continue

    views = parse_number(views_match.group(1))
    likes = parse_number(likes_match.group(1))

    if views == 0:
        continue

    engagement = (likes / views) * 100
    engagement_str = f"{engagement:.2f}%"

    new_name = f"[{engagement_str}] {filename}"
    src = os.path.join(output_dir, filename)
    dst = os.path.join(output_dir, new_name)

    os.rename(src, dst)
    print(f"✅ Renamed: {new_name}")

