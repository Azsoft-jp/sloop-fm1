#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Leo Kuroshita (@kurogedelic), Hügelton Instruments
"""Render the bitmap fonts to a C header (assets/fonts/):
  S  labels / units / status   Latin-1 32..255 at 1x
  L  large values / titles     32..95 (digits, signs, capitals), the same glyphs at 2x
Terminus Bold 8x16 (BDF, SIL OFL 1.1). TTF fonts also work through render()
(anti-aliased, tabular figures via the OpenType `tnum` feature).

Glyph format: rows top to bottom. The BDF's blank side bearings are omitted
after verifying them, so Terminus occupies 8x16 pixels per glyph and starts
at the pen. Uniform advance/width/stride live in the font header rather than
three repeated flash tables. On/off pixels are stored at 1 bit each; an
anti-aliased TTF stays at
2 pixels per byte (high nibble first), alpha 0..15, bits = 0 (gfx.c cv_text).
The sparse Japanese bitmaps also use 1 bit per pixel.
"""
import sys
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
# (name, file, px, scale, pixel, first, last): pixel fonts are rendered without
# anti-aliasing at their design size and enlarged by an integer factor
# SLOOP 2.6: Terminus Bold (the same 8 x 16 cell and advances as the regular one: no layout moves), drawn in
# capitals only (gfx.c glyph); the regular ter-u16n.bdf stays for the web editor's font (gen_webfont.py)
SIZES = [("S", "ter-u16b.bdf", 16, 1, True, 32, 255),   # Latin-1 (Hügelton needs the umlaut)
         ("L", "ter-u16b.bdf", 16, 2, True, 32, 95)]   # values / titles: digits, signs, capitals
PAD = 2


def ui_kana():
    """Only glyphs present in the firmware display resources enter the image."""
    src = (FONTS.parent.parent / "firmware/src/ui_strings.def").read_text()
    ja = re.findall(r'UI_STRING\([^,]+,\s*"[^"]*",\s*"([^"]*)"\)', src)
    return sorted({c for s in ja for c in s if ord(c) > 255})


def upscale(px_, w, h, scale):
    """integer nearest-neighbour enlargement of a w x h glyph"""
    if scale == 1:
        return px_
    big = []
    for y in range(h):
        row = []
        for x in range(w):
            row += [px_[y * w + x]] * scale
        big += row * scale
    return big


