# SLOOP 2.4 日本語UI - 実装・検証記録

対象: upstream `v2.4` (`8d3823f`) を起点とする、`Azsoft-jp/sloop-fm1` の
`codex/ja-localization-sloop-2.4`。上流リポジトリへのPRは作成しない。

## 変更ファイル一覧

- 本体: `firmware/src/felucca.c`, `gfx.c`, `main.c`, `project.c`, `recovery.c`, `ui.c`, `ui_draw.c`, `ui_input.c`, `ui_layers.c`, `ui_menu.c`, `ui_song.c`, `ui_studio.c`, `ui_vis.c`, `upreset.c`, `ui_strings.def`, `ui_strings.h`
- フォント: `assets/fonts/NotoSansJP-ui.ttf`, `NotoSansJP-OFL.txt`, `tools/gen_font.py`
- Web: `web/editor.html`, `index_pkg.html`, `test_layout.cjs`, `capture_ja_report.cjs`, `test_ja_report.cjs`
- 試験・生成: `tests/check_ja_resources.py`, `run_tests.sh`, `ui_pages_test.c`, `tools/render_ui_evidence.py`, `build_ja_ui_report.py`, `build_ja_ui_pdf.py`
- 文書・画面: `docs/JA_LOCALIZATION.md`, `ja-ui-report.html`, `ja-ui-report.pdf`, `ja-ui-evidence/`（画像ごとの全ファイル名は`lcd-manifest.json`）
- リポジトリ設定: `.gitattributes`, `.gitignore`

## 調査結果

### 確認済み事実

- 本体表示は240×240px。`firmware/src/gfx.c` は最大240×124pxの帯状キャンバスを使う。小フォントはTerminus 8×16、大フォントはそのbitmapを描画時に2倍化する32px表示。
- 文字描画と幅測定は`gfx.c`の`cv_text`と`text_w`。元のASCII描画を保ち、UTF-8デコーダ、疎なglyph検索、2bppの日本語bitmapを追加した。
- 本体のページ、状態、設定、レイヤー、エラー、復旧表示は`firmware/src/ui*.c`、`main.c`、`recovery.c`、`project.c`、`upreset.c`にある。2.4でセクション型設定メニュー、visualizer、FM6、fill、quick chain、ユーザードラムキットなどが増えた。
- Web Editorは`web/editor.html`の単一ページ。2.4にはすでに`TEXT.ja`/`TEXT.en`と`data-t`がある。インストーラー`web/index_pkg.html`にも同方式がある。プロトコル名・ファイル形式・保存データは英語の識別子を使う。
- 通常ビルドは`build.sh`、ホスト総合試験は`tests/run_tests.sh`、Webのプロトコル試験は`node web/test_web.mjs`。本体2.4には専用のメニュー・visualizer・stress試験が含まれる。
- baselineと日本語版は同じJieLiツールチェーン/SDKでビルドした。測定値は`ja-ui-evidence/metrics.json`に保存した。

### 推測・設計上の判断

- 音声割り込み領域`.ram_text`のbinary SHA-256が両ビルドで同一であり、UI描画は音声のISR本体へ入らない。このため今回の文字列処理は音声ISRの命令列を変えていない。ただし実機の最大割り込み待ち時間までは、この事実だけでは証明できない。
- 240px画面では漢字追加や横スクロールより、短いカタカナと定着した英字略語を優先する方が、表示時間と読みやすさを安定させる。

### 未確認

- 実機LCDの色、輝度、物理的な視認性、実機操作での全メニュー遷移。
- 実機の音声遅延、ISR p99、USB MIDIとの同時負荷。
- 実機でのファーム書き込み、バックアップ復元、元FWへの書き戻し。

## 実装

### 本体文字列・glyph

- `firmware/src/ui_strings.def`: 238個のIDで英語と日本語を1対1に定義。`ui_strings.h`が2テーブルと`ui_text()`を作る。Phase 2では日本語固定。
- `ui_display_name()`は既存の英語ディスクリプタを描画境界で日本語に解決する。SysExや保存データの識別子は変えない。
- `tools/gen_font.py`が日本語欄から必要文字だけ抽出し、75字・6,000 Bの2bpp bitmapを作る。収録glyphは`アィイウェエオカガキギクグケコサザシジスズセゼソゾタダチッツヅテデトドナニネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロワヲン・ー`。生成ヘッダの集合と文字列テーブルの集合が等しいことを試験する。
- `gfx.c`の小型UTF-8デコーダはASCII、必要な日本語、Latin-1の既存表示を扱う。不正UTF-8と未収録glyphは`?`へフォールバック。画面外描画はクリップする。2.4の大フォント共有bitmapも保持した。
- メニューは2.4の4セクション・ノブ操作を保持。タブと説明文の幅を試験して短縮した。新しいvisualizer名は表示時だけ日本語へ変え、診断名は英語のまま。ソングの小さい行では単位が入らないとき数値のみ表示する。数値や極小のキー上ではREC、FX、MIDI、USB、SOLO等を残す。
- 横スクロール処理は追加していない。本体の描画フレームや音声処理へ継続的な文字アニメーションを持ち込まない。

### Web Editor

- 2.4の`TEXT.ja`/`TEXT.en`を保持。プロトコルのDESCラベルは`LABEL_JA`で表示時だけ変換し、送受信値を変えない。言語切替時はパラメーターカードも再描画する。
- インストーラーのヒーロー文、4つの機能タイル、クレジットと復旧説明を`data-t`へ移した。ページタイトルも両言語で更新する。
- 8タブ（音色、シーケンサー、トラック、ライブラリ、サンプル、ドラムキット、プロジェクト、設定）とインストーラーを確認した。

