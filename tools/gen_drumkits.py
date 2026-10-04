#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Synthesised drum kits for firmware/src/drum_synth.c -> felucca_drumkits.h

Each kit has 14 sounds (lanes): KICK SNARE CLAP CHH OHH TOMLO TOMHI CRASH RIDE SHAKER
CONGA RIM COWBELL CLAVE. A sound is written in musical units (Hz, ms) and converted to
the table indices the firmware uses (MIDI note, DECAY_K and CUTOFF_HZ indices).

  tools/gen_drumkits.py OUT.h
"""
import copy
import math
import sys
from pathlib import Path

LANES = ["KICK", "SNARE", "CLAP", "CHH", "OHH", "TOMLO", "TOMHI", "CRASH", "RIDE", "SHAKER",
         "CONGA", "RIM", "COWBELL", "CLAVE"]
WAVE = {None: 0, "sine": 1, "tri": 2, "square": 3, "fm": 4, "bell": 5}
SRC = {None: 0, "white": 1, "metal": 2, "cym": 3, "chip": 4, "clap": 0x11}


def note(hz):
    return max(0, min(127, int(round(69 + 12 * math.log2(hz / 440.0)))))


def dec(ms):                       # DECAY_K: 5 ms .. 4 s, index 0..127
    ms = max(5.0, min(4000.0, ms))
    return int(round(127 * math.log(ms / 5.0) / math.log(800)))


def cut(hz):                       # CUTOFF_HZ: 30 Hz .. 16 kHz
    hz = max(30.0, min(16000.0, hz))
    return int(round(127 * math.log(hz / 30.0) / math.log(16000 / 30)))


def S(wave=None, hz=100, bend=0, bt=20, decay=100, tlev=110, src=None, nlev=0, ndec=50,
      lpf=None, hpf=None, drive=0, chip=None):
    return dict(wave=wave, hz=hz, bend=bend, bt=bt, decay=decay, tlev=tlev, src=src, nlev=nlev,
                ndec=ndec, lpf=lpf, hpf=hpf, drive=drive, chip=chip)


def enc(s):
    lpf = 127 if s["lpf"] is None else cut(s["lpf"])
    if s["src"] == "chip":
        lpf = s["chip"] if s["chip"] is not None else 100       # CHIP: clock note
    return [WAVE[s["wave"]], SRC[s["src"]], note(s["hz"]), int(s["bend"]), dec(s["bt"]), dec(s["decay"]),
            int(s["tlev"]) if s["wave"] else 0, int(s["nlev"]) if s["src"] else 0, dec(s["ndec"]), lpf,
            0 if s["hpf"] is None else cut(s["hpf"]), int(s["drive"])]


def kit(base, **mods):
    k = copy.deepcopy(base)
    for lane, ch in mods.items():
        if isinstance(ch, dict) and "wave" in ch:
            k[lane] = ch
        else:
            k[lane].update(ch)
    return k


# ---- base kits ---------------------------------------------------------------------------
K808 = dict(
    KICK=S("sine", 49, 26, 45, 750, 122, "white", 22, 4, 3000),
    SNARE=S("tri", 180, 4, 20, 110, 80, "white", 92, 170, 9000, 1500),
    CLAP=S(None, src="clap", nlev=122, ndec=210, lpf=2400, hpf=800),
    CHH=S(None, 205, src="metal", nlev=118, ndec=45, hpf=7000),
    OHH=S(None, 205, src="metal", nlev=112, ndec=380, hpf=6500),
    TOMLO=S("sine", 98, 5, 60, 380, 115, "white", 14, 25, 2000),
    TOMHI=S("sine", 147, 5, 60, 320, 112, "white", 14, 25, 2500),
    CRASH=S(None, 205, src="cym", nlev=104, ndec=1700, hpf=4500),
    RIDE=S(None, 260, src="metal", nlev=112, ndec=1100, lpf=12000, hpf=3500),
    SHAKER=S(None, src="white", nlev=84, ndec=55, hpf=6000),
    CONGA=S("sine", 310, 3, 25, 200, 112),
    RIM=S("tri", 1700, 0, 5, 22, 92, "white", 50, 5, None, 2500),
    COWBELL=S("bell", 540, 0, 5, 280, 104, lpf=4000, hpf=500),
    CLAVE=S("sine", 2500, 0, 5, 45, 104),
)
K909 = kit(K808,
    KICK=S("sine", 55, 36, 28, 320, 122, "white", 70, 7, 6000, None, 40),
    SNARE=S("sine", 190, 7, 15, 110, 88, "white", 115, 230, 12000, 1000, 20),
    CLAP=dict(nlev=124, ndec=260, lpf=2600, hpf=900),
    CHH=S(None, 230, src="cym", nlev=112, ndec=55, hpf=8000),
    OHH=S(None, 230, src="cym", nlev=108, ndec=420, hpf=7500),
    TOMLO=S("sine", 110, 10, 40, 300, 115, "white", 26, 30, 3000),
    TOMHI=S("sine", 165, 10, 40, 260, 112, "white", 26, 30, 3500),
    CRASH=S(None, 250, src="cym", nlev=106, ndec=1900, hpf=5000),
    RIDE=S(None, 300, src="cym", nlev=110, ndec=1400, lpf=13000, hpf=4000),
    RIM=S("tri", 1900, 2, 4, 18, 96, "white", 70, 6, None, 3000),
)
K606 = kit(K808,
    KICK=S("sine", 60, 18, 30, 190, 122, "white", 30, 4, 4000),
    SNARE=S("tri", 220, 3, 10, 70, 70, "white", 102, 120, 10000, 2500),
    CHH=S(None, 260, src="metal", nlev=114, ndec=30, hpf=9000),
    OHH=S(None, 260, src="metal", nlev=108, ndec=200, hpf=8500),
    TOMLO=S("sine", 150, 4, 30, 180, 112),
    TOMHI=S("sine", 220, 4, 30, 160, 110),
    CRASH=S(None, 300, src="metal", nlev=100, ndec=900, hpf=6000),
)
KCR78 = kit(K808,
    KICK=S("sine", 65, 8, 20, 160, 118, lpf=2000),
    SNARE=S("sine", 240, 2, 10, 60, 70, "white", 72, 90, 6000, 2000),
    CLAP=S(None, src="white", nlev=90, ndec=140, lpf=8000, hpf=4000),        # tambourine-ish
    CHH=S(None, 280, src="metal", nlev=106, ndec=25, hpf=9000),
    OHH=S(None, 280, src="metal", nlev=100, ndec=160, hpf=8500),
    TOMLO=S("sine", 180, 2, 20, 160, 110),
    TOMHI=S("sine", 260, 2, 20, 140, 108),
    SHAKER=S(None, src="white", nlev=90, ndec=30, hpf=7000),
    CONGA=S("sine", 400, 2, 15, 120, 110),
    RIM=S("sine", 1600, 0, 5, 30, 100),
    COWBELL=S("bell", 800, 0, 5, 160, 100, lpf=5000, hpf=800),
)
KLINN = kit(K808,
    KICK=S("sine", 58, 20, 22, 240, 122, "white", 60, 6, 5000, None, 20),
    SNARE=S("tri", 200, 6, 15, 120, 86, "white", 112, 260, 10000, 900, 30),
    CLAP=dict(nlev=124, ndec=300, lpf=2800),
    CHH=S(None, 240, src="cym", nlev=104, ndec=40, hpf=8000),
    OHH=S(None, 240, src="cym", nlev=100, ndec=300, hpf=7500),
    TOMLO=S("sine", 90, 12, 80, 500, 118, "white", 20, 40, 2500),
    TOMHI=S("sine", 140, 12, 80, 420, 115, "white", 20, 40, 3000),
)
KCHIP = dict(
    KICK=S("square", 70, 30, 40, 120, 104),
    SNARE=S("square", 220, 12, 20, 40, 60, "chip", 106, 130, chip=100),
    CLAP=S(None, src="chip", nlev=108, ndec=110, chip=108),
    CHH=S(None, src="chip", nlev=96, ndec=30, chip=124),
    OHH=S(None, src="chip", nlev=92, ndec=220, chip=122),
    TOMLO=S("square", 110, 14, 80, 160, 100),
    TOMHI=S("square", 165, 14, 80, 140, 100),
    CRASH=S(None, src="chip", nlev=96, ndec=900, chip=112),
    RIDE=S("square", 1500, 0, 5, 300, 50, "chip", 60, 200, chip=126),
    SHAKER=S(None, src="chip", nlev=84, ndec=45, chip=127),
    CONGA=S("tri", 330, 5, 30, 120, 110),
    RIM=S("square", 1200, 0, 5, 25, 90),
    COWBELL=S("square", 700, 0, 5, 150, 90),
    CLAVE=S("square", 2000, 0, 5, 35, 90),
)
KFM = dict(
    KICK=S("fm", 55, 40, 30, 220, 120, drive=30),
    SNARE=S("fm", 200, 18, 20, 90, 90, "white", 90, 140, 9000, 1500),
    CLAP=S(None, src="clap", nlev=118, ndec=180, lpf=3000, hpf=1000),
    CHH=S("fm", 4200, 0, 5, 30, 70, "white", 70, 30, None, 8000),
    OHH=S("fm", 4200, 0, 5, 220, 64, "white", 64, 220, None, 7000),
    TOMLO=S("fm", 120, 30, 120, 260, 110),
    TOMHI=S("fm", 200, 30, 120, 220, 108),
    CRASH=S("fm", 900, 0, 5, 1200, 50, "cym", 90, 1300, None, 4000),
    RIDE=S("fm", 1300, 0, 5, 900, 60, "metal", 50, 700, 9000, 5000),
    SHAKER=S(None, src="white", nlev=80, ndec=50, hpf=6000),
    CONGA=S("fm", 330, 12, 40, 160, 108),
    RIM=S("fm", 1500, 4, 5, 25, 96),
    COWBELL=S("fm", 600, 0, 5, 200, 96),
    CLAVE=S("fm", 2300, 0, 5, 40, 100),
)

KITS = [
    ("808", "HIP HOP", 0, K808),
    ("909", "HOUSE", 0, K909),
    ("606", "ACID", 0, K606),
    ("VINTAGE", "RHYTHM BOX", 0, KCR78),
    ("80S", "80S POP", 0, KLINN),
    ("TRAP", "TRAP", 0, kit(K808,
        KICK=dict(hz=46, bend=30, bt=60, decay=1300, drive=34),
        SNARE=S("tri", 200, 5, 10, 90, 70, "white", 110, 150, 12000, 2200, 20),
        CLAP=dict(nlev=126, ndec=170, lpf=3000, hpf=1100),
        CHH=dict(ndec=24, hpf=9000), OHH=dict(ndec=260))),
    ("DRILL", "UK DRILL", 0, kit(K808,
        KICK=dict(hz=44, bend=12, bt=200, decay=1600, drive=40),
        SNARE=S("tri", 270, 8, 8, 60, 84, "white", 104, 110, 12000, 2500, 30),
        CHH=dict(ndec=28, hpf=8500), RIM=dict(hz=2000, decay=30, tlev=104))),
    ("BOOMBAP", "HIP HOP", 0x13, kit(K909,
        KICK=dict(decay=260, drive=70, nlev=80),
        SNARE=S("tri", 175, 5, 15, 130, 92, "white", 110, 200, 5000, 700, 50),
        CHH=dict(ndec=40, hpf=6000), OHH=dict(ndec=260, hpf=5500))),
    ("LO-FI", "LO-FI", 0x34, kit(K808,
        KICK=dict(decay=420, lpf=1500, tlev=114),
        SNARE=dict(lpf=4500, hpf=900, ndec=150),
        CLAP=dict(lpf=1800, hpf=600),
        CHH=dict(hpf=4000, nlev=90), OHH=dict(hpf=3800, nlev=86),
        CRASH=dict(hpf=3000, nlev=80), RIDE=dict(lpf=6000, hpf=3000, nlev=70))),
    ("HOUSE", "HOUSE", 0, kit(K909,
        KICK=dict(decay=360, drive=30), OHH=dict(ndec=300, nlev=112),
        CLAP=dict(nlev=126, ndec=320), SHAKER=dict(ndec=70, nlev=90))),
    ("TECHNO", "TECHNO", 0, kit(K909,
        KICK=dict(hz=50, bend=30, bt=24, decay=420, drive=95),
        CHH=dict(ndec=35, hpf=9500), OHH=dict(ndec=280, hpf=9000),
        RIDE=dict(nlev=96, ndec=900), RIM=dict(drive=40),
        CLAP=dict(ndec=200, lpf=2200))),
    ("MINIMAL", "MINIMAL", 0, kit(K808,
        KICK=S("sine", 60, 20, 10, 150, 122, "white", 50, 3, 7000),
        SNARE=S("tri", 1100, 0, 5, 18, 90, "white", 60, 25, None, 3000),
        CLAP=dict(ndec=90), CHH=dict(ndec=18, hpf=10000), OHH=dict(ndec=120),
        CONGA=dict(decay=90, hz=420), RIM=dict(decay=12))),
    ("ELECTRO", "ELECTRO", 0, kit(K808,
        KICK=dict(bend=40, bt=70, decay=500),
        SNARE=dict(ndec=120, hpf=2000),
        TOMLO=S("fm", 130, 30, 120, 240, 110), TOMHI=S("fm", 220, 30, 120, 200, 108),
        CHH=K606["CHH"], OHH=K606["OHH"])),
    ("JUNGLE", "DRUM & BASS", 0, kit(K909,
        KICK=dict(decay=200, drive=50),
        SNARE=S("tri", 260, 9, 10, 90, 92, "white", 112, 160, 12000, 1500, 40),
        CHH=dict(ndec=30), RIDE=dict(nlev=92))),
    ("DUBSTEP", "BASS MUSIC", 0, kit(K909,
        KICK=dict(hz=48, decay=420, drive=60),
        SNARE=S("tri", 170, 8, 20, 160, 96, "white", 120, 420, 9000, 600, 60),
        CLAP=dict(ndec=380), OHH=dict(ndec=300))),
    ("DEMBOW", "REGGAETON", 0, kit(K808,
        KICK=dict(decay=520, drive=20),
        SNARE=S("tri", 230, 5, 10, 80, 84, "white", 100, 130, 11000, 1800, 20),
        CLAP=dict(ndec=160), RIM=dict(tlev=104), SHAKER=dict(ndec=70, nlev=96))),
    ("AFRO", "AFROBEAT", 0, kit(K808,
        KICK=S("sine", 60, 10, 30, 260, 118, lpf=2000),
        SNARE=S("tri", 330, 3, 10, 60, 92, "white", 70, 60, 9000, 2500),
        CONGA=dict(decay=260, bend=2), TOMLO=S("sine", 160, 2, 20, 260, 112),
        TOMHI=S("sine", 230, 2, 20, 220, 110), SHAKER=dict(ndec=80, nlev=100),
        COWBELL=dict(hz=900, decay=180))),
    ("LATIN", "LATIN", 0, kit(KCR78,
        KICK=S("sine", 62, 6, 20, 220, 114, lpf=1800),
        TOMLO=S("sine", 200, 3, 15, 200, 112, "white", 20, 15, 4000),     # timbales
        TOMHI=S("sine", 300, 3, 15, 180, 112, "white", 20, 15, 4500),
        CONGA=dict(hz=330, decay=240), COWBELL=dict(hz=650, decay=240),
        CLAVE=dict(hz=2400, decay=55))),
    ("DISCO", "DISCO", 0, kit(K909,
        KICK=dict(decay=260, drive=20),
        OHH=dict(ndec=520, nlev=114),
        TOMLO=S("sine", 120, 24, 300, 600, 116), TOMHI=S("sine", 180, 24, 300, 520, 114))),
    ("SYNTHWV", "SYNTHWAVE", 0, kit(KLINN,
        SNARE=dict(ndec=340, drive=50, nlev=118),
        TOMLO=S("sine", 85, 18, 160, 600, 118, "white", 24, 50, 2500),
        TOMHI=S("sine", 130, 18, 160, 520, 116, "white", 24, 50, 3000))),
    ("CHIP", "CHIPTUNE", 0x04, KCHIP),
    ("8BIT", "HANDHELD", 0x26, kit(KCHIP, KICK=dict(decay=160), SNARE=dict(ndec=160))),
    ("ARCADE", "VIDEO GAME", 0x02, KFM),
    ("GLITCH", "GLITCH", 0x25, kit(KFM,
        KICK=dict(decay=120, bt=12), SNARE=S(None, src="chip", nlev=112, ndec=70, chip=96),
        CHH=S(None, src="chip", nlev=100, ndec=15, chip=127), OHH=S(None, src="chip", nlev=96, ndec=90, chip=125),
        CLAP=dict(ndec=80), TOMLO=dict(bt=40, decay=120), TOMHI=dict(bt=40, decay=100))),
    ("INDUSTR", "INDUSTRIAL", 0x02, kit(K909,
        KICK=dict(drive=127, decay=380), SNARE=dict(drive=110, ndec=260),
        CLAP=dict(nlev=127, ndec=280), CHH=dict(src="metal", ndec=60), OHH=dict(src="metal", ndec=500),
        TOMLO=S("fm", 90, 24, 200, 400, 118, drive=100), TOMHI=S("fm", 140, 24, 200, 340, 116, drive=100),
        CRASH=dict(src="metal", ndec=2200, nlev=118))),
    ("TRIBAL", "TRIBAL", 0, kit(K808,
        KICK=S("sine", 52, 14, 60, 600, 122, "white", 30, 10, 1500),
        SNARE=S("sine", 160, 6, 30, 260, 110, "white", 40, 60, 3000),
        TOMLO=S("sine", 75, 8, 90, 600, 120, "white", 26, 30, 1500),
        TOMHI=S("sine", 115, 8, 90, 520, 118, "white", 26, 30, 2000),
        CHH=S(None, src="white", nlev=86, ndec=40, hpf=5000),
        OHH=S(None, src="white", nlev=90, ndec=160, hpf=4000),
        CONGA=dict(decay=320))),
    ("HYPER", "HYPERPOP", 0, kit(K909,
        KICK=dict(drive=110, decay=380, bend=44),
        SNARE=S("tri", 300, 10, 10, 90, 100, "white", 120, 180, 14000, 2000, 80),
        CLAP=dict(nlev=127, ndec=240, hpf=1300),
        CHH=dict(hpf=10000, ndec=30), OHH=dict(hpf=9500))),
    ("AMBIENT", "AMBIENT", 0, kit(K808,
        KICK=dict(tlev=100, decay=900, nlev=0, lpf=800),
        SNARE=dict(lpf=3500, ndec=420, nlev=70, tlev=60),
        CLAP=dict(lpf=1500, ndec=500, nlev=90),
        CHH=dict(nlev=70, ndec=70, hpf=6000), OHH=dict(nlev=70, ndec=900),
        CRASH=dict(nlev=80, ndec=3500), RIDE=dict(nlev=60, ndec=2500, lpf=7000))),
    ("JAZZ", "JAZZ", 0, kit(K808,
        KICK=S("sine", 62, 8, 20, 220, 96, "white", 30, 8, 1200),
        SNARE=S("tri", 210, 2, 10, 60, 40, "white", 90, 320, 5000, 1500),      # brushes
        CHH=S(None, 300, src="cym", nlev=80, ndec=60, lpf=9000, hpf=5000),
        OHH=S(None, 300, src="cym", nlev=80, ndec=500, lpf=9000, hpf=4500),
        RIDE=S(None, 320, src="cym", nlev=86, ndec=2400, lpf=8000, hpf=3500),
        TOMLO=S("sine", 110, 3, 30, 400, 104, "white", 16, 40, 2000),
        TOMHI=S("sine", 160, 3, 30, 340, 102, "white", 16, 40, 2500))),
]


def main(path):
    L = ["/* generated by tools/gen_drumkits.py */", "#pragma once",
         f"#define DS_NKITS {len(KITS)}u", "static const dkit_t DS_KITS[DS_NKITS] = {"]
    for name, style, crush, k in KITS:
        assert len(name) <= 8 and len(style) <= 12, name
        L.append(f'    {{"{name}", "{style}", 0x{crush:02X}, {{')
        for lane in LANES:
            v = enc(k[lane])
            assert all(0 <= x <= 127 for x in v[2:]) and len(v) == 12, (name, lane, v)
            L.append("        {" + ", ".join(str(x) for x in v) + f"}},   /* {lane} */")
        L.append("    }},")
    L.append("};")
    L.append("#define DS_KIT_NAME_LIST " + ", ".join(f'"{k[0]}"' for k in KITS))
    L.append("#define DS_KIT_STYLE_LIST " + ", ".join(f'"{k[1]}"' for k in KITS))
    Path(path).write_text("\n".join(L) + "\n")
    print(f"drum kits: {len(KITS)} synthesised -> {path}")


if __name__ == "__main__":
    main(sys.argv[1])
