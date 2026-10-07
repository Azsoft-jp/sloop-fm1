#!/usr/bin/env python3
"""Build a self-contained navigation page for the SLOOP 2.4 review evidence.

The linked PNGs are exact 240x240 host framebuffer captures. GIFs are actual
375x820 browser scroll recordings. This script does not claim device testing.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/ja-ui-report.html"
E = ROOT / "docs/ja-ui-evidence"
manifest = json.loads((E / "lcd-manifest.json").read_text())
layout = json.loads((E / "browser-layout.json").read_text())
scroll = json.loads((E / "scroll-capture.json").read_text())["results"]
metrics_path = E / "metrics.json"
metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}


def esc(x):
    return html.escape(str(x), quote=True)


def fig(path, label, klass=""):
    return (f'<figure class="{klass}"><a href="{esc(path)}"><img src="{esc(path)}" '
            f'alt="{esc(label)}" loading="lazy"></a><figcaption>{esc(label)}</figcaption></figure>')


featured = ["menu-screen", "menu-audio", "layer-song-chain", "layer-mix-fill", "page-step", "page-song"]
web_tabs = ["sound", "sequencer", "tracks", "library", "samples", "kits", "projects", "settings"]
web_labels = ["音色", "シーケンサー", "トラック", "ライブラリ", "サンプル", "ドラムキット", "プロジェクト", "設定"]
lcd = "\n".join(fig(f"ja-ui-evidence/lcd/{s}.png", s, "lcd") for s in featured)
all_lcd = "\n".join(fig(f"ja-ui-evidence/lcd/{e['screen']}.png", e["screen"], "lcd") for e in manifest)
web = "\n".join(fig(f"ja-ui-evidence/editor-375-{s}.png", label) for s, label in zip(web_tabs, web_labels))
web += fig("ja-ui-evidence/installer-375.png", "インストーラー")
gifs = "\n".join(fig(f"ja-ui-evidence/{x['gif']}", f"{x['label']} - {x['frames']} frames / {x['height']}px")
                    for x in scroll if x["gif"])
firmware = metrics.get("firmware", {})
binary = (f"上流2.4: {firmware['baseline_bytes']:,} B → 日本語版: {firmware['localized_bytes']:,} B "
          f"({firmware['localized_bytes'] - firmware['baseline_bytes']:+,} B)"
          if firmware.get("baseline_bytes") is not None and firmware.get("localized_bytes") is not None
          else "ターゲットFWサイズは未測定")
ram = (f"RAM .data+.bss: {firmware['baseline_ram']:,} B → {firmware['localized_ram']:,} B"
       if firmware.get("baseline_ram") is not None and firmware.get("localized_ram") is not None
       else "RAM使用量は未測定")
headroom = (f"アプリ領域残量: {firmware['localized_slot_free_bytes']:,} B / {firmware['app_slot_bytes']:,} B"
            if firmware.get("localized_slot_free_bytes") is not None else "アプリ領域残量は未測定")

OUT.write_text(f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SLOOP 2.4 日本語UI 検証レポート</title>
<style>
:root{{--bg:#10141b;--card:#1b2532;--line:#334456;--fg:#eaf1fa;--dim:#abb9c9;--accent:#80d4ff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 system-ui,-apple-system,sans-serif}}
header{{padding:44px max(20px,calc((100vw - 1100px)/2));background:#192737;border-bottom:1px solid var(--line)}}
main{{max-width:1100px;margin:auto;padding:30px 20px 90px}} h1{{font-size:clamp(26px,4vw,42px);line-height:1.2;margin:0 0 12px}} h2{{margin:42px 0 14px;font-size:23px}}
p{{max-width:78ch}} .dim{{color:var(--dim)}} .badges{{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0}}
.badges span{{padding:6px 12px;border:1px solid var(--line);border-radius:99px;background:var(--card)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;align-items:start}}
figure{{margin:0;padding:12px;background:var(--card);border:1px solid var(--line);border-radius:12px;min-width:0}}
figure img{{display:block;width:100%;height:auto;max-height:600px;object-fit:contain;object-position:top;background:#000}}
figure.lcd img{{width:240px;height:240px;max-width:100%;image-rendering:pixelated;object-fit:contain;margin:auto}}
figcaption{{margin-top:9px;color:var(--dim);font-size:13px;overflow-wrap:anywhere}}
a{{color:var(--accent)}} details{{margin:22px 0}} summary{{cursor:pointer;color:var(--accent)}}
.metrics{{padding:18px;background:var(--card);border-left:4px solid var(--accent)}}
@media(max-width:560px){{header{{padding:28px 20px}} .grid{{grid-template-columns:1fr}} figure img{{max-height:none}}}}
</style></head><body>
<header><h1>SLOOP 2.4 日本語UI</h1><p>FM-1本体とWeb Editorの画面・レイアウト・回帰確認</p>
<div class="badges"><span>{len(manifest)} 本体画面</span><span>{len(web_tabs)} Web画面＋インストーラー</span>
<span>{len([x for x in scroll if x['gif']])} スクロールGIF</span><span>{len(layout)} レイアウト計測</span></div></header>
<main><p class="dim">このページは君のフォークのSLOOP 2.4日本語化作業用。FM-1画像は本体描画コードをホスト上で実行した実ピクセルの240×240 PNG。
実機LCDの写真ではありません。Web画面はChromeのモック接続で撮影。機器への書き込み・実機の音声遅延は未確認です。</p>
<section class="metrics"><strong>容量</strong><br>{esc(binary)}<br>{esc(ram)}<br>{esc(headroom)}<br>
<strong>確認済み</strong>：本体描画テスト、2.4操作ストレス、Webプロトコルテスト、375/1280pxブラウザー画面。
詳細は<a href="JA_LOCALIZATION.md">検証記録</a>へ。</section>
<h2>本体の主要画面（実ドット）</h2><div class="grid">{lcd}</div>
<details><summary>全{len(manifest)}画面を見る</summary><div class="grid">{all_lcd}</div></details>
<h2>Web Editor・インストーラー</h2><div class="grid">{web}</div>
<h2>モバイル縦スクロール</h2><p class="dim">375×820pxのブラウザー画面を実際にスクロールして録画。GIFをクリックすると元サイズで開きます。</p>
<div class="grid">{gifs}</div>
<p><a href="ja-ui-report.pdf">PDF版を開く</a>　<a href="ja-ui-evidence/lcd-manifest.json">画像一覧JSON</a>　
<a href="ja-ui-evidence/browser-layout.json">ブラウザー計測JSON</a></p>
</main></body></html>''', encoding="utf-8")
print(f"{OUT}: {len(manifest)} LCD images, {len(web_tabs) + 1} web views, {len(scroll)} scroll captures")
