import re
import requests

# API Endpoints
TOKEN_URL = "https://api.hridoytvheart.workers.dev/get-token"
PLAYLIST_BASE_URL = "https://api.hridoytvheart.workers.dev/master.m3u"

def get_valid_token():
    """টোকেন API থেকে নতুন টোকেন ফেচ করে"""
    try:
        response = requests.get(TOKEN_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # API Response অনুযায়ী টোকেন এক্সট্র্যাক্ট
        token = data.get("token") or data.get("data", {}).get("token")
        if token:
            print("Successfully fetched token.")
            return token
        else:
            print("Token key not found in JSON response.")
            return None
    except Exception as e:
        print(f"Error fetching token: {e}")
        return None

def fetch_m3u_playlist(token):
    """টোকেন ব্যবহার করে M3U ফাইলটি ডাউনলোড করে"""
    url = f"{PLAYLIST_BASE_URL}?token={token}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return None

def parse_m3u(m3u_content):
    """M3U কন্টেন্ট পার্স করে চ্যানেলের নাম, লোগো এবং লিংক বের করে"""
    channels = []
    lines = m3u_content.strip().split("\n")
    
    current_channel = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            # tvg-logo এক্সট্র্যাক্ট করা
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            logo = logo_match.group(1) if logo_match else ""
            
            # চ্যানেলের নাম এক্সট্র্যাক্ট করা (কমা-র পরের অংশ)
            name_match = line.split(",")
            name = name_match[-1].strip() if len(name_match) > 1 else "Unknown Channel"
            
            current_channel = {
                "name": name,
                "logo": logo
            }
        elif line and not line.startswith("#"):
            # স্ট্রিম ইউআরএল
            if current_channel:
                current_channel["url"] = line
                channels.append(current_channel)
                current_channel = {}
                
    return channels

def generate_cleaned_m3u(channels, output_file="playlist.m3u"):
    """পার্স করা চ্যানেলগুলোকে নতুন M3U ফাইলে সেভ করে"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')
    print(f"Saved {len(channels)} channels to {output_file}")

if __name__ == "__main__":
    token = get_valid_token()
    if token:
        m3u_data = fetch_m3u_playlist(token)
        if m3u_data:
            channels = parse_m3u(m3u_data)
            generate_cleaned_m3u(channels, "playlist.m3u")
