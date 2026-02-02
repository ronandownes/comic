#!/usr/bin/env python3
"""
MATHS COMIC GALLERY BUILDER
===========================
version: v003
date: 2025-02-02

Creates flat WebP gallery from JPEGs with strand-based TOC.
Output: E:\comic\
  - index.html (strand TOC + viewer)
  - CCPP.webp files (topic-page)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

# CONFIG
SOURCE_PATH = Path(r"E:\comic")
OUTPUT_PATH = Path(r"E:\comic")
TOC_FILE = Path(r"E:\comic\toc.txt")
WEBP_QUALITY = 75

STRAND_COLORS = {
    'Number': '#e74c3c',
    'Algebra': '#9b59b6',
    'Geometry & Measurement': '#27ae60',
    'Statistics & Probability': '#3498db',
    'Logic & Problem Solving': '#f39c12'
}

def parse_toc(toc_path):
    """Parse strand-based TOC"""
    strands = []
    topics = {}
    current_strand = None
    
    if not toc_path.exists():
        print(f"✗ TOC not found: {toc_path}")
        return None, None
    
    with open(toc_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            if parts[0] == 'STRAND':
                current_strand = {
                    'name': parts[1],
                    'color': STRAND_COLORS.get(parts[1], '#666'),
                    'topics': []
                }
                strands.append(current_strand)
            elif parts[0] == 'TOPIC' and current_strand:
                num = int(parts[1])
                topic = {
                    'num': num,
                    'title': parts[2],
                    'orig_book': int(parts[3]),
                    'orig_chap': int(parts[4])
                }
                topics[num] = topic
                current_strand['topics'].append(topic)
    
    return strands, topics

def find_source_folder(book, chap):
    """Find source jpegs folder"""
    chap_folder = SOURCE_PATH / f"book-{book}" / f"chap{chap}"
    jpegs_folder = chap_folder / "jpegs"
    
    if jpegs_folder.exists():
        return jpegs_folder
    elif chap_folder.exists():
        return chap_folder
    return None

def convert_topic(src_folder, topic_num, dest_folder):
    """Convert JPEGs to WebPs with CCPP naming"""
    jpgs = sorted([f for f in src_folder.glob("*.jpg") if f.stem.isdigit()],
                  key=lambda f: int(f.stem))
    
    if not jpgs:
        return 0
    
    for jpg in jpgs:
        page_num = int(jpg.stem)
        new_name = f"{topic_num:02d}{page_num:02d}.webp"
        webp_path = dest_folder / new_name
        
        try:
            img = Image.open(jpg)
            img.save(webp_path, 'WEBP', quality=WEBP_QUALITY)
        except Exception as e:
            print(f"      ✗ {jpg.name}: {e}")
    
    return len(jpgs)

def generate_index(strands, page_counts):
    """Generate index with strand-based TOC"""
    
    # Build TOC HTML
    toc_html = ""
    js_topics = "{\n"
    
    for strand in strands:
        topic_count = len([t for t in strand['topics'] if page_counts.get(t['num'], 0) > 0])
        if topic_count == 0:
            continue
        
        topics_html = ""
        for t in strand['topics']:
            pages = page_counts.get(t['num'], 0)
            if pages == 0:
                continue
            
            topics_html += f'''
                <div class="topic" data-t="{t['num']}" onclick="openTopic({t['num']})">
                    <span class="topic-num">{t['num']}.</span>
                    <span class="topic-title">{t['title']}</span>
                    <span class="topic-pages">{pages}p</span>
                </div>'''
            
            js_topics += f'    {t["num"]}: {{title: "{t["title"]}", pages: {pages}}},\n'
        
        toc_html += f'''
        <div class="strand">
            <div class="strand-header" onclick="toggleStrand(this)" style="border-left: 4px solid {strand['color']}">
                <span class="strand-arrow">▶</span>
                <span class="strand-name">{strand['name']}</span>
                <span class="strand-count">{topic_count}</span>
            </div>
            <div class="strand-topics">{topics_html}
            </div>
        </div>'''
    
    js_topics += "}"
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>Maths Comic</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
            display: flex;
        }}
        
        /* TOC Toggle */
        .toc-toggle {{
            position: fixed;
            top: 50px;
            left: 0;
            z-index: 2000;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 0 6px 6px 0;
            padding: 10px 8px;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        }}
        .toc-toggle:hover {{ background: #764ba2; padding-left: 12px; }}
        
        /* TOC Sidebar */
        .toc-sidebar {{
            width: 320px;
            background: #222;
            border-right: 1px solid #333;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s, width 0.3s;
            z-index: 1000;
            flex-shrink: 0;
        }}
        body.toc-collapsed .toc-sidebar {{ transform: translateX(-320px); width: 0; }}
        
        .toc-header {{
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-bottom: 1px solid #333;
        }}
        .toc-header h1 {{ font-size: 18px; color: #fff; margin-bottom: 4px; }}
        .toc-header p {{ font-size: 12px; color: rgba(255,255,255,0.7); }}
        
        .toc-content {{
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }}
        .toc-content::-webkit-scrollbar {{ width: 6px; }}
        .toc-content::-webkit-scrollbar-thumb {{ background: #444; border-radius: 3px; }}
        
        /* Strands */
        .strand {{ margin-bottom: 8px; }}
        .strand-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 14px;
            background: #2a2a2a;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .strand-header:hover {{ background: #333; }}
        .strand-arrow {{
            font-size: 10px;
            color: #888;
            transition: transform 0.2s;
            width: 12px;
        }}
        .strand.expanded .strand-arrow {{ transform: rotate(90deg); }}
        .strand-name {{
            flex: 1;
            font-weight: 600;
            font-size: 14px;
        }}
        .strand-count {{
            background: #444;
            color: #aaa;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
        }}
        
        /* Topics */
        .strand-topics {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s;
        }}
        .strand.expanded .strand-topics {{ max-height: 2000px; }}
        
        .topic {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px 10px 30px;
            margin-top: 2px;
            background: #252525;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .topic:hover {{ background: #333; }}
        .topic.active {{ background: #667eea; }}
        .topic-num {{ color: #667eea; font-weight: 600; font-size: 12px; min-width: 28px; }}
        .topic.active .topic-num {{ color: #fff; }}
        .topic-title {{ flex: 1; font-size: 13px; }}
        .topic-pages {{ color: #555; font-size: 11px; }}
        .topic.active .topic-pages {{ color: rgba(255,255,255,0.7); }}
        
        /* Viewer */
        .viewer {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        /* Top bar */
        .top-bar {{
            background: #222;
            padding: 10px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
            min-height: 50px;
        }}
        .topic-name {{
            font-size: 15px;
            color: #fff;
        }}
        .topic-name strong {{ color: #667eea; }}
        .top-right {{ display: flex; align-items: center; gap: 12px; }}
        .page-info {{ font-size: 13px; color: #888; }}
        .page-info span {{ color: #fff; }}
        
        .copy-btn {{
            background: #333;
            border: 1px solid #444;
            color: #ccc;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
        }}
        .copy-btn:hover {{ background: #444; }}
        .copy-btn.copied {{ background: #27ae60; border-color: #27ae60; color: #fff; }}
        
        /* Image */
        .image-container {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            overflow: auto;
            background: #111;
        }}
        .image-container img {{
            width: 100%;
            max-width: 950px;
            height: auto;
        }}
        
        /* Side nav */
        .side-nav {{
            position: fixed;
            top: 50%;
            transform: translateY(-50%);
            z-index: 100;
            background: rgba(0,0,0,0.6);
            color: #fff;
            border: none;
            width: 50px;
            height: 120px;
            font-size: 26px;
            cursor: pointer;
            opacity: 0.4;
            transition: opacity 0.2s, background 0.2s;
        }}
        .side-nav:hover {{ opacity: 1; background: #667eea; }}
        .side-nav:disabled {{ opacity: 0.15; cursor: default; background: rgba(0,0,0,0.6); }}
        .side-nav.prev {{ left: 0; border-radius: 0 10px 10px 0; }}
        .side-nav.next {{ right: 0; border-radius: 10px 0 0 10px; }}
        
        /* Landing */
        .landing {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 40px;
        }}
        .landing h1 {{ font-size: 2rem; margin-bottom: 10px; }}
        .landing p {{ color: #888; margin-bottom: 20px; }}
        .landing-hint {{ color: #667eea; }}
        
        .viewer-content {{ display: none; flex: 1; flex-direction: column; }}
        .viewer-content.active {{ display: flex; }}
        
        /* Mobile */
        @media (max-width: 600px) {{
            .toc-sidebar {{ width: 280px; }}
            body.toc-collapsed .toc-sidebar {{ transform: translateX(-280px); }}
            .side-nav {{ width: 40px; height: 80px; font-size: 20px; }}
        }}
    </style>
</head>
<body class="toc-collapsed">

<button class="toc-toggle" onclick="toggleTOC()">📖</button>

<div class="toc-sidebar">
    <div class="toc-header">
        <h1>📚 Maths Comic</h1>
        <p>5 Strands · 60 Topics</p>
    </div>
    <div class="toc-content">{toc_html}
    </div>
</div>

<div class="viewer">
    <div class="landing" id="landing">
        <h1>📚 Maths Comic</h1>
        <p>60 Topics · JC Aligned</p>
        <div class="landing-hint">← Open menu to select a topic</div>
    </div>
    
    <div class="viewer-content" id="viewerContent">
        <div class="top-bar">
            <div class="topic-name" id="topicName"></div>
            <div class="top-right">
                <div class="page-info"><span id="pageNum">1</span> / <span id="totalPages">1</span></div>
                <button class="copy-btn" onclick="copyLink()">🔗 Copy</button>
            </div>
        </div>
        <div class="image-container" id="imageContainer">
            <img id="pageImage" src="" alt="">
        </div>
    </div>
</div>

<button class="side-nav prev" id="prevBtn" onclick="prevPage()" style="display:none;">◀</button>
<button class="side-nav next" id="nextBtn" onclick="nextPage()" style="display:none;">▶</button>

<script>
const topics = {js_topics};

let currentTopic = 0;
let currentPage = 1;
let totalPages = 1;

function toggleTOC() {{
    document.body.classList.toggle('toc-collapsed');
}}

function toggleStrand(el) {{
    el.parentElement.classList.toggle('expanded');
}}

function openTopic(t) {{
    if (!topics[t]) return;
    
    currentTopic = t;
    totalPages = topics[t].pages;
    currentPage = 1;
    
    // Check URL for page
    const params = new URLSearchParams(location.search);
    if (parseInt(params.get('t')) === t && params.get('p')) {{
        currentPage = Math.max(1, Math.min(totalPages, parseInt(params.get('p'))));
    }}
    
    // Update UI
    document.getElementById('landing').style.display = 'none';
    document.getElementById('viewerContent').classList.add('active');
    document.getElementById('prevBtn').style.display = 'flex';
    document.getElementById('nextBtn').style.display = 'flex';
    document.getElementById('topicName').innerHTML = '<strong>' + t + '.</strong> ' + topics[t].title;
    document.getElementById('totalPages').textContent = totalPages;
    
    // Update active state
    document.querySelectorAll('.topic').forEach(el => {{
        el.classList.toggle('active', parseInt(el.dataset.t) === t);
    }});
    
    // Close TOC on mobile
    if (window.innerWidth <= 600) toggleTOC();
    
    updatePage();
}}

function updatePage() {{
    const img = String(currentTopic).padStart(2,'0') + String(currentPage).padStart(2,'0') + '.webp';
    document.getElementById('pageImage').src = img;
    document.getElementById('pageNum').textContent = currentPage;
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    history.replaceState(null, '', '?t=' + currentTopic + '&p=' + currentPage);
}}

function prevPage() {{ if (currentPage > 1) {{ currentPage--; updatePage(); }} }}
function nextPage() {{ if (currentPage < totalPages) {{ currentPage++; updatePage(); }} }}

function copyLink() {{
    navigator.clipboard.writeText(location.href).then(() => {{
        const b = document.querySelector('.copy-btn');
        b.classList.add('copied');
        b.textContent = '✓ Copied!';
        setTimeout(() => {{ b.classList.remove('copied'); b.textContent = '🔗 Copy'; }}, 2000);
    }});
}}

// Keyboard
document.addEventListener('keydown', e => {{
    if (e.key === 'ArrowLeft') prevPage();
    if (e.key === 'ArrowRight') nextPage();
    if (e.key === 't' || e.key === 'T') toggleTOC();
}});

// Touch swipe
let touchX = 0;
document.getElementById('imageContainer').addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }});
document.getElementById('imageContainer').addEventListener('touchend', e => {{
    const diff = e.changedTouches[0].clientX - touchX;
    if (Math.abs(diff) > 50) diff > 0 ? prevPage() : nextPage();
}});

// Load from URL
window.onload = () => {{
    const params = new URLSearchParams(location.search);
    const t = parseInt(params.get('t'));
    if (t && topics[t]) {{
        openTopic(t);
        // Expand parent strand
        document.querySelectorAll('.topic').forEach(el => {{
            if (parseInt(el.dataset.t) === t) {{
                el.closest('.strand').classList.add('expanded');
            }}
        }});
    }} else {{
        // Show TOC, expand first strand
        document.body.classList.remove('toc-collapsed');
        const first = document.querySelector('.strand');
        if (first) first.classList.add('expanded');
    }}
}};
</script>
</body>
</html>'''

def main():
    print("=" * 50)
    print("MATHS COMIC GALLERY BUILDER v003")
    print("=" * 50)
    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 50)
    
    # Parse TOC
    strands, topics = parse_toc(TOC_FILE)
    if not topics:
        return
    
    print(f"\n📚 {len(strands)} strands, {len(topics)} topics")
    
    # Check which topics have source files
    found = []
    for num, t in topics.items():
        src = find_source_folder(t['orig_book'], t['orig_chap'])
        if src:
            jpgs = [f for f in src.glob("*.jpg") if f.stem.isdigit()]
            if jpgs:
                found.append((num, t, src, len(jpgs)))
                print(f"  {num:02d}. {t['title']} ({len(jpgs)}p)")
    
    if not found:
        print("\n✗ No source files found")
        return
    
    print(f"\n✓ Found {len(found)} topics with files")
    
    confirm = input("\nBuild gallery? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return
    
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    # Convert all topics
    print("\n" + "=" * 50)
    page_counts = {}
    
    for num, t, src, _ in found:
        print(f"\n{num:02d}. {t['title']}")
        count = convert_topic(src, num, OUTPUT_PATH)
        page_counts[num] = count
        print(f"    ✓ {count} pages")
    
    # Generate index
    print("\n" + "=" * 50)
    index_html = generate_index(strands, page_counts)
    (OUTPUT_PATH / "index.html").write_text(index_html, encoding='utf-8')
    print("✓ index.html")
    
    # Summary
    total_files = sum(page_counts.values())
    print(f"\n{'=' * 50}")
    print(f"✓ Done!")
    print(f"  Topics: {len(page_counts)}")
    print(f"  Files: {total_files} WebPs")
    print(f"  Output: {OUTPUT_PATH}")
    
    # Cleanup option
    cleanup = input("\nDelete book-* folders (JPEGs)? (y/n): ").strip().lower()
    if cleanup == 'y':
        for folder in OUTPUT_PATH.glob("book-*"):
            if folder.is_dir():
                shutil.rmtree(folder)
                print(f"  ✓ Deleted {folder.name}")
        print("✓ Cleanup done")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
