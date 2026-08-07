import re
import sys
import time
from playwright.sync_api import sync_playwright

TOKEN_URL = "https://api.hridoytvheart.workers.dev/get-token"
PLAYLIST_BASE_URL = "https://api.hridoytvheart.workers.dev/master.m3u"

def get_m3u_with_browser():
    with sync_playwright() as p:
        # Headless Browser চালু করা
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # ১. মূল ওয়েবসাইট পেজ লোড করা
            page.goto("https://hridoytv.pages.dev/", wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # ২. ব্রাউজার কনটেক্সট থেকে টোকেন API কল
            token_response = page.evaluate(f"""
                async () => {{
                    const res = await fetch('{TOKEN_URL}', {{
                        headers: {{
                            'Origin': 'https://hridoytv.pages.dev',
                            'Referer': 'https://hridoytv.pages.dev/'
                        }}
                    }});
                    return await res.json();
                }}
            """)

            token = token_response.get("token") or token_response.get("data", {}).get("token")
            print("Token Received:", token)

            if not token:
                browser.close()
                return None

            # ৩. ব্রাউজার কনটেক্সট থেকে M3U ফেচ করা (Origin/Cookie সিঙ্ক থাকবে)
            m3u_url = f"{PLAYLIST_BASE_URL}?token={token}"
            m3u_text = page.evaluate(f"""
                async () => {{
                    const res = await fetch('{m3u_url}', {{
                        headers: {{
                            'Origin': 'https://hridoytv.pages.dev',
                            'Referer': 'https://hridoytv.pages.dev/'
                        }}
                    }});
                    return await res.text();
                }}
            """)

            browser.close()
            return m3u_text

        except Exception as e:
            print(f"Error during browser fetch: {e}")
            browser.close()
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
    m3u_content = get_m3u_with_browser()
    if m3u_content and "#EXTM3U" in m3u_content:
        channels = parse_m3u(m3u_content)
        if channels:
            save_m3u(channels, "playlist.m3u")
        else:
            print("No channels parsed.")
            sys.exit(1)
    else:
        print("Failed to get valid M3U playlist.")
        sys.exit(1)
