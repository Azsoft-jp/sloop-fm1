<p align="center"><img src="assets/logo/sloop-logo.png" alt="SLOOP" width="420"></p>

<p align="center"><b>A hip-hop beat machine firmware for the M-VAVE FM-1.</b><br>
Free and open source (GPL-3.0), based on <a href="https://github.com/hugelton/Felucca">Felucca</a>.</p>

---

SLOOP turns the FM-1 into a four-track beat machine you play live: three synths and a drum machine with 16 sounds on the white keys. No factory patterns, nothing to load: everything you hear, you play.

## Features

- **Hold a button, touch a key.** Every function button is a layer: hold it and the 16 white keys and the four knobs change job, and the screen shows how. Tap it and its pages open.
  - **FX**: 16 punch-in effects (loops, stutter, reverse, tape stop, filters, crush…)
  - **EDIT**: erase a sound or a note as the loop plays; shift, double or halve the pattern; undo / redo
  - **ARP**: note repeat (1/8 to 1/64), locked to the grid
  - **SEQ**: step entry, with a level and a ratchet per step
  - **SCL**: the key of the song, and one-key chords (triad, 7th, 9th, sus4, power)
  - **GLO**: mute, solo, tap tempo, track levels
- **Drums:** 16 sounds on the white keys, ghost and hard hits (hold OCT− / OCT+), ratchets x1–x4, 34 kits (5 sampled, 29 synthesised: 808, 909, boom bap, trap, drill, lo-fi, jungle…).
- **Sounds:** 54 presets for hip-hop and drum & bass on 9 engines — 808s that slide, Rhodes, organs, horn and string stabs, talkbox, granular pads, scratches.
- **Recording with no click:** a free take sets the loop length and the tempo from your playing; REC records at once while playing; notes land where you heard them (latency-compensated).
- **Groove:** MPC-style swing (50–75 %), a sample-accurate clock (no drift at any tempo), polymeters.
- **Master:** DUST (old sampler + vinyl), DUCK (the kick pumps the synths), a DJ filter.
- **Memory:** undo / redo, autosave of the working project, 4 projects, 32 user presets, a song mode of 4 sections.
- **Your own samples:** three user slots; the web editor chops a recording into 16 pieces (tap along while it plays) and uploads them.
- **Web editor:** every parameter, the drum track as a 16-lane grid, the mixer, a preset library, sample upload. Live sync with the device.

## Install

**From the browser:** open **[the SLOOP installer](https://isod89.github.io/sloop-fm1/)** in **Chrome or Edge**, connect the FM-1 by USB (a data cable, no hub), press **INSTALL** and wait for *Done*. Nothing to download or compile. The [web editor](https://isod89.github.io/sloop-fm1/webapp/editor/) works the same way.

Other ways: the `.fwsc` of each [release](../../releases) with `python tools/fm1_install.py sloop-2.0.fwsc` (needs `pip install mido python-rtmidi`), or build it yourself and run `INSTALL-SLOOP.bat` (Windows).

Going back: M-VAVE's own updater (M-UPGRADE) and the official FM-1 firmware. If an install is cut off, the FM-1 stays in update mode: press Install again and it finishes.

> Custom firmware is installed at your own risk. If an FM-1 no longer starts, recovery needs [FM-1-transporter](https://github.com/kurogedelic/FM-1-transporter).

## Documentation

- [SLOOP.md](SLOOP.md) — the manual
- [DEMARRAGE-RAPIDE-FR.md](DEMARRAGE-RAPIDE-FR.md) — guide de démarrage en français
- [BUILDING.md](BUILDING.md) — building and testing
- [web/EDITOR_PROTOCOL.md](web/EDITOR_PROTOCOL.md) — the editor's SysEx protocol

## Building

See [BUILDING.md](BUILDING.md). In short: the JieLi toolchain and three files of the AC79 SDK, then `./build.sh` (Linux / macOS) or `INSTALL-SLOOP.bat` (Windows with WSL). `tests/run_tests.sh` runs the host test suite (audio renders, sequencer timing, UI, storage, update loader, web pages).

## Credits

SLOOP is a fork of **[Felucca](https://github.com/hugelton/Felucca)** by Leo Kuroshita (@kurogedelic), Hügelton Instruments: the engines, the sequencer, the editor and the installer come from there. Font: Terminus (SIL OFL 1.1). Samples: Versilian Studios VSCO-2 CE and VCSL (CC0), Hügelton Sample Pack. PHASE engine after CrispyZebra; VOICE after klattsch. Icons: Fukiai.

## Licence

Code: GPL-3.0-only (see [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md) for the assets). No warranty. M-VAVE and FM-1 are trademarks of their owners; SLOOP is not affiliated with M-VAVE. Drum kit names describe styles, not products.
