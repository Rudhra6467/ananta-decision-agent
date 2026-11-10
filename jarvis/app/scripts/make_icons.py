"""Home Screen icons for the website (plan 2.5), from Ananta's mark (its shapes are read from src/logo.tsx) in the Bat Mode colours, rendered with the
Chromium that Playwright ships, or on the Mac with Quick Look and sips. Run from jarvis/app:  python3 scripts/make_icons.py   (writes public/icons/*.png)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def mark2() -> dict:
    """10 Nov 2026 (the redesign, Icon A): the forged-bronze mark's shapes and colours, read from src/logo.tsx (MARK2, the one place they live)."""
    import json
    src = (ROOT / "src" / "logo.tsx").read_text()
    block = src[src.index("MARK2-START"):src.index("MARK2-END")]
    return json.loads(block[block.index("{"):block.rindex("}") + 1])


D = mark2()["icon_bg"]                  # the page behind the mark in every icon: the emblem's own near-black


def mark_svg(full: bool) -> str:
    """The mark's inner drawing in a 100 x 100 box (the same as AnantaMark in src/logo.tsx)."""
    m = mark2()
    c = m["full" if full else "small"]
    fac = "".join(f'<path d="{m["facets"][k]}" fill="{c[k]}"/>' for k in ("lo", "li", "ri", "ro", "bt", "bb"))
    eng = ""
    if full:
        blades = "".join(f'<path d="{d}"/>' for d in m["blades"])
        eng = (f'<clipPath id="h"><path clip-rule="evenodd" d="{m["hull"]}"/></clipPath><g clip-path="url(#h)"><g transform="{m["engraving_transform"]}" '
               f'fill="{m["engraving"]["fill"]}" stroke="{m["engraving"]["stroke"]}" stroke-width="0.45" stroke-linejoin="round">{blades}</g></g>')
    return (f'<defs><radialGradient id="d" cx="50" cy="42" r="52" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{m["disc"][0]}"/><stop offset="1" stop-color="{m["disc"][1]}"/></radialGradient>'
            f'<linearGradient id="s" gradientUnits="userSpaceOnUse" x1="20" y1="4" x2="80" y2="96"><stop offset="0" stop-color="{m["steel"][0]}"/><stop offset="0.45" stop-color="{m["steel"][1]}"/><stop offset="1" stop-color="{m["steel"][2]}"/></linearGradient>'
            f'<linearGradient id="b" gradientUnits="userSpaceOnUse" x1="20" y1="8" x2="80" y2="92"><stop offset="0" stop-color="{m["bronze"][0]}"/><stop offset="0.5" stop-color="{m["bronze"][1]}"/><stop offset="1" stop-color="{m["bronze"][2]}"/></linearGradient></defs>'
            f'<circle cx="50" cy="50" r="48" fill="url(#d)"/><circle cx="50" cy="50" r="46.4" fill="none" stroke="url(#s)" stroke-width="{3 if full else 3.6}"/>'
            f'<circle cx="50" cy="50" r="43.2" fill="none" stroke="url(#b)" stroke-width="{1.1 if full else 1.6}"/>{eng}'
            f'<g transform="{m["a_transform"]}">{fac}<path d="M50 12 L16 86" stroke="{c["edge"]}" stroke-width="0.875" stroke-linecap="round" fill="none" opacity="0.85"/>'
            f'<path d="M50 27.2 L76.8 86" stroke="{c["edge"]}" stroke-width="0.5" fill="none" opacity="0.35"/></g>')


def svg(pad: float, full: bool = False) -> str:
    """The mark on its own near-black square, shrunk by `pad` around the centre (maskable icons need a safe margin). Icon A: the small mark."""
    k = (1 - pad) * (1 if full else mark2()["icon_scale"] if pad == 0.1 else 1)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1024" height="1024"><rect width="100" height="100" fill="{D}"/>'
            f'<g transform="translate(50 50) scale({k:.4f}) translate(-50 -50)">{mark_svg(full)}</g></svg>')


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
        text = svg(pad, full=png.name == "splash-icon.png")       # 10 Nov: the splash shows the full mark, every icon the small one (Icon A)
        if platform.system() == "Darwin":
            _render_mac(text, n, png)
        else:
            _render_chromium(text, n, png, out)
        if png.name == "icon.png" and platform.system() == "Darwin":      # the App Store refuses an icon with an alpha channel
            jpg = png.with_suffix(".jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "best", str(png), "--out", str(jpg)], check=True, capture_output=True)
            subprocess.run(["sips", "-s", "format", "png", str(jpg), "--out", str(png)], check=True, capture_output=True)
            jpg.unlink()
        print("wrote", png)
