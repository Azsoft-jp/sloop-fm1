#!/usr/bin/env python3
"""Build the PR's printable Japanese UI evidence report.

Requires ReportLab, Pillow, and a local Noto Sans JP TTF. The font is embedded
as a subset in the PDF; its full source is deliberately not committed.

    SLOOP_PDF_FONT=build/deps/NotoSansJP-500.ttf python tools/build_ja_ui_pdf.py

Noto Sans JP's Google Fonts file is variable and defaults to weight 100.
If build/deps/NotoSansJP-wght.ttf exists, fontTools instantiates weight 500
automatically. ReportLab does not apply the variable axis itself.

Font source: https://github.com/google/fonts/tree/main/ofl/notosansjp
License: SIL Open Font License 1.1
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVIDENCE = DOCS / "ja-ui-evidence"
OUTPUT = DOCS / "ja-ui-report.pdf"
FONT = Path(os.environ.get("SLOOP_PDF_FONT", ROOT / "build/deps/NotoSansJP-500.ttf"))
if not FONT.is_file() and "SLOOP_PDF_FONT" not in os.environ:
    source = ROOT / "build/deps/NotoSansJP-wght.ttf"
    if source.is_file():
        from fontTools.ttLib import TTFont as VariableFont
        from fontTools.varLib.instancer import instantiateVariableFont

        variable = VariableFont(source)
        instantiateVariableFont(variable, {"wght": 500}, inplace=True)
        variable.save(FONT)
if not FONT.is_file():
    raise SystemExit(f"Japanese TTF missing: {FONT}; see this script's header")
pdfmetrics.registerFont(TTFont("NotoJP", str(FONT)))

W, H = A4
M = 42
NAVY = colors.HexColor("#15233A")
BLUE = colors.HexColor("#225BB8")
PALE = colors.HexColor("#EAF2FF")
INK = colors.HexColor("#172236")
MUTED = colors.HexColor("#52627A")
LINE = colors.HexColor("#DAE1EA")
BG = colors.HexColor("#F4F7FB")
PR = "https://github.com/isod89/sloop-fm1/pull/39"
BRANCH = "https://github.com/Azsoft-jp/sloop-fm1/blob/codex/ja-localization-phase1-2/docs/"
RAW = "https://raw.githubusercontent.com/Azsoft-jp/sloop-fm1/codex/ja-localization-phase1-2/docs/"

pdf = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
pdf.setTitle("SLOOP for M-VAVE FM-1 日本語UI 画面・検証レポート")
pdf.setAuthor("SLOOP Japanese localization PR evidence")
pdf.setSubject("FM-1本体とWeb Editorの日本語化、画面、容量、回帰試験")
page_number = 0


def txt(x: float, y: float, value: str, size: float = 9, color=INK) -> None:
    pdf.setFont("NotoJP", size)
    pdf.setFillColor(color)
    pdf.drawString(x, y, value)


def wrap(value: str, width: float, size: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in value:
        if ch == "\n":
            lines.append(current)
            current = ""
        elif pdfmetrics.stringWidth(current + ch, "NotoJP", size) > width and current:
            lines.append(current)
            current = ch
        else:
            current += ch
    if current:
        lines.append(current)
    return lines


def para(x: float, y: float, value: str, width: float, size: float = 9,
         leading: float = 14, color=INK) -> float:
    for line in wrap(value, width, size):
        txt(x, y, line, size, color)
        y -= leading
    return y


def round_box(x: float, y: float, width: float, height: float, fill=BG,
              stroke=LINE, radius: float = 9) -> None:
    pdf.setFillColor(fill)
    pdf.setStrokeColor(stroke)
    pdf.roundRect(x, y, width, height, radius, fill=1, stroke=1)


def image(path: Path, x: float, y: float, width: float, height: float,
          source_url: str | None = None) -> None:
    pdf.drawImage(ImageReader(str(path)), x, y, width=width, height=height,
                  preserveAspectRatio=False, mask="auto")
    if source_url:
        pdf.linkURL(source_url, (x, y, x + width, y + height), relative=0)


def pil_image(im: Image.Image, x: float, y: float, width: float, height: float) -> None:
    stream = io.BytesIO()
    im.convert("RGB").save(stream, format="PNG")
    stream.seek(0)
    pdf.drawImage(ImageReader(stream), x, y, width=width, height=height,
                  preserveAspectRatio=False)


def link_label(x: float, y: float, value: str, url: str, size: float = 9) -> None:
    txt(x, y, value, size, BLUE)
    width = pdfmetrics.stringWidth(value, "NotoJP", size)
    pdf.linkURL(url, (x, y - 3, x + width, y + size + 2), relative=0)


def start_page(section: str, title: str, subtitle: str = "") -> None:
    global page_number
    page_number += 1
    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, W, H, fill=1, stroke=0)
    pdf.setFillColor(NAVY)
    pdf.rect(0, H - 58, W, 58, fill=1, stroke=0)
    txt(M, H - 25, "SLOOP  /  FM-1  /  日本語UI", 11, colors.white)
    txt(M, H - 44, section, 8, colors.HexColor("#B8D2FA"))
    txt(M, H - 84, title, 19, INK)
    if subtitle:
        para(M, H - 104, subtitle, W - 2 * M, 8.2, 12, MUTED)


def finish_page() -> None:
    pdf.setStrokeColor(LINE)
    pdf.line(M, 33, W - M, 33)
    txt(M, 20, "PR #39  |  ホスト描画・ブラウザーモックの証跡  |  実機確認待ち", 7, MUTED)
    txt(W - M - 15, 20, str(page_number), 8, MUTED)
    pdf.showPage()


# Cover: the raw 240 × 240 screenshots are the focus, with no contact-sheet scaling.
start_page("概要", "画面・検証レポート", "Phase 1 Web Editor / Phase 2 FM-1本体  ―  PRレビュー用PDF")
txt(M, 697, "本体のドット画面を、描画コードから出力した240×240 PNGで確認", 11)
para(M, 679, "実機LCDの写真ではありません。Web画面はChromeとEditorのモック接続で撮影しました。"
     "文字切れ修正後の2bit階調フォントを使用しています。", W - 2 * M, 8.7, 14, MUTED)
for x, key, label in [(M + 16, "page-step", "ステップ画面"), (W / 2 + 6, "page-song", "ソング画面")]:
    round_box(x - 8, 379, 240, 266, colors.HexColor("#E9EEF5"))
    image(EVIDENCE / f"{key}.png", x + 4, 398, 216, 216,
          RAW + f"ja-ui-evidence/{key}.png")
    txt(x + 4, 626, label, 9)
round_box(M, 292, W - 2 * M, 68, PALE, PALE)
for x, value, label in [(M + 18, "35", "本体画面"), (M + 126, "74", "日本語glyph"),
                         (M + 236, "206", "UI文字列ID"), (M + 358, "97", "音声一致")]:
    txt(x, 324, value, 18, BLUE)
    txt(x, 307, label, 7.5, MUTED)
txt(M, 262, "表示品質の変更", 11)
para(M, 245, "使用文字だけの2bit階調glyph（5,920 B）。「ヘ」の最下段欠けを修正し、全74字の上下端を生成時に検査。"
     "60px列に入らない語は短縮英字名へ切り替え、本体に文字スクロールを追加していません。", W - 2 * M, 8.8, 14)
txt(M, 189, "検証と制限", 11)
para(M, 172, "ターゲットFWビルド、UI描画テスト2万フレーム、音声ゴールデン97件は通過。"
     "総合テストのCPU命令予算超過は元コミットから同値で残存。実機の表示品質と音声割り込み最大時間は未確認です。", W - 2 * M, 8.8, 14)
link_label(M, 99, "PR #39 を開く ↗", PR)
link_label(M + 152, 99, "HTML・GIF版を開く ↗", BRANCH + "ja-ui-report.html")
link_label(M + 329, 99, "詳細記録を開く ↗", BRANCH + "JA_LOCALIZATION.md")
finish_page()


# Full firmware gallery, 9 shots per page. Every image opens its raw 240 × 240 PNG.
manifest = json.loads((EVIDENCE / "lcd-manifest.json").read_text())
assert len(manifest) == 35
labels = {
    "hold-clear": "全消去確認", "layer-erase": "レイヤー消去", "layer-key": "キー", "layer-locked": "ロック",
    "layer-mix": "ミックス", "layer-punch-on": "パンチON", "layer-punch": "パンチ", "layer-roll": "ロール",
    "layer-song": "ソング層", "layer-steps": "ステップ層", "live-free-take": "フリー録音テイク",
    "live-grid": "グリッド", "live-kit": "キット", "live-rec-count": "録音カウント",
    "live-rec-countin": "録音カウントイン", "live-rec-free": "フリー録音", "live-rec-notes": "録音ノート",
    "live-rec-ready": "録音準備", "live-rec-tempo": "録音テンポ", "live-tracks": "トラック",
    "menu-usb": "USBメニュー", "page-about": "バージョン", "page-edit": "編集", "page-env": "エンベロープ",
    "page-fx": "FX", "page-global": "全体設定", "page-master": "マスター", "page-menu-lights": "ライト設定",
    "page-menu-notes": "ノート設定", "page-scale": "スケール", "page-song": "ソング", "page-splash": "起動画面",
    "page-step": "ステップ", "page-tracks": "トラック画面", "song-screen": "ソング編集",
}
col_w = (W - 2 * M - 24) / 3
card_h = 196
for sheet in range(4):
    entries = manifest[sheet * 9:sheet * 9 + 9]
    start_page("FM-1本体  /  全35画面", f"LCD描画ギャラリー  {sheet + 1} / 4",
               f"ホスト側の本体描画コードによる240×240px出力。各画像をクリックすると元PNGを開きます。  {sheet * 9 + 1}–{sheet * 9 + len(entries)} / 35")
    for i, entry in enumerate(entries):
        col, row = i % 3, i // 3
        x = M + col * (col_w + 12)
        top = 712 - row * (card_h + 10)
        bottom = top - card_h
        round_box(x, bottom, col_w, card_h, BG)
        key = entry["screen"]
        path = EVIDENCE / "lcd" / f"{key}.png"
        assert path.is_file() and Image.open(path).size == (240, 240)
        img_side = 157
        image(path, x + (col_w - img_side) / 2, bottom + 30, img_side, img_side,
              RAW + f"ja-ui-evidence/lcd/{key}.png")
        txt(x + 10, bottom + 13, f"{sheet * 9 + i + 1:02d}  {labels[key]}", 8)
    finish_page()


# Web Editor overview, showing real mobile viewport crops (not stretched full pages).
web = [("sound", "音色"), ("sequencer", "シーケンサー"), ("tracks", "トラック"),
       ("library", "ライブラリ"), ("samples", "サンプル"), ("projects", "プロジェクト"),
       ("settings", "設定"), ("installer", "インストーラー")]
web_w = (W - 2 * M - 14) / 2
web_h = 318
for sheet in range(2):
    start_page("Web Editor  /  7タブ＋インストーラー", f"日本語Web画面  {sheet + 1} / 2",
               "Chromeの375px幅で撮影。カードは画面上部510pxを表示します。クリックで元の全長PNGを開けます。")
    for i, (key, label) in enumerate(web[sheet * 4:sheet * 4 + 4]):
        col, row = i % 2, i // 2
        x = M + col * (web_w + 14)
        top = 715 - row * (web_h + 12)
        bottom = top - web_h
        round_box(x, bottom, web_w, web_h, BG)
        filename = "installer-375.png" if key == "installer" else f"editor-375-{key}.png"
        source = EVIDENCE / filename
        screenshot = Image.open(source).convert("RGB").crop((0, 0, 375, 510))
        preview_w = 209
        preview_h = preview_w * 510 / 375
        pil_image(screenshot, x + (web_w - preview_w) / 2, bottom + 24, preview_w, preview_h)
        txt(x + 10, bottom + 9, label, 8.5)
        pdf.linkURL(RAW + "ja-ui-evidence/" + filename,
                    (x, bottom, x + web_w, top), relative=0)
    txt(M, 57, "15画面を375px・1280pxで計測。横はみ出しとパラメーター名のクリップは検出なし。", 8, MUTED)
    finish_page()


# The PDF is static; provide meaningful frame pairs and direct GIF links.
start_page("Web Editor  /  動きの証跡", "縦スクロールGIF", "各行の左が開始、右が終了フレームの縮小表示。青いリンクから375×820pxの元GIFを再生できます。")
scroll = [("sound", "音色"), ("sequencer", "シーケンサー"), ("tracks", "トラック"),
          ("library", "ライブラリ"), ("samples", "サンプル"), ("settings", "設定"),
          ("installer", "インストーラー")]
for i, (key, label) in enumerate(scroll):
    top = 713 - i * 88
    bottom = top - 80
    round_box(M, bottom, W - 2 * M, 80, BG)
    gif = Image.open(EVIDENCE / f"scroll-{key}.gif")
    first = gif.convert("RGB")
    gif.seek(gif.n_frames - 1)
    last = gif.convert("RGB")
    for frame, x in [(first, M + 9), (last, M + 47)]:
        pil_image(frame, x, bottom + 5, 32, 70)
    txt(M + 93, bottom + 52, label, 10)
    txt(M + 93, bottom + 34, f"開始 → 終了  /  {gif.n_frames} フレーム", 7.5, MUTED)
    link_label(M + 93, bottom + 13, "元GIFを再生 ↗", RAW + f"ja-ui-evidence/scroll-{key}.gif", 8)
    txt(W - M - 118, bottom + 14, "375 × 820 px", 7.5, MUTED)
finish_page()


# Measured results and limitations. Do not imply a hardware timing guarantee.
start_page("測定・回帰", "容量と検証結果", "前後値は保存したビルドログから。実機を使う項目は未確認としています。")
rows = [
    ("FWアプリ", "550,256 B", "562,016 B  (+11,760 B / +2.1%)"),
    ("アプリ領域残量", "31,308 B", "19,548 B"),
    ("RAM .data + .bss", "72,720 B", "72,892 B  (+172 B)"),
    ("描画プール", "322,272 B", "322,272 B  (変化なし)"),
    ("Web Editor生HTML", "242,617 B", "245,961 B  (+3,344 B)"),
    ("インストーラー生HTML", "19,241 B", "20,847 B  (+1,606 B)"),
]
round_box(M, 474, W - 2 * M, 238, colors.white)
pdf.setFillColor(PALE)
pdf.roundRect(M, 680, W - 2 * M, 32, 9, fill=1, stroke=0)
for x, label in [(M + 12, "項目"), (M + 164, "変更前"), (M + 277, "変更後")]:
    txt(x, 691, label, 8.5, INK)
for i, (label, before, after) in enumerate(rows):
    y = 654 - i * 32
    txt(M + 12, y, label, 8)
    txt(M + 164, y, before, 8)
    txt(M + 277, y, after, 8)
    if i < len(rows) - 1:
        pdf.setStrokeColor(LINE)
        pdf.line(M + 10, y - 12, W - M - 10, y - 12)
txt(M, 445, "回帰試験", 11)
items = [
    ("PASS", "ターゲットFWビルド、Flash・RAM・描画プールの制限検査"),
    ("PASS", "ASCII・カタカナ・UTF-8異常系・画面外描画・主要操作・UI fuzz 2万フレーム"),
    ("PASS", "音声ゴールデン97件のハッシュが元コミットと一致"),
    ("PASS", "ブラウザー15画面、375px・1280px、横はみ出しと名前クリップなし"),
    ("既存FAIL", "総合テストのCPU命令予算超過は元コミットと同じ項目・値"),
]
for i, (status, description) in enumerate(items):
    y = 420 - i * 29
    txt(M, y, status, 8, BLUE if status == "PASS" else colors.HexColor("#AC641D"))
    txt(M + 64, y, description, 7.7)
txt(M, 250, "音声処理と実機確認", 11)
para(M, 232, "音声DMA割り込み・DSP・MIDIタイミングのコードは変更なし。日本語は既存のオフスクリーン描画で処理し、"
     "LCD転送サイズと更新回数も変えません。実機の最大割り込み時間・音切れは未測定です。マージ前に再生負荷別の max_us と late を変更前後で比較してください。",
     W - 2 * M, 8.4, 13)
txt(M, 169, "未確認・次段階", 11)
para(M, 151, "実機LCDの色・視認性、実機Flash更新と復帰、音声割り込み実測は未確認。Phase 3は ui_strings.h の言語選択、"
     "ui_menu.c / ui_input.c のLANG項目、既存設定保存処理の永続化を追加。元FWへ戻す際はプロジェクトを保存し、公式FM-1 V15のFM-1.fwscをインストーラーから選択します。",
     W - 2 * M, 8.1, 12)
link_label(M, 68, "ビルド・テストログと詳細手順 ↗", BRANCH + "JA_LOCALIZATION.md", 8.5)
finish_page()

pdf.save()
print(f"Created {OUTPUT} ({page_number} pages, {OUTPUT.stat().st_size:,} bytes)")
