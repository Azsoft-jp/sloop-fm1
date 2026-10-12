# SLOOP 2.6 日本語UI — 実装・検証記録

対象は上流の正式リリース`v2.6`（`d30d6553353373cf5506b9ed285fc4a2aa0c30ef`）を起点にした、Azsoft-jp所有の`codex/ja-localization-sloop-2.6`です。上流へのPRや公開配布は行っていません。この文書の数値は同じJieLiツールチェーンとSDKで上流2.6と日本語版をビルドして測定しました。実機に書き込んだ結果ではありません。

## 変更ファイル

- 本体UI・文字列: `firmware/src/felucca.c`, `gfx.c`, `main.c`, `project.c`, `recovery.c`, `ui.c`, `ui_draw.c`, `ui_input.c`, `ui_layers.c`, `ui_menu.c`, `ui_song.c`, `ui_studio.c`, `ui_vis.c`, `upreset.c`, `ui_strings.def`, `ui_strings.h`
- 最小フォントと生成: `assets/fonts/NotoSansJP-ui.ttf`, `NotoSansJP-OFL.txt`, `tools/gen_font.py`, `tools/gen_ui_hash.py`, `tools/build.py`
- Webと更新サイト: `web/editor.html`, `index_pkg.html`, `make_site.py`, `test_layout.cjs`, `capture_ja_report.cjs`, `test_ja_report.cjs`, `tools/build_ja_site.sh`, `dist/ja-2.6/`
- 試験・証跡: `tests/check_ja_resources.py`, `font_test.c`, `ui_pages_test.c`, `run_tests.sh`, `tools/render_ui_evidence.py`, `build_ja_ui_report.py`, `build_ja_ui_pdf.py`, `docs/ja-ui-report.html`, `ja-ui-report.pdf`, `ja-ui-evidence/`, `.gitattributes`, `.gitignore`

## 最初の調査

### 確認済み事実

1. 本体描画は`firmware/src/gfx.c`の`cv_text`、`text_w`などを通り、ページ・メニュー・状態・エラーの表示は主に`firmware/src/ui*.c`、`main.c`、`project.c`、`recovery.c`に分散していた。
2. 表示は240×240px。帯状キャンバスは最大240×124px。元の小フォントはTerminus Bold 8×16、大フォントは同じビットマップの2倍表示。元の描画系は1バイト文字を想定していた。ページごとに文字数と描画幅の制限が異なる。
3. 元のASCIIやLatin-1文字列は描画箇所に直接現れ、メニュー、ステータス、レイヤー、設定、保存・読込、復旧、各種ページに散在していた。調査した文字列は`ui_strings.def`へ263 IDとして収集し、実際のUI描画には`ui_text()`または表示名変換を使う。
4. Web Editorは`web/editor.html`の単一ページ。元から`TEXT.ja`/`TEXT.en`と`data-t`を用いた簡易i18nがあり、インストーラー`web/index_pkg.html`も同形式。2.6にはSongとDrum Synthのタブ、TEXTURE、トラックINSERT、MIDIなどが追加されている。
5. ビルドは`build.sh`、サイト生成は`web/make_site.py`、本体とWebの総合試験は`tests/run_tests.sh`。ブラウザー実画面の試験・撮影はPlaywright/Chromeで行える。CI設定と既存ホスト試験は維持した。
6. 日本語化前の上流2.6はFW本体573,052 B、RAM `.data+.bss` 92,696 B、`.pool` 333,900 B。上限はアプリ581,564 B、RAM 98,304 B、pool 344,064 B。
7. USB経由のファーム更新はブラウザーのインストーラーから`fwsc`を取得する構造。配布パッケージは機種ID`FM-1_926`の固定長610,019 B。

### 推測・設計上の判断

- 音声割り込み領域`.ram_text`が上流2.6と日本語版でバイナリ完全一致し、925命令・外部呼出しなしだったため、今回の日本語描画は音声ISRの命令列を変更していない。ただし実機の割り込み待ち時間や音声ジッターの実測にはならない。
- 2.6のFlash残量は厳しい。全角漢字や常時動く横スクロールより、短いカタカナとFX/BPM/MIDI/USBなどの定着した略語を使い、画面内に収める方が妥当と判断した。

### 未確認

- 実機LCDの色・輝度・物理的な視認性と全メニュー遷移。
- 実機での音声p95/p99、USB MIDIと画面更新を同時に使ったときの遅延。
- 実機への書き込み、Projectsのバックアップと復元、元FWへの書き戻し。検証時にFM-1はUSB接続されていなかった。

