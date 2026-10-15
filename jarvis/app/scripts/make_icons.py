"""Home Screen icons for the website (plan 2.5), from Ananta's mark (src/logo.tsx) in the Bat Mode colours, rendered with the
Chromium that Playwright ships. Run from jarvis/app:  python3 scripts/make_icons.py   (writes public/icons/*.png)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Y, G, D = "#F2CF66", "#5A5E66", "#141518"
NODES = [(20, 46), (25, 38), (29, 52), (22, 60), (31, 64), (80, 46), (75, 38), (71, 52), (78, 60), (69, 64)]
EDGES = [(0, 1), (0, 2), (2, 3), (2, 4), (5, 6), (5, 7), (7, 8), (7, 9)]


def svg(pad: float) -> str:
    """The mark in a 100 x 100 box, shrunk by `pad` around the centre (maskable icons need a safe margin)."""
    k = 1 - pad
    lat = "".join(f'<line x1="{NODES[a][0]}" y1="{NODES[a][1]}" x2="{NODES[b][0]}" y2="{NODES[b][1]}"/>' for a, b in EDGES)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.7"/>' for x, y in NODES)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1024" height="1024"><rect width="100" height="100" fill="{D}"/>
<g transform="translate(50 50) scale({k}) translate(-50 -50)">
<circle cx="50" cy="50" r="47" fill="none" stroke="{G}" stroke-width="4"/><circle cx="50" cy="50" r="42.5" fill="none" stroke="{Y}" stroke-width="1.2" opacity="0.55"/>
<g fill="{G}"><path d="M47 66 L53 66 L52 24 L48 24 Z"/><path d="M50 12 L55 24 L45 24 Z"/><path d="M44 60 C32 52 30 36 37 20 L30 19 C24 36 27 56 41 66 Z"/>
<path d="M56 60 C68 52 70 36 63 20 L70 19 C76 36 73 56 59 66 Z"/><path d="M40 66 C44 72 56 72 60 66 L58 62 C55 66 45 66 42 62 Z"/></g>
<g stroke="{Y}" stroke-width="0.9" opacity="0.6" fill="{Y}">{lat}{dots}</g>
<path fill-rule="evenodd" d="M50 20 L79 82 L66 82 L60 68 L40 68 L34 82 L21 82 Z M50 41 L56 57 L44 57 Z" fill="{Y}" stroke="{D}" stroke-width="2.2" stroke-linejoin="round"/>
</g></svg>'''


if __name__ == "__main__":
    out = ROOT / "public" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for name, n, pad in (("icon-192.png", 192, 0.0), ("icon-512.png", 512, 0.0), ("maskable-512.png", 512, 0.28), ("apple-touch-icon.png", 180, 0.06), ("favicon-32.png", 32, 0.0)):
        (out / "_mark.svg").write_text(svg(pad))
        js = f"""const {{ chromium }} = require('playwright'); const fs = require('fs');
(async () => {{ const b = await chromium.launch(); const p = await b.newPage({{ viewport: {{ width: {n}, height: {n} }} }});
  await p.setContent('<body style="margin:0;background:{D}">' + fs.readFileSync('{out / "_mark.svg"}', 'utf8').replace('width="1024" height="1024"', 'width="{n}" height="{n}"') + '</body>');
  await p.screenshot({{ path: '{out / name}' }}); await b.close(); }})();"""
        subprocess.run(["node", "-e", js], check=True)
        print("wrote", out / name)
    (out / "_mark.svg").unlink()
