import os
import glob
import re

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), 'public')

# Load base template
base_path = os.path.join(PUBLIC_DIR, 'base.html')
with open(base_path, 'r', encoding='utf-8') as f:
    base_content = f.read()

# Replace url_for in base
base_content = re.sub(r"\{\{\s*url_for\('static',\s*filename='(.*?)'\)\s*\}\}", r"\1", base_content)
# Specifically, replace url_for('video_feed') and similar in base if any
base_content = re.sub(r"\{\{\s*url_for\('(.*?)'\)\s*\}\}", r"/\1", base_content)

# We want to replace {% block content %}{% endblock %} with `{content}` so we can format it
base_structure = re.sub(r"\{%\s*block\s+content\s*%\}[\s\S]*?\{%\s*endblock\s*%\}", "{content}", base_content)

html_files = glob.glob(os.path.join(PUBLIC_DIR, '*.html'))

for html_file in html_files:
    if os.path.basename(html_file) == 'base.html':
        continue
        
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check if it extends base
    if "{% extends 'base.html' %}" in content:
        # Extract block content
        match = re.search(r"\{%\s*block\s+content\s*%}([\s\S]*?)\{%\s*endblock\s*%}", content)
        if match:
            inner_content = match.group(1)
            
            # Replace url_for in inner_content
            inner_content = re.sub(r"\{\{\s*url_for\('static',\s*filename='(.*?)'\)\s*\}\}", r"\1", inner_content)
            inner_content = re.sub(r"\{\{\s*url_for\('(.*?)'\)\s*\}\}", r"\1.html", inner_content) # Convert routes to .html
            inner_content = re.sub(r"\{\{\s*url_for\('(.*?)',.*?\)\s*\}\}", r"\1.html", inner_content) 
            
            # Replace jinja variable injections with placeholders or defaults
            inner_content = re.sub(r"\{%.*?%\}", "", inner_content) # remove logic blocks like if/for
            inner_content = re.sub(r"\{\{.*?\}\}", "", inner_content) # remove variable prints
            
            # Special manual fix for video_feed src
            inner_content = inner_content.replace('src=""', 'src="/api/video_feed"')
            
            full_html = base_structure.replace("{content}", inner_content)
            
            # Write back
            with open(html_file, 'w', encoding='utf-8') as fh:
                fh.write(full_html)
                
    else:
        # Just replace url_for
        content = re.sub(r"\{\{\s*url_for\('static',\s*filename='(.*?)'\)\s*\}\}", r"\1", content)
        content = re.sub(r"\{\{\s*url_for\('(.*?)'\)\s*\}\}", r"\1.html", content)
        content = re.sub(r"\{%.*?%\}", "", content)
        content = re.sub(r"\{\{.*?\}\}", "", content)
        with open(html_file, 'w', encoding='utf-8') as fh:
            fh.write(content)

# Delete base.html as it's no longer needed
if os.path.exists(base_path):
    os.remove(base_path)

print("Conversion complete!")