## 実装構造

### FM-1本体

- `firmware/src/ui_strings.def`に英語・日本語を263 IDで1対1に定義。`tools/gen_ui_hash.py`が日本語文字列のbyte blobとoffset、既存英語表示名の検索用hashを生成し、`ui_strings.h`の`ui_text()`が参照する。同じ語と、長い語の末尾に一致する短い語は格納領域を共有する。英語リソースは定義側に保持し、Phase 3では`UI_ENABLE_LANGUAGE_SWITCH`を有効にして言語別テーブルを選べる。
- `ui_display_name()`はプロトコルで使う英語の音色・パラメーター名を表示時だけ日本語へ変換する。SysEx、保存ファイルの識別子、プロトコル値は変えない。
- `tools/gen_font.py`は実際の日本語文字列から使う文字だけを抽出し、**75字・2,400 B**の疎な1bpp 16×16 glyphを生成する。収録文字: `アィイウェエオカガキギクグケコサザシジスズセゼソゾタダチッツヅテデトドナニネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロワヲン・ー`。ライセンスは`assets/fonts/NotoSansJP-OFL.txt`。
- `gfx.c`へ境界付きの小型UTF-8 decoderとglyph lookupを追加した。ASCII、既存Latin-1、収録カタカナを表示し、不正な列や未登録glyphは`?`にする。日本語glyphの固定長offset表とTerminusの固定幅・送り・offset表を省き、Terminusの無画素の左右2列も保存しない。ASCIIの描画画素と送り幅は全字のフォント試験で従来版と完全一致した。大フォントは同じbitmapの2倍表示を再利用する。
- 2.6で追加されたTEXTURE、INSERT、MIDI、LEARN、Song、Drum Synth関連も表示側で日本語化した。狭い行は短い語にし、幅検査にかけた。継続的な文字スクロールは追加していない。

### Web Editorとブラウザー更新

- 既存の`TEXT.ja`/`TEXT.en`、`data-t`を維持し、2.6の10タブ（音色、シーケンサー、トラック、ソング、ライブラリ、サンプル、ドラムキット、ドラムシンセ、プロジェクト、設定）とダイアログ、ツールチップ、通知、ファーム更新の文字列を整理した。descriptorラベルは`LABEL_JA`で表示時だけ変換する。
- インストーラーのヒーロー、機能タイル、説明、タイトルを日英リソース化し、2.6の153音色・37ドラムキット・27 FXに更新した。
- `tools/build_ja_site.sh`が`2.6-JA BETA`のFWとローカル更新サイト`dist/ja-2.6/`を生成する。`firmware/sloop-2.6-ja.fwsc`と`SHA256SUMS`を収録。`SLOOP_ONLINE_URL`でオフラインWeb Editorのインストーラーリンクを同サイトへ向けられる。既定は`http://127.0.0.1:8766/`。

## 実測サイズ

| 項目 | 上流2.6 | 日本語版 | 差 |
|---|---:|---:|---:|
| `felucca.bin` | 573,052 B | 577,972 B | +4,920 B |
| RAM `.data+.bss` | 92,696 B | 92,968 B | +272 B |
| RAM `.pool` | 333,900 B | 333,900 B | 0 B |
| `web/editor.html` | 574,533 B | 578,209 B | +3,676 B |
| `web/index_pkg.html` | 19,659 B | 20,977 B | +1,318 B |

前回の日本語版581,252 Bから**3,280 B削減**し、アプリ領域の残りは**3,592 B**になった。日本語文字列blobは3,742 Bから3,457 B、Terminusのbitmapは5,376 Bから3,584 B。RAMとpoolは前回日本語版から変化なし。今後のFW機能追加時には再測定が必要。`fwsc`は610,019 Bの固定長で、SHA-256は`8976732861a36d70fb7cd19ede06b084c645a4d453deffd2221b699b9c780d83`。`.ram_text`は上流2.6と同じSHA-256 `0d0540c3071b9230d6275623cb0874c4f61bbe18a1d02ba9f1aadc27d3582f36`。UI描画の実機フレーム時間は未測定。

## 試験・画面証跡

