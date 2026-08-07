import re
import sys
import json
import time
from playwright.sync_api import sync_playwright

def run_debug_and_scrape():
    found_channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("Navigating to target website...")
            page.goto("https://hridoytv.pages.dev/", wait_until="networkidle", timeout=60000)
            time.sleep(5)

            # JavaScript Context Evaluator
            channels_data = page.evaluate("""
                () => {
                    let channels = [];
                    
                    const elements = document.querySelectorAll('a, button, div, iframe, source, video');
                    elements.forEach(el => {
                        let rawName = el.innerText || el.getAttribute('title') || el.getAttribute('alt') || el.getAttribute('aria-label') || '';
                        let url = el.getAttribute('href') || el.getAttribute('data-url') || el.getAttribute('src') || el.getAttribute('data-src') || '';
                        
                        let img = el.querySelector('img');
                        let logo = img ? (img.getAttribute('src') || img.getAttribute('data-src') || '') : '';

                        // JS trim() ব্যবহার করা হয়েছে
                        let cleanName = rawName.split('\\n')[0].trim();

                        if (url && (url.includes('.m3u8') || url.includes('.mpd') || url.includes('stream') || url.includes('live')) && !url.endsWith('.ts')) {
                            channels.push({
                                name: cleanName || 'TV Channel',
                                logo: logo,
                                url: url
                            });
                        }
                    });

                    if (window.channels && Array.isArray(window.channels)) {
                        window.channels.forEach(ch => {
                            channels.push({
                                name: ch.name || ch.title || 'TV Channel',
                                logo: ch.logo || ch.image || '',
                                url: ch.url || ch.link || ch.file || ''
                            });
                        });
                    }

                    return channels;
                }
            """)

            if channels_data:
                found_channels.extend(channels_data)

            browser.close()
            return found_channels

        except Exception as e:
            print(f"Error during navigation: {e}")
            browser.close()
            return found_channels

def save_m3u(channels, output_file="playlist.m3u"):
    unique_channels = []
    seen_urls = set()
    
    for ch in channels:
        url = ch.get("url", "")
        name = ch.get("name", "TV Channel").strip()
        logo = ch.get("logo", "")

        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = "https://hridoytv.pages.dev" + url

        if url and url not in seen_urls and not url.endswith(".ts"):
            seen_urls.add(url)
            unique_channels.append({"name": name, "logo": logo, "url": url})

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
        print("No channel elements extracted from DOM.")
        sys.exit(1)
