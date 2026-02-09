"""
detect_plaques.py — Find section title plaques in Beast Academy comic pages.
═══════════════════════════════════════════════════════════════════════════════
Run in your raw/ or pages/ folder:
    python detect_plaques.py E:\stem-learning\comic2\raw

Outputs to: plaque_results/ in the same parent directory
  - contact sheets (one per chapter) showing top-left crops
  - detected_sections.txt with auto-detected plaque pages
  - toc_updated.txt with corrected page numbers

How it works:
  1. Crops top-left 25% x 12% of each page (where plaques live)
  2. Scores each crop: plaques have MORE edges + text-like contrast
     than regular comic art in that region (borders, bold text, solid bg)
  3. For each chapter, picks top N scoring pages (N = expected sections)
  4. Generates contact sheets for visual verification
"""

import os, sys, re, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

# ── Expected sections per chapter (from toc.txt) ──
SECTIONS = {
    '1-01': ['First Day', 'Campus Tour', 'One Hundred'],
    '1-02': ['Names', 'Spins & Flips', 'Apart & Together'],
    '1-03': ['One for One', 'More or Less', 'Lengths', 'The Beginning'],
    '1-04': ['Addition', '+ & =', 'Strategies', 'Ten'],
    '1-05': ['Taking Away', 'Difference', 'Strategies'],
    '1-06': ['Odd One Out', 'Categories', 'Circle Diagrams'],
    '1-07': ['Review', 'The Number Line', 'Ten', 'Tens & Ones'],
    '1-08': ['Comparing', 'Expressions', 'Comparing Differences', 'Tricks'],
    '1-09': ['Shape Patterns', 'Number Patterns', 'Special Patterns'],
    '1-10': ['Beyond 100', 'Counting Up', 'Blocks', 'Apart'],
    '1-11': ['Comparing Lengths', 'Length', 'Days', 'Clocks'],
    '1-12': ['Location', 'Directions', 'Turns', 'Order'],
    '2-01': ['First Day', 'Pirate Numbers', 'Ones Tens Hundreds', 'Regrouping & Breaking'],
    '2-02': ['Stacking', 'Groggs Notes', 'Making Hundreds', 'Abacus', 'Rounding'],
    '2-03': ['Odds & Evens', 'Skip-Counting', 'Counting Back', 'Math Meet'],
    '2-04': ['Taking Away', '+ & -', 'Counting Up', 'A Little Extra', "Alex's Notes", 'Order'],
    '2-05': ['Connections', 'Order of Operations', "Grogg's Notes", 'Parentheses', 'Variables', 'Math Meet'],
    '2-06': ['Guessing', 'Backwards', 'Drawing', 'Math Meet'],
    '2-07': ['Measurement', 'Rulers', "Grogg's Notes", 'From Inches to Miles', 'Mixed Measures'],
    '2-08': ['Adding and Subtracting', 'Zero-Sum Game', 'Evaluating Expressions', 'Parentheses', 'Skip-Counting'],
    '2-09': ['Even & Odd', 'Doubling', 'Halving', 'Splitting', "Alex's Notes", 'Math Meet'],
    '2-10': ['Thousands and Beyond', "Grogg's Notes", 'Computing', 'Comparing', 'Estimation', 'Infinity'],
    '2-11': ['Algorithms', 'Stacking', 'More Than Two', 'Stacking Subtraction', 'Cryptarithms'],
    '2-12': ['Counting Paths', 'Organizing', 'Finding a Pattern', 'Math Meet'],
    '3-01': ['Angles', 'Triangles', "Don't Make a Triangle", 'Quadrilaterals', "Grogg's Notes", 'Polyominoes'],
    '3-02': ['Multiplication', 'Lizards', 'Multiples', 'Math Meet'],
    '3-03': ['Perfect Squares', 'Square Roots', "Winnie's Notes", 'Cubes', 'Cube Roots', 'Exponents', 'Math Meet'],
    '3-04': ['St Ives', 'The Times Table', 'The Commutative Property', 'Block Blob', 'Multiplying Big Numbers', 'The Associative Property', 'Multiplying by 4 and by 5', "Winnie's Notes", 'Penny Rows', "Grogg's Notes"],
    '3-05': ['Dozens of Eggs', 'Distributive Property', "Lizzie's Notes", 'Decimals', 'Multiplying by 9', "Alex's Notes", "Winnie's Notes", 'Math Meet'],
    '3-06': ['Order of Operations', 'Big Rectangles', 'Pirate Booty', 'The Distributive Property', 'Math Meet'],
    '3-07': ['The number n', 'Variables', "Winnie's Notes", 'Writing Equations', "Lizzie's Notes", 'Solving Equations', 'Wild Tic-tac-toe', 'Capsules'],
    '3-08': ['The Number Line', 'Negative Numbers', 'Negative Signs', 'Addition', 'Subtraction', 'Absolute Value', 'Math Meet'],
    '3-09': ['Flossie', 'Units', 'Customary Units', "Lizzie's Notes", 'Carpool', 'The Metric System', 'Math Meet', "Alex's Notes", "Proper Measurin'"],
    '3-10': ['Sharing', 'Quotients', 'Leftovers', 'Divisibility', "Lizzie's Notes", "Winnie's Notes", 'Division by Zero', 'Long Division', 'Remainders', 'Math Meet'],
    '3-11': ['Area', 'Units', 'Rectangles', 'Make a Rectangle', 'Right Triangles', 'Little Monsters'],
    '3-12': ['Fractions', 'The Number Line', 'Comparisons', 'Adding and Subtracting', "Alex's Notes", 'Mixed Numbers', 'Math Meet'],
    '4-01': ['Shapes', 'Angles', "Grogg's Notes", 'Parallel & Perpendicular', 'Symmetry', 'Math Relays'],
    '4-02': ['Multiplication Review', 'The Distributive Property', 'Large Products', 'Math Meet'],
    '4-03': ['Factors', 'Factor Pairs', 'Primes and Composites', 'Factor Trees', 'Prime Factorization', 'Venn Diagrams', 'GCFs and LCMs', 'Math Relays'],
    '4-04': ['Division', 'Quotients', 'Story Problems', "Grogg's Notes", 'Checking', "Lizzie's Notes", 'Large Quotients', 'Math Relays'],
    '4-05': ['Multiples', 'Equivalent Fractions', "Winnie's Notes", 'Comparing', 'Mixed Numbers', 'Math Meet'],
    '4-06': ['Adding', "Alex's Notes", 'Subtracting', 'Mixed Numbers', 'Word Problems', 'Math Relays'],
    '4-07': ['Counting', 'Lists', 'Multiplication', 'Venn Diagrams', 'Math Relays'],
    '4-08': ['Decimal Place Value', 'Comparing Decimals', 'Addition', "Lizzie's Notes", 'Subtraction', "Alex's Notes", 'Money', "Winnie's Notes", 'Math Meet'],
    '4-09': ['Multiplication Review', "Lizzie's Notes", 'Estimation', 'Products', 'Patterns', "Grogg's Notes", 'Division', 'Math Relays'],
    '4-10': ['Probability', 'Outcomes', 'Compound Events', 'Think About It', 'Expected Value', 'Math Meet'],
    '4-11': ['Integers', 'Addition', 'More Addition', 'Subtraction', 'Multiplication', "Alex's Notes", 'Division', 'Math Relays'],
    '4-12': ['Congruence', 'Transformations', 'Rotational Symmetry', "Grogg's Notes", 'Constructions', 'Make a Shape', 'Tessellations', 'Math Relays'],
    '5-01': ['Base-10 Blocks', 'Powers of 10', 'Shifting', 'Decimal Multiplication', "Alex's Notes", 'Big Products', 'Decimal Division', 'Math Relays'],
    '5-02': ['Sequences', 'Sequence Rules', "Grogg's Notes", "Winnie's Notes", 'Growth', "Alex's Notes", 'Explicit Rules', 'Fibonacci', 'Math Relays'],
    '5-03': ['Stats', 'Mean', 'Median', 'Mean vs Median', 'Stem-and-Leaf', 'Math Meet'],
    '5-04': ['Expressions', 'Evaluating', 'Simplifying', 'Distribution', 'Math Relays'],
    '5-05': ['Equal or Not', 'Solving Equations', 'Balance', "Winnie's Notes", 'Word Problems', "Lizzie's Notes", 'Math Relays'],
    '5-06': ['Coordinate Plane', 'Graphing', 'Lines', 'Slope', "Grogg's Notes", "Lizzie's Notes", 'Nonlinear Graphs', 'Math Relays'],
    '5-07': ['Ratios', 'Equal Ratios', 'Rates', 'Unit Rates', 'Math Meet'],
    '5-08': ['Multiplying Fractions', 'Products', 'Mixed Numbers', 'Reciprocals', 'Division'],
    '5-09': ['Angles', 'Triangles', 'Quadrilaterals', 'Regular Polygons', 'Math Meet'],
    '5-10': ['Percents & Fractions', 'Percents & Decimals', 'Percent of a Number', 'Finding Percents', 'Proportions'],
    '5-11': ['Square Roots', 'Area', 'The Pythagorean Theorem', "Winnie's Notes", 'Right Triangles', "Alex's Notes", 'Math Relays'],
    '5-12': ['Scales', 'Similar Figures', 'Perimeter', 'Area', 'Volume', 'Surface Area', 'Math Meet'],
}


