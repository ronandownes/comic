#!/usr/bin/env python3
"""
build-comic.py v2 - Comic Viewer Generator
Place in E:\\comic alongside pages/ and toc.txt, then run.

Features:
  - Instagram-style ‹ › page navigation
  - ↑ ↓ scroll buttons (for PC without touchscreen)
  - Breadcrumb showing current chapter + page
  - TOC sidebar from toc.txt (human-editable, with JC LO codes)
  - Falls back to toc.json if no toc.txt
  - Fullscreen: tap to show/hide ALL controls + Safari chrome
  - Fit height/width modes, zoom, keyboard, touch swipe

File structure expected:
  comic/
    pages/       ← WebP images (1-01-01.webp ... 5-12-XX.webp)
    thumbs/      ← (optional, not used by viewer)
    toc.txt      ← human-editable TOC (primary)
    toc.json     ← structured TOC (fallback)
    build-comic.py
    index.html   ← generated output

Navigation:
  ‹ ›           prev/next page (side buttons + touch swipe)
  ↑             scroll page up
  ↓             scroll page down
  ← → keys     prev/next page
  Ctrl+← →     prev/next (even when zoomed)
  Ctrl+Scroll   zoom in/out
  Double-click  reset zoom
  H / W         fit height / width
  T             toggle TOC
  F             fullscreen (tap image to show/hide controls)
  U             depth up
  Home / End    first / last page
"""

import json
import re
from pathlib import Path

# Version history:
#   1  - initial viewer (build-comic2.py, toc.txt STRAND/TOPIC format)
#   2  - toc.txt human-editable format with JC LO codes, toc.json fallback,
#        breadcrumb, depth-up nav, Safari fullscreen, pages/ folder scan
#   3  - flat 2-tier TOC (no book grouping), capture-relative page numbers,
#        CH B-CC format, collapsible chapter→section sidebar
VERSION = "3"
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}


def natural_sort_key(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(s))]


def find_images(folder):
    """Find images in pages/, webp/, or folder itself"""
    for sub in ['pages', 'webp']:
        d = folder / sub
        if d.is_dir():
            imgs = [f.name for f in d.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTENSIONS]
            if imgs:
                return sorted(imgs, key=natural_sort_key), d
    # Fallback: folder itself
    imgs = [f.name for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTENSIONS]
    return sorted(imgs, key=natural_sort_key), folder


def parse_toc_txt(folder):
    """Parse toc.txt into flat chapter list for 2-tier navigation.
    
    Supports two formats:
      Old: BOOK num | name / CH num | name / page | section | LOs
      New: CH B-CC | name / page | section | LOs  (flat, no BOOK lines)
    
    Output structure (always flat):
      [{"ref":"1-01", "name":"Counting", "toc":"1-01-01", "sections":[...]}]
    """
    f = folder / 'toc.txt'
    if not f.exists():
        return None

    chapters = []
    cur_book = None
    cur_ch = None

    for raw in f.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        # Strip trailing ! or ~ markers (approx/manual flags)
        clean = line.rstrip(' !~')
        parts = [p.strip() for p in clean.split('|')]

        # BOOK num | name (old format — just sets cur_book)
        if parts[0].upper().startswith('BOOK'):
            cur_book = int(parts[0].split()[1])
            continue

        # CH line — two formats:
        #   CH 04 | name        (old, needs cur_book)
        #   CH 3-04 | name      (new, book embedded)
        if parts[0].upper().startswith('CH'):
            token = parts[0].split()[1]  # "04" or "3-04"
            ch_name = parts[1] if len(parts) > 1 else ''
            
            if '-' in token:
                # New flat format: CH B-CC
                b, c = token.split('-')
                cur_book = int(b)
                ch_num = int(c)
            else:
                # Old format: CH num (uses cur_book)
                ch_num = int(token)
            
            if cur_book is None:
                continue
            
            ch_ref = f"{cur_book}-{ch_num:02d}"
            toc_ref = f"{ch_ref}-01"
            cur_ch = {'ref': ch_ref, 'number': ch_num, 'name': ch_name, 'toc': toc_ref, 'sections': []}
            chapters.append(cur_ch)
            continue

        # Section: page | name | LOs
        if cur_ch is not None and parts[0].isdigit():
            page_num = int(parts[0])
            sec_name = parts[1] if len(parts) > 1 else f'Page {page_num}'
            lo_str = parts[2] if len(parts) > 2 else ''
            los = [x.strip() for x in lo_str.split(',') if x.strip()] if lo_str else []
            page_ref = f"{cur_ch['ref']}-{page_num:02d}"
            sec = {'name': sec_name, 'page': page_ref}
            if los:
                sec['lo'] = los
            cur_ch['sections'].append(sec)

    return chapters if chapters else None


