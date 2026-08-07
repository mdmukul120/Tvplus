import re
import sys
import json
import time
from playwright.sync_api import sync_playwright

def run_debug_and_scrape():
    found_channels = []

    with sync_playwright() as p:
        # Client Spoofing সহ ব্রাউজার চালু
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # নেটওয়ার্ক ইন্টারসেপ্টর: সাইটটি যেসব নেটওয়ার্ক রিকোয়েস্ট পাঠায় তা দেখা
        def log_and_intercept(response):
            nonlocal found_channels
            url = response.url
            
            # শুধুমাত্র ইমেজ বা স্টাইলশ্রিট বাদ দিয়ে ব্যাকএন্ড কলগুলো চেক করা
            if not any(ext in url for ext in [".png", ".jpg", ".jpeg", ".css", ".svg", ".ico"]):
                print(f"Network Call: {url} [{response.status}]")
                
            try:
                # যদি রেসপন্সটি জেসন অথবা m3u টেক্সট হয়
                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    data = response.json()
                    # যদি ডাটার ভেতরে কোন লিস্ট বা চ্যানেলের তালিকা পাওয়া যায়
                    raw_items = []
                    if isinstance(data, list):
                        raw_items = data
                    elif isinstance(data, dict):
                        raw_items = data.get("channels") or data.get("data") or data.get("result") or []
                    
                    if isinstance(raw_items, list) and len(raw_items) > 0:
                        for item in raw_items:
                            if isinstance(item, dict):
                                name = item.get("name") or item.get("title") or item.get("channel_name")
                                logo = item.get("logo") or item.get("icon") or item.get("image") or ""
                                url_val = item.get("url") or item.get("stream") or item.get("link") or item.get("file") or ""
                                if name and url_val and not url_val.endswith(".ts"):
                                    found_channels.append({"name": name, "logo": logo, "url": url_val})
            except Exception:
                pass

        page.on("response", log_and_intercept)

        try:
            print("Navigating to https://hridoytv.pages.dev/ ...")
            page.goto("https://hridoytv.pages.dev/", wait_until="domcontentloaded", timeout=60000)
            
            # পেজের স্ক্রিপ্টগুলো রান হওয়া এবং API কল সম্পূর্ণ করার জন্য ১০ সেকেন্ড সময় দেওয়া
            time.sleep(10)

            # যদি নেটওয়ার্ক ইন্টারসেপশনে না আসে, ফ্রন্টএন্ড DOM / JavaScript State থেকে ডাটা এক্সট্র্যাক্ট করা
            if not found_channels:
                print("Checking page HTML & DOM elements...")
                # পেজের ভেতরে তৈরি হওয়া ভিডিও সোর্স বা চ্যানেল কার্ড পার্স করা
                cards_data = page.evaluate("""
                    () => {
                        let channels = [];
                        // DOM elements check
                        document.querySelectorAll('a, button, div[data-url], iframe').forEach(el => {
                            let name = el.innerText || el.getAttribute('title') || el.getAttribute('alt') || '';
                            let url = el.getAttribute('href') || el.getAttribute('data-url') || el.getAttribute('src') || '';
                            let img = el.querySelector('img');
                            let logo = img ? img.getAttribute('src') : '';
                            
                            if (url && (url.includes('.m3u8') || url.includes('stream') || url.includes('live'))) {
                                channels.append({name: name.trim(), logo: logo, url: url});
                            }
                        });
                        return channels;
                    }
                """)
                if cards_data:
                    found_channels.extend(cards_data)

            browser.close()
            return found_channels

        except Exception as e:
            print(f"Error during navigation: {e}")
            browser.close()
            return found_channels

def save_m3u(channels, output_file="playlist.m3u"):
    unique_channels = []
    seen = set()
    
    for ch in channels:
        if ch["url"] not in seen:
            seen.add(ch["url"])
            unique_channels.append(ch)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in unique_channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}",{ch["name"]}\n')
            f.write(f'{ch["url"]}\n')
    print(f"Successfully generated {output_file} with {len(unique_channels)} channels.")

if __name__ == "__main__":
    channels = run_debug_and_scrape()
    if channels:
        save_m3u(channels)
    else:
        print("Failed to capture valid channels. Check network log outputs above.")
        sys.exit(1)