## サイズ・性能

| 項目 | 上流v2.4 | 日本語版 | 差 |
|---|---:|---:|---:|
| `felucca.bin` | 563,120 B | 575,712 B | +12,592 B |
| RAM `.data+.bss` | 82,916 B | 83,188 B | +272 B |
| RAM `.pool` | 334,560 B | 334,560 B | 0 B |
| `web/editor.html` | 460,974 B | 464,301 B | +3,327 B |
| `web/index_pkg.html` | 19,308 B | 20,659 B | +1,351 B |

アプリ領域上限は581,564 Bで、日本語版の残りは5,852 B。今後glyphや機能を追加する場合は容量再測定が必要。Flash上のFWパッケージ`felucca.fwsc`はどちらも610,019 B（固定コンテナサイズ）。`.ram_text`は925命令・外部呼出しなし、両ビルドのSHA-256が`0d0540c3071b9230d6275623cb0874c4f61bbe18a1d02ba9f1aadc27d3582f36`で完全一致した。UI描画速度そのものは個別計測していない。

## 試験と画面証跡

- 本体: `tests/ui_pages_test.c`でASCII、日本語、濁点、半濁点、長音、小書き文字、UTF-8末尾、不正列、未登録glyph、画面端クリップ、メニュー幅、visualizer名幅、主要操作を確認。
- 2.4 stress: 大文字フォントのbitmap共有、ランダム操作、visualizer、fill、chain、FM6、停止後ボイス解放を確認。
- Web: `node web/test_web.mjs`でプロトコル、プロジェクト、サンプル、ドラムキット、バックアップ、更新を確認。`web/test_layout.cjs`で375px/1280pxの17画面、パラメーター名、ツールチップ、確認ダイアログ、英語切替を確認。
- `ja-ui-evidence/lcd/`の60枚はホスト描画からの240×240 PNG。実機写真ではない。`ja-ui-evidence/scroll-*.gif`の9本は375×820pxの実ブラウザースクロール。
- テスト結果`ja-ui-evidence/test-results.json`とレイアウト計測を`ja-ui-evidence/`に保存。HTMLは`ja-ui-report.html`、静的PDFは`ja-ui-report.pdf`。

総合テストの終了コードには上流v2.4からの予算超過が残る。日本語版・無変更の上流v2.4とも、音声回帰の105件は変化0で、`cpu/PHASE/00_CZ_BASS`と`cpu/PHASE/03_RESO_PLUCK`の2件が既存CPU基準を超える。ターゲットの`fm1_alnk0_irq`も両者ともコスト268、基準174（+54%）で同じ。これを日本語化による性能劣化として数えないが、2.4自体の実機性能については別途測定が必要。予算値を書き換えて合格扱いにはしていない。

### 再現コマンド

```sh
JIELI_TOOLCHAIN=/path/to/jieli/toolchain AC79_SDK=/path/to/ac79 PYTHON=.venv/bin/python sh build.sh
AC79_SDK=/path/to/ac79 SOAK_MIN=1 STRESS_FRAMES=5000 STRESS_ASAN_FRAMES=3000 sh tests/run_tests.sh
PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome node web/test_layout.cjs
PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome node web/capture_ja_report.cjs
.venv/bin/python tools/render_ui_evidence.py build/host docs/ja-ui-evidence
python3 tools/build_ja_ui_report.py
SLOOP_PDF_FONT=/path/to/static/NotoSansJP.ttf .venv/bin/python tools/build_ja_ui_pdf.py
```

スクロールGIF生成には`ffmpeg`、PDF生成にはReportLabとPillowを使う。実機バイナリ生成にはJieLiのLinux x86-64ツールチェーンとSDK、macOSではDocker/Colimaが必要。

## 制限・未対応

- 漢字全般、ユーザー入力の任意Unicode、他言語、言語設定UIと永続化は対象外。
- エンジン名、音色名、プリセット名、ノート名、極小キー上の英字略語、一部の単位は既存の英字を維持する。プロトコル/保存ファイル互換のため、内部識別子も英語のまま。
- 実機LCDでのジャギー、輝度、ちらつきの最終確認が必要。PNGはnativeのドットを保持し、レポート上の拡大はnearest-neighbor表示にする。

## Phase 3の日英切替で変更するファイルと処理

1. `firmware/src/ui_strings.h`: `Language` enum、`currentLanguage`を追加し、`ui_text()`が`ui_strings_en`/`ui_strings_ja`を選ぶようにする。`ui_display_name()`も選択言語を参照する。
2. `firmware/src/ui_menu.c`と`ui_strings.def`: SettingsにLANG行とEN/JA値を加え、変更時にUI cacheを無効化する。
3. 設定の保存・復元箇所（`firmware/src/ui_input.c`、`firmware/src/project.c`、必要なら`main.c`）: 言語コードを既存形式の互換性を保って永続化する。
4. `tests/ui_pages_test.c`: 起動時、切替、再起動相当、既存設定の移行、メニュー幅を両言語で確認する。
5. Web側はすでに`lang`で日英を切り替える。保存設定を本体と同期する場合のみ`web/editor.html`の接続・設定表示を追加する。

## 元FWへ戻す方法

事前にWeb EditorのProjectsからバックアップを保存する。インストーラーの「公式ファームウェア（V15）に戻す」を使い、M-VAVEが配布する未変更の`FM-1.fwsc`を選ぶ。M-VAVE公式のM-UPGRADEも選択肢。作業前に公式配布物と対象機種を確認する。実機での復元手順は今回未検証。
