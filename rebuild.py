#!/usr/bin/env python3
"""
MATHS COMIC REBUILD
===================
version: 1.0
date: 2025-02-02

Combined script for:
  1. Rebuilding index.html from existing WebPs (fast)
  2. Converting JPEGs to WebPs + building index (full build)

Usage:
  python rebuild.py          # Interactive menu
  python rebuild.py index    # Just rebuild index.html
  python rebuild.py convert  # Convert JPEGs + rebuild index
"""

import os
import sys
import subprocess
import shutil
import re
from pathlib import Path

# ============================================================
# CONFIG - Edit these paths for your setup
# ============================================================
COMIC_PATH = Path(r"E:\comic")          # Main folder (WebPs + index.html)
SOURCE_PATH = Path(r"E:\comic")          # Where book-*/chap*/jpegs/ folders are
TOC_FILE = COMIC_PATH / "toc.txt"        # Your TOC file
WEBP_QUALITY = 75                        # WebP quality (1-100)
IMG_FOLDER = "webp"                      # Subfolder for images (blank = same as index.html)
# ============================================================

# Strand colors for TOC
STRAND_COLORS = {
    'Number':                   ('red',    '#e53935'),
    'Algebra':                  ('blue',   '#1e88e5'),
    'Geometry & Measurement':   ('green',  '#43a047'),
    'Statistics & Probability': ('orange', '#fb8c00'),
    'Logic & Problem Solving':  ('purple', '#8e24aa'),
}

def parse_toc(toc_path):
    """Parse strand-based TOC file"""
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
                name = parts[1]
                color_key, color_hex = STRAND_COLORS.get(name, ('grey', '#666'))
                current_strand = {
                    'name': name,
                    'color_key': color_key,
                    'color_hex': color_hex,
                    'topics': []
                }
                strands.append(current_strand)
            elif parts[0] == 'TOPIC' and current_strand:
                num = int(parts[1])
                topic = {
                    'num': num,
                    'title': parts[2],
                    'orig_book': int(parts[3]) if len(parts) > 3 else 0,
                    'orig_chap': int(parts[4]) if len(parts) > 4 else 0
                }
                topics[num] = topic
                current_strand['topics'].append(topic)
    
    return strands, topics

def scan_webps(folder):
    """Scan WebPs and count pages per topic"""
    page_counts = {}
    
    for f in folder.glob("*.webp"):
        # Match TTPP format (2 digit topic, 2 digit page)
        m = re.match(r'^(\d{2})(\d{2})\.webp$', f.name)
        if m:
            topic = int(m.group(1))
            page = int(m.group(2))
            if topic not in page_counts:
                page_counts[topic] = 0
            page_counts[topic] = max(page_counts[topic], page)
    
    return page_counts

def find_source_folder(book, chap):
    """Find source JPEGs folder"""
    chap_folder = SOURCE_PATH / f"book-{book}" / f"chap{chap}"
    jpegs_folder = chap_folder / "jpegs"
    
    if jpegs_folder.exists():
        return jpegs_folder
    elif chap_folder.exists():
        return chap_folder
    return None

