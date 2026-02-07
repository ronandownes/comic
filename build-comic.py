#!/usr/bin/env python3
"""
build-comic.py v08 - Image Viewer Generator
Drop in any folder with images, run to generate index.html

Features:
  - Instagram-style ‹ › page navigation
  - ↑ ↓ scroll buttons (desktop only, fit-width mode)
  - TOC sidebar with STRAND/TOPIC support
  - Fit height/width modes
  - Zoom with Ctrl+scroll
  - All keyboard/mouse/touch navigation

Navigation:
  Mouse scroll     - scroll page
  Ctrl+scroll      - zoom in/out
  Ctrl+Left/Right  - prev/next page (always)
  Arrow Left/Right - prev/next page (or pan when zoomed)
  Arrow Up/Down    - scroll (fit-width) or pan (zoomed)
  PageUp/PageDown  - prev/next page
  Double-click     - reset zoom
  H key            - fit height
  W key            - fit width
  T key            - toggle TOC
  F key            - fullscreen
"""

import os
import json
import re
from pathlib import Path

VERSION = "08"

# Image extensions to find
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

def natural_sort_key(s):
    """Sort strings with numbers naturally: page1, page2, page10"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(s))]

def find_images(folder):
    """Find all images in folder (or webp subfolder), sorted naturally"""
    # Check for webp subfolder first
    webp_folder = folder / 'webp'
    if webp_folder.is_dir():
        folder = webp_folder
    
    images = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in IMG_EXTENSIONS:
            images.append(f.name)
    return sorted(images, key=natural_sort_key), folder

def parse_toc(folder, images=None):
    """Parse toc.txt - supports STRAND|name and TOPIC|num|title|... format
    
    If images list provided, maps topic numbers to actual page indices.
    Image naming: TTPP.ext where TT=topic, PP=page within topic
    """
    toc_file = folder / 'toc.txt'
    if not toc_file.exists():
        return None
    
    # Build topic -> first image index map from image filenames
    topic_to_page = {}
    if images:
        for i, img in enumerate(images):
            # Extract topic number from filename (first 2 digits)
            # Handle paths like "webp/0101.webp" -> "0101" -> "01"
            basename = Path(img).stem
            if len(basename) >= 2:
                topic = basename[:2]
                if topic not in topic_to_page:
                    topic_to_page[topic] = i
    
    chapters = []
    current_strand = None
    
    for line in toc_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = line.split('|')
        
        # STRAND|name - strand header (non-clickable, just a label)
        if parts[0].upper() == 'STRAND' and len(parts) >= 2:
            current_strand = {
                'title': parts[1],
                'isStrand': True,  # Mark as strand header
                'sections': []
            }
            chapters.append(current_strand)
            continue
        
        # TOPIC|num|title|orig_book|orig_chap
        if parts[0].upper() == 'TOPIC' and len(parts) >= 3:
            topic_num = parts[1]  # e.g. "01", "02"
            topic_title = parts[2]
            
            # Find page index from image filenames, fallback to topic number
            page = topic_to_page.get(topic_num, int(topic_num) - 1 if topic_num.isdigit() else 0)
            
            section = {
                'title': topic_title,
                'start': page,
                'code': topic_num
            }
            
            if current_strand:
                current_strand['sections'].append(section)
            else:
                # No strand yet, add as standalone
                chapters.append({
                    'title': topic_title,
                    'start': page,
                    'code': topic_num,
                    'sections': []
                })
            continue
    
    return {'chapters': chapters} if chapters else None

def get_template():
    """Return the embedded viewer template"""
    return '''<!DOCTYPE html>
<!-- build-comic.py v__VERSION__ | __DATE__ -->
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>__TITLE__</title>
    <link rel="canonical" href="__CANONICAL__">
    <meta name="generator" content="build-comic.py v__VERSION__">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { height: 100dvh; overflow: hidden; touch-action: pan-x pan-y; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            display: flex;
        }
        
        /* TOC Sidebar */
        .toc-toggle {
            position: fixed; top: 50px; left: 0; z-index: 2000;
            background: #0066cc; color: white; border: none;
            border-radius: 0 4px 4px 0; padding: 8px 6px;
            cursor: pointer; font-size: 14px;
        }
        .toc-toggle:hover { background: #0080ff; }
        
        .toc-sidebar {
            width: 280px; background: #222; border-right: 1px solid #333;
            display: flex; flex-direction: column;
            transition: margin-left 0.3s; z-index: 1000; flex-shrink: 0;
        }
        .toc-hidden .toc-sidebar { margin-left: -280px; }
        .toc-header {
            padding: 10px; border-bottom: 1px solid #333;
            display: flex; justify-content: space-between; align-items: center;
        }
        .toc-header h2 { font-size: 14px; }
        .toc-close { background: none; border: none; color: #888; font-size: 18px; cursor: pointer; }
        .toc-content { flex: 1; overflow-y: auto; padding: 8px; }
        .toc-strand {
            margin-top: 12px; padding: 6px 8px; font-weight: bold;
            font-size: 11px; color: #0af; text-transform: uppercase;
            border-bottom: 1px solid #333;
        }
        .toc-item {
            padding: 8px 10px; cursor: pointer; border-radius: 4px;
            font-size: 12px; margin-bottom: 2px;
        }
        .toc-item:hover { background: #333; }
        .toc-item.active { background: #0066cc; }
        .toc-chapter { font-weight: bold; }
        .toc-section { padding-left: 20px; color: #aaa; }
        
        /* Viewer */
        .viewer { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
        
        .controls {
            background: #222; padding: 6px 10px; border-bottom: 1px solid #333;
            display: flex; justify-content: center; align-items: center;
            gap: 8px; flex-wrap: wrap;
        }
        
        button {
            background: #333; border: 1px solid #444; color: #ccc;
            padding: 6px 10px; border-radius: 4px; cursor: pointer;
            font-size: 14px; min-width: 36px; height: 32px;
        }
        button:hover { background: #444; }
        button.active { background: #0066cc; border-color: #0080ff; color: #fff; }
        button small { font-size: 9px; opacity: 0.6; margin-left: 1px; vertical-align: baseline; }
        
        .page-info { display: flex; align-items: center; gap: 4px; font-size: 13px; }
        #currentPage {
            cursor: pointer; padding: 4px 8px; border-radius: 4px;
            min-width: 30px; text-align: center;
        }
        #currentPage:hover { background: #444; }
        .page-input {
            width: 50px; padding: 4px; text-align: center;
            background: #1a1a1a; border: 1px solid #0066cc;
            border-radius: 4px; color: #e0e0e0;
        }
        
        .sep { width: 1px; height: 20px; background: #444; }
        
        .image-container {
            flex: 1; display: flex; justify-content: center; align-items: flex-start;
            overflow: auto; background: #111; position: relative; min-height: 0;
            -webkit-overflow-scrolling: touch;
        }
        .image-container.fit-height { align-items: center; overflow: hidden; }
        .image-container.fit-height img { max-height: 100%; width: auto; height: auto; }
        .image-container.fit-width { overflow-y: auto; overflow-x: hidden; }
        .image-container.fit-width img { width: 100%; max-width: 100%; height: auto; }
        
        #pageImage {
            display: block; box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            transform-origin: center center;
        }
        
        .zoom-indicator {
            position: fixed; bottom: 20px; right: 80px;
            background: rgba(0,0,0,0.7); color: #fff;
            padding: 6px 12px; border-radius: 4px; font-size: 13px; display: none;
        }
        
        /* Side nav buttons */
        /* Instagram-style side nav buttons */
        .side-nav {
            position: fixed; top: 50%; transform: translateY(-50%); z-index: 1100;
            background: rgba(255,255,255,0.85); color: #262626; border: none;
            width: 40px; height: 40px; border-radius: 50%;
            cursor: pointer; opacity: 0.7; transition: all 0.15s ease;
            font-size: 20px; font-weight: 300;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .side-nav:hover { opacity: 1; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.25); }
        .side-nav.prev { left: 10px; }
        .side-nav.next { right: 10px; }
        
        /* Scroll nav buttons (vertical) - only visible in fit-width */
        .scroll-nav {
            position: fixed; left: 50%; transform: translateX(-50%); z-index: 1100;
            background: rgba(255,255,255,0.85); color: #262626; border: none;
            width: 36px; height: 36px; border-radius: 50%;
            cursor: pointer; opacity: 0; transition: all 0.15s ease;
            font-size: 18px; font-weight: 300;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            pointer-events: none;
        }
        .scroll-nav:hover { opacity: 1; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.25); }
        .scroll-nav.down { top: 60px; }
        .scroll-nav.up { bottom: 20px; }
        body.show-scroll-nav .scroll-nav { opacity: 0.6; pointer-events: auto; }
        /* Hide scroll nav on touch devices - they can scroll naturally */
        @media (pointer: coarse) {
            .scroll-nav { display: none !important; }
        }
        
        /* Fullscreen mode - hide controls until tapped */
        :fullscreen .controls,
        :fullscreen .toc-toggle,
        :fullscreen .toc-sidebar,
        :fullscreen .side-nav,
        :fullscreen .scroll-nav,
        :fullscreen .zoom-indicator {
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }
        :fullscreen.show-controls .controls,
        :fullscreen.show-controls .toc-toggle,
        :fullscreen.show-controls .side-nav,
        :fullscreen.show-controls .scroll-nav,
        :fullscreen.show-controls .zoom-indicator {
            opacity: 1;
            pointer-events: auto;
        }
        :fullscreen .toc-sidebar { display: none; }
        
        /* Fullscreen info overlay */
        #fsInfo {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            display: none; flex-direction: column;
            justify-content: center; align-items: center;
            z-index: 10000; color: #fff; text-align: center;
            font-family: system-ui, sans-serif;
        }
        #fsInfo.visible { display: flex; }
        #fsInfo h2 { font-size: 24px; margin: 0 0 20px; font-weight: 600; }
        #fsInfo .info-row { font-size: 14px; color: #aaa; margin: 4px 0; }
        #fsInfo .info-row span { color: #fff; }
        #fsInfo .hint { margin-top: 30px; font-size: 13px; color: #666; }
        #fsInfo .hint strong { color: #888; }
        
        @media (max-width: 600px) {
            .controls { padding: 4px 6px; gap: 4px; }
            button { padding: 4px 8px; font-size: 12px; min-width: 30px; height: 28px; }
            .toc-sidebar { width: 240px; }
            .toc-hidden .toc-sidebar { margin-left: -240px; }
            .side-nav { width: 36px; height: 36px; font-size: 18px; opacity: 0.6; }
            .side-nav.prev { left: 6px; }
            .side-nav.next { right: 6px; }
            .scroll-nav { width: 32px; height: 32px; font-size: 16px; }
            .scroll-nav.down { top: 54px; }
            .scroll-nav.up { bottom: 14px; }
        }
    </style>
</head>
<body class="toc-hidden">

<button class="toc-toggle" id="tocToggle">☰</button>

<div class="toc-sidebar">
    <div class="toc-header">
        <h2>Contents</h2>
        <button class="toc-close" id="tocClose">×</button>
    </div>
    <div class="toc-content" id="tocContent"></div>
</div>

<div class="viewer">
    <div class="controls">
        <div class="page-info">
            <span id="currentPage">1</span>
            <span style="color:#666">/</span>
            <span id="totalPages" style="color:#666">1</span>
        </div>
        <div class="sep"></div>
        <button id="fitHeight" title="Fit Height (H)">↕<small>H</small></button>
        <button id="fitWidth" title="Fit Width (W)">↔<small>W</small></button>
        <div class="sep"></div>
        <button id="zoomOut" title="Zoom Out">−</button>
        <button id="zoomIn" title="Zoom In">+</button>
        <div class="sep"></div>
        <button id="copyLink" title="Copy Link">🔗</button>
        <button id="fullscreen" title="Fullscreen (F)">⛶</button>
    </div>
    <div class="image-container fit-height" id="imageContainer">
        <img id="pageImage" src="" alt="Page">
    </div>
</div>

<div class="zoom-indicator" id="zoomIndicator">100%</div>

<!-- Fullscreen info overlay -->
<div id="fsInfo">
    <h2>__TITLE__</h2>
    <div class="info-row">Page <span id="fsPage">1</span> of <span id="fsTotal">1</span></div>
    <div class="info-row">build-comic.py v__VERSION__ | __DATE__</div>
    <div class="hint">Tap anywhere to show controls<br><strong>Tap again</strong> or wait to hide</div>
</div>
<button class="side-nav prev" id="sidePrev">‹</button>
<button class="side-nav next" id="sideNext">›</button>
<button class="scroll-nav down" id="scrollDown">↓</button>
<button class="scroll-nav up" id="scrollUp">↑</button>



<script>
const CONFIG = __CONFIG__;
const $ = id => document.getElementById(id);
const img = $('pageImage');
const container = $('imageContainer');

let state = { page: 0, zoom: 1, fitMode: 'height', translateX: 0, translateY: 0 };

try {
    const saved = localStorage.getItem('viewerState_' + location.pathname);
    if (saved) Object.assign(state, JSON.parse(saved));
} catch(e) {}

function saveState() {
    try { localStorage.setItem('viewerState_' + location.pathname, JSON.stringify(state)); } catch(e) {}
}

function loadPage(idx) {
    if (idx < 0 || idx >= CONFIG.pages.length) return;
    state.page = idx;
    img.src = CONFIG.pages[idx];
    $('currentPage').textContent = idx + 1;
    state.zoom = 1; state.translateX = state.translateY = 0;
    updateTransform();
    container.scrollTop = container.scrollLeft = 0;
    updateTOC();
    saveState();
}

function setFitMode(mode) {
    state.fitMode = mode;
    container.classList.remove('fit-height', 'fit-width');
    container.classList.add('fit-' + mode);
    $('fitHeight').classList.toggle('active', mode === 'height');
    $('fitWidth').classList.toggle('active', mode === 'width');
    document.body.classList.toggle('show-scroll-nav', mode === 'width');
    state.zoom = 1; state.translateX = state.translateY = 0;
    updateTransform();
    saveState();
}

function updateTransform() {
    if (state.zoom === 1) {
        img.style.transform = '';
        $('zoomIndicator').style.display = 'none';
    } else {
        img.style.transform = `scale(${state.zoom}) translate(${state.translateX}px, ${state.translateY}px)`;
        $('zoomIndicator').textContent = Math.round(state.zoom * 100) + '%';
        $('zoomIndicator').style.display = 'block';
    }
}

function zoom(delta) {
    state.zoom = Math.max(0.25, Math.min(5, state.zoom + delta));
    updateTransform();
}

function pan(dx, dy) {
    if (state.zoom > 1) {
        state.translateX += dx; state.translateY += dy;
        updateTransform();
        return true;
    }
    return false;
}

function showPageInput() {
    const span = $('currentPage');
    const inp = document.createElement('input');
    inp.type = 'number'; inp.className = 'page-input';
    inp.value = state.page + 1; inp.min = 1; inp.max = CONFIG.pages.length;
    inp.onkeydown = e => {
        if (e.key === 'Enter') { loadPage(parseInt(inp.value) - 1); inp.replaceWith(span); }
        else if (e.key === 'Escape') { inp.replaceWith(span); }
    };
    inp.onblur = () => { loadPage(parseInt(inp.value) - 1); inp.replaceWith(span); };
    span.replaceWith(inp); inp.focus(); inp.select();
}

function toggleTOC(show) {
    if (show === true) document.body.classList.remove('toc-hidden');
    else if (show === false) document.body.classList.add('toc-hidden');
    else document.body.classList.toggle('toc-hidden');
}

function renderTOC() {
    const content = $('tocContent');
    if (!CONFIG.toc?.chapters?.length) {
        let html = '';
        for (let i = 0; i < CONFIG.pages.length; i += 10) {
            html += `<div class="toc-item" data-page="${i}">Pages ${i+1}–${Math.min(i+10, CONFIG.pages.length)}</div>`;
        }
        content.innerHTML = html;
    } else {
        let html = '';
        CONFIG.toc.chapters.forEach(ch => {
            // Strand = non-clickable header
            if (ch.isStrand) {
                html += `<div class="toc-strand">${ch.title}</div>`;
            } else {
                // Regular chapter/topic
                html += `<div class="toc-item toc-chapter" data-page="${(ch.start||1)-1}">${ch.code ? ch.code + '. ' : ''}${ch.title}</div>`;
            }
            // Topics under strand
            (ch.sections || []).forEach(s => {
                html += `<div class="toc-item toc-section" data-page="${(s.start||1)-1}">${s.code}. ${s.title}</div>`;
            });
        });
        content.innerHTML = html;
    }
    content.querySelectorAll('.toc-item').forEach(el => {
        el.onclick = () => { loadPage(parseInt(el.dataset.page)); toggleTOC(false); };
    });
}

function updateTOC() {
    document.querySelectorAll('.toc-item').forEach(el => {
        el.classList.toggle('active', parseInt(el.dataset.page) === state.page);
    });
}

function copyLink() {
    const url = new URL(location.href); url.hash = '#page=' + (state.page + 1);
    navigator.clipboard.writeText(url.toString()).then(() => {
        const btn = $('copyLink'); btn.textContent = '✓';
        setTimeout(() => btn.textContent = '🔗', 1200);
    });
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen?.() || document.documentElement.webkitRequestFullscreen?.();
    } else {
        document.exitFullscreen?.() || document.webkitExitFullscreen?.();
    }
}

// Events
$('tocToggle').onclick = () => toggleTOC();
$('tocClose').onclick = () => toggleTOC(false);
$('sidePrev').onclick = () => loadPage(state.page - 1);
$('sideNext').onclick = () => loadPage(state.page + 1);
$('scrollDown').onclick = () => container.scrollBy({ top: window.innerHeight * 0.85, behavior: 'smooth' });
$('scrollUp').onclick = () => container.scrollBy({ top: -window.innerHeight * 0.85, behavior: 'smooth' });
$('fitHeight').onclick = () => setFitMode('height');
$('fitWidth').onclick = () => setFitMode('width');
$('zoomIn').onclick = () => zoom(0.15);
$('zoomOut').onclick = () => zoom(-0.15);
$('copyLink').onclick = copyLink;
$('fullscreen').onclick = toggleFullscreen;
$('currentPage').onclick = showPageInput;
img.ondblclick = () => { state.zoom = 1; state.translateX = state.translateY = 0; updateTransform(); };

// Keyboard
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    const key = e.key;
    
    // Ctrl+Arrow = always change page (even when zoomed)
    if (e.ctrlKey || e.metaKey) {
        if (key === 'ArrowLeft') { loadPage(state.page - 1); e.preventDefault(); return; }
        if (key === 'ArrowRight') { loadPage(state.page + 1); e.preventDefault(); return; }
    }
    
    // When zoomed: arrows pan
    if (state.zoom > 1) {
        if (key === 'ArrowLeft') { pan(50, 0); e.preventDefault(); return; }
        if (key === 'ArrowRight') { pan(-50, 0); e.preventDefault(); return; }
        if (key === 'ArrowUp') { pan(0, 50); e.preventDefault(); return; }
        if (key === 'ArrowDown') { pan(0, -50); e.preventDefault(); return; }
    }
    
    // When NOT zoomed:
    // - Left/Right = change page
    // - Up/Down = scroll container (fit-width) or do nothing (fit-height)
    if (key === 'ArrowLeft') { loadPage(state.page - 1); e.preventDefault(); }
    else if (key === 'ArrowRight') { loadPage(state.page + 1); e.preventDefault(); }
    else if (key === 'ArrowUp') { 
        if (state.fitMode === 'width') container.scrollBy(0, -100);
        e.preventDefault();
    }
    else if (key === 'ArrowDown') {
        if (state.fitMode === 'width') container.scrollBy(0, 100);
        e.preventDefault();
    }
    else if (key === 'PageUp') { loadPage(state.page - 1); e.preventDefault(); }
    else if (key === 'PageDown') { loadPage(state.page + 1); e.preventDefault(); }
    else if (key === 'h' || key === 'H') setFitMode('height');
    else if (key === 'w' || key === 'W') setFitMode('width');
    else if (key === 't' || key === 'T') toggleTOC();
    else if (key === 'f' || key === 'F') toggleFullscreen();
    else if (key === 'Home') loadPage(0);
    else if (key === 'End') loadPage(CONFIG.pages.length - 1);
});

// Ctrl+wheel = zoom (document level so works anywhere)
document.addEventListener('wheel', e => {
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        zoom(e.deltaY > 0 ? -0.1 : 0.1);
    }
}, { passive: false });

// Regular wheel on container handled by browser (overflow: auto)

// Touch swipe
let touchStart = null;
container.addEventListener('touchstart', e => {
    if (e.touches.length === 1 && state.zoom === 1) touchStart = { x: e.touches[0].clientX };
}, { passive: true });
container.addEventListener('touchend', e => {
    if (touchStart && state.zoom === 1) {
        const dx = e.changedTouches[0].clientX - touchStart.x;
        if (Math.abs(dx) > 50) loadPage(state.page + (dx > 0 ? -1 : 1));
    }
    touchStart = null;
});

// Init
$('totalPages').textContent = CONFIG.pages.length;
renderTOC();
setFitMode(state.fitMode);
const hash = location.hash.match(/#page=(\\d+)/);
if (hash) state.page = parseInt(hash[1]) - 1;
loadPage(state.page);
window.onhashchange = () => { const m = location.hash.match(/#page=(\\d+)/); if (m) loadPage(parseInt(m[1]) - 1); };

// Ensure focus for keyboard navigation
container.tabIndex = 0;
container.style.outline = 'none';
container.addEventListener('click', () => container.focus());
document.addEventListener('click', e => { if (e.target === document.body) container.focus(); });
container.focus();
</script>
</body>
</html>'''

def build(folder):
    """Build index.html from images in folder"""
    folder = Path(folder)
    images, img_folder = find_images(folder)
    
    if not images:
        print(f"No images found in {folder}")
        print(f"  Checked: {folder} and {folder / 'webp'}")
        print(f"  Supported: {', '.join(IMG_EXTENSIONS)}")
        return False
    
    # Determine image path prefix (relative to index.html)
    img_prefix = ''
    if img_folder != folder:
        img_prefix = img_folder.name + '/'
    
    # Add prefix to image paths
    images = [img_prefix + img for img in images]
    
    # Get title from folder name
    title = folder.name.replace('-', ' ').replace('_', ' ').title()
    
    # Parse TOC if exists (pass images for correct page mapping)
    toc = parse_toc(folder, images)
    
    # Build config
    config = {
        'pages': images,
        'toc': toc
    }
    
    # Generate HTML
    from datetime import datetime
    html = get_template()
    html = html.replace('__TITLE__', title)
    html = html.replace('__CONFIG__', json.dumps(config))
    html = html.replace('__VERSION__', VERSION)
    html = html.replace('__DATE__', datetime.now().strftime('%Y-%m-%d %H:%M'))
    html = html.replace('__CANONICAL__', f'./{folder.name}/')
    
    # Write output
    output = folder / 'index.html'
    output.write_text(html, encoding='utf-8')
    
    print(f"build-comic.py v{VERSION}")
    print(f"  Folder: {folder.name}")
    print(f"  Images: {len(images)} (from {img_folder.name}/)" if img_prefix else f"  Images: {len(images)}")
    print(f"  TOC: {'Yes' if toc else 'No'}")
    print(f"  Output: index.html")
    print()
    print("Navigation:")
    print("  ‹ ›           Page prev/next (side buttons)")
    print("  ↑ ↓           Scroll up/down (desktop, fit-width)")
    print("  ← → keys      Page prev/next (pan when zoomed)")
    print("  Ctrl+Scroll   Zoom in/out")
    print("  H / W         Fit height / width")
    print("  T             Toggle TOC")
    print("  F             Fullscreen")
    
    return True

if __name__ == '__main__':
    import sys
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    build(folder)
