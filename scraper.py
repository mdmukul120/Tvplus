import re
import sys
import json
import time
from playwright.sync_api import sync_playwright

captured_data = {"m3u": None, "json": None}

def handle_response(response):
    url = response.url
    # যদি নেটওয়ার্ক ট্র্যাফিকের মাঝে M3U বা Channel API রেসপন্স থাকে
    if "master.m3u" in url or ".m3u" in url or "get-playlist" in url:
        try:
            text = response.text()
            if "#EXTM3U" in text:
                captured_data["m3u"] = text
        except Exception:
            pass
    elif "channels" in url or "get-channels" in url or "get-token" in url:
        try:
            res_json = response.json()
            if isinstance(res_json, list) or (isinstance(res_json, dict) and "channels" in res_json):
                captured_data["json"] = res_json
        except Exception:
            pass

def get_data_via_interception():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # নেটওয়ার্ক ইন্টারসেপ্টর চালু করা
        page.on("response", handle_response)

        try:
            print("Navigating to target website...")
            page.goto("https://hridoytv.pages.dev/", wait_until="networkidle", timeout=45000)
            time.sleep(5) # নেটওয়ার্ক রিকোয়েস্ট কমপ্লিট হওয়ার জন্য কিছুটা সময় দেওয়া

            # যদি ইন্টারসেপ্টরে না আসে, তবে পেজের গ্লোবাল স্ক্রিপ্ট ভেরিয়েবল বা ডম থেকে ট্রাই করা
            if not captured_data["m3u"] and not captured_data["json"]:
                print("Trying fallback fetch from inside page context...")
                eval_res = page.evaluate("""
                    async () => {
                        try {
                            const tokRes = await fetch('https://api.hridoytvheart.workers.dev/get-token');
                            const tokData = await tokRes.json();
                            const token = tokData.token || (tokData.data && tokData.data.token);
                            
                            if(token) {
                                const m3uRes = await fetch('https://api.hridoytvheart.workers.dev/master.m3u?token=' + token);
                                return await m3uRes.text();
                            }
                        } catch(e) {
                            return null;
                        }
                    }
                """)
                if eval_res and "#EXTM3U" in eval_res:
                    captured_data["m3u"] = eval_res

            browser.close()
            return captured_data
        except Exception as e:
            print(f"Error during page navigation: {e}")
            browser.close()
            return captured_data

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
    data = get_data_via_interception()
    
    if data["m3u"]:
        print("M3U Playlist captured successfully via Network Interception!")
        channels = parse_m3u(data["m3u"])
        if channels:
            save_m3u(channels)
            sys.exit(0)
            
    print("Failed to capture valid playlist data.")
    sys.exit(1)
