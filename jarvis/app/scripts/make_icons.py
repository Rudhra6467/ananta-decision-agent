"""Home Screen icons for the website (plan 2.5), drawn without any image library: a soft-yellow "A" on charcoal (Bat Mode colours).
Run: python3 jarvis/app/scripts/make_icons.py   (writes jarvis/app/public/icons/*.png)"""
import math
import struct
import zlib
from pathlib import Path

BG, FG = (0x14, 0x15, 0x18), (0xF2, 0xCF, 0x66)
OUT = Path(__file__).resolve().parents[1] / "public" / "icons"


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def icon(n: int, scale: float = 1.0) -> bytes:
    # the letter A in unit coordinates, shrunk by `scale` around the centre (maskable icons need a safe margin)
    segs = [(0.30, 0.76, 0.50, 0.24), (0.50, 0.24, 0.70, 0.76), (0.37, 0.58, 0.63, 0.58)]
    segs = [tuple(0.5 + (v - 0.5) * scale for v in s) for s in segs]
    w = 0.055 * scale
    rows = []
    for y in range(n):
        row = bytearray([0])
        for x in range(n):
            px, py = (x + 0.5) / n, (y + 0.5) / n
            d = min(seg_dist(px, py, *s) for s in segs) - w
            a = max(0.0, min(1.0, 0.5 - d * n))          # 1-pixel anti-aliased edge
            row += bytes(round(BG[i] + (FG[i] - BG[i]) * a) for i in range(3))
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, n, sc in (("icon-192.png", 192, 1.0), ("icon-512.png", 512, 1.0), ("maskable-512.png", 512, 0.72),
                        ("apple-touch-icon.png", 180, 0.9), ("favicon-32.png", 32, 1.15)):
        (OUT / name).write_bytes(icon(n, sc))
        print("wrote", OUT / name)
