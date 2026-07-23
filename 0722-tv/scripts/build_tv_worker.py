#!/usr/bin/env python3
"""Build tv worker from HTML file by embedding it as a string in a worker wrapper."""
import sys

HTML_FILE = sys.argv[1] if len(sys.argv) > 1 else '/home/z/my-project/download/tv-app-v1.3.html'
TEMPLATE_FILE = '/home/z/my-project/scripts/tv_worker_template.js'
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else '/home/z/my-project/scripts/tv_worker_v1.3.js'

with open(HTML_FILE, 'r', encoding='utf8') as f:
    html = f.read()

with open(TEMPLATE_FILE, 'r', encoding='utf8') as f:
    template = f.read()

# Escape backticks, ${, and backslashes in HTML for safe embedding in a JS template literal
escaped = html.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

worker_code = template.replace('__HTML_BODY_PLACEHOLDER__', escaped)

with open(OUTPUT_FILE, 'w', encoding='utf8') as f:
    f.write(worker_code)

print(f'Built {OUTPUT_FILE}: {len(worker_code)} bytes (HTML: {len(html)} bytes)')
