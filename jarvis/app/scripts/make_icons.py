"""Home Screen icons for the website (plan 2.5), from Ananta's mark (its shapes are read from src/logo.tsx) in the Bat Mode colours, rendered with the
Chromium that Playwright ships, or on the Mac with Quick Look and sips. Run from jarvis/app:  python3 scripts/make_icons.py   (writes public/icons/*.png)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def shapes() -> dict:
    """The mark's shapes and colours, read from src/logo.tsx (the one place they live; 9 Nov 2026: Shiva's trishul in forged steel, the
    lattice gone, the emblem on its own near-black disc)."""
    import json
    import re
    src = (ROOT / "src" / "logo.tsx").read_text()
    block = src[src.index("MARK-SHAPES-START"):src.index("MARK-SHAPES-END")]
    tri = json.loads(re.sub(r",\s*\]", "]", re.search(r"export const TRISHUL\s*=\s*(\[.*?\]);\n", block, re.S).group(1)))
    a = re.search(r'export const LETTER_A = "([^"]+)"', block).group(1)
    col = json.loads(re.search(r"export const MARK_COLORS = (\{.*?\});", block, re.S).group(1))
    return {"trishul": tri, "a": a, "colors": col}


D = shapes()["colors"]["disc"]          # the page behind the mark in every icon: the emblem's own near-black


def svg(pad: float) -> str:
    """The mark in a 100 x 100 box, shrunk by `pad` around the centre (maskable icons need a safe margin)."""
    s = shapes()
    c = s["colors"]
    k = 1 - pad
    tri = "".join(f'<path d="{d}"/>' for d in s["trishul"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1024" height="1024"><rect width="100" height="100" fill="{c["disc"]}"/>
<defs><linearGradient id="st" gradientUnits="userSpaceOnUse" x1="0" y1="4" x2="0" y2="94"><stop offset="0" stop-color="{c["steelTop"]}"/><stop offset="0.5" stop-color="{c["steelMid"]}"/><stop offset="1" stop-color="{c["steelBottom"]}"/></linearGradient></defs>
<g transform="translate(50 50) scale({k}) translate(-50 -50)">
<circle cx="50" cy="50" r="48" fill="{c["disc"]}"/><circle cx="50" cy="50" r="46.6" fill="none" stroke="{c["ring"]}" stroke-width="4.4"/>
<circle cx="50" cy="50" r="42.6" fill="none" stroke="{c["gold"]}" stroke-width="1.1" opacity="0.6"/>
<g fill="url(#st)">{tri}</g>
<path fill-rule="evenodd" d="{s["a"]}" fill="{c["gold"]}" stroke="{c["disc"]}" stroke-width="2.4" stroke-linejoin="round"/>
</g></svg>'''


def _render_mac(svg_text: str, n: int, png: Path) -> None:
    """7 Nov 2026: this Mac has no Playwright Chromium; macOS renders an SVG with Quick Look (WebKit) and sips scales it to n x n."""
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="ananta_icon_"))
    (tmp / "m.svg").write_text(svg_text)
    subprocess.run(["qlmanage", "-t", "-s", "1024", "-o", str(tmp), str(tmp / "m.svg")], check=True, capture_output=True)
    subprocess.run(["sips", "-s", "format", "png", "-z", str(n), str(n), str(tmp / "m.svg.png"), "--out", str(png)], check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)


def _render_chromium(svg_text: str, n: int, png: Path, out: Path) -> None:
    (out / "_mark.svg").write_text(svg_text)
    try:
        js = f"""const {{ chromium }} = require('playwright'); const fs = require('fs');
(async () => {{ const b = await chromium.launch(); const p = await b.newPage({{ viewport: {{ width: {n}, height: {n} }} }});
  await p.setContent('<body style="margin:0;background:{D}">' + fs.readFileSync('{out / "_mark.svg"}', 'utf8').replace('width="1024" height="1024"', 'width="{n}" height="{n}"') + '</body>');
  await p.screenshot({{ path: '{png}' }}); await b.close(); }})();"""
        subprocess.run(["node", "-e", js], check=True)
    finally:
        (out / "_mark.svg").unlink(missing_ok=True)


if __name__ == "__main__":
    import platform
    out = ROOT / "public" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(out / name, n, pad) for name, n, pad in (("icon-192.png", 192, 0.0), ("icon-512.png", 512, 0.0), ("maskable-512.png", 512, 0.28),
                                                         ("apple-touch-icon.png", 180, 0.06), ("favicon-32.png", 32, 0.0))]
    # 8 Nov 2026 (the TestFlight build): the iPhone app's icon (1024, square, no transparency; iOS rounds the corners) and the splash mark
    (ROOT / "assets").mkdir(exist_ok=True)
    jobs += [(ROOT / "assets" / "icon.png", 1024, 0.1), (ROOT / "assets" / "splash-icon.png", 1024, 0.0)]
    for png, n, pad in jobs:
        if platform.system() == "Darwin":
            _render_mac(svg(pad), n, png)
        else:
            _render_chromium(svg(pad), n, png, out)
        if png.name == "icon.png" and platform.system() == "Darwin":      # the App Store refuses an icon with an alpha channel
            jpg = png.with_suffix(".jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "best", str(png), "--out", str(jpg)], check=True, capture_output=True)
            subprocess.run(["sips", "-s", "format", "png", str(jpg), "--out", str(png)], check=True, capture_output=True)
            jpg.unlink()
        print("wrote", png)
