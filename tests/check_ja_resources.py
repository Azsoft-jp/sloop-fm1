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
first = re.search(r'#define FONT_J_FIRST 0x([0-9a-f]+)u', generated)
match = re.search(r'FONT_J_MAP\[(\d+)\] = \{([^}]+)\}', generated)
assert first and match, "run tools.build.generate() first"
indices = [int(x) for x in re.findall(r'\d+', match[2])]
assert len(indices) == int(match[1])
glyphs = {int(first[1], 16) + i for i, index in enumerate(indices) if index}
assert sorted(index for index in indices if index) == list(range(1, len(glyphs) + 1))
assert glyphs == used, f"glyph mismatch: missing {used-glyphs}, unused {glyphs-used}"
data = re.search(r'FONT_J_DATA\[(\d+)\]', generated)
assert data and int(data[1]) == len(glyphs) * 32, "Japanese font must be packed 1 bpp, 16x16 per glyph"
hash_header = (root / "build/gen/felucca_ui_hash.h").read_text()
assert f"UI_EN_HASH[{len(entries)}]" in hash_header
assert f"UI_JA_OFF[{len(entries)}]" in hash_header
blob_match = re.search(r'UI_JA_BLOB\[\d+\] = \{([^}]+)\}', hash_header)
offset_match = re.search(r'UI_JA_OFF\[\d+\] = \{([^}]+)\}', hash_header)
assert blob_match and offset_match
blob = bytes(int(x, 16) for x in re.findall(r'0x[0-9a-f]+', blob_match[1]))
offsets = [int(x) for x in re.findall(r'\d+', offset_match[1])]
assert len(offsets) == len(entries)
for (_, _, ja), offset in zip(entries, offsets):
    encoded = ja.encode("utf-8") + b"\0"
    assert blob[offset:offset + len(encoded)] == encoded, f"bad JA offset for {ja}"
for file in (root / "firmware/src").glob("*.[ch]"):
    assert not re.search(r'[\u3040-\u30ff\u3400-\u9fff]', file.read_text()), f"direct Japanese UI in {file}"
print(f"resources: {len(entries)} EN/JA IDs, {len(glyphs)} sparse glyphs, all used, no direct Japanese in C")
print("glyphs:", "".join(chr(c) for c in sorted(glyphs)))
