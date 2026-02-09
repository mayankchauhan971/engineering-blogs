import os
import re
import json
import requests
import datetime
from github import Github

def escape_md(text):
    if text:
        return text.replace('[', '\\[').replace(']', '\\]')
    return text

def process_issues():
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPOSITORY')
    
    if not token or not repo_name:
        print("GITHUB_TOKEN or GITHUB_REPOSITORY not set. Skipping issue processing.")
        return

    g = Github(token)
    repo = g.get_repo(repo_name)

    # Get issues with label 'add-blog'
    # Note: verify label exists in repo, or handle potential error if not found? 
    # Usually get_issues(labels=['add-blog']) works fine even if no issues.
    try:
        label = repo.get_label("add-blog")
        issues = repo.get_issues(state='open', labels=[label])
    except:
        print("Label 'add-blog' not found or other error. Skipping.")
        return

    json_path = 'data/blogs.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        blogs = json.load(f)

    existing_urls = {b['url'].rstrip('/').lower() for b in blogs}
    
    # Regex to parse the issue body (based on the YAML template)
    # The template fields are: Blog Name, Blog URL, Category, RSS Feed
    # Markdown body usually looks like:
    # ### Blog Name
    # My Blog
    #
    # ### Blog URL
    # https://...
    
    name_pattern = re.compile(r'### Blog Name\s*\n+(.+)', re.MULTILINE)
    url_pattern = re.compile(r'### Blog URL\s*\n+(.+)', re.MULTILINE)
    category_pattern = re.compile(r'### Category\s*\n+(.+)', re.MULTILINE)

    for issue in issues:
        print(f"Processing Issue #{issue.number}: {issue.title}")
        body = issue.body or ""
        
        # Parse
        name_match = name_pattern.search(body)
        url_match = url_pattern.search(body)
        category_match = category_pattern.search(body)
        
        if not name_match or not url_match or not category_match:
            print("  Missing required fields.")
            issue.create_comment("Error: Could not parse issue body. Please ensure you didn't modify the template structure.")
            continue

        name = name_match.group(1).strip()
        url = url_match.group(1).strip()
        category_raw = category_match.group(1).strip()
        
        # Map category
        category = 'other'
        if 'Company' in category_raw: category = 'company'
        elif 'Individual' in category_raw: category = 'individual'
        elif 'Product' in category_raw: category = 'product'

        # Validate URL
        clean_url = url.rstrip('/').lower()
        if clean_url in existing_urls:
            print("  Duplicate URL.")
            issue.create_comment(f"Error: The blog URL `{url}` is already in the list.")
            issue.edit(state='closed')
            continue
            
        # Check Reachability
        try:
            print(f"  Verifying {url}...")
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"  Unreachable: {resp.status_code}")
                issue.create_comment(f"Error: The blog URL `{url}` is not reachable (Status Code: {resp.status_code}).")
                continue
        except Exception as e:
            print(f"  Error verifying: {e}")
            issue.create_comment(f"Error: Could not verify URL `{url}`. Exception: {e}")
            continue

        # Add to List
        new_entry = {
            "name": name,
            "url": url,
            "category": category,
            "status": "active",
            "date_added": datetime.date.today().isoformat(),
            "last_checked_at": datetime.date.today().isoformat()
        }
            
        blogs.append(new_entry)
        existing_urls.add(clean_url)
        
        print(f"  Added {name}!")
        issue.create_comment(f"Success! invalidating the cache and adding **{escape_md(name)}** to the list.")
        issue.edit(state='closed')

    # Sort and Save
    blogs.sort(key=lambda x: x['name'].lower())
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(blogs, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    process_issues()
