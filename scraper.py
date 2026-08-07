import re
import sys
import cloudscraper

TOKEN_URL = "https://api.hridoytvheart.workers.dev/get-token"
PLAYLIST_BASE_URL = "https://api.hridoytvheart.workers.dev/master.m3u"

def run_scraper():
    # Cloudflare scraper ইনিশিয়ালাইজেশন
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    base_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://hridoytv.pages.dev',
        'Referer': 'https://hridoytv.pages.dev/',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    try:
        # ১. টোকেন ও সেশন কুকি সংগ্রহ
        token_res = scraper.get(TOKEN_URL, headers=base_headers, timeout=15)
        print(f"Token Status Code: {token_res.status_code}")
        
        if token_res.status_code != 200:
            print(f"Token Error: {token_res.text}")
            return None

        data = token_res.json()
        token = data.get("token") or data.get("data", {}).get("token")
        
        if not token:
            print("Token missing in JSON response.")
            return None
            
        print(f"Token Received: {token}")

        # ২. M3U প্লেলিস্ট রিকোয়েস্ট
        playlist_headers = base_headers.copy()
        playlist_headers['Accept'] = '*/*'
        
        # সেশন কুকিজ ধরে রেখে এবং URL Parameter আকারে টোকেন পাস
        m3u_url = f"{PLAYLIST_BASE_URL}?token={token}"
        m3u_res = scraper.get(m3u_url, headers=playlist_headers, timeout=20)
        
        print(f"Playlist Status Code: {m3u_res.status_code}")
        
        if m3u_res.status_code == 200 and "#EXTM3U" in m3u_res.text:
            return m3u_res.text
            
        # বিকল্প চেষ্টা: সরাসরি JSON Channel List থাকলে
        json_url = f"https://api.hridoytvheart.workers.dev/channels?token={token}"
        alt_res = scraper.get(json_url, headers=base_headers, timeout=15)
        if alt_res.status_code == 200:
            return alt_res.json()

        print(f"Playlist Fetch Error: {m3u_res.text[:200]}")
        return None

    except Exception as e:
        print(f"Scraper Exception: {e}")
        return None

def parse_m3u(m3u_content):
    channels = []
    
    # JSON ফরম্যাট সাপোর্ট
    if isinstance(m3u_content, list):
        for item in m3u_content:
            channels.append({
                "name": item.get("name") or item.get("title") or "Unknown Channel",
                "logo": item.get("logo") or item.get("image") or "",
                "url": item.get("link") or item.get("url") or ""
            })
        return channels

    # সাধারণ M3U ফরম্যাট
    lines = m3u_content.strip().split("\n")
    current_channel = {}

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            logo = logo_match.group(1) if logo_match else ""

            name_split = line.split(",")
            name = name_split[-1].strip() if len(name_split) > 1 else "Unknown Channel"

            current_channel = {"name": name, "logo": logo}
        elif line and not line.startswith("#"):
            if current_channel:
                current_channel["url"] = line
                channels.append(current_channel)
                current_channel = {}

    return channels

def save_m3u(channels, output_file="playlist.m3u"):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')
    print(f"Successfully generated {output_file} with {len(channels)} channels.")

if __name__ == "__main__":
    content = run_scraper()
    if content:
        channels = parse_m3u(content)
        if channels:
            save_m3u(channels, "playlist.m3u")
        else:
            print("No channels extracted.")
            sys.exit(1)
    else:
        print("Scraping failed.")
        sys.exit(1)