def score_plaque(img_path, crop_box=(0, 0, 0.25, 0.12)):
    """Score how likely the top-left crop contains a title plaque.
    
    Plaques have:
    - Strong edges (rectangular border + bold text)
    - Regions of solid color (plaque background)  
    - High contrast between text and background
    
    Returns score (higher = more likely plaque).
    """
    try:
        img = Image.open(img_path)
    except:
        return -1
    
    w, h = img.size
    x0 = int(w * crop_box[0])
    y0 = int(h * crop_box[1])
    x1 = int(w * crop_box[2])
    y1 = int(h * crop_box[3])
    crop = img.crop((x0, y0, x1, y1))
    
    # Resize for speed
    thumb = crop.resize((100, 50), Image.LANCZOS)
    arr = np.array(thumb).astype(float)
    
    # Score 1: Edge density (plaques have strong rectangular borders)
    gray = thumb.convert('L')
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_score = np.mean(np.array(edges))
    
    # Score 2: Color block uniformity — look for large-ish patches of solid color
    # Split into 5x5 grid, count blocks with low internal variance
    gh, gw = 5, 5
    bh, bw = arr.shape[0] // gh, arr.shape[1] // gw
    uniform_blocks = 0
    for gy in range(gh):
        for gx in range(gw):
            block = arr[gy*bh:(gy+1)*bh, gx*bw:(gx+1)*bw]
            var = np.mean([np.var(block[:, :, c]) for c in range(min(3, block.shape[2]))])
            if var < 300:
                uniform_blocks += 1
    block_score = uniform_blocks / (gh * gw)
    
    # Score 3: Contrast — high std dev across whole crop means text+bg contrast
    contrast_score = np.std(arr) / 80.0  # normalize
    
    # Score 4: Check for horizontal/vertical structure (plaque borders)
    gray_arr = np.array(gray).astype(float)
    h_edges = np.mean(np.abs(np.diff(gray_arr, axis=1)))
    v_edges = np.mean(np.abs(np.diff(gray_arr, axis=0)))
    structure_score = (h_edges + v_edges) / 30.0
    
    # Combined score (tuned to prefer plaque characteristics)
    total = edge_score * 0.3 + block_score * 15 + contrast_score * 5 + structure_score * 3
    
    return total


def make_contact_sheet(chapter_key, file_list, folder, out_dir, scores):
    """Create a visual grid of top-left crops for manual verification."""
    n = len(file_list)
    if n == 0:
        return
    
    cols = min(8, n)
    rows = (n + cols - 1) // cols
    
    thumb_w, thumb_h = 180, 100
    pad = 4
    label_h = 20
    cell_w = thumb_w + pad * 2
    cell_h = thumb_h + pad * 2 + label_h
    
    sheet_w = cols * cell_w
    sheet_h = rows * cell_h + 40  # title bar
    
    sheet = Image.new('RGB', (sheet_w, sheet_h), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    
    # Title
    n_expected = len(SECTIONS.get(chapter_key, []))
    title = f"CH {chapter_key} — {n} pages, {n_expected} sections expected"
    draw.text((10, 10), title, fill=(0, 0, 0))
    
    for i, fname in enumerate(file_list):
        col = i % cols
        row = i // cols
        x = col * cell_w + pad
        y = row * cell_h + 40 + pad
        
        fpath = os.path.join(folder, fname)
        try:
            img = Image.open(fpath)
            w, h = img.size
            crop = img.crop((0, 0, int(w * 0.30), int(h * 0.15)))
            crop = crop.resize((thumb_w, thumb_h), Image.LANCZOS)
        except:
            crop = Image.new('RGB', (thumb_w, thumb_h), (200, 200, 200))
        
        # Highlight detected plaques
        score = scores.get(fname, 0)
        expected = SECTIONS.get(chapter_key, [])
        ranked = sorted([(scores.get(f, 0), f) for f in file_list], reverse=True)
        top_n = [f for _, f in ranked[:len(expected)]]
        
        if fname in top_n:
            # Green border for detected
            draw.rectangle([x - 3, y - 3, x + thumb_w + 3, y + thumb_h + 3], 
                          outline=(0, 180, 0), width=3)
        
        sheet.paste(crop, (x, y))
        
        # Label
        page_num = fname.split('-')[-1].split('.')[0]
        label = f"p{page_num} ({score:.0f})"
        draw.text((x, y + thumb_h + 2), label, fill=(0, 0, 0))
    
    sheet.save(os.path.join(out_dir, f"contact_{chapter_key}.png"))


def main():
    if len(sys.argv) < 2:
        print("Usage: python detect_plaques.py <folder_path>")
        print("  folder_path: path to raw/ or pages/ folder with B-CC-PP.jpg/webp files")
        sys.exit(1)
    
    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"Error: {folder} is not a directory")
        sys.exit(1)
    
    # Detect file extension
    files = sorted(os.listdir(folder))
    img_files = [f for f in files if re.match(r'\d-\d\d-\d\d\.(jpg|webp|png)', f)]
    if not img_files:
        print(f"No B-CC-PP image files found in {folder}")
        sys.exit(1)
    
    ext = img_files[0].split('.')[-1]
    print(f"Found {len(img_files)} {ext} files")
    
    # Group by chapter
    chapters = {}
    for f in img_files:
        ch_key = f[:4]  # "1-01"
        chapters.setdefault(ch_key, []).append(f)
    
    print(f"Found {len(chapters)} chapters")
    
    # Output directory
    out_dir = os.path.join(os.path.dirname(folder), 'plaque_results')
    os.makedirs(out_dir, exist_ok=True)
    
    # Process each chapter
    all_detections = {}
    
    for ch_key in sorted(chapters.keys()):
        ch_files = sorted(chapters[ch_key])
        expected = SECTIONS.get(ch_key, [])
        n_expected = len(expected)
        
        if n_expected == 0:
            print(f"  {ch_key}: no sections defined, skipping")
            continue
        
        # Score every page
        scores = {}
        for fname in ch_files:
            fpath = os.path.join(folder, fname)
            scores[fname] = score_plaque(fpath)
        
        # Rank and pick top N (but page 01 is always TOC, skip it)
        # Also first section always starts at page 02 or 03
        non_toc = [f for f in ch_files if not f.endswith('-01.' + ext)]
        ranked = sorted(non_toc, key=lambda f: scores.get(f, 0), reverse=True)
        detected = sorted(ranked[:n_expected])  # sort by page order
        
        # Extract page numbers
        pages = []
        for f in detected:
            pg = int(f.split('-')[-1].split('.')[0])
            pages.append(pg)
        
        all_detections[ch_key] = {
            'expected_sections': expected,
            'detected_pages': pages,
            'detected_files': detected,
            'scores': {f: round(scores.get(f, 0), 1) for f in ch_files}
        }
        
        status = "✓" if len(pages) == n_expected else "?"
        print(f"  {ch_key}: {n_expected} sections → pages {pages} {status}")
        
        # Generate contact sheet
        make_contact_sheet(ch_key, ch_files, folder, out_dir, scores)
    
    # ── Write results ──
    
    # 1. Raw detections JSON
    with open(os.path.join(out_dir, 'detections.json'), 'w') as f:
        json.dump(all_detections, f, indent=2)
    
    # 2. Human-readable detected sections
    with open(os.path.join(out_dir, 'detected_sections.txt'), 'w') as f:
        f.write("# Auto-detected section plaques\n")
        f.write("# Format: CH B-CC | section_name → page_number (capture)\n")
        f.write("# Review contact sheets to verify!\n\n")
        for ch_key in sorted(all_detections.keys()):
            det = all_detections[ch_key]
            f.write(f"CH {ch_key}\n")
            for i, (name, pg) in enumerate(zip(det['expected_sections'], det['detected_pages'])):
                f.write(f"  {pg:3d} | {name}\n")
            f.write("\n")
    
    # 3. Updated toc.txt format
    with open(os.path.join(out_dir, 'toc_detected.txt'), 'w') as f:
        f.write("# Comic 2 - Table of Contents (auto-detected from plaques)\n")
        f.write("# ═══════════════════════════════════════════════════════\n")
        f.write("# Format:  CH B-CC | chapter name\n")
        f.write("#          page | section name | LO codes\n")
        f.write("# Page = capture number → file B-CC-PP.webp\n")
        f.write("# ═══════════════════════════════════════════════════════\n\n")
        
        # Chapter names (will need to be filled in)
        for ch_key in sorted(all_detections.keys()):
            det = all_detections[ch_key]
            f.write(f"  CH {ch_key} | \n")
            for name, pg in zip(det['expected_sections'], det['detected_pages']):
                f.write(f"    {pg} | {name}\n")
    
    print(f"\nResults saved to: {out_dir}/")
    print(f"  contact_*.png  — visual grids for verification (green = detected)")
    print(f"  detections.json — full scores")
    print(f"  detected_sections.txt — readable summary")
    print(f"  toc_detected.txt — toc format")
    print(f"\nPlease review the contact sheets and correct any misdetections!")


if __name__ == '__main__':
    main()