- 本体ホスト試験: ASCII、全glyph、濁点・半濁点・長音・小書き文字、UTF-8末尾と不正列、未登録glyph、画面端、幅と重なり、2.6メニュー遷移、SAVE/LOADなどの操作、20,000フレームのfuzzを確認。
- Webプロトコル試験: 2.6のSong、Drum Synth、Samples、Projects、Settings、バックアップ、更新プロトコルを確認。ブラウザーは375pxと1280pxで21画面を計測し、横はみ出しと切れを確認。
- `docs/ja-ui-evidence/lcd/`は本体の描画関数をホスト上で実行した**71枚の240×240px実ピクセル画像**。実機写真ではない。`scroll-*.gif`はChrome上で375×820pxの画面を実際に縦スクロールした9本。SongとDrum Synthのモック画面は縦スクロール不要だった。
- HTMLレポートは`docs/ja-ui-report.html`、PDFは`docs/ja-ui-report.pdf`。計測値と各画面のJSONは`docs/ja-ui-evidence/`にある。
- 総合テストは上流2.6でも再現する予算超過2件だけでexit 1。`PHASE/03_RESO_PLUCK`は1131対基準899（+26%、許容25%）、`fm1_alnk0_irq`はcost 268対予算174（+54%、許容10%）。予算を緩めて合格扱いにしていない。上流2.6の同条件でも同じ結果。音声golden 182件の差分は0、health/voice/routing失敗0。
- 実機のUSB更新と音声遅延は未確認。現時点のブラウザー確認はサイトのFW fetch、hash照合、インストールボタン有効化まで。

### 再現手順

```sh
JIELI_TOOLCHAIN=/path/to/jieli/toolchain AC79_SDK=/path/to/ac79 PYTHON=.venv/bin/python sh tools/build_ja_site.sh
AC79_SDK=/path/to/ac79 SOAK_MIN=1 STRESS_FRAMES=5000 STRESS_ASAN_FRAMES=3000 sh tests/run_tests.sh
python3 -m http.server 8766 --bind 127.0.0.1 --directory dist/ja-2.6
# 別の端末で、Chrome/Edgeから http://127.0.0.1:8766/ を開く
PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome SLOOP_SITE_URL=http://127.0.0.1:8766/ node web/test_layout.cjs
PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome node web/capture_ja_report.cjs
.venv/bin/python tools/render_ui_evidence.py build/host docs/ja-ui-evidence
python3 tools/build_ja_ui_report.py
SLOOP_PDF_FONT=/path/to/static/NotoSansJP.ttf .venv/bin/python tools/build_ja_ui_pdf.py
```

## 未対応・制限

- 漢字全般、任意Unicode、他言語、言語設定UI・永続化・起動時選択、ユーザーフォント、横スクロールは対象外。
- エンジン・音色・プリセット・ノート名、FX/BPM/MIDI/USB/RECなどの小さい略語は英字のまま。保存形式と通信識別子は変更しない。
- 2.6のプロジェクト形式は2.5へ書き戻せない。更新前にWeb Editorで全体バックアップを保存する。2.5以前へのダウングレードとデータ復元は別途慎重に検証する。
- 2.6のアプリ領域の空きは3,592 B。上流が機能を追加した場合は再測定し、必要ならこのフォント集合や文字列を調整する。

## Phase 3の日英切替で変更するファイルと処理

1. `firmware/src/ui_strings.h`: `Language` enumと`currentLanguage`を追加し、`ui_text()`および`ui_display_name()`の参照テーブルを切り替える。`UI_ENABLE_LANGUAGE_SWITCH`で保持される英語テーブルを有効化し、アプリ領域の再測定を行う。
2. `firmware/src/ui_strings.def`、`tools/gen_ui_hash.py`: EN/JAの全IDを維持して生成物を再出力。英語側のビルド容量を確認する。
3. `firmware/src/ui_menu.c`: SettingsにLANG行、EN/JA選択、変更時の再描画とUI cache無効化を追加する。狭い行の両言語の幅を再試験する。
4. `firmware/src/project.c`と設定の読み書き箇所: 互換性のある言語設定の保存・復元、古い設定の既定値を追加する。必要に応じ`main.c`の起動時反映を変更する。
5. `tests/ui_pages_test.c`、`web/test_layout.cjs`: 起動・切替・再起動・設定移行と両言語レイアウトを検証する。Web側はすでに日英切替を持つ。

## 元FWへ戻す方法

更新前のProjectsバックアップと、現在の元FWパッケージを保管する。インストーラーの「公式ファームウェア（V15）に戻す」ではM-VAVEが配布する未変更の`FM-1.fwsc`を指定する。上流SLOOP 2.6へ戻す場合は上流の正式リリースのFWを選ぶ。機種IDと配布元を確認し、書き込み完了後に再接続する。実機での復旧は未検証。
