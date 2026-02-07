#!/usr/bin/env python3
"""
build-comic.py v07 - Image Viewer Generator
Drop in any folder with images, run to generate index.html

Features:
  - Ruler (📏) for classroom reading - drag, rotate, measure
  - Drawing tools: pens (red/blue/green/black) + highlighters (yellow/green/blue/pink)
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
  Space+drag       - pan image
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
    """Return the embedded viewer template with ruler and drawing tools"""
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
        
        /* Ruler */
        #ruler {
            position: fixed; left: -25%; right: -25%; height: 56px;
            top: 50%; transform: translateY(-50%); z-index: 9995;
            display: none; user-select: none; cursor: ns-resize; touch-action: none;
        }
        #ruler .ruler-body {
            width: 100%; height: 100%;
            background: rgba(80,80,90,0.22);
            border-top: 1px solid rgba(255,255,255,0.3);
            border-bottom: 1px solid rgba(255,255,255,0.3);
            backdrop-filter: blur(1px); position: relative; overflow: hidden;
        }
        #ruler.dragging .ruler-body { background: rgba(80,80,90,0.32); }
        #ruler .tick { position: absolute; width: 1px; background: rgba(255,255,255,0.7); }
        #ruler .tick-cm { top: 0; }
        #ruler .tick-in { bottom: 0; }
        #ruler .tick-cm.major { height: 16px; width: 1.5px; background: rgba(255,255,255,0.9); }
        #ruler .tick-cm.half { height: 10px; }
        #ruler .tick-cm.minor { height: 5px; background: rgba(255,255,255,0.5); }
        #ruler .tick-in.major { height: 16px; width: 1.5px; background: rgba(255,255,255,0.9); }
        #ruler .tick-in.half { height: 12px; }
        #ruler .tick-in.quarter { height: 8px; }
        #ruler .tick-in.eighth { height: 5px; background: rgba(255,255,255,0.5); }
        #ruler .label {
            position: absolute; font: 600 9px system-ui;
            color: rgba(255,255,255,0.9); text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
        #ruler .label-cm { top: 18px; transform: translateX(-50%); }
        #ruler .label-in { bottom: 18px; transform: translateX(-50%); }
        #ruler .unit-label {
            position: absolute; font: 600 8px system-ui;
            color: rgba(255,255,255,0.6); text-transform: uppercase;
        }
        #ruler .unit-cm { top: 18px; left: 8px; }
        #ruler .unit-in { bottom: 18px; left: 8px; }
        #ruler .drag-handle {
            position: absolute; left: 50%; top: 50%;
            transform: translate(-50%,-50%);
            width: 36px; height: 36px;
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 50%; cursor: pointer; z-index: 10;
            display: flex; align-items: center; justify-content: center;
        }
        #ruler .drag-handle::before { content: '⟲'; color: rgba(255,255,255,0.6); font-size: 18px; }
        #ruler .rotate-btn {
            position: absolute; top: 50%; transform: translateY(-50%);
            width: 28px; height: 28px;
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 50%; color: rgba(255,255,255,0.75);
            font-size: 12px; cursor: pointer; z-index: 10;
            display: flex; align-items: center; justify-content: center;
        }
        #ruler .rotate-btn:active { background: rgba(255,255,255,0.3); }
        #ruler .rot-l { left: calc(50% - 80px); }
        #ruler .rot-r { left: calc(50% + 52px); }
        #ruler .rot-90 { left: calc(50% + 100px); }
        #ruler .angle-display {
            position: absolute; top: -22px; left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.5); color: rgba(255,255,255,0.9);
            padding: 2px 8px; border-radius: 8px; font: 600 10px system-ui;
        }
        
        #rulerToggle {
            position: fixed; right: 14px; bottom: 14px; z-index: 9999;
            padding: 10px 14px; border: 1px solid rgba(255,255,255,0.3);
            background: linear-gradient(180deg, rgba(200,220,255,0.9) 0%, rgba(140,180,240,0.85) 50%, rgba(100,150,220,0.9) 100%);
            color: #1a3a5c; border-radius: 12px; font: 600 14px system-ui;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3), inset 0 1px 2px rgba(255,255,255,0.5);
        }
        #rulerToggle:hover { background: linear-gradient(180deg, rgba(210,230,255,0.95) 0%, rgba(160,200,250,0.9) 50%, rgba(120,170,230,0.95) 100%); }
        #rulerToggle.active { 
            background: linear-gradient(180deg, rgba(100,200,150,0.9) 0%, rgba(60,180,120,0.85) 50%, rgba(40,150,100,0.9) 100%);
            color: #0a3020;
        }
        
        /* Drawing Tools */
        #drawCanvas {
            position: absolute;
            pointer-events: none; z-index: 50;
            image-rendering: auto;
        }
        #drawCanvas.active { pointer-events: auto; cursor: crosshair; }
        
        #drawToggle {
            position: fixed; right: 14px; bottom: 70px; z-index: 9999;
            padding: 10px 14px; border: 1px solid rgba(255,255,255,0.3);
            background: linear-gradient(180deg, rgba(255,220,180,0.9) 0%, rgba(255,180,120,0.85) 50%, rgba(240,150,80,0.9) 100%);
            color: #5a3a1c; border-radius: 12px; font: 600 14px system-ui;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3), inset 0 1px 2px rgba(255,255,255,0.5);
        }
        #drawToggle:hover { background: linear-gradient(180deg, rgba(255,230,200,0.95) 0%, rgba(255,200,150,0.9) 50%, rgba(250,170,100,0.95) 100%); }
        #drawToggle.active { 
            background: linear-gradient(180deg, rgba(100,200,150,0.9) 0%, rgba(60,180,120,0.85) 50%, rgba(40,150,100,0.9) 100%);
            color: #0a3020;
        }
        
        #drawPanel {
            position: fixed; right: 70px; bottom: 14px; z-index: 9999;
            background: #222; border: 1px solid #444; border-radius: 8px;
            padding: 8px; display: none; flex-direction: column; gap: 6px;
        }
        #drawPanel.visible { display: flex; }
        .draw-row { display: flex; gap: 4px; align-items: center; }
        .draw-label { font-size: 10px; color: #888; width: 55px; }
        .draw-btn {
            width: 28px; height: 28px; border-radius: 50%; border: 2px solid transparent;
            cursor: pointer; padding: 0;
        }
        .draw-btn:hover { border-color: #fff; }
        .draw-btn.active { border-color: #0af; box-shadow: 0 0 6px #0af; }
        .draw-btn.pen-red { background: #e53935; }
        .draw-btn.pen-blue { background: #1e88e5; }
        .draw-btn.pen-green { background: #43a047; }
        .draw-btn.pen-black { background: #222; border-color: #666; }
        .draw-btn.hl-yellow { background: rgba(255,235,59,0.7); }
        .draw-btn.hl-green { background: rgba(76,175,80,0.5); }
        .draw-btn.hl-blue { background: rgba(33,150,243,0.5); }
        .draw-btn.hl-pink { background: rgba(233,30,99,0.5); }
        #clearDraw {
            background: #c62828; color: #fff; border: none; border-radius: 4px;
            padding: 4px 8px; font-size: 11px; cursor: pointer; margin-top: 4px;
        }
        #clearDraw:hover { background: #e53935; }
        
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
<button class="side-nav prev" id="sidePrev">‹</button>
<button class="side-nav next" id="sideNext">›</button>
<button class="scroll-nav down" id="scrollDown">↓</button>
<button class="scroll-nav up" id="scrollUp">↑</button>

<!-- Ruler -->
<button id="rulerToggle" title="Toggle Ruler">📏</button>
<div id="ruler">
    <div class="ruler-body" id="rulerBody"></div>
    <button class="rotate-btn rot-l" id="rotL" title="-15°">↶</button>
    <div class="drag-handle" id="rulerHandle"></div>
    <button class="rotate-btn rot-r" id="rotR" title="+15°">↷</button>
    <button class="rotate-btn rot-90" id="rot90" title="90°">⊥</button>
    <div class="angle-display" id="angleDisplay">0°</div>
</div>

<!-- Drawing Tools -->
<button id="drawToggle" title="Toggle Drawing">✏️</button>
<div id="drawPanel">
    <div class="draw-row">
        <span class="draw-label">Pens</span>
        <button class="draw-btn pen-red" data-tool="pen" data-color="#e53935" title="Red Pen"></button>
        <button class="draw-btn pen-blue" data-tool="pen" data-color="#1e88e5" title="Blue Pen"></button>
        <button class="draw-btn pen-green" data-tool="pen" data-color="#43a047" title="Green Pen"></button>
        <button class="draw-btn pen-black" data-tool="pen" data-color="#222222" title="Black Pen"></button>
    </div>
    <div class="draw-row">
        <span class="draw-label">Highlighters</span>
        <button class="draw-btn hl-yellow" data-tool="hl" data-color="rgba(255,235,59,0.4)" title="Yellow Highlighter"></button>
        <button class="draw-btn hl-green" data-tool="hl" data-color="rgba(76,175,80,0.4)" title="Green Highlighter"></button>
        <button class="draw-btn hl-blue" data-tool="hl" data-color="rgba(33,150,243,0.4)" title="Blue Highlighter"></button>
        <button class="draw-btn hl-pink" data-tool="hl" data-color="rgba(233,30,99,0.4)" title="Pink Highlighter"></button>
    </div>
    <button id="clearDraw">Clear Page</button>
</div>

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
    if (window.redrawCanvas) setTimeout(window.redrawCanvas, 100);
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
        img.style.transform = ''; img.style.width = ''; img.style.height = '';
        $('zoomIndicator').style.display = 'none';
    } else {
        const w = img.naturalWidth * state.zoom;
        const h = img.naturalHeight * state.zoom;
        img.style.width = w + 'px'; img.style.height = h + 'px';
        img.style.transform = `translate(${state.translateX}px, ${state.translateY}px)`;
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

// Ruler
(function() {
    const ruler = $('ruler'), body = $('rulerBody'), toggle = $('rulerToggle');
    const handle = $('rulerHandle'), angleDisp = $('angleDisplay');
    let visible = false, dragging = false, angle = 0, currentTop = null;
    let dragStartY = 0, rulerStartTop = 0, pxPerMm = null;

    function updateTransform() {
        if (currentTop !== null) {
            ruler.style.top = currentTop + 'px';
            ruler.style.transform = `rotate(${angle}deg)`;
        } else {
            ruler.style.transform = `translateY(-50%) rotate(${angle}deg)`;
        }
        angleDisp.textContent = angle + '°';
    }

    function drawTicks() {
        if (!pxPerMm) pxPerMm = window.innerWidth / 210;
        body.innerHTML = '';
        const width = window.innerWidth * 1.5;
        const pxPerCm = pxPerMm * 10, pxPerInch = pxPerMm * 25.4;
        
        // Unit labels
        body.innerHTML += '<div class="unit-label unit-cm">cm</div><div class="unit-label unit-in">in</div>';
        
        // CM ticks
        for (let mm = 0; mm * pxPerMm < width; mm++) {
            const x = mm * pxPerMm;
            let cls = 'tick tick-cm';
            if (mm % 10 === 0) { cls += ' major'; if (mm > 0) body.innerHTML += `<div class="label label-cm" style="left:${x}px">${mm/10}</div>`; }
            else if (mm % 5 === 0) cls += ' half';
            else cls += ' minor';
            body.innerHTML += `<div class="${cls}" style="left:${x}px"></div>`;
        }
        
        // Inch ticks
        for (let e = 0; e * (pxPerInch/8) < width; e++) {
            const x = e * (pxPerInch/8);
            let cls = 'tick tick-in';
            if (e % 8 === 0) { cls += ' major'; if (e > 0) body.innerHTML += `<div class="label label-in" style="left:${x}px">${e/8}</div>`; }
            else if (e % 4 === 0) cls += ' half';
            else if (e % 2 === 0) cls += ' quarter';
            else cls += ' eighth';
            body.innerHTML += `<div class="${cls}" style="left:${x}px"></div>`;
        }
    }

    function show() {
        visible = true; angle = 0; currentTop = null;
        ruler.style.top = '50%'; ruler.style.display = 'block';
        toggle.classList.add('active'); updateTransform(); drawTicks();
    }
    function hide() { visible = false; ruler.style.display = 'none'; toggle.classList.remove('active'); }

    toggle.onclick = () => visible ? hide() : show();
    handle.onclick = () => { angle = 0; updateTransform(); };
    handle.ondblclick = () => { currentTop = null; ruler.style.top = '50%'; updateTransform(); };
    $('rotL').onclick = e => { e.stopPropagation(); angle -= 15; updateTransform(); };
    $('rotR').onclick = e => { e.stopPropagation(); angle += 15; updateTransform(); };
    $('rot90').onclick = e => { e.stopPropagation(); angle = (angle === 90) ? 0 : 90; updateTransform(); };

    ruler.onmousedown = e => {
        if (e.target.tagName === 'BUTTON') return;
        dragging = true; ruler.classList.add('dragging');
        dragStartY = e.clientY;
        const rect = ruler.getBoundingClientRect();
        rulerStartTop = rect.top + rect.height / 2;
        e.preventDefault();
    };
    window.onmousemove = e => {
        if (!dragging) return;
        currentTop = Math.max(28, Math.min(window.innerHeight - 28, rulerStartTop + e.clientY - dragStartY));
        updateTransform();
    };
    window.onmouseup = () => { dragging = false; ruler.classList.remove('dragging'); };

    // Touch
    ruler.ontouchstart = e => {
        if (e.target.tagName === 'BUTTON') return;
        dragging = true; ruler.classList.add('dragging');
        dragStartY = e.touches[0].clientY;
        const rect = ruler.getBoundingClientRect();
        rulerStartTop = rect.top + rect.height / 2;
        e.preventDefault();
    };
    window.ontouchmove = e => {
        if (!dragging) return;
        currentTop = Math.max(28, Math.min(window.innerHeight - 28, rulerStartTop + e.touches[0].clientY - dragStartY));
        updateTransform();
    };
    window.ontouchend = () => { dragging = false; ruler.classList.remove('dragging'); };

    window.addEventListener('resize', () => { if (visible) drawTicks(); });
    img.onload = () => { if (visible) drawTicks(); };
})();

// Drawing Tools
(function() {
    let canvas, ctx;
    let drawing = false, drawActive = false;
    let currentTool = 'pen', currentColor = '#e53935';
    const drawings = {}; // Store drawings per page
    
    function createCanvas() {
        if (canvas) return;
        canvas = document.createElement('canvas');
        canvas.id = 'drawCanvas';
        container.appendChild(canvas);
        ctx = canvas.getContext('2d');
        resizeCanvas();
    }
    
    function resizeCanvas() {
        if (!canvas || !img.complete || !img.naturalWidth) return;
        const imgRect = img.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        
        // Position canvas exactly over the image
        canvas.style.position = 'absolute';
        canvas.style.left = (imgRect.left - containerRect.left + container.scrollLeft) + 'px';
        canvas.style.top = (imgRect.top - containerRect.top + container.scrollTop) + 'px';
        canvas.style.width = imgRect.width + 'px';
        canvas.style.height = imgRect.height + 'px';
        
        // Set canvas resolution to match display size
        canvas.width = imgRect.width;
        canvas.height = imgRect.height;
        
        redraw();
    }
    
    function saveDrawing() {
        if (!canvas) return;
        drawings[state.page] = canvas.toDataURL();
    }
    
    function redraw() {
        if (!ctx || !canvas) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (drawings[state.page]) {
            const img2 = new Image();
            img2.onload = () => ctx.drawImage(img2, 0, 0, canvas.width, canvas.height);
            img2.src = drawings[state.page];
        }
    }
    
    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return { x: clientX - rect.left, y: clientY - rect.top };
    }
    
    function startDraw(e) {
        if (!drawActive) return;
        drawing = true;
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
        ctx.strokeStyle = currentColor;
        ctx.lineWidth = currentTool === 'pen' ? 2 : 20;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        if (currentTool === 'hl') ctx.globalCompositeOperation = 'multiply';
        else ctx.globalCompositeOperation = 'source-over';
    }
    
    function draw(e) {
        if (!drawing) return;
        e.preventDefault();
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
    }
    
    function endDraw() {
        if (drawing) { drawing = false; saveDrawing(); }
    }
    
    function toggleDraw(active) {
        drawActive = active !== undefined ? active : !drawActive;
        $('drawToggle').classList.toggle('active', drawActive);
        $('drawPanel').classList.toggle('visible', drawActive);
        if (drawActive) {
            createCanvas();
            canvas.classList.add('active');
            resizeCanvas();
        } else if (canvas) {
            canvas.classList.remove('active');
        }
    }
    
    function selectTool(btn) {
        document.querySelectorAll('.draw-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTool = btn.dataset.tool;
        currentColor = btn.dataset.color;
    }
    
    function clearPage() {
        if (!ctx) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        delete drawings[state.page];
    }
    
    // Events
    $('drawToggle').onclick = () => toggleDraw();
    $('clearDraw').onclick = clearPage;
    document.querySelectorAll('.draw-btn').forEach(btn => {
        btn.onclick = () => selectTool(btn);
    });
    
    // Drawing events (delegated to window for canvas)
    container.addEventListener('mousedown', e => { if (e.target === canvas) startDraw(e); });
    window.addEventListener('mousemove', draw);
    window.addEventListener('mouseup', endDraw);
    container.addEventListener('touchstart', e => { if (e.target === canvas) startDraw(e); }, { passive: false });
    window.addEventListener('touchmove', e => { if (drawing) draw(e); }, { passive: false });
    window.addEventListener('touchend', endDraw);
    
    // Resize canvas on image load or resize
    img.addEventListener('load', () => setTimeout(resizeCanvas, 100));
    window.addEventListener('resize', () => setTimeout(resizeCanvas, 100));
    container.addEventListener('scroll', () => { if (canvas) resizeCanvas(); });
    
    // Expose redraw for page changes
    window.redrawCanvas = () => { resizeCanvas(); redraw(); };
    window.resizeDrawCanvas = resizeCanvas;
})();

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
    print("Tools:")
    print("  📏 Ruler       Drag to position, rotate buttons")
    print("  ✏️ Draw        Pens (R/B/G/K) + Highlighters (Y/G/B/P)")
    print()
    print("Navigation:")
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
