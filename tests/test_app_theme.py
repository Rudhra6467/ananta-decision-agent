"""Plan 2.4: light and Bat Mode palettes as tokens. Text must be readable in both (WCAG 4.5:1), and no screen may paint a
colour of its own outside the tokens (or Bat Mode would show white boxes)."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"
THEME = (APP / "src" / "theme.ts").read_text()


def palette(name: str) -> dict:
    body = THEME.split(f"const {name}")[1].split("};")[0]
    return dict(re.findall(r'(\w+): "(#[0-9A-Fa-f]{6})"', body))


def lum(h: str) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (foreground, background, minimum): body text 4.5:1; large or decorative marks 3:1
PAIRS = [("text", "bg", 4.5), ("text", "card", 4.5), ("text", "card2", 4.5), ("dim", "bg", 4.5), ("dim", "card", 4.5),
         ("dim", "card2", 4.5), ("accent", "card", 4.5), ("accent", "bg", 4.5), ("good", "card", 4.5), ("bad", "card", 4.5),
         ("warn", "card", 4.5), ("goodDeep", "goodSoft", 4.5), ("badDeep", "badSoft", 4.5), ("warnDeep", "warnSoft", 4.5),
         ("accent", "accentSoft", 4.5), ("onInk", "ink", 4.5), ("onInk", "accent", 4.5), ("onInk", "inkBtn", 4.5),
         ("onInk", "good", 3.0), ("onInk", "bad", 3.0), ("inkDim", "ink", 4.5), ("faint", "card", 2.5)]


def test_both_palettes_have_every_token():
    light, bat = palette("LIGHT"), palette("BAT: Palette")
    assert set(light) == set(bat), set(light) ^ set(bat)


def test_text_is_readable_in_both_themes():
    bad = []
    for name in ("LIGHT", "BAT: Palette"):
        p = palette(name)
        for fg, bg, need in PAIRS:
            r = ratio(p[fg], p[bg])
            if r < need:
                bad.append(f"{name.split(':')[0]}: {fg} on {bg} = {r:.2f} (needs {need})")
    assert not bad, "\n".join(bad)


def test_no_screen_paints_its_own_colours():
    allowed = {"#000"}                                            # shadows
    bad = []
    for p in list((APP / "app").rglob("*.tsx")) + list((APP / "src").rglob("*.ts*")):
        if p.name in ("theme.ts",):
            continue
        for n, line in enumerate(p.read_text().split("\n"), 1):
            for h in re.findall(r'"(#[0-9A-Fa-f]{3,8})"', line):
                if h in allowed or (p.name == "charts.tsx" and 'fill="#FFFFFF"' in line):   # labels on the fixed mid-tone level tags
                    continue
                bad.append(f"{p.relative_to(APP)}:{n} {h}")
    assert not bad, "colours outside the theme tokens:\n" + "\n".join(bad)
