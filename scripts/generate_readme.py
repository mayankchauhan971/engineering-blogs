import json
import datetime
import os


def escape_md(text):
    if text:
        return text.replace('[', '\\[').replace(']', '\\]')
    return text

def generate_readme():
    json_path = 'data/blogs.json'
    readme_path = 'README.md'
    archive_path = 'ARCHIVE.md'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        blogs = json.load(f)

    # Filter active vs invalid
    active_blogs = [b for b in blogs if b.get('status') == 'active']
    archived_blogs = [b for b in blogs if b.get('status') != 'active']
    
    # Sort active blogs by name
    active_blogs.sort(key=lambda x: x['name'].lower())

    # Group by Category
    categories = {
        'aggregator': [],
        'company': [],
        'individual': [],
        'product': []
    }
    
    for blog in active_blogs:
        cat = blog.get('category', 'other')
        if cat in categories:
            categories[cat].append(blog)
        else:
            if 'other' not in categories:
                categories['other'] = []
            categories['other'].append(blog)

    # Calculate Stats
    total_blogs = len(active_blogs)
    today = datetime.date.today().strftime("%-d %b %Y")
    
    # Generate Markdown Content
    lines = []
    
    # Header
    lines.append("# Engineering Blogs")
    lines.append(f"> A curated list of {total_blogs} engineering blogs.  ")
    lines.append(f"> *Last updated: {today}*")
    lines.append("")
    lines.append("This repository is automatically maintained by GitHub Actions. It validates links weekly and harvests new blogs from community submissions to ensure it never goes stale.")
    lines.append("")
    
    # Quick Links & Stats
    lines.append("## Categories")
    lines.append("| Category | Count |")
    lines.append("| :--- | :--- |")
    for cat, items in categories.items():
        display_name = cat.title()
        if cat == 'individual': display_name = 'Individuals'
        if cat == 'company': display_name = 'Companies'
        if cat == 'product': display_name = 'Products/Technologies'
        if cat == 'aggregator': display_name = 'Engineering Blog Aggregators'
        
        lines.append(f"| [{display_name}](#{cat}) | {len(items)} |")
    lines.append("")

    # Recent Additions Logic (Last 30 days)
    thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
    
    # Render Categories
    for cat, items in categories.items():
        if not items: continue
        
        display_name = cat.title()
        if cat == 'individual': display_name = 'Individuals'
        if cat == 'company': display_name = 'Companies'
        if cat == 'product': display_name = 'Products/Technologies'
        if cat == 'aggregator': display_name = 'Engineering Blog Aggregators'
        
        lines.append(f"## <a name='{cat}'></a>{display_name}")
        lines.append("")
        
        # Group by first letter for better navigation within category? 
        # The original had this. Let's do simple list first, maybe add letter headers if list is long.
        # Original had "#### A companies" etc. Let's keep it simple for now: pure list.
        
        for blog in items:
            name = blog['name']
            url = blog['url']
            
            lines.append(f"* [{escape_md(name)}]({url})")
        
        lines.append("")
        lines.append("[⬆ Back to Top](#categories)")
        lines.append("")

    # Archive Link
    if archived_blogs:
        lines.append("## Archive")
        lines.append(f"View {len(archived_blogs)} archived/inactive blogs in [ARCHIVE.md](ARCHIVE.md).")
        lines.append("")

    # Contribute Section
    lines.append("## Contributing")
    lines.append("Found a broken link? Want to add a blog?")
    lines.append("- **Add a Blog**: Open an issue using the **Add Engineering Blog** template. Our daily workflow will automatically validate and add it!") 
    lines.append("- **Fix a Link**: Open a PR or an issue describing the fix.")

    # Function to smart update file
    def smart_update(path, new_lines, date_line_index):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            old_lines = old_content.split('\n')
            
            # Check if content matches (ignoring the date line)
            match = True
            if len(old_lines) != len(new_lines):
                match = False
            else:
                for i in range(len(new_lines)):
                    if i == date_line_index: continue
                    if new_lines[i] != old_lines[i]:
                        match = False
                        break
            
            if match:
                print(f"No changes detected in {path}, keeping existing timestamp.")
                # Use old line for date to preserve it
                if len(old_lines) > date_line_index:
                    new_lines[date_line_index] = old_lines[date_line_index]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"Generated {path}")

    # Write README.md
    smart_update(readme_path, lines, 2)

    # Write ARCHIVE.md (Always generate to ensure file exists for CI)
    alink = []
    alink.append("# Archived Engineering Blogs")
    alink.append(f"> These blogs were detected as invalid or inactive. Last updated: {today}")
    alink.append("")
    
    if archived_blogs:
        for blog in archived_blogs:
                alink.append(f"* {escape_md(blog['name'])} - {blog['url']} (Status: {blog.get('status')})")
    else:
        alink.append("No archived blogs currently.")
    
    # Write ARCHIVE.md - date is at index 1
    smart_update(archive_path, alink, 1)

if __name__ == "__main__":
    generate_readme()
