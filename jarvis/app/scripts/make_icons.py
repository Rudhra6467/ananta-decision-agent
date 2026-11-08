"""Home Screen icons for the website (plan 2.5), from Ananta's mark (its shapes are read from src/logo.tsx) in the Bat Mode colours, rendered with the
Chromium that Playwright ships, or on the Mac with Quick Look and sips. Run from jarvis/app:  python3 scripts/make_icons.py   (writes public/icons/*.png)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Y, G, D = "#F2CF66", "#5A5E66", "#141518"


def shapes() -> dict:
    """The mark's shapes, read from src/logo.tsx (the one place they live; 7 Nov 2026: the trishul replaced the trident there)."""
    import json
    import re
    src = (ROOT / "src" / "logo.tsx").read_text()
    block = src[src.index("MARK-SHAPES-START"):src.index("MARK-SHAPES-END")]
    def arr(name: str):
        m = re.search(rf"export const {name}(?::[^=]+)?\s*=\s*(\[.*?\]);\n", block, re.S)
        return json.loads(re.sub(r",\s*\]", "]", m.group(1)))
    a = re.search(r'export const LETTER_A = "([^"]+)"', block).group(1)
    return {"arms": arr("TRISHUL_ARMS"), "trishul": arr("TRISHUL"), "a": a, "nodes": arr("NODES"), "edges": arr("EDGES")}


def svg(pad: float) -> str:
    """The mark in a 100 x 100 box, shrunk by `pad` around the centre (maskable icons need a safe margin)."""
    s = shapes()
    k = 1 - pad
    N = s["nodes"]
    lat = "".join(f'<line x1="{N[a][0]}" y1="{N[a][1]}" x2="{N[b][0]}" y2="{N[b][1]}"/>' for a, b in s["edges"])
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.7"/>' for x, y in N)
    arms = "".join(f'<path d="{d}"/>' for d in s["arms"])
    tri = "".join(f'<path d="{d}"/>' for d in s["trishul"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1024" height="1024"><rect width="100" height="100" fill="{D}"/>
<g transform="translate(50 50) scale({k}) translate(-50 -50)">
<circle cx="50" cy="50" r="47" fill="none" stroke="{G}" stroke-width="4"/><circle cx="50" cy="50" r="42.5" fill="none" stroke="{Y}" stroke-width="1.2" opacity="0.55"/>
<g fill="none" stroke="{G}" stroke-width="3.2" stroke-linecap="round">{arms}</g><g fill="{G}">{tri}</g>
<g stroke="{Y}" stroke-width="0.9" opacity="0.6" fill="{Y}">{lat}{dots}</g>
<path fill-rule="evenodd" d="{s["a"]}" fill="{Y}" stroke="{D}" stroke-width="2.2" stroke-linejoin="round"/>
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
    for name, n, pad in (("icon-192.png", 192, 0.0), ("icon-512.png", 512, 0.0), ("maskable-512.png", 512, 0.28), ("apple-touch-icon.png", 180, 0.06), ("favicon-32.png", 32, 0.0)):
        if platform.system() == "Darwin":
            _render_mac(svg(pad), n, out / name)
        else:
            _render_chromium(svg(pad), n, out / name, out)
        print("wrote", out / name)
