import json
import requests
import datetime
import time
import argparse
from urllib.parse import urlparse

def get_domain(url):
    try:
        return urlparse(url).netloc.replace('www.', '')
    except:
        return ''

# Domains that are known to block bots but are valid
# We will mark these as active if we get 403/429 or 200
TRUSTED_DOMAINS = {
    'stripe.com',
    'twilio.com',
    'blog.duolingo.com',
    'hashicorp.com',
    'openai.com',
    'x.com',
    'uber.com',
    'medium.com' # Often blocks
}

def validate():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Force validation regardless of last check date')
    args = parser.parse_args()

    json_path = 'data/blogs.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        blogs = json.load(f)
    
    print(f"Validating {len(blogs)} blogs...")
    
    # Mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    
    session = requests.Session()
    
    today = datetime.date.today()
    updated_count = 0
    
    for blog in blogs:
        last_checked_str = blog.get('last_checked_at')
        
        # Check if we should skip
        if not args.force and last_checked_str:
            last_checked = datetime.date.fromisoformat(last_checked_str)
            if (today - last_checked).days < 7:
                continue
            
        url = blog.get('url')
        domain = get_domain(url)
        print(f"Checking {blog.get('name')} - {url}...", end='', flush=True)
        
        try:
            # First attempt: HEAD
            try:
                response = session.head(url, headers=headers, timeout=10, allow_redirects=True)
            except requests.RequestException:
                response = None

            # Retry on 429 (Too Many Requests) with backoff
            if response and response.status_code == 429:
                time.sleep(2)
                try:
                    response = session.get(url, headers=headers, timeout=15)
                except:
                    pass

            # If 405 (Method Not Allowed) or HEAD failed or 403 (Forbidden), try GET
            if response is None or response.status_code in [405, 403] or response.status_code >= 400:
                try:
                    response = session.get(url, headers=headers, timeout=15)
                except requests.RequestException:
                     pass 

            if response and response.status_code == 200:
                print(" OK")
                blog['status'] = 'active'
                blog['last_checked_at'] = today.isoformat()
                updated_count += 1
            elif response and response.status_code == 404:
                print(f" FAILED (404) - Marking Invalid")
                blog['status'] = 'invalid'
                blog['last_checked_at'] = today.isoformat()
                updated_count += 1
            elif response and response.status_code in [403, 429, 999] and (domain in TRUSTED_DOMAINS or any(d in domain for d in TRUSTED_DOMAINS)):
                # Special handling for known protected domains
                print(f" Protected ({response.status_code}) - Marking Active (Trusted Domain)")
                blog['status'] = 'active'
                blog['last_checked_at'] = today.isoformat()
                updated_count += 1
            else:
                status_code = response.status_code if response else "Error"
                print(f" Warning ({status_code}) - Keeping Status")
                blog['last_checked_at'] = today.isoformat()
                
        except Exception as e:
            print(f" ERROR: {str(e)}")
            pass
        
        # Sleep to be nice
        time.sleep(0.5)

    if updated_count > 0:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(blogs, f, indent=2, ensure_ascii=False)
        print(f"Saved updates to {json_path}")
    else:
        print("No updates needed.")

if __name__ == "__main__":
    validate()
