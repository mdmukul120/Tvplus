import re
import sys
import urllib.parse
import cloudscraper

TOKEN_URL = "https://api.hridoytvheart.workers.dev/get-token"
PLAYLIST_BASE_URL = "https://api.hridoytvheart.workers.dev/master.m3u"

def get_valid_token(scraper):
    headers = {
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
        response = scraper.get(TOKEN_URL, headers=headers, timeout=15)
        print(f"Token API Status Code: {response.status_code}")
        print(f"Token API Response Raw: {response.text}")

        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("data", {}).get("token") or data.get("result", {}).get("token")
            if token:
                print(f"Fetched Token Successfully: {token}")
                return token
            else:
                print("Token key missing in JSON response.")
        return None
    except Exception as e:
        print(f"Error fetching token: {e}")
        return None

def fetch_m3u_playlist(token, scraper):
    # params দিয়ে পাঠালে requests/cloudscraper অটোমেটিক URL Encode করে দেয়
    params = {'token': token}
    
    headers = {
        'Accept': 'text/plain, */*; q=0.01',
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
        response = scraper.get(PLAYLIST_BASE_URL, params=params, headers=headers, timeout=20)
        print(f"Playlist API Status Code: {response.status_code}")
        
        # যদি params কাজ না করে, URL Encode করে সরাসরি ট্রাই করা
        if response.status_code != 200 or "Invalid" in response.text:
            encoded_token = urllib.parse.quote(token, safe='')
            direct_url = f"{PLAYLIST_BASE_URL}?token={encoded_token}"
            response = scraper.get(direct_url, headers=headers, timeout=20)
            print(f"Retry Playlist API Status Code: {response.status_code}")

        if response.status_code == 200 and not response.text.startswith("{"):
            return response.text
        else:
            print(f"Playlist Error Raw: {response.text}")
            return None
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return None

def parse_m3u(m3u_content):
    channels = []
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
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    token = get_valid_token(scraper)
    if token:
        m3u_data = fetch_m3u_playlist(token, scraper)
        if m3u_data:
            channels = parse_m3u(m3u_data)
            if channels:
                save_m3u(channels, "playlist.m3u")
            else:
                print("No channels parsed.")
                sys.exit(1)
        else:
            print("Failed to get playlist data.")
            sys.exit(1)
    else:
        print("Failed to get token.")
        sys.exit(1)
