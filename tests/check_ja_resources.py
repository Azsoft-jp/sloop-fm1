#!/usr/bin/env python3
"""Check that firmware display strings and generated sparse glyphs agree."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "firmware/src/ui_strings.def").read_text()
entries = re.findall(r'^UI_STRING\(([^,]+),\s*"([^"]*)",\s*"([^"]*)"\)', source, re.M)
assert entries, "no UI resources"
ids = [x[0] for x in entries]
assert len(ids) == len(set(ids)), "duplicate UI resource ID"
used = {ord(c) for _, _, ja in entries for c in ja if ord(c) > 255}
generated = (root / "build/gen/felucca_font.h").read_text()
match = re.search(r'FONT_J_CODE\[\d+\] = \{([^}]+)\}', generated)
assert match, "run tools.build.generate() first"
glyphs = {int(x, 16) for x in re.findall(r'0x[0-9a-f]+', match[1])}
assert glyphs == used, f"glyph mismatch: missing {used-glyphs}, unused {glyphs-used}"
for file in (root / "firmware/src").glob("*.[ch]"):
    assert not re.search(r'[\u3040-\u30ff\u3400-\u9fff]', file.read_text()), f"direct Japanese UI in {file}"
print(f"resources: {len(entries)} EN/JA IDs, {len(glyphs)} sparse glyphs, all used, no direct Japanese in C")
print("glyphs:", "".join(chr(c) for c in sorted(glyphs)))