def load_toc(folder):
    """Load TOC: prefer toc.txt, fall back to toc.json. Always returns flat chapter list."""
    toc = parse_toc_txt(folder)
    if toc:
        return toc, 'toc.txt'

    f = folder / 'toc.json'
    if f.exists():
        data = json.loads(f.read_text(encoding='utf-8'))
        # Convert nested book>chapter to flat chapter list
        flat = []
        for book in data:
            b = book.get('book', 0)
            for ch in book.get('chapters', []):
                ch_ref = f"{b}-{ch['number']:02d}"
                entry = {
                    'ref': ch_ref,
                    'number': ch['number'],
                    'name': ch.get('name', ''),
                    'toc': ch.get('toc', f"{ch_ref}-01"),
                    'sections': ch.get('sections', [])
                }
                flat.append(entry)
        return flat, 'toc.json'

    return None, None


def get_template():
    return r'''<!DOCTYPE html>
<!-- build-comic.py v__VERSION__ | __DATE__ -->
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>__TITLE__</title>
<link rel="canonical" href="__CANONICAL__">
<meta name="generator" content="build-comic.py v__VERSION__">
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100dvh;overflow:hidden;touch-action:pan-x pan-y}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#1a1a1a;color:#e0e0e0;display:flex}

/* ── TOC sidebar ── */
.toc-toggle{position:fixed;top:50px;left:0;z-index:2000;background:#0066cc;color:#fff;border:none;border-radius:0 4px 4px 0;padding:8px 6px;cursor:pointer;font-size:14px}
.toc-toggle:hover{background:#0080ff}
.toc-sidebar{width:300px;background:#222;border-right:1px solid #333;display:flex;flex-direction:column;transition:margin-left .3s;z-index:1500;flex-shrink:0}
.toc-hidden .toc-sidebar{margin-left:-300px}
.toc-header{padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center}
.toc-header h2{font-size:14px}
.toc-close{background:none;border:none;color:#888;font-size:18px;cursor:pointer}
.toc-content{flex:1;overflow-y:auto;padding:6px}
.toc-chapter{padding:8px 10px;font-weight:600;font-size:12px;color:#0af;cursor:pointer;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center}
.toc-chapter::after{content:'▸';font-size:10px;transition:transform .2s;flex-shrink:0}
.toc-chapter.open::after{transform:rotate(90deg)}
.toc-chapter:hover{background:#2a2a2a}
.toc-chapter.active-ch{color:#fff}
.toc-sections{display:none;padding-bottom:4px}
.toc-chapter.open+.toc-sections{display:block}
.toc-item{padding:6px 10px;cursor:pointer;border-radius:4px;font-size:12px;margin:1px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.toc-item:hover{background:#333}
.toc-item.active{background:#0066cc;color:#fff}
.toc-section{padding-left:20px;color:#999;font-size:11px}
.toc-section:hover{color:#ccc}

/* ── Viewer ── */
.viewer{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.controls{background:#222;padding:5px 8px;border-bottom:1px solid #333;display:flex;align-items:center;gap:6px;flex-shrink:0;min-height:38px;z-index:100}
.controls-left{display:flex;align-items:center;gap:6px}
.controls-right{display:flex;align-items:center;gap:6px;margin-left:auto}
.breadcrumb{font-size:11px;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:40vw}
.breadcrumb span{cursor:pointer;padding:2px 4px;border-radius:3px}
.breadcrumb span:hover{background:#333;color:#ccc}
.breadcrumb .bc-sep{color:#555;cursor:default;padding:0 1px}
.breadcrumb .bc-sep:hover{background:none;color:#555}

button{background:#333;border:1px solid #444;color:#ccc;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:14px;min-width:32px;height:30px;display:flex;align-items:center;justify-content:center}
button:hover{background:#444}
button.active{background:#0066cc;border-color:#0080ff;color:#fff}
button.copied{background:#1a7a1a;border-color:#2a9a2a;color:#fff;transition:background .15s}
.sep{width:1px;height:20px;background:#444;flex-shrink:0}

.page-info{display:flex;align-items:center;gap:3px;font-size:12px;color:#aaa;white-space:nowrap}
#currentPage{cursor:pointer;padding:3px 6px;border-radius:3px;color:#ccc;font-weight:600}
#currentPage:hover{background:#444}
.page-input{width:50px;padding:3px;text-align:center;background:#1a1a1a;border:1px solid #0066cc;border-radius:4px;color:#e0e0e0;font-size:12px}

/* ── Image container ── */
.image-container{flex:1;display:flex;justify-content:center;align-items:flex-start;overflow:auto;background:#111;position:relative;min-height:0;-webkit-overflow-scrolling:touch}
.image-container.fit-height{align-items:center;overflow:hidden}
.image-container.fit-height img{max-height:100%;width:auto;height:auto}
.image-container.fit-width{overflow-y:auto;overflow-x:hidden}
.image-container.fit-width img{width:100%;max-width:100%;height:auto}
#pageImage{display:block;box-shadow:0 4px 20px rgba(0,0,0,.5);transform-origin:center center}

.zoom-indicator{position:fixed;bottom:20px;right:80px;background:rgba(0,0,0,.7);color:#fff;padding:6px 12px;border-radius:4px;font-size:13px;display:none;z-index:1200}

/* ── Instagram side nav ── */
.side-nav{position:fixed;top:50%;transform:translateY(-50%);z-index:1100;background:rgba(255,255,255,.85);color:#262626;border:none;width:40px;height:40px;border-radius:50%;cursor:pointer;opacity:.7;transition:all .15s;font-size:20px;font-weight:300;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.side-nav:hover{opacity:1;background:#fff;box-shadow:0 2px 12px rgba(0,0,0,.25)}
.side-nav.prev{left:10px;transition:all .3s}
.side-nav.next{right:10px}
body:not(.toc-hidden) .side-nav.prev{left:310px}

/* ── Depth-up button ── */
.scroll-btn{position:fixed;bottom:60px;z-index:1100;background:rgba(255,255,255,.85);color:#262626;border:none;width:36px;height:36px;border-radius:50%;cursor:pointer;opacity:0;pointer-events:none;transition:all .15s;font-size:16px;font-weight:600;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.scroll-btn:hover{opacity:1!important;background:#fff}
.scroll-btn.visible{opacity:.7;pointer-events:auto}
.scroll-down{left:calc(50% - 24px);transform:translateX(-100%)}
.scroll-up{left:calc(50% + 24px)}

/* ── Hide on mobile ── */
.hide-mobile{}
@media(max-width:600px){
  .hide-mobile{display:none!important}
  .controls{padding:4px 6px;gap:4px}
  button{padding:3px 6px;font-size:12px;min-width:28px;height:26px}
  .toc-sidebar{width:260px}
  .toc-hidden .toc-sidebar{margin-left:-260px}
  .side-nav{width:34px;height:34px;font-size:16px;opacity:.5}
  .side-nav.prev{left:6px}.side-nav.next{right:6px}
  body:not(.toc-hidden) .side-nav.prev{left:270px}
  .breadcrumb{max-width:30vw;font-size:10px}
  .scroll-btn{width:30px;height:30px;font-size:14px;bottom:50px}
}

/* ── FULLSCREEN: hide everything, tap to show ── */
:fullscreen .controls,
:fullscreen .toc-toggle,
:fullscreen .toc-sidebar,
:fullscreen .scroll-btn,
:fullscreen .zoom-indicator{opacity:0;pointer-events:none;transition:opacity .3s}
:fullscreen .side-nav{opacity:.25;transition:opacity .3s}
:fullscreen .side-nav:hover{opacity:.9}
/* Show UI on tap */
:fullscreen.show-ui .controls{opacity:1;pointer-events:auto}
:fullscreen.show-ui .toc-toggle{opacity:1;pointer-events:auto}
:fullscreen.show-ui .scroll-btn.visible{opacity:.7;pointer-events:auto}
:fullscreen.show-ui .side-nav{opacity:.7}
/* Safari */
:-webkit-full-screen .controls,
:-webkit-full-screen .toc-toggle,
:-webkit-full-screen .toc-sidebar,
:-webkit-full-screen .scroll-btn,
:-webkit-full-screen .zoom-indicator{opacity:0;pointer-events:none;transition:opacity .3s}
:-webkit-full-screen .side-nav{opacity:.25;transition:opacity .3s}
:-webkit-full-screen .side-nav:hover{opacity:.9}
:-webkit-full-screen.show-ui .controls{opacity:1;pointer-events:auto}
:-webkit-full-screen.show-ui .toc-toggle{opacity:1;pointer-events:auto}
:-webkit-full-screen.show-ui .scroll-btn.visible{opacity:.7;pointer-events:auto}
:-webkit-full-screen.show-ui .side-nav{opacity:.7}

/* ── Clean mode fallback (iOS no Fullscreen API) ── */
.clean-mode .controls,
.clean-mode .toc-toggle,
.clean-mode .toc-sidebar,
.clean-mode .scroll-btn,
.clean-mode .zoom-indicator{opacity:0;pointer-events:none;transition:opacity .3s}
.clean-mode .side-nav{opacity:.25}
.clean-mode .side-nav:hover{opacity:.9}
.clean-mode.show-ui .controls{opacity:1;pointer-events:auto}
.clean-mode.show-ui .toc-toggle{opacity:1;pointer-events:auto}
.clean-mode.show-ui .scroll-btn.visible{opacity:.7;pointer-events:auto}
.clean-mode.show-ui .side-nav{opacity:.7}
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
  <div class="controls" id="controls">
    <div class="controls-left">
      <button id="tocBtn" title="Contents (T)">☰</button>
      <div class="breadcrumb" id="breadcrumb"></div>
    </div>
    <div class="controls-right">
      <div class="page-info">
        <span id="currentPage">1</span>
        <span style="color:#666" id="pageTotal"></span>
      </div>
      <div class="sep"></div>
      <button id="fitHeight" title="Fit Height (H)">↕</button>
      <button id="fitWidth" title="Fit Width (W)">↔</button>
      <div class="sep hide-mobile"></div>
      <button id="zoomOut" class="hide-mobile" title="Zoom Out">−</button>
      <button id="zoomIn" class="hide-mobile" title="Zoom In">+</button>
      <div class="sep"></div>
      <button id="fullscreen" title="Fullscreen (F)">⛶</button>
      <button id="copyLink" title="Copy link to page">📎</button>
    </div>
  </div>
  <div class="image-container fit-height" id="imageContainer">
    <img id="pageImage" src="" alt="Page">
  </div>
</div>

<button class="side-nav prev" id="sidePrev">‹</button>
<button class="side-nav next" id="sideNext">›</button>
<button class="scroll-btn scroll-up visible" id="scrollUp" title="Scroll up">↑</button>
<button class="scroll-btn scroll-down visible" id="scrollDown" title="Scroll down">↓</button>
<div class="zoom-indicator" id="zoomIndicator">100%</div>

<script>
const CONFIG = __CONFIG__;
const $ = id => document.getElementById(id);
const img = $('pageImage');
const container = $('imageContainer');

// ── State ──
let state = { page: 0, zoom: 1, fitMode: 'height', translateX: 0, translateY: 0 };
try { const s = localStorage.getItem('ba_viewer'); if (s) Object.assign(state, JSON.parse(s)); } catch(e) {}
function saveState() { try { localStorage.setItem('ba_viewer', JSON.stringify(state)); } catch(e) {} }

// ── Ref parsing: "pages/3-04-25.webp" → {book:3, chapter:4, page:25} ──
function getRef(idx) {
    return CONFIG.pages[idx].replace(/^.*\//, '').replace(/\.[^.]+$/, '');
}
function parseRef(ref) {
    const m = ref.match(/^(\d+)-(\d+)-(\d+)$/);
    return m ? { book: +m[1], chapter: +m[2], page: +m[3], ref } : null;
}
function makeRef(b, c, p) {
    return b + '-' + String(c).padStart(2,'0') + '-' + String(p).padStart(2,'0');
}

// ── TOC lookup (flat chapter list) ──
function findChapter(ref) {
    return CONFIG.toc?.find(x => x.ref === ref);
}
function chRef(p) { return p.book + '-' + String(p.chapter).padStart(2,'0'); }

// ── Load page ──
function loadPage(idx) {
    if (idx < 0 || idx >= CONFIG.pages.length) return;
    state.page = idx;
    img.src = CONFIG.pages[idx];
    state.zoom = 1; state.translateX = state.translateY = 0;
    updateTransform();
    container.scrollTop = container.scrollLeft = 0;
    updateBreadcrumb();
    updateTOCHighlight();
    updateScrollButtons();
    saveState();
}

// ── Breadcrumb ──
function updateBreadcrumb() {
    const p = parseRef(getRef(state.page));
    const bc = $('breadcrumb');
    const cp = $('currentPage');
    const pt = $('pageTotal');

    if (!p) { bc.innerHTML = ''; cp.textContent = state.page + 1; pt.textContent = '/ ' + CONFIG.pages.length; return; }

    const chapter = findChapter(chRef(p));
    const chLabel = chapter ? 'Ch' + p.chapter + ': ' + chapter.name : 'Ch ' + p.chapter;
    const pageLabel = p.page === 1 ? 'Contents' : 'p.' + p.page;

    // Count pages in this chapter
    const chPrefix = chRef(p) + '-';
    const chPages = CONFIG.pages.filter(pg => pg.includes(chPrefix)).length;

    bc.innerHTML =
        `<span data-nav="chapter" data-ref="${chRef(p)}">${chLabel}</span>`;

    cp.textContent = pageLabel;
    pt.textContent = '/ ' + chPages;

    // Breadcrumb click → chapter TOC
    bc.querySelectorAll('[data-nav]').forEach(el => {
        el.onclick = () => {
            const ref = el.dataset.ref + '-01';
            const idx = CONFIG.pageMap[ref];
            if (idx !== undefined) loadPage(idx);
        };
    });
}

// ── Scroll up/down (for fit-width on PC without touch) ──
function scrollPage(dir) {
    container.scrollBy({ top: dir * container.clientHeight * 0.6, behavior: 'smooth' });
}

function updateScrollButtons() {
    $('scrollUp').classList.add('visible');
    $('scrollDown').classList.add('visible');
}

// ── Fit mode ──
function setFitMode(mode) {
    state.fitMode = mode;
    container.classList.remove('fit-height', 'fit-width');
    container.classList.add('fit-' + mode);
    $('fitHeight').classList.toggle('active', mode === 'height');
    $('fitWidth').classList.toggle('active', mode === 'width');
    state.zoom = 1; state.translateX = state.translateY = 0;
    updateTransform();
    updateScrollButtons();
    saveState();
}

// ── Zoom / pan ──
function updateTransform() {
    if (state.zoom === 1) {
        img.style.transform = '';
        $('zoomIndicator').style.display = 'none';
    } else {
        img.style.transform = `scale(${state.zoom}) translate(${state.translateX}px,${state.translateY}px)`;
        $('zoomIndicator').textContent = Math.round(state.zoom * 100) + '%';
        $('zoomIndicator').style.display = 'block';
    }
}
function zoom(delta) { state.zoom = Math.max(.25, Math.min(5, state.zoom + delta)); updateTransform(); }
function pan(dx, dy) { if (state.zoom > 1) { state.translateX += dx; state.translateY += dy; updateTransform(); return true; } return false; }

// ── Page input ──
function showPageInput() {
    const span = $('currentPage');
    const inp = document.createElement('input');
    inp.type = 'number'; inp.className = 'page-input';
    inp.value = state.page + 1; inp.min = 1; inp.max = CONFIG.pages.length;
    const done = () => { loadPage(parseInt(inp.value) - 1); inp.replaceWith(span); };
    inp.onkeydown = e => { if (e.key === 'Enter') done(); else if (e.key === 'Escape') inp.replaceWith(span); };
    inp.onblur = done;
    span.replaceWith(inp); inp.focus(); inp.select();
}

// ── TOC sidebar ──
function toggleTOC(show) {
    if (show === true) document.body.classList.remove('toc-hidden');
    else if (show === false) document.body.classList.add('toc-hidden');
    else document.body.classList.toggle('toc-hidden');
}

function renderTOC() {
    const content = $('tocContent');
    if (!CONFIG.toc?.length) {
        let html = '';
        for (let i = 0; i < CONFIG.pages.length; i += 20) {
            html += `<div class="toc-item" data-idx="${i}">Pages ${i+1}–${Math.min(i+20, CONFIG.pages.length)}</div>`;
        }
        content.innerHTML = html;
        content.querySelectorAll('.toc-item').forEach(el => {
            el.onclick = () => { loadPage(+el.dataset.idx); toggleTOC(false); };
        });
        return;
    }

    let html = '';
    CONFIG.toc.forEach(ch => {
        const chIdx = CONFIG.pageMap[ch.toc] ?? 0;
        html += `<div class="toc-chapter" data-ref="${ch.ref}" data-idx="${chIdx}">${ch.ref.replace(/^\d+-/,'')}. ${ch.name}</div>`;
        html += `<div class="toc-sections" data-ref="${ch.ref}">`;
        (ch.sections || []).forEach(s => {
            const sIdx = CONFIG.pageMap[s.page];
            html += `<div class="toc-item toc-section" data-idx="${sIdx ?? 0}" data-ref="${ch.ref}">${s.name}</div>`;
        });
        html += `</div>`;
    });
    content.innerHTML = html;

    // Chapter toggle (click heading → expand/collapse, also navigate)
    content.querySelectorAll('.toc-chapter').forEach(el => {
        el.onclick = () => {
            const wasOpen = el.classList.contains('open');
            if (!wasOpen) {
                // Close all, open this one
                content.querySelectorAll('.toc-chapter').forEach(x => x.classList.remove('open'));
                el.classList.add('open');
            } else {
                el.classList.toggle('open');
            }
            loadPage(+el.dataset.idx);
            toggleTOC(false);
        };
    });
    // Section click → navigate
    content.querySelectorAll('.toc-section').forEach(el => {
        el.onclick = e => { e.stopPropagation(); loadPage(+el.dataset.idx); toggleTOC(false); };
    });
}

function updateTOCHighlight() {
    const p = parseRef(getRef(state.page));
    const ref = p ? chRef(p) : null;
    // Expand current chapter
    document.querySelectorAll('.toc-chapter').forEach(el => {
        el.classList.toggle('open', ref && el.dataset.ref === ref);
        el.classList.toggle('active-ch', ref && el.dataset.ref === ref);
    });
    // Highlight nearest section
    let best = null, bestDist = Infinity;
    document.querySelectorAll('.toc-section[data-idx]').forEach(el => {
        const idx = +el.dataset.idx;
        el.classList.remove('active');
        const dist = state.page - idx;
        if (dist >= 0 && dist < bestDist && ref && el.dataset.ref === ref) {
            best = el; bestDist = dist;
        }
    });
    if (best) {
        best.classList.add('active');
        if (!document.body.classList.contains('toc-hidden')) {
            best.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }
}

// ── Fullscreen ──
let uiTimeout;
function isFullscreen() { return !!(document.fullscreenElement || document.webkitFullscreenElement); }
function isCleanMode() { return document.body.classList.contains('clean-mode'); }
function isImmersive() { return isFullscreen() || isCleanMode(); }

function toggleFullscreen() {
    if (isFullscreen()) {
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    } else if (isCleanMode()) {
        document.body.classList.remove('clean-mode', 'show-ui');
    } else {
        const el = document.documentElement;
        const req = el.requestFullscreen || el.webkitRequestFullscreen;
        if (req) {
            req.call(el).catch(() => {
                // Fullscreen API failed (e.g. iPhone) → clean mode
                document.body.classList.add('clean-mode');
            });
        } else {
            document.body.classList.add('clean-mode');
        }
    }
}

function showUI() {
    clearTimeout(uiTimeout);
    document.documentElement.classList.add('show-ui');
    document.body.classList.add('show-ui');
    uiTimeout = setTimeout(() => {
        document.documentElement.classList.remove('show-ui');
        document.body.classList.remove('show-ui');
    }, 3000);
}

// Exit clean mode when exiting fullscreen
document.addEventListener('fullscreenchange', () => {
    if (!isFullscreen()) { document.documentElement.classList.remove('show-ui'); document.body.classList.remove('show-ui'); }
});
document.addEventListener('webkitfullscreenchange', () => {
    if (!isFullscreen()) { document.documentElement.classList.remove('show-ui'); document.body.classList.remove('show-ui'); }
});

// ── Events ──
$('tocToggle').onclick = () => toggleTOC();
$('tocBtn').onclick = () => toggleTOC();
$('tocClose').onclick = () => toggleTOC(false);
$('sidePrev').onclick = () => loadPage(state.page - 1);
$('sideNext').onclick = () => loadPage(state.page + 1);
$('scrollUp').onclick = () => scrollPage(-1);
$('scrollDown').onclick = () => scrollPage(1);
$('fitHeight').onclick = () => setFitMode('height');
$('fitWidth').onclick = () => setFitMode('width');
$('zoomIn').onclick = () => zoom(.15);
$('zoomOut').onclick = () => zoom(-.15);
$('fullscreen').onclick = toggleFullscreen;
$('copyLink').onclick = () => {
    const url = location.origin + location.pathname + '#page=' + (state.page + 1);
    navigator.clipboard.writeText(url).then(() => {
        const btn = $('copyLink');
        btn.classList.add('copied');
        btn.textContent = '✔';
        setTimeout(() => { btn.classList.remove('copied'); btn.textContent = '📎'; }, 2000);
    });
};
$('currentPage').onclick = showPageInput;
img.ondblclick = () => { state.zoom = 1; state.translateX = state.translateY = 0; updateTransform(); };

// Tap on image to toggle UI in immersive mode
container.addEventListener('click', e => {
    if (isImmersive() && (e.target === img || e.target === container)) {
        showUI();
        e.stopPropagation();
    }
    container.focus();
});

// ── Keyboard ──
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key;

    // Ctrl+Arrow always changes page
    if (e.ctrlKey || e.metaKey) {
        if (k === 'ArrowLeft') { loadPage(state.page - 1); e.preventDefault(); return; }
        if (k === 'ArrowRight') { loadPage(state.page + 1); e.preventDefault(); return; }
    }

    // Zoomed: arrows pan
    if (state.zoom > 1) {
        if (k === 'ArrowLeft') { pan(50, 0); e.preventDefault(); return; }
        if (k === 'ArrowRight') { pan(-50, 0); e.preventDefault(); return; }
        if (k === 'ArrowUp') { pan(0, 50); e.preventDefault(); return; }
        if (k === 'ArrowDown') { pan(0, -50); e.preventDefault(); return; }
    }

    if (k === 'ArrowLeft') { loadPage(state.page - 1); e.preventDefault(); }
    else if (k === 'ArrowRight') { loadPage(state.page + 1); e.preventDefault(); }
    else if (k === 'ArrowUp') { scrollPage(-1); e.preventDefault(); }
    else if (k === 'ArrowDown') { scrollPage(1); e.preventDefault(); }
    else if (k === 'PageUp') { loadPage(state.page - 1); e.preventDefault(); }
    else if (k === 'PageDown') { loadPage(state.page + 1); e.preventDefault(); }
    else if (k === 'Home') loadPage(0);
    else if (k === 'End') loadPage(CONFIG.pages.length - 1);
    else if (k === 'h' || k === 'H') setFitMode('height');
    else if (k === 'w' || k === 'W') setFitMode('width');
    else if (k === 't' || k === 'T') toggleTOC();
    else if (k === 'f' || k === 'F') toggleFullscreen();
    else if (k === 'Escape') { if (isCleanMode()) { document.body.classList.remove('clean-mode','show-ui'); } }
});

// Ctrl+wheel zoom
document.addEventListener('wheel', e => {
    if (e.ctrlKey || e.metaKey) { e.preventDefault(); zoom(e.deltaY > 0 ? -.1 : .1); }
}, { passive: false });

// Touch swipe
let touchStart = null;
container.addEventListener('touchstart', e => {
    if (e.touches.length === 1 && state.zoom === 1) touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY, t: Date.now() };
}, { passive: true });
container.addEventListener('touchend', e => {
    if (!touchStart || state.zoom !== 1) { touchStart = null; return; }
    const dx = e.changedTouches[0].clientX - touchStart.x;
    const dy = e.changedTouches[0].clientY - touchStart.y;
    const dt = Date.now() - touchStart.t;
    // Horizontal swipe: change page
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5 && dt < 500) {
        loadPage(state.page + (dx > 0 ? -1 : 1));
    }
    // Quick tap in immersive mode (handled by click)
    touchStart = null;
});

// ── Init ──
renderTOC();
setFitMode(state.fitMode);
const hash = location.hash.match(/#page=(\d+)/);
if (hash) state.page = parseInt(hash[1]) - 1;
loadPage(state.page);
window.onhashchange = () => { const m = location.hash.match(/#page=(\d+)/); if (m) loadPage(parseInt(m[1]) - 1); };

container.tabIndex = 0;
container.style.outline = 'none';
container.focus();
</script>
</body>
</html>'''


