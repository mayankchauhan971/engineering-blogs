import json
import requests
import datetime
import time
import argparse

def validate():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Force validation regardless of last check date')
    args = parser.parse_args()

    json_path = 'data/blogs.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        blogs = json.load(f)
    
    print(f"Validating {len(blogs)} blogs...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        print(f"Checking {blog.get('name')} - {url}...", end='', flush=True)
        
        try:
            # First attempt: HEAD
            try:
                response = session.head(url, headers=headers, timeout=10, allow_redirects=True)
            except requests.RequestException:
                # If HEAD fails (connection error), try GET immediately
                response = None

            # If 405 (Method Not Allowed) or HEAD failed, try GET
            if response is None or response.status_code == 405 or response.status_code >= 400:
                try:
                    response = session.get(url, headers=headers, timeout=15)
                except requests.RequestException:
                     pass # Will be handled below

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
            else:
                status_code = response.status_code if response else "Error"
                print(f" Warning ({status_code}) - Keeping Status")
                # We don't update last_checked_at so we can retry next time?
                # or we update it to avoid hammering?
                # Let's update it to avoid hammering.
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
