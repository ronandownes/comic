#!/usr/bin/env python3
"""
FLAT GALLERY BUILDER (JC Aligned)
=================================
version: v003
date: 2025-02-01

Creates flat structure with TOC sidebar viewer:
  comic/
  ├── index.html  (TOC sidebar + viewer)
  ├── 0101.webp   (Ch01 Page01)
  └── ...

60 chapters, CCPP naming, single page with sidebar TOC.
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
SOURCE_PATH = Path(r"E:\maths-comic")  # Your JPEGs (keep safe)
OUTPUT_PATH = Path(r"E:\comic")        # WebPs only (for GitHub)
TOC_FILE = Path(r"E:\comic\toc.txt")
WEBP_QUALITY = 75

def parse_toc(toc_path):
    """Parse JC-aligned TOC"""
    chapters = {}
    
    if not toc_path.exists():
        print(f"✗ TOC not found: {toc_path}")
        return None
    
    with open(toc_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            if parts[0] == 'CHAPTER':
                new_num = int(parts[1])
                title = parts[2]
                orig_book = int(parts[3])
                orig_chap = int(parts[4])
                
                chapters[new_num] = {
                    'title': title,
                    'orig_book': orig_book,
                    'orig_chap': orig_chap
                }
    
    return chapters

def find_source_folder(book, chap):
    """Find source jpegs folder"""
    chap_folder = SOURCE_PATH / f"book-{book}" / f"chap{chap}"
    jpegs_folder = chap_folder / "jpegs"
    
    if jpegs_folder.exists():
        return jpegs_folder
    elif chap_folder.exists():
        return chap_folder
    return None

def convert_chapter(src_folder, new_chap_num, dest_folder):
    """Convert JPEGs to WebPs with CCPP naming"""
    jpgs = sorted([f for f in src_folder.glob("*.jpg") if f.stem.isdigit()],
                  key=lambda f: int(f.stem))
    
    if not jpgs:
        return 0
    
    for jpg in jpgs:
        page_num = int(jpg.stem)
        new_name = f"{new_chap_num:02d}{page_num:02d}.webp"
        webp_path = dest_folder / new_name
        
        try:
            img = Image.open(jpg)
            img.save(webp_path, 'WEBP', quality=WEBP_QUALITY)
        except Exception as e:
            print(f"      ✗ {jpg.name}: {e}")
    
    return len(jpgs)

def generate_index(chapters, page_counts):
    """Generate single index with TOC sidebar viewer"""
    
    # Build TOC sidebar HTML
    toc_html = ""
    js_chapters = "{\n"
    
    for num in sorted(chapters.keys()):
        ch = chapters[num]
        pages = page_counts.get(num, 0)
        if pages == 0:
            continue
        
        toc_html += f'''
            <div class="toc-item" data-ch="{num}" onclick="openChapter({num})">
                <span class="toc-num">{num}.</span>
                <span class="toc-title">{ch['title']}</span>
                <span class="toc-pages">{pages}p</span>
            </div>'''
        
        js_chapters += f'    {num}: {{title: "{ch["title"]}", pages: {pages}}},\n'
    
    js_chapters += "}"
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>Maths Comic</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ touch-action: pan-x pan-y; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
            display: flex;
        }}
        
        /* TOC Toggle Button */
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
            width: 300px;
            background: #222;
            border-right: 1px solid #333;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s, width 0.3s;
            z-index: 1000;
            flex-shrink: 0;
        }}
        body.toc-collapsed .toc-sidebar {{ transform: translateX(-300px); width: 0; }}
        
        .toc-header {{
            padding: 12px 15px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .toc-header h2 {{ font-size: 15px; color: #fff; font-weight: 600; }}
        .toc-close {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: #fff;
            font-size: 18px;
            cursor: pointer;
            padding: 2px 8px;
            border-radius: 4px;
        }}
        .toc-close:hover {{ background: rgba(255,255,255,0.3); }}
        
        .toc-content {{
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }}
        .toc-content::-webkit-scrollbar {{ width: 6px; }}
        .toc-content::-webkit-scrollbar-thumb {{ background: #444; border-radius: 3px; }}
        
        .toc-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            margin-bottom: 4px;
            background: #2a2a2a;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .toc-item:hover {{ background: #333; }}
        .toc-item.active {{ background: #667eea; }}
        .toc-num {{ color: #667eea; font-weight: 700; font-size: 13px; min-width: 28px; }}
        .toc-item.active .toc-num {{ color: #fff; }}
        .toc-title {{ flex: 1; font-size: 13px; }}
        .toc-pages {{ color: #666; font-size: 11px; }}
        .toc-item.active .toc-pages {{ color: rgba(255,255,255,0.7); }}
        
        /* Viewer */
        .viewer {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }}
        
        /* Minimal top bar */
        .top-bar {{
            background: #222;
            padding: 8px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #333;
        }}
        .chapter-title {{
            font-size: 14px;
            color: #ccc;
        }}
        .chapter-title strong {{ color: #fff; }}
        
        .top-right {{ display: flex; align-items: center; gap: 10px; }}
        
        .page-info {{
            font-size: 13px;
            color: #888;
        }}
        .page-info span {{ color: #fff; }}
        
        .copy-btn {{
            background: #333;
            border: 1px solid #444;
            color: #ccc;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{ background: #444; }}
        .copy-btn.copied {{ background: #27ae60; border-color: #27ae60; color: #fff; }}
        
        /* Image container - fit width by default */
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
            display: block;
        }}
        
        /* Side nav buttons */
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
        
        /* Landing state */
        .landing {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
            text-align: center;
        }}
        .landing h1 {{ font-size: 2rem; margin-bottom: 10px; color: #fff; }}
        .landing p {{ color: #888; margin-bottom: 30px; }}
        .landing-hint {{ color: #667eea; font-size: 14px; }}
        
        .viewer-content {{ display: none; flex: 1; flex-direction: column; }}
        .viewer-content.active {{ display: flex; }}
        
        /* Mobile */
        @media (max-width: 600px) {{
            .toc-sidebar {{ width: 260px; }}
            body.toc-collapsed .toc-sidebar {{ transform: translateX(-260px); }}
            .side-nav {{ width: 40px; height: 80px; font-size: 20px; }}
            .top-bar {{ padding: 6px 10px; }}
            .chapter-title {{ font-size: 12px; }}
        }}
    </style>
</head>
<body class="toc-collapsed">

<button class="toc-toggle" onclick="toggleTOC()" title="Contents">📖</button>

<div class="toc-sidebar">
    <div class="toc-header">
        <h2>📚 60 Chapters</h2>
        <button class="toc-close" onclick="toggleTOC()">×</button>
    </div>
    <div class="toc-content" id="tocContent">
        {toc_html}
    </div>
</div>

<div class="viewer">
    <!-- Landing -->
    <div class="landing" id="landing">
        <h1>📚 Maths Comic</h1>
        <p>60 Chapters · JC Aligned</p>
        <div class="landing-hint">← Open menu to select a chapter</div>
    </div>
    
    <!-- Viewer Content -->
    <div class="viewer-content" id="viewerContent">
        <div class="top-bar">
            <div class="chapter-title" id="chapterTitle"></div>
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
const chapters = {js_chapters};

let currentChapter = 0;
let currentPage = 1;
let totalPages = 1;

function toggleTOC() {{
    document.body.classList.toggle('toc-collapsed');
}}

function openChapter(ch) {{
    if (!chapters[ch]) return;
    
    currentChapter = ch;
    totalPages = chapters[ch].pages;
    currentPage = 1;
    
    // Check URL for page
    const params = new URLSearchParams(location.search);
    if (parseInt(params.get('c')) === ch && params.get('p')) {{
        currentPage = Math.max(1, Math.min(totalPages, parseInt(params.get('p'))));
    }}
    
    // Update UI
    document.getElementById('landing').style.display = 'none';
    document.getElementById('viewerContent').classList.add('active');
    document.getElementById('prevBtn').style.display = 'flex';
    document.getElementById('nextBtn').style.display = 'flex';
    document.getElementById('chapterTitle').innerHTML = '<strong>' + ch + '.</strong> ' + chapters[ch].title;
    document.getElementById('totalPages').textContent = totalPages;
    
    // Update TOC active state
    document.querySelectorAll('.toc-item').forEach(el => {{
        el.classList.toggle('active', parseInt(el.dataset.ch) === ch);
    }});
    
    // Close TOC on mobile
    if (window.innerWidth <= 600) toggleTOC();
    
    updatePage();
}}

function updatePage() {{
    const img = String(currentChapter).padStart(2,'0') + String(currentPage).padStart(2,'0') + '.webp';
    document.getElementById('pageImage').src = img;
    document.getElementById('pageNum').textContent = currentPage;
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
    history.replaceState(null, '', '?c=' + currentChapter + '&p=' + currentPage);
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
    const c = parseInt(params.get('c'));
    if (c && chapters[c]) {{
        openChapter(c);
    }} else {{
        // Show TOC by default on landing
        document.body.classList.remove('toc-collapsed');
    }}
}};
</script>
</body>
</html>'''

def main():
    print("=" * 50)
    print("FLAT GALLERY BUILDER v002 (JC Aligned)")
    print("=" * 50)
    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 50)
    
    # Parse TOC
    chapters = parse_toc(TOC_FILE)
    if not chapters:
        return
    
    print(f"\n📚 {len(chapters)} chapters in TOC")
    
    # Check which chapters have source files
    found = []
    for num, ch in chapters.items():
        src = find_source_folder(ch['orig_book'], ch['orig_chap'])
        if src:
            jpgs = [f for f in src.glob("*.jpg") if f.stem.isdigit()]
            if jpgs:
                found.append((num, ch, src, len(jpgs)))
                print(f"  {num:02d}. {ch['title']} ({len(jpgs)}p)")
    
    if not found:
        print("\n✗ No source files found")
        return
    
    print(f"\n✓ Found {len(found)} chapters with files")
    
    confirm = input("\nBuild gallery? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return
    
    # DON'T clear output since source=output
    # Just add WebPs alongside existing files
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    # Convert all chapters
    print("\n" + "=" * 50)
    page_counts = {}
    
    for num, ch, src, _ in found:
        print(f"\n{num:02d}. {ch['title']}")
        count = convert_chapter(src, num, OUTPUT_PATH)
        page_counts[num] = count
        print(f"    ✓ {count} pages")
    
    # Generate index
    print("\n" + "=" * 50)
    index_html = generate_index(chapters, page_counts)
    (OUTPUT_PATH / "index.html").write_text(index_html, encoding='utf-8')
    print("✓ index.html")
    
    # Summary
    total_files = sum(page_counts.values())
    print(f"\n{'=' * 50}")
    print(f"✓ Done!")
    print(f"  Chapters: {len(page_counts)}")
    print(f"  Files: {total_files} WebPs")
    print(f"  Output: {OUTPUT_PATH}")
    
    # Offer to delete source folders
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
