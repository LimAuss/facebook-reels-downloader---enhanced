# facebook-reels-downloader
Download all reels on a channel with a single command.

YOU'LL NEED TO GET COOKIES FIRST, SEE README_cookie.md FOR DETAILS

Facebook Reels Downloader is a simple Python script that lets you download and save your favorite Facebook reels to your computer in HD (High Definition) or SD (Standard Definition) quality.

Depending on the available quality of the video, the downloader extracts HD and SD video links. You can choose whichever you want. However, in some cases, only SD quality is available.

All videos will be in MPEG-4 Part 14 (MP4) format.

![fb_v](demo.gif)

## Clone & Configure
```
# 1. Clone the repo
git clone https://github.com/duongxthanh/facebook-reels-downloader.git

# 2. Change into the project directory
cd facebook-reels-downloader

# 3. (Optional) Install ffmpeg for best results (some downloads may fail without it, particularly the smaller files)
#    - Debian/Ubuntu: sudo apt install ffmpeg
#    - macOS (Homebrew): brew install ffmpeg
#    - Windows (Chocolatey):
#         1. Install Chocolatey (run in an elevated PowerShell):
#            ```powershell
#            Set-ExecutionPolicy Bypass -Scope Process -Force
#            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
#            iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
#            ```
#         2. Once Chocolatey is installed, install ffmpeg:
#            ```powershell
#            choco install ffmpeg -y
#   

# 4. Install Python requirements
pip install -r requirements.txt
```
## Usage
```
python reels.py <channel_name> <channel_reel_url> [max_count_download]
```

    <channel_name>: Your target page or profile name.

    <channel_reel_url>: URL of one reel; script will fetch the rest automatically.

    [max_count_download] (optional): Maximum number of reels to download.



## For your Attention
If you are downloading copyrighted content you should respect author's rights and use the content either for personal purposes or for non-commercial needs with proper mention and authorisation from the author.

## Support & Contributions
- Please ⭐️ this repository if this project helped you!
- Contributions of any kind welcome!