def convert_topic(src_folder, topic_num, dest_folder):
    """Convert JPEGs to WebPs with TTPP naming"""
    try:
        from PIL import Image
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image
    
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
    """Generate index.html with improved viewer"""
    
    # Build TOC HTML
    toc_html = ""
    js_topics = "{\n"
    total_topics = 0
    
    for strand in strands:
        topic_items = [t for t in strand['topics'] if page_counts.get(t['num'], 0) > 0]
        if not topic_items:
            continue
        
        total_topics += len(topic_items)
        
        topics_html = ""
        for t in topic_items:
            pages = page_counts[t['num']]
            topics_html += f'''
                <div class="topic" data-t="{t['num']}" onclick="openTopic({t['num']})">
                    <span class="topic-num">{t['num']}.</span>
                    <span class="topic-title">{t['title']}</span>
                </div>'''
            js_topics += f'    {t["num"]}: {{title: "{t["title"]}", pages: {pages}}},\n'
        
        toc_html += f'''
        <div class="strand" data-color="{strand['color_key']}">
            <div class="strand-header" onclick="toggleStrand(this)">
                <span class="strand-arrow">▶</span>
                <span class="strand-name">{strand['name']}</span>
                <span class="strand-count">{len(topic_items)}</span>
            </div>
            <div class="strand-topics">{topics_html}
            </div>
        </div>'''
    
    js_topics += "}"
    
    # Image path prefix (for subfolder support)
    img_prefix = f"{IMG_FOLDER}/" if IMG_FOLDER else ""
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
    <title>Maths Comic</title>
    <!-- ============ TRACKING SCRIPTS ============ -->
    <!-- Add Google Analytics, Plausible, etc. here -->
    <!-- ============ END TRACKING ============ -->
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ height: 100%; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            height: 100%;
            overflow: hidden;
            display: flex;
        }}
        
        /* TOC Toggle Button */
        .toc-toggle {{
            position: fixed;
            top: 8px;
            left: 0;
            z-index: 2000;
            background: #0066cc;
            color: white;
            border: none;
            border-radius: 0 4px 4px 0;
            padding: 6px 5px;
            cursor: pointer;
            font-size: 12px;
            box-shadow: 1px 1px 4px rgba(0,0,0,0.15);
        }}
        .toc-toggle:hover {{ background: #0080ff; }}
        
        /* Sidebar */
        .toc-sidebar {{
            width: 200px;
            background: #fff;
            border-right: 1px solid #ddd;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s, width 0.2s;
            z-index: 1000;
            flex-shrink: 0;
        }}
        body.toc-collapsed .toc-sidebar {{ transform: translateX(-200px); width: 0; }}
        
        .toc-header {{
            padding: 8px 10px;
            background: #fff;
            border-bottom: 1px solid #eee;
        }}
        .toc-header h1 {{ font-size: 13px; color: #333; font-weight: 600; }}
        
        .toc-content {{ flex: 1; overflow-y: auto; padding: 4px; }}
        .toc-content::-webkit-scrollbar {{ width: 4px; }}
        .toc-content::-webkit-scrollbar-thumb {{ background: #ccc; border-radius: 2px; }}
        
        /* Strands */
        .strand {{ margin-bottom: 2px; }}
        .strand-header {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 8px;
            background: #f8f8f8;
            border-radius: 3px;
            cursor: pointer;
            border-left: 3px solid transparent;
        }}
        .strand-header:hover {{ background: #f0f0f0; }}
        .strand-arrow {{ font-size: 8px; color: #999; transition: transform 0.2s; width: 10px; }}
        .strand.expanded .strand-arrow {{ transform: rotate(90deg); }}
        .strand-name {{ flex: 1; font-weight: 500; font-size: 11px; color: #444; }}
        .strand-count {{ color: #999; font-size: 9px; }}
        
        /* Strand Colors */
        .strand[data-color="red"] .strand-header {{ border-left-color: #e53935; }}
        .strand[data-color="blue"] .strand-header {{ border-left-color: #1e88e5; }}
        .strand[data-color="green"] .strand-header {{ border-left-color: #43a047; }}
        .strand[data-color="orange"] .strand-header {{ border-left-color: #fb8c00; }}
        .strand[data-color="purple"] .strand-header {{ border-left-color: #8e24aa; }}
        
        /* Topics List */
        .strand-topics {{ max-height: 0; overflow: hidden; transition: max-height 0.2s; }}
        .strand.expanded .strand-topics {{ max-height: 2000px; }}
        
        /* Individual Topics */
        .topic {{
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 6px 4px 16px;
            cursor: pointer;
            border-radius: 2px;
        }}
        .topic:hover {{ background: #f0f0f0; }}
        .topic.active {{ background: #e3f2fd; }}
        .topic-num {{ color: #888; font-size: 9px; min-width: 18px; }}
        .topic.active .topic-num {{ color: #1e88e5; font-weight: 600; }}
        .topic-title {{ flex: 1; font-size: 10px; color: #555; line-height: 1.3; }}
        .topic.active .topic-title {{ color: #1e88e5; }}
        
        /* Main Viewer */
        .viewer {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #fff; min-height: 0; }}
        
        /* Controls Bar */
        .controls {{
            background: #fff;
            padding: 4px 10px;
            display: flex;
            justify-content: center;
            align-items: center;
            border-bottom: 1px solid #eee;
            gap: 6px;
            min-height: 36px;
            flex-shrink: 0;
        }}
        
        .topic-name {{ font-size: 12px; color: #333; margin-right: auto; }}
        .topic-name strong {{ color: #1e88e5; }}
        
        button {{
            background: #f5f5f5;
            border: 1px solid #ddd;
            color: #555;
            padding: 4px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            min-width: 28px;
            height: 26px;
        }}
        button:hover {{ background: #eee; border-color: #ccc; }}
        button.active {{ background: #1e88e5; border-color: #1e88e5; color: #fff; }}
        button:disabled {{ opacity: 0.4; cursor: default; }}
        
        .sep {{ width: 1px; height: 16px; background: #ddd; }}
        .page-info {{ font-size: 11px; color: #888; display: flex; align-items: center; gap: 2px; }}
        .page-info span {{ color: #333; }}
        .page-input {{
            width: 32px;
            text-align: center;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 11px;
            padding: 2px 4px;
            color: #333;
            background: #fff;
        }}
        .page-input:focus {{ outline: none; border-color: #1e88e5; }}
        .page-input::-webkit-inner-spin-button {{ -webkit-appearance: none; }}
        
        /* Image Container */
        .image-container {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            overflow: auto;
            background: #e8e8e8;
            position: relative;
            min-height: 0; /* Critical for flex height to work */
            -webkit-overflow-scrolling: touch;
        }}
        .image-container img {{ 
            display: block; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.15); 
            background: #fff;
        }}
        .image-container.fit-height {{ 
            align-items: center;
            overflow: hidden; /* No scroll when fit */
        }}
        .image-container.fit-height img {{ 
            max-height: 100%;
            max-width: 100%;
            width: auto; 
            height: auto;
            object-fit: contain;
        }}
        .image-container.fit-width img {{ 
            width: 100%; 
            max-width: 900px; 
            height: auto;
        }}
        
        .zoom-indicator {{
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0,0,0,0.6);
            color: white;
            padding: 3px 6px;
            border-radius: 3px;
            font-size: 10px;
            display: none;
        }}
        
        /* Side Navigation */
        .side-nav {{
            position: fixed;
            top: 50%;
            transform: translateY(-50%);
            z-index: 100;
            background: rgba(0,0,0,0.3);
            color: #fff;
            border: none;
            width: 36px;
            height: 80px;
            font-size: 18px;
            cursor: pointer;
            opacity: 0.5;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .side-nav:hover {{ opacity: 1; background: #1e88e5; }}
        .side-nav:disabled {{ opacity: 0.2; cursor: default; background: rgba(0,0,0,0.3); }}
        .side-nav.prev {{ left: 0; border-radius: 0 4px 4px 0; }}
        .side-nav.next {{ right: 0; border-radius: 4px 0 0 4px; }}
        
        /* Landing */
        .landing {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 40px;
            background: #fff;
        }}
        .landing h1 {{ font-size: 1.5rem; color: #333; margin-bottom: 8px; font-weight: 500; }}
        .landing p {{ color: #888; font-size: 13px; }}
        
        .viewer-content {{ display: none; flex: 1; flex-direction: column; }}
        .viewer-content.active {{ display: flex; }}
        
        .image-container::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        .image-container::-webkit-scrollbar-thumb {{ background: #ccc; border-radius: 3px; }}
        
        @media (max-width: 600px) {{
            .toc-sidebar {{ width: 180px; }}
            body.toc-collapsed .toc-sidebar {{ transform: translateX(-180px); }}
            .controls {{ padding: 4px 6px; gap: 4px; }}
            .side-nav {{ width: 30px; height: 60px; font-size: 14px; }}
        }}
    </style>
</head>
<body class="toc-collapsed">

<button class="toc-toggle" onclick="toggleTOC()">☰</button>

<div class="toc-sidebar">
    <div class="toc-header">
        <h1>📚 Contents</h1>
    </div>
    <div class="toc-content">{toc_html}
    </div>
</div>

<div class="viewer">
    <div class="landing" id="landing">
        <h1>📚 Maths Comic</h1>
        <p>A site designed to make reading maths simple and fun</p>
    </div>
    
    <div class="viewer-content" id="viewerContent">
        <div class="controls">
            <div class="topic-name" id="topicName"></div>
            <button id="fitHeight" onclick="setFitMode('height')" title="Fit Height (H)">↕</button>
            <button id="fitWidth" onclick="setFitMode('width')" title="Fit Width (W)">↔</button>
            <div class="sep"></div>
            <button onclick="zoomOut()" title="Zoom Out (-)">−</button>
            <button onclick="zoomIn()" title="Zoom In (+)">+</button>
            <div class="sep"></div>
            <div class="page-info"><input type="number" id="pageNum" class="page-input" value="1" min="1"> / <span id="totalPages">1</span></div>
        </div>
        <div class="image-container" id="imageContainer">
            <img id="pageImage" src="" alt="">
            <div class="zoom-indicator" id="zoomIndicator">100%</div>
        </div>
    </div>
</div>

<button class="side-nav prev" id="prevBtn" onclick="loadPage(currentPage-1)" style="display:none;">◀</button>
<button class="side-nav next" id="nextBtn" onclick="loadPage(currentPage+1)" style="display:none;">▶</button>

<script>
const IMG_PREFIX = '{img_prefix}';
const topics = {js_topics};

let currentTopic = 0;
let currentPage = 1;
let totalPages = 1;
let zoom = 1.0;
let fitMode = localStorage.getItem('fitMode') || 'height';

const $ = id => document.getElementById(id);

function toggleTOC() {{ document.body.classList.toggle('toc-collapsed'); }}
function toggleStrand(el) {{ el.parentElement.classList.toggle('expanded'); }}

function openTopic(t) {{
    if (!topics[t]) return;
    
    currentTopic = t;
    totalPages = topics[t].pages;
    currentPage = 1;
    
    const params = new URLSearchParams(location.search);
    if (parseInt(params.get('t')) === t && params.get('p')) {{
        currentPage = Math.max(1, Math.min(totalPages, parseInt(params.get('p'))));
    }}
    
    $('landing').style.display = 'none';
    $('viewerContent').classList.add('active');
    $('prevBtn').style.display = 'flex';
    $('nextBtn').style.display = 'flex';
    $('topicName').innerHTML = '<strong>' + t + '.</strong> ' + topics[t].title;
    $('totalPages').textContent = totalPages;
    $('pageNum').max = totalPages;
    
    document.querySelectorAll('.topic').forEach(el => {{
        el.classList.toggle('active', parseInt(el.dataset.t) === t);
    }});
    
    if (window.innerWidth <= 600) toggleTOC();
    loadPage(currentPage);
}}

function loadPage(p) {{
    if (p < 1 || p > totalPages) return;
    currentPage = p;
    const img = IMG_PREFIX + String(currentTopic).padStart(2,'0') + String(currentPage).padStart(2,'0') + '.webp';
    $('pageImage').src = img;
    $('pageNum').value = currentPage;
    $('prevBtn').disabled = currentPage <= 1;
    $('nextBtn').disabled = currentPage >= totalPages;
    history.replaceState(null, '', '?t=' + currentTopic + '&p=' + currentPage);
    resetZoom();
    $('imageContainer').scrollTop = 0;
    $('imageContainer').scrollLeft = 0;
}}

function updateZoom() {{
    const img = $('pageImage');
    const container = $('imageContainer');
    
    // Remove fit classes temporarily for manual zoom
    if (zoom !== 1) {{
        container.classList.remove('fit-height', 'fit-width');
        container.style.overflow = 'auto'; // Allow scroll when zoomed
        // Set actual dimensions based on zoom
        img.style.width = (zoom * 100) + '%';
        img.style.height = 'auto';
        img.style.maxWidth = 'none';
        img.style.maxHeight = 'none';
    }} else {{
        // Reset to fit mode
        img.style.width = '';
        img.style.height = '';
        img.style.maxWidth = '';
        img.style.maxHeight = '';
        container.style.overflow = '';
        container.classList.add('fit-' + fitMode);
    }}
    
    $('zoomIndicator').textContent = Math.round(zoom * 100) + '%';
    $('zoomIndicator').style.display = zoom !== 1 ? 'block' : 'none';
}}

function zoomIn() {{ zoom = Math.min(3, zoom + 0.25); updateZoom(); }}
function zoomOut() {{ zoom = Math.max(0.5, zoom - 0.25); updateZoom(); }}
function resetZoom() {{ zoom = 1; updateZoom(); }}

function setFitMode(mode) {{
    fitMode = mode;
    zoom = 1; // Reset zoom when changing fit mode
    const img = $('pageImage');
    img.style.width = '';
    img.style.height = '';
    img.style.maxWidth = '';
    img.style.maxHeight = '';
    
    const c = $('imageContainer');
    c.style.overflow = '';
    c.classList.remove('fit-height', 'fit-width');
    c.classList.add('fit-' + mode);
    $('fitHeight').classList.toggle('active', mode === 'height');
    $('fitWidth').classList.toggle('active', mode === 'width');
    $('zoomIndicator').style.display = 'none';
    localStorage.setItem('fitMode', mode);
}}

// Keyboard
document.addEventListener('keydown', e => {{
    if (e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowLeft') loadPage(currentPage - 1);
    if (e.key === 'ArrowRight') loadPage(currentPage + 1);
    if (e.key === 't' || e.key === 'T') toggleTOC();
    if (e.key === 'h' || e.key === 'H') setFitMode('height');
    if (e.key === 'w' || e.key === 'W') setFitMode('width');
    if (e.key === '+' || e.key === '=') {{ zoomIn(); e.preventDefault(); }}
    if (e.key === '-') {{ zoomOut(); e.preventDefault(); }}
    if (e.key === '0') {{ resetZoom(); e.preventDefault(); }}
}});

// Mouse wheel: Ctrl/Cmd+scroll = zoom, normal scroll = scroll page
const container = $('imageContainer');
container.addEventListener('wheel', e => {{
    // Ctrl+scroll OR Cmd+scroll (Mac) = zoom
    if (e.ctrlKey || e.metaKey) {{
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.15 : 0.15;
        zoom = Math.max(0.5, Math.min(3, zoom + delta));
        updateZoom();
    }}
    // Normal scroll = let browser handle it (scrolls the container)
}}, {{ passive: false }});

// Trackpad pinch zoom (fires as wheel with ctrlKey on most browsers)
// Already handled above

// Double-click to reset zoom
$('pageImage').addEventListener('dblclick', e => {{
    e.preventDefault();
    resetZoom();
}});

// Touch: pinch zoom + swipe navigation
let touch = {{ startX: 0, startY: 0, startDist: 0, startZoom: 1, isPinch: false }};

container.addEventListener('touchstart', e => {{
    if (e.touches.length === 1) {{
        touch.startX = e.touches[0].clientX;
        touch.startY = e.touches[0].clientY;
        touch.isPinch = false;
    }} else if (e.touches.length === 2) {{
        touch.isPinch = true;
        touch.startDist = Math.hypot(
            e.touches[1].clientX - e.touches[0].clientX,
            e.touches[1].clientY - e.touches[0].clientY
        );
        touch.startZoom = zoom;
    }}
}}, {{ passive: true }});

container.addEventListener('touchmove', e => {{
    if (e.touches.length === 2 && touch.isPinch) {{
        const dist = Math.hypot(
            e.touches[1].clientX - e.touches[0].clientX,
            e.touches[1].clientY - e.touches[0].clientY
        );
        zoom = Math.max(0.5, Math.min(3, touch.startZoom * (dist / touch.startDist)));
        updateZoom();
    }}
}}, {{ passive: true }});

container.addEventListener('touchend', e => {{
    if (e.touches.length === 0 && !touch.isPinch) {{
        const diffX = e.changedTouches[0].clientX - touch.startX;
        const diffY = e.changedTouches[0].clientY - touch.startY;
        // Horizontal swipe > vertical = page navigation
        if (Math.abs(diffX) > 50 && Math.abs(diffX) > Math.abs(diffY)) {{
            if (diffX > 0) loadPage(currentPage - 1);
            else loadPage(currentPage + 1);
        }}
    }}
    touch.isPinch = false;
}}, {{ passive: true }});

// Page jump input
function jumpToPage(val) {{
    const p = parseInt(val);
    if (p && p >= 1 && p <= totalPages) {{
        loadPage(p);
    }} else {{
        $('pageNum').value = currentPage; // Reset to current
    }}
}}

$('pageNum').addEventListener('keydown', e => {{
    if (e.key === 'Enter') {{
        e.preventDefault();
        jumpToPage(e.target.value);
        e.target.blur();
    }}
}});

$('pageNum').addEventListener('blur', e => {{
    jumpToPage(e.target.value);
}});

$('pageNum').addEventListener('focus', e => {{
    e.target.select();
}});

// Init
window.onload = () => {{
    setFitMode(fitMode);
    const params = new URLSearchParams(location.search);
    const t = parseInt(params.get('t'));
    if (t && topics[t]) {{
        openTopic(t);
        document.querySelectorAll('.topic').forEach(el => {{
            if (parseInt(el.dataset.t) === t) el.closest('.strand').classList.add('expanded');
        }});
    }}
    // TOC stays collapsed, first strand expanded for when user opens it
    document.querySelector('.strand')?.classList.add('expanded');
}};
</script>
</body>
</html>'''

# ============================================================
# COMMANDS
# ============================================================

def cmd_index():
    """Rebuild index.html from existing WebPs"""
    print("=" * 50)
    print("REBUILD INDEX")
    print("=" * 50)
    
    # Parse TOC
    strands, topics = parse_toc(TOC_FILE)
    if not topics:
        return
    
    print(f"📚 {len(strands)} strands, {len(topics)} topics in TOC")
    
    # Scan existing WebPs
    webp_folder = COMIC_PATH / IMG_FOLDER if IMG_FOLDER else COMIC_PATH
    page_counts = scan_webps(webp_folder)
    print(f"🖼️  Found WebPs for {len(page_counts)} topics")
    
    if not page_counts:
        print("\n✗ No WebP files found!")
        return
    
    for t in sorted(page_counts.keys()):
        title = topics.get(t, {}).get('title', '?')
        print(f"  {t:2d}. {title} ({page_counts[t]}p)")
    
    # Generate index
    index_html = generate_index(strands, page_counts)
    (COMIC_PATH / "index.html").write_text(index_html, encoding='utf-8')
    
    total = sum(page_counts.values())
    print(f"\n✓ index.html generated")
    print(f"✓ {len(page_counts)} topics, {total} pages")

def cmd_convert():
    """Convert JPEGs to WebPs + build index"""
    print("=" * 50)
    print("CONVERT IMAGES + BUILD INDEX")
    print("=" * 50)
    print(f"Source: {SOURCE_PATH}")
    print(f"Output: {COMIC_PATH}")
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
    
    confirm = input("\nConvert now? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled")
        return
    
    COMIC_PATH.mkdir(parents=True, exist_ok=True)
    
    # Output folder for WebPs
    webp_output = COMIC_PATH / IMG_FOLDER if IMG_FOLDER else COMIC_PATH
    webp_output.mkdir(parents=True, exist_ok=True)
    
    # Convert all topics
    print("\n" + "=" * 50)
    page_counts = {}
    
    for num, t, src, _ in found:
        print(f"\n{num:02d}. {t['title']}")
        count = convert_topic(src, num, webp_output)
        page_counts[num] = count
        print(f"    ✓ {count} pages")
    
    # Generate index
    print("\n" + "=" * 50)
    index_html = generate_index(strands, page_counts)
    (COMIC_PATH / "index.html").write_text(index_html, encoding='utf-8')
    print("✓ index.html generated")
    
    # Summary
    total_files = sum(page_counts.values())
    print(f"\n{'=' * 50}")
    print(f"✓ Done!")
    print(f"  Topics: {len(page_counts)}")
    print(f"  Files: {total_files} WebPs → {webp_output}")
    print(f"  Index: {COMIC_PATH / 'index.html'}")
    
    # Cleanup option
    cleanup = input("\nDelete book-* folders (JPEGs)? (y/n): ").strip().lower()
    if cleanup == 'y':
        for folder in COMIC_PATH.glob("book-*"):
            if folder.is_dir():
                shutil.rmtree(folder)
                print(f"  ✓ Deleted {folder.name}")
        print("✓ Cleanup done")

def main():
    # Command line args
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == 'index':
            cmd_index()
        elif cmd == 'convert':
            cmd_convert()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python rebuild.py [index|convert]")
        return
    
    # Interactive menu
    print("=" * 50)
    print("MATHS COMIC REBUILD")
    print("=" * 50)
    print(f"Path: {COMIC_PATH}")
    print("=" * 50)
    print()
    print("  1. Rebuild index.html (from existing WebPs)")
    print("  2. Convert JPEGs → WebPs + rebuild index")
    print("  3. Exit")
    print()
    
    choice = input("Choice (1-3): ").strip()
    
    if choice == '1':
        cmd_index()
    elif choice == '2':
        cmd_convert()
    elif choice == '3':
        print("Bye!")
        return
    else:
        print("Invalid choice")
        return
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