def build(folder):
    folder = Path(folder)
    images, img_folder = find_images(folder)

    if not images:
        print(f"No images found in {folder}")
        print(f"  Checked: {folder}, {folder / 'pages'}, {folder / 'webp'}")
        return False

    # Path prefix relative to index.html
    img_prefix = ''
    if img_folder != folder:
        img_prefix = img_folder.name + '/'
    images_full = [img_prefix + im for im in images]

    # Build ref → index map from filenames
    page_map = {}
    for i, im in enumerate(images):
        stem = Path(im).stem  # "1-01-14"
        page_map[stem] = i

    # Load TOC (toc.txt preferred, toc.json fallback)
    toc, toc_source = load_toc(folder)

    title = folder.name.replace('-', ' ').replace('_', ' ').title()

    config = {
        'pages': images_full,
        'toc': toc,
        'pageMap': page_map
    }

    from datetime import datetime
    html = get_template()
    html = html.replace('__TITLE__', title)
    html = html.replace('__CONFIG__', json.dumps(config, separators=(',', ':')))
    html = html.replace('__VERSION__', VERSION)
    html = html.replace('__DATE__', datetime.now().strftime('%Y-%m-%d %H:%M'))
    html = html.replace('__CANONICAL__', f'./{folder.name}/')

    output = folder / 'index.html'
    output.write_text(html, encoding='utf-8')

    toc_info = 'No'
    if toc:
        chs = len(toc)
        secs = sum(len(c.get('sections', [])) for c in toc)
        lo_count = sum(1 for c in toc for s in c.get('sections', []) if s.get('lo'))
        toc_info = f"{toc_source} ({chs} chapters, {secs} sections, {lo_count} with LOs)"

    print(f"build-comic.py v{VERSION}")
    print(f"  Folder:  {folder}")
    print(f"  Images:  {len(images)} (from {img_folder.name}/)")
    print(f"  TOC:     {toc_info}")
    print(f"  PageMap: {len(page_map)} refs")
    print(f"  Output:  index.html")
    print()
    print("Navigation:")
    print("  ‹ ›         Page prev/next (side buttons + swipe)")
    print("  ↑ ↓         Scroll page up/down")
    print("  ← → keys   Page prev/next")
    print("  H / W       Fit height / width")
    print("  T           Toggle TOC sidebar")
    print("  F           Fullscreen (tap image to show/hide controls)")
    print("  Ctrl+Scroll Zoom")
    return True


if __name__ == '__main__':
    import sys
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    build(folder)