def render_bdf(path, scale, first, last):
    """BDF bitmap font (Terminus 8x16): exact pixels, cell = the font bounding box."""
    lines = path.read_text(errors="replace").splitlines()
    fbb = next(l for l in lines if l.startswith("FONTBOUNDINGBOX")).split()
    cw, ch, fx, fy = int(fbb[1]), int(fbb[2]), int(fbb[3]), int(fbb[4])
    base = ch + fy                                     # rows above the baseline
    glyphs, i = {}, 0
    while i < len(lines):
        if lines[i].startswith("ENCODING"):
            code = int(lines[i].split()[1])
            j = i
            while not lines[j].startswith("BBX"):
                j += 1
            bw, bh, bx, by = map(int, lines[j].split()[1:5])
            dw = cw
            k = i
            while not lines[k].startswith("BITMAP"):
                if lines[k].startswith("DWIDTH"):
                    dw = int(lines[k].split()[1])
                k += 1
            rows = [int(r, 16) for r in lines[k + 1:k + 1 + bh]]
            nbits = ((bw + 7) // 8) * 8
            cell = [0] * (cw * ch)
            top = base - (by + bh)
            for r, bits in enumerate(rows):
                for c in range(bw):
                    if bits >> (nbits - 1 - c) & 1:
                        x, y = bx + c, top + r
                        if 0 <= x < cw and 0 <= y < ch:
                            cell[y * cw + x] = 15
            glyphs[code] = (dw, cell)
            i = k + bh
        i += 1
    if 0xDC not in glyphs and ord("U") in glyphs:      # Ü for "HÜGELTON": U with dots on its top row
        dw, cell = glyphs[ord("U")]
        cell = cell[:]
        lit = [x for y in range(ch) for x in range(cw) if cell[y * cw + x]]
        if lit:
            top = min(y for y in range(ch) for x in range(cw) if cell[y * cw + x])
            for x in range(cw):
                cell[top * cw + x] = 15 if x in (min(lit), max(lit)) else 0
            for x in range(cw):
                cell[(top + 1) * cw + x] = 0
            glyphs[0xDC] = (dw, cell)
    missing = [chr(c) for c in range(first, min(last, 126) + 1) if c not in glyphs]
    if missing:
        print(f"font {path.name}: no glyph for {''.join(missing)!r} (drawn as '?')")
    out = []
    for c in range(first, last + 1):
        dw, cell = glyphs.get(c, glyphs[ord("?")])
        bw = cw + 2 * PAD                              # keep the PAD convention of the TTF path
        px_ = []
        for y in range(ch):
            px_ += [0] * PAD + cell[y * cw:(y + 1) * cw] + [0] * PAD
        out.append((dw * scale, bw * scale, upscale(px_, bw, ch, scale)))
    return ch * scale, out


def render(ttf, px, scale, pixel, first, last):
    if ttf.endswith(".bdf"):
        return render_bdf(FONTS / ttf, scale, first, last)
    font = ImageFont.truetype(str(FONTS / ttf), px)
    feats = None if pixel else ["tnum"]
    asc, desc = font.getmetrics()
    top = max(0, font.getbbox("A8|(", features=feats)[1] - 1)
    h = asc + desc - top
    glyphs = []
    for c in range(first, last + 1):
        ch = chr(c)
        adv = int(round(font.getlength(ch, features=feats)))
        bw = adv + 2 * PAD
        img = Image.new("L", (bw, asc + desc), 0)
        ImageDraw.Draw(img).text((PAD, 0), ch, font=font, fill=255, features=feats)
        img = img.crop((0, top, bw, top + h))
        px_ = [(15 if v >= 128 else 0) if pixel else min(15, (v + 8) // 17) for v in img.tobytes()]
        glyphs.append((adv * scale, bw * scale, upscale(px_, bw, h, scale)))
    return h * scale, glyphs


def main(out):
    lines = [f"/* generated by tools/gen_font.py from {SIZES[0][1]} */",
             "#pragma once", "#include <stdint.h>", f"#define FONT_PAD {PAD}  /* source BDF guard band; omitted in stored glyphs */", ""]
    base = None                                        # (name, first, h, glyphs, one, off ref, stride)
    for name, ttf, px, scale, pixel, first, last in SIZES:
        h, glyphs = render(ttf, px, scale, pixel, first, last)
        cropped = pixel and ttf.endswith(".bdf")
        if cropped:
            pad = PAD * scale
            trimmed = []
            for adv, bw, g in glyphs:
                assert bw > 2 * pad
                inner = bw - 2 * pad
                for y in range(h):
                    assert not any(g[y * bw:y * bw + pad] + g[y * bw + pad + inner:(y + 1) * bw]), \
                        "BDF side bearing contains ink"
                trimmed.append((adv, inner, [v for y in range(h)
                                             for v in g[y * bw + pad:y * bw + pad + inner]]))
            glyphs = trimmed
        draw_pad = 0 if cropped else PAD * scale
        if scale > 1 and pixel and base is not None:
            # SLOOP 2.4: a pixel font at 2x is the 1x font's own bitmaps, enlarged while drawing (gfx.c
            # cv_text): no second copy in flash (24 KB). Same glyphs, same pixels: checked here.
            bname, bfirst, bh, bglyphs, bone, boff, bstride = base
            assert scale == 2 and first == bfirst and h == bh * 2, "L must be S at 2x, same first glyph"
            for (adv, bw, g), (badv, bbw, bg) in zip(glyphs, bglyphs):
                assert adv == badv * 2 and bw == bbw * 2 and g == upscale(bg, bbw, bh, 2)
            fixed = len({a for a, _, _ in glyphs}) == len({b for _, b, _ in glyphs}) == 1
            if not fixed:
                lines.append(f"static const uint8_t FONT_{name}_ADV[{len(glyphs)}] = {{" +
                             ", ".join(str(a) for a, _, _ in glyphs) + "};")
                lines.append(f"static const uint8_t FONT_{name}_BW[{len(glyphs)}] = {{" +
                             ", ".join(str(b) for _, b, _ in glyphs) + "};")
            adv_ref, bw_ref = ("0", "0") if fixed else (f"FONT_{name}_ADV", f"FONT_{name}_BW")
            fixed_adv, fixed_bw = (glyphs[0][0], glyphs[0][1]) if fixed else (0, 0)
            lines.append(f"static const felucca_font_t FONT_{name} = {{ {h}, {draw_pad}, {first}, {last}, 1, "
                         f"{adv_ref}, {bw_ref}, {boff}, FONT_{bname}_DATA, {1 if bone else 0}, "
                         f"{fixed_adv}, {fixed_bw}, {bstride} }};")
            lines.append("")
            print(f"font {name}: {ttf} {px}px h {h}, digit adv {glyphs[ord('0') - first][0]}, "
                  f"the {bname} bitmaps at {scale}x (0 B)")
            continue
        data, offs = [], []
        one = all(v in (0, 15) for _, _, g in glyphs for v in g)   # on / off only: 1 bit a pixel
        for adv, bw, g in glyphs:
            offs.append(len(data))
            if one:
                acc = 0
                for i, v in enumerate(g + [0] * (-len(g) % 8)):
                    acc = (acc << 1) | (v != 0)
                    if i % 8 == 7:
                        data.append(acc)
                        acc = 0
                unp = [15 if data[offs[-1] + i // 8] >> (7 - i % 8) & 1 else 0 for i in range(len(g))]
                assert unp == g, "1-bit packing must give the glyph back"
                continue
            for y in range(h):
                row = g[y * bw:(y + 1) * bw] + [0]
                for x in range(0, bw, 2):
                    data.append((row[x] << 4) | row[x + 1])
        assert len(data) < 65536
        lines.append(f"static const uint8_t FONT_{name}_DATA[{len(data)}] = {{")
        for i in range(0, len(data), 24):
            lines.append("    " + ", ".join(f"0x{b:02x}" for b in data[i:i + 24]) + ",")
        lines.append("};")
        stride = len(data) // len(glyphs)
        fixed = (one and len(data) % len(glyphs) == 0 and stride < 256 and
                 all(o == i * stride for i, o in enumerate(offs)) and
                 len({a for a, _, _ in glyphs}) == len({b for _, b, _ in glyphs}) == 1)
        if not fixed:
            lines.append(f"static const uint16_t FONT_{name}_OFF[{len(offs)}] = {{" + ", ".join(map(str, offs)) + "};")
            lines.append(f"static const uint8_t FONT_{name}_ADV[{len(glyphs)}] = {{" +
                         ", ".join(str(a) for a, _, _ in glyphs) + "};")
            lines.append(f"static const uint8_t FONT_{name}_BW[{len(glyphs)}] = {{" +
                         ", ".join(str(b) for _, b, _ in glyphs) + "};")
        off_ref, adv_ref, bw_ref = ("0", "0", "0") if fixed else (
            f"FONT_{name}_OFF", f"FONT_{name}_ADV", f"FONT_{name}_BW")
        fixed_adv, fixed_bw, fixed_stride = (glyphs[0][0], glyphs[0][1], stride) if fixed else (0, 0, 0)
        lines.append(f"static const felucca_font_t FONT_{name} = {{ {h}, {draw_pad}, {first}, {last}, 0, "
                     f"{adv_ref}, {bw_ref}, {off_ref}, FONT_{name}_DATA, {1 if one else 0}, "
                     f"{fixed_adv}, {fixed_bw}, {fixed_stride} }};")
        lines.append("")
        if scale == 1:
            base = (name, first, h, glyphs, one, off_ref, fixed_stride)
        print(f"font {name}: {ttf} {px}px h {h}, digit adv {glyphs[ord('0') - first][0]}, {len(data)} B")

    kana = ui_kana()
    jp_font = ImageFont.truetype(str(FONTS / "NotoSansJP-ui.ttf"), 16)
    # Store only the Japanese UI glyphs. The 2.6 app slot leaves less room than
    # 2.4, so these match the 1-bit Terminus renderer (16x16 = 32 B each).
    # FONT_L reuses the same bitmap at 2x.
    jp_data = []
    for ch in kana:
        # Render with a guard band so even anti-aliased edge pixels cannot be
        # silently cut by the 16px cell. -5 centers the font and keeps ヘ's
        # bottom stroke, which was cropped at -4.
        guarded = Image.new("L", (20, 48), 0)
        ImageDraw.Draw(guarded).text((PAD, 16 - 5), ch, font=jp_font, fill=255)
        assert guarded.crop((0, 0, 20, 16)).getbbox() is None, f"{ch}: clipped above cell"
        assert guarded.crop((0, 32, 20, 48)).getbbox() is None, f"{ch}: clipped below cell"
        small = guarded.crop((0, 16, 20, 32)).point(lambda v: 255 if v >= 80 else 0)
        bounds = small.getbbox()
        assert bounds is None or (bounds[0] >= PAD and bounds[2] <= 20 - PAD), f"{ch}: clipped at side"
        px = [v != 0 for v in small.crop((PAD, 0, 20 - PAD, 16)).tobytes()]
        for start in range(0, 16 * 16, 8):
            jp_data.append(sum(int(px[start + bit]) << (7 - bit) for bit in range(8)))
    assert len(jp_data) < 65536
    first_cp, last_cp = ord(kana[0]), ord(kana[-1])
    assert last_cp - first_cp < 256 and len(kana) < 256, "Japanese UI glyph map needs widening"
    glyph_index = {ord(ch): i + 1 for i, ch in enumerate(kana)}
    lines.append(f"#define FONT_J_FIRST 0x{first_cp:04x}u")
    lines.append(f"#define FONT_J_SPAN {last_cp - first_cp + 1}u")
    lines.append(f"static const uint8_t FONT_J_MAP[{last_cp - first_cp + 1}] = {{" +
                 ", ".join(str(glyph_index.get(cp, 0)) for cp in range(first_cp, last_cp + 1)) + "};")
    lines.append(f"static const uint8_t FONT_J_DATA[{len(jp_data)}] = {{")
    for i in range(0, len(jp_data), 24):
        lines.append("    " + ", ".join(f"0x{b:02x}" for b in jp_data[i:i + 24]) + ",")
    lines.append("};")
    lines.append(f"#define FONT_J_COUNT {len(kana)}")
    print(f"font J: {len(kana)} used glyphs, {len(jp_data)} B (shared at 1x/2x)")
    Path(out).write_text("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
