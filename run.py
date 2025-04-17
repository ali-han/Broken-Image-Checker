import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import csv
import time
import signal
import sys
import datetime

visited_urls = set()
broken_images = []
checked_images = {}
checked_css = set()
# Default User-Agent
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# Alternative User-Agent (can be switched if needed)
# headers = {
#     "User-Agent": "Mozilla/5.0 (compatible; ImageCheckerBot/1.0; +https://example.com/bot)"
# }

# Global flag to stop crawling
stop_crawling = False

def signal_handler(sig, frame):
    global stop_crawling
    print("\n[Stopping] Crawl process interrupted by user.")
    stop_crawling = True

# Register signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def safe_request(method, url, **kwargs):
    wait_time = 1
    while True:
        try:
            response = requests.request(method, url, headers=headers, timeout=10, **kwargs)
            if response.status_code == 429:
                print(f"[429 Too Many Requests] Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
                wait_time = min(wait_time * 2, 60)
                continue

            # Check if the response URL is still within the domain
            if response.status_code in (301, 302) and 'domain' in kwargs:
                redirected_domain = urlparse(response.url).netloc
                if kwargs['domain'] not in redirected_domain:
                    print(f"[Redirected Outside Domain] Skipping URL: {response.url}")
                    return None

            return response
        except requests.exceptions.RequestException as e:
            print(f"[Request Error] {e}")
            return None

def extract_images(soup, base_url):
    img_urls = []

    for img in soup.find_all('img', src=True):
        img_urls.append(urljoin(base_url, img['src']))

    for tag in soup.find_all(['img', 'source']):
        srcset = tag.get('srcset')
        if srcset:
            candidates = [s.strip().split(' ')[0] for s in srcset.split(',')]
            img_urls.extend([urljoin(base_url, c) for c in candidates if c])

    for style in soup.find_all('style'):
        img_urls.extend(extract_urls_from_css(style.string or "", base_url))

    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href:
            css_url = urljoin(base_url, href)
            if css_url not in checked_css:
                checked_css.add(css_url)
                css_response = safe_request('GET', css_url)
                if css_response and css_response.status_code == 200:
                    img_urls.extend(extract_urls_from_css(css_response.text, css_url))

    return list(set(img_urls))

def extract_urls_from_css(css_text, base_url):
    if not css_text:
        return []
    urls = re.findall(r'url\((.*?)\)', css_text)
    clean_urls = []
    for u in urls:
        u = u.strip('\'" ')
        if u and not u.startswith('data:'):
            clean_urls.append(urljoin(base_url, u))
    return clean_urls

def get_all_links(url):
    # Dosya uzantısı kontrolü: HTML dışı dosyalar taranmaz
    non_html_exts = ['.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.7z', '.tar', '.gz', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv', '.webm', '.ico']
    parsed_url = urlparse(url)
    if any(parsed_url.path.lower().endswith(ext) for ext in non_html_exts):
        print(f"[Skip Non-HTML] {url}")
        return [], []
    # Redirect kontrolü
    response = safe_request('GET', url, allow_redirects=False)
    if response is not None and response.status_code in (301, 302):
        redirect_url = response.headers.get('Location')
        print(f"[Redirect Detected] {url} -> {redirect_url}")
        broken_images.append((url, f"[REDIRECT] {redirect_url}"))
        return [], []
    response = safe_request('GET', url)
    if not response or response.status_code != 200:
        print(f"[{response.status_code if response else 'ERR'}] Failed to load page: {url}")
        return [], []
    soup = BeautifulSoup(response.text, 'lxml')
    image_urls = extract_images(soup, url)
    page_links = [urljoin(url, a.get('href')) for a in soup.find_all('a', href=True)]
    return image_urls, page_links

def is_image_broken(url, page_url):
    if url in checked_images:
        # Add the current page to the list of pages where this image is used
        checked_images[url].add(page_url)
        return False

    # Initialize the set of pages for this image
    checked_images[url] = {page_url}

    # Redirect kontrolü
    resp = safe_request('HEAD', url, allow_redirects=False)
    if resp is not None and resp.status_code in (301, 302):
        redirect_url = resp.headers.get('Location')
        print(f"[Image Redirect Detected] {url} -> {redirect_url}")
        broken_images.append((page_url, url, f"[IMAGE REDIRECT] {redirect_url}"))
        return True

    resp = safe_request('HEAD', url, allow_redirects=True)
    return not resp or resp.status_code >= 400

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ["http", "https"]

# Update crawl function to skip invalid URLs
def crawl(url, domain, current_count=1, total_count=None):
    global stop_crawling
    if stop_crawling:
        return

    if not is_valid_url(url):
        print(f"[Invalid URL] Skipping: {url}")
        return

    if url in visited_urls:
        return
    visited_urls.add(url)

    if total_count is None:
        total_count = len(visited_urls) + 1  # Estimate total count dynamically

    print(f"\n[Crawling {current_count}/{total_count}] {url}")
    img_urls, links = get_all_links(url)
    if len(img_urls) > 0:
        print(f"[Images found] {len(img_urls)}")

    broken_on_page = 0
    for img in img_urls:
        if is_image_broken(img, url):
            print(f"[❌] {img}")
            broken_images.append((url, img))
            broken_on_page += 1
        else:
            print(f"[✅] {img}")

    if broken_on_page > 0:
        print(f"[Broken on page] {broken_on_page}")

    for index, link in enumerate(links, start=1):
        if stop_crawling:
            return

        parsed = urlparse(link)
        # Only follow links within the specified domain
        if parsed.netloc == '' or domain in parsed.netloc:
            crawl(link, domain, current_count + index, total_count + len(links))

def save_to_csv(data, filename=None):
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"broken_images_{timestamp}.csv"

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Page URL', 'Broken Image URL', 'Details'])
        writer.writerows(data)
    print(f"\n[Saved] CSV report written to: {filename}")

if __name__ == "__main__":
    start_url = input("Enter the start URL (e.g. https://example.com): ").strip()
    if not start_url.startswith("http"):
        print("[Error] Invalid URL. Please include http:// or https://")
        exit(1)

    domain = urlparse(start_url).netloc
    start_time = time.time()

    print("\n[Start] Scanning...\n")
    crawl(start_url, domain)

    print("\n[Done] Scan complete.")
    print(f"[Pages visited] {len(visited_urls)}")
    print(f"[Images checked] {len(checked_images)}")
    total_size = sum([safe_request('HEAD', img).headers.get('Content-Length', 0) for img in checked_images if safe_request('HEAD', img)])
    print(f"[Total image size] {total_size} bytes")

    save_to_csv(broken_images)
    print(f"[Time elapsed] {round(time.time() - start_time, 2)} seconds\n")
    print("------------------------------------------------")
    print("Thank you for using ImageCheckerBot!")
    print("Please report any issues to the developer.")
    print("Have a great day!")
    print("------------------------------------------------")
    print("Disclaimer: This script is for educational purposes only. Use responsibly and respect website policies. The developer is not responsible for any misuse.")
    print("------------------------------------------------")