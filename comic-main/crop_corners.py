"""
crop_corners.py - Crop top-left corners from comic pages for plaque detection.
Run: python e:/comic/crop_corners.py e:/comic/raw
Output: e:/comic/corners/ with same filenames
"""

import os, sys, re
from PIL import Image

def main():
    if len(sys.argv) < 2:
        print("Usage: python crop_corners.py <raw_folder>")
        sys.exit(1)

    raw = sys.argv[1]
    out = os.path.join(os.path.dirname(raw), 'corners')
    os.makedirs(out, exist_ok=True)

    files = sorted(f for f in os.listdir(raw)
                   if re.match(r'\d-\d\d-\d\d\.(jpg|webp|png)', f))

    print(f"Cropping {len(files)} files -> {out}")

    for i, fname in enumerate(files):
        img = Image.open(os.path.join(raw, fname))
        w, h = img.size
        # Top-left: 1/2 width, 1/5 height
        crop = img.crop((0, 0, w // 2, h // 5))
        crop.save(os.path.join(out, fname), quality=85)
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(files)}")

    print(f"Done. {len(files)} corners saved to {out}")

if __name__ == '__main__':
    main()
