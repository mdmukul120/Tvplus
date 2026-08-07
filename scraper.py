import re
import sys
import json
import time
from playwright.sync_api import sync_playwright

captured_channels = []

def handle_response(response):
    global captured_channels
    url = response.url
    
    # ১. যদি ব্যাকএন্ড থেকে জেসন ফরম্যাটে চ্যানেলের লিস্ট আসে
    if any(keyword in url for keyword in ["channels", "get-channels", "playlist", "get-playlist", "all-tv"]):
        try:
            contentType = response.headers.get("content-type", "")
            if "json" in contentType:
                data = response.json()
                items = data if isinstance(data, list) else data.get("channels") or data.get("data") or []
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("title") or item.get("channel_name")
                        logo = item.get("logo") or item.get("icon") or item.get("image") or ""
                        stream_url = item.get("url") or item.get("stream") or item.get("link") or item.get("file") or ""
                        
                        if name and stream_url and not stream_url.endswith(".ts"):
                            captured_channels.append({"name": name, "logo": logo, "url": stream_url})
        except Exception:
            pass

def get_real_playlist():
    global captured_channels
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        page.on("response", handle_response)

        try:
            print("Navigating to target site...")
            page.goto("https://hridoytv.pages.dev/", wait_until="networkidle", timeout=45000)
            time.sleep(5)

            # ২. ইন্টারসেপ্টে না পেলে DOM / Javascript Context থেকে চ্যানেলের ডাটা ফেচ করা
            if not captured_channels:
                print("Extracting channels directly from Page Context...")
                page_data = page.evaluate("""
                    async () => {
                        try {
                            // ওয়েবসাইট ফ্রন্টএন্ডে সাধারণত যে সব API ব্যবহার করা হয়
                            const endpoints = [
                                'https://api.hridoytvheart.workers.dev/channels',
                                'https://api.hridoytvheart.workers.dev/get-channels',
                                'https://api.hridoytvheart.workers.dev/playlist'
                            ];
                            
                            for (let ep of endpoints) {
                                try {
                                    const res = await fetch(ep);
                                    if(res.ok) {
                                        const json = await res.json();
                                        if (Array.isArray(json) && json.length > 0) return json;
                                        if (json.channels && Array.isArray(json.channels)) return json.channels;
                                    }
                                } catch(e){}
                            }
                        } catch(e) {
                            return null;
                        }
                        return null;
                    }
                """)

                if page_data and isinstance(page_data, list):
                    for item in page_data:
                        if isinstance(item, dict):
                            name = item.get("name") or item.get("title")
                            logo = item.get("logo") or item.get("icon") or ""
                            stream_url = item.get("url") or item.get("stream") or item.get("link") or ""
                            if name and stream_url:
                                captured_channels.append({"name": name, "logo": logo, "url": stream_url})

            browser.close()
            return captured_channels

        except Exception as e:
            print(f"Browser navigation error: {e}")
            browser.close()
            return captured_channels

def save_m3u(channels, output_file="playlist.m3u"):
    # ইউনিক চ্যানেল ফিল্টার করা
    unique_channels = []
    seen_urls = set()
    
    for ch in channels:
        if ch["url"] not in seen_urls and not ch["url"].endswith(".ts"):
            seen_urls.add(ch["url"])
            unique_channels.append(ch)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in unique_channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')
    print(f"Successfully generated {output_file} with {len(unique_channels)} real channels.")

if __name__ == "__main__":
    channels = get_real_playlist()
    if channels:
        save_m3u(channels)
    else:
        print("Failed to find valid channels list.")
        sys.exit(1)
