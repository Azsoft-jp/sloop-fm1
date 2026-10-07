# SLOOP 日本語UI（Phase 1・2）実装記録

対象コミット: `d691ba7b2d922f1a1f41a3622cffe29ce41c5506` を起点とした変更。レビュー時には、差分とともに [`ja-ui-evidence/`](ja-ui-evidence/) の画像・ログを確認する。

画面付きのレビュー用資料は [`ja-ui-report.html`](ja-ui-report.html) と印刷用の [`ja-ui-report.pdf`](ja-ui-report.pdf)。Web Editorの7タブとインストーラーの静止画、縦スクロールがある7画面のGIF、FM-1本体の35画面、容量とテスト結果をまとめた。PDFは9ページで、35画面を個別画像として掲載し、GIFは開始・終了フレームと元GIFへのリンクを載せた。GIFの再生成は `web/capture_ja_report.cjs`、HTML内の画像・レイアウト確認は `web/test_ja_report.cjs` を使用する。

PDFの再生成は `tools/build_ja_ui_pdf.py` を使用する。Pythonの `reportlab`、`Pillow`、`fonttools` と、[SIL OFL 1.1のNoto Sans JP可変TTF](https://github.com/google/fonts/tree/main/ofl/notosansjp)を `build/deps/NotoSansJP-wght.ttf` に置き、`python tools/build_ja_ui_pdf.py` を実行する。スクリプトがウエイト500の静的TTFをローカル生成し、PDFには必要glyphのサブセットだけを埋め込む。PDFの9ページはPopplerでPNG化して目視確認し、[`pdf-validation.log`](ja-ui-evidence/pdf-validation.log)にページ数、文字抽出、35画面・8 Web画面・7 GIFへのリンク検査を記録した。

## 変更前の調査

### 確認済み事実

- 本体描画は `firmware/src/gfx.c` の小さなキャンバスに描いてLCDへ転送する方式。表示器は240×240ピクセル。`firmware/src/ui.c` は上部20px、4列各60pxの操作領域、グラフ、下部38pxを配置する。
- 英数字フォントは `assets/fonts/ter-u16n.bdf` 由来の小16px／大32px。`tools/gen_font.py` が `build/gen/felucca_font.h` を生成する。元の描画器は1バイトの文字値を参照し、UTF-8を解釈しなかった。
- 本体UI文字列は `ui_draw.c`、`ui_layers.c`、`ui_menu.c`、`ui_song.c`、`ui_studio.c`、`ui_input.c`、`project.c`、`upreset.c`、更新・復旧画面に分散していた。ページ名・パラメーター名は `params.c` などの機器プロトコル記述子も兼ねる。
- Web Editor は単一の `web/editor.html` に7タブ（音色、シーケンサー、トラック、ライブラリ、サンプル、プロジェクト、設定）と既存の `TEXT.ja/en`、`t()`、言語ボタンを持っていた。`web/index_pkg.html` も既存の `TEXT.ja/en` を持っていた。両ページには英語のままの静的表示・機器記述子が残り、初期言語は一部ブラウザー依存だった。
- 音声レンダリングは `firmware/src/audio.c` のDMA割り込みから `mix_block()` を呼び、UIは `firmware/src/main.c` のメインループから描画する。音声半バッファは256フレーム、44.1kHzで約5.8ms。既存コードには割り込み時間・取りこぼしを記録する `felucca_dbg.max_us` と `late` がある。
- ビルドは `sh build.sh`、ホストテストは `tests/run_tests.sh`（完成済みファームウェアを要求）、Webテストは `node web/test_web.mjs`。リポジトリに `.github/workflows` はない。ビルドはJieLiツールチェーン、AC79 SDKの3ファイル、macOSではDockerを要求する。今回これらを取得し、SDK 3ファイルのSHA-256を `tools/build.py` の既知値と照合した。
- `tools/build.py` はアプリスロット、RAM `.data+.bss` 96KiB、描画プール0x54000バイトと8KiB以上の余裕を検査する。

### 推測・設計判断

- 4列の各ラベル領域は最大54pxで、カタカナ3文字程度が限界。英字の技術名を残すほうが読める語がある。列で収まらない日本語は、途中で切る代わりに元の短い英字名を使う。
- スクロールは更新回数と状態管理を増やすため今回は不要と判断した。固定幅内で短縮・英字への復帰・説明行の言い換えで収めた。
- `ui_display_name()` はUI描画側のみで使い、音声割り込み・データ保存・SysExの識別子は変更しない。

### 未確認

- 実機LCDの発色、実機での日本語可読性、操作時の割り込み最大時間・取りこぼし、実機Flashへの書き込みと復旧操作。
- ターゲット命令予算の超過が実機の音切れに結びつくか。元コミットにも同じ超過があり、この変更で増えた値ではない。

## 実装

### 本体

- `firmware/src/ui_strings.def` に206個のIDと英語・日本語を一対で収録。`ui_strings.h` の `ui_text(ID)` が現在は日本語を返す。既存のページ・パラメーター記述子は `ui_display_name()` で描画時に変換し、通信や保存の識別子を維持する。
- `gfx.c` は境界検査付きの小型UTF-8デコーダー、疎なUnicode glyph検索、未収録・不正文字の `?` 表示、UTF-8文字境界を守るコピーと削除を追加。既存英数字の描画経路はそのまま使う。
- `tools/gen_font.py` は日本語リソースを走査し、実際に使う74文字だけを `FONT_J_CODE/OFF/DATA` に書く。16pxの2ビット階調glyphを1字80Bで記録し、小フォントで使い、大フォントでは描画時に2倍表示する。全面的なUnicodeフォントは組み込まない。原字形はOFLの `assets/fonts/NotoSansJP-ui.ttf`（使用文字に絞ったサブセット）とそのライセンスファイル。
- 収録glyph（コードポイント昇順）: `アィイウェエオカガキギクグケコサザシジスズセゼソゾタダチッツヅテデトドナニネノハバパヒビフブプヘベペホボポマミムメモャヤュユョヨラリルレロワヲン・ー`。`tests/check_ja_resources.py` がリソース使用文字との完全一致を検査する。
- 画面画像の再確認で、旧1bit fontの「ヘ」に最下段1行（13画素）の欠けを確認。描画位置を1px上げ、glyph生成時に上下のガード領域を検査するよう修正した。輪郭のギザつきを抑えるため2bit階調に変更し、使用文字数は増やしていない。これらはUI描画だけの変更で、音声割り込み・DSPは変更していない。
- メニュー、ホーム、各編集ページ、ライブ演奏、REC、ソング、ホールド操作、保存／読込通知、キャリブレーション、更新／復旧、クラッシュ表示を日本語化した。FX、BPM、MIDI、USB、REC、機器名、音色名などの短い技術表記は必要に応じて保持した。
- 狭い4列は `column_text()` で幅を確認し、日本語の語が丸ごと入らない場合は英字IDを使う。RECの右見出しは64px、説明行は176pxをテストで検査。メッセージは236pxまでにUTF-8文字単位で収める。自動スクロールは追加していない。

### Web Editor／インストーラー

- 既存の `TEXT.ja/en` と `t()` を拡充し、初期表示を日本語に固定した。画面上部、フッター、ファームウェア更新・公式FWへの復帰案内もリソース化。英語の言語ボタンと英語リソースは残した。
- `LABEL_JA`／`DISPLAY_LABELS` は機器のDESC／列挙値を表示時だけ翻訳する。送受信・保存データの英語ラベルは変えない。シーケンサーのステップ種別・ツールチップもこの境界で変換する。
- 375px幅で折り返していた短い見出しを簡潔にし、設定のシステム情報はラベルが1行で読める幅を確保した。プロトコル上の音色名、エンジン名、ファイル名は翻訳しない。

## 計測と検証

| 項目 | 変更前 | 変更後 | 根拠 |
| --- | ---: | ---: | --- |
| 英数字S bitmap | 21,504 B | 21,504 B | `tools/gen_font.py` の生成出力 |
| 英数字L bitmap | 24,576 B | 24,576 B | 同上 |
| 日本語bitmap | 0 B | 5,920 B（74字） | 同上。コード表・オフセット各148 Bは別 |
| FWアプリ `felucca.bin` | 550,256 B | 562,016 B（+11,760 B、+2.1%） | 同じツールチェーン・SDKで元コミットと今回版をビルド |
| アプリ領域の残量 | 31,308 B | 19,548 B | 領域581,564 Bからアプリサイズを減算 |
| ターゲットRAM `.data+.bss` | 72,720 B | 72,892 B（+172 B） | `tools/build.py` のリンカシンボル計測 |
| 描画プール使用量 | 322,272 B | 322,272 B | 同上。上限344,064 B |
| インストール用 `.fwsc` | 610,019 B | 610,019 B | 固定容量のパッケージ |
| `web/editor.html` 生HTML | 242,617 B | 245,961 B（+3,344 B） | `wc -c` と元コミット |
| `web/index_pkg.html` 生HTML | 19,241 B | 20,847 B（+1,606 B） | 同上 |

- [`firmware-build-baseline.log`](ja-ui-evidence/firmware-build-baseline.log)／[`firmware-build-ja.log`](ja-ui-evidence/firmware-build-ja.log): 両方のターゲットビルド、RAM・描画プール・アプリ領域検査はPASS。旧1bit版の圧縮検証ログは履歴として保存した。現在の2bit版は [`firmware-build-font-aa.log`](ja-ui-evidence/firmware-build-font-aa.log) でビルドと容量を再測定した。
- [`firmware-ui-font-aa.log`](ja-ui-evidence/firmware-ui-font-aa.log): ASCII、濁点・半濁点、長音、小文字、不正UTF-8、未収録glyph、UTF-8境界、画面外クリップ、主要メニューと操作、2万フレームのUI fuzzがPASS。
- [`song-ui-font-aa.log`](ja-ui-evidence/song-ui-font-aa.log): セクション保存・読込・上書き確認・描画境界がPASS。`ja-host.log` には音声、ドラム、シーケンサー、FX、プロジェクト、ユーザープリセットの6テストを収録。
- [`web-test.log`](ja-ui-evidence/web-test.log): Editorプロトコル、Samples、Projects、Backup、更新／公式FW復帰の既存テストを実行。
- [`browser-layout.json`](ja-ui-evidence/browser-layout.json) と画像: Chromeのモック機器で7タブ×375/1280px、インストーラー×375pxの15画面を検査。ページ全体の横はみ出しとパラメーター見出しのクリップなし。日本語ツールチップ・確認ダイアログ、英語切替も検査。画像はブラウザー描画およびホストLCDシミュレーターの出力で、実機写真ではない。
- [`font-before-after.png`](ja-ui-evidence/font-before-after.png) はコミット `1fe72d1` の旧1bitステップ画像を3分の1に戻した左側と、現2bit版の240px原寸画像を右側で比較。現在の[`lcd/`](ja-ui-evidence/lcd/)内の35枚は `tools/render_ui_evidence.py` でホストのPPMから240×240のPNGへ変換し、3倍拡大による見かけのジャギーを排除した。画像は実機写真ではない。
- 上記画像の再生成: `git show 1fe72d1:docs/ja-ui-evidence/page-step.png > build/page-step-before.png`、UIホストテストでPPMを更新後、`.venv/bin/python tools/render_ui_evidence.py build/host docs/ja-ui-evidence build/page-step-before.png` を実行する。
- [`full-tests-font-aa.log`](ja-ui-evidence/full-tests-font-aa.log) は `SOAK_MIN=1`（ソーク1分）で全ホストテストを実行した記録。保存／読込、更新、音声、Web等の各機能テストは通り、総合結果はCPU予算の既存超過によりFAIL。元コミットのターゲット命令予算も [`target-budget-baseline.log`](ja-ui-evidence/target-budget-baseline.log) で比較した。
- [`regress-font-aa.log`](ja-ui-evidence/regress-font-aa.log) と [`regress-baseline.log`](ja-ui-evidence/regress-baseline.log): 音声ゴールデン97件のハッシュは両方0件変更。両方で同じ3項目が既存CPU予算を超過し、最終測定の3項目は元コミットと同じ358／681／1,986命令/サンプル。[`target-budget-font-aa.log`](ja-ui-evidence/target-budget-font-aa.log) の `fm1_alnk0_irq` も元コミットと同じ255（既存予算174）。予算テスト全体を合格とは記録しない。
- 音声割り込み、DSP、MIDIタイミング、DMAのコードは変更していない。2bit化は既存のオフスクリーン描画だけに作用し、LCD転送サイズと更新回数は変えない。ターゲット音声割り込みの静的命令予算値は元コミットと同じ255。実機での無遅延は未確認。PRを実機で検証する際は `felucca_dbg.max_us` と `felucca_dbg.late` を日本語化前後・再生負荷別に比較する。
- `JIELI_TOOLCHAIN=<取得したツールチェーン> AC79_SDK=<検証済みSDKファイルの配置先> PYTHON=.venv/bin/python sh build.sh` はPASS。OTAパッケージ検査を含むテストを実行した。`git diff --check` はPASS。
- macOSのセクション属性だけを無効化した `cc -fsyntax-only -w '-D__attribute__(x)=' -Ibuild/gen -Ifirmware/hal -Ifirmware/src firmware/src/felucca.c` はPASS。これはターゲット用コンパイラ・リンカの代用ではない。

### 未対応・制限

- 固有名詞、音色・ドラムキット・ユーザープリセット名、パラメーターの短い英字、著作権表示は英語。プロトコル互換性と4列幅を優先した。
- FM-1は一般的な日本語入力や任意Unicodeを表示しない。未収録文字は `?`。本体の言語設定・永続化はPhase 3で行う。
- 実機のLCD・音声割り込みは本作業環境では測定できていない。上流への提案前に実機表示、録音・再生中の最大割り込み時間、音切れの有無を確認する。

## Phase 3で変更するファイルと処理

1. `firmware/src/ui_strings.h`: `Language` enumと `currentLanguage` を追加し、`ui_text()` が `ui_strings_en/ja` を選ぶようにする。`ui_display_name()` と描画コードはそのまま使う。
2. `firmware/src/ui_menu.c`／`ui_input.c`: 設定メニューの `LANG` 項目とEN/JA操作を追加。変更時に `ui.force=1` とし、画面キャッシュを再描画させる。
3. `firmware/src/project.c` または既存設定保存処理: `currentLanguage` を設定レコードへ追加し、旧バージョンの読み込み時は既定言語にフォールバックする。言語だけの変更が演奏中のFlash書き込みを誘発しないよう、既存の設定保存条件に従う。
4. `web/editor.html`／`web/index_pkg.html`: 既存の言語ボタンと `TEXT.en/ja` を維持し、必要なら選択言語をブラウザー内に保存する。機器への言語設定反映を導入する場合は既存プロトコルの拡張版として扱う。
5. `tests/ui_pages_test.c`／`web/test_layout.cjs`: 同じ画面を両言語で描画し、幅、切替直後のキャッシュ更新、旧設定の互換性を確認する。

## 元のファームウェアへ戻す

1. Web Editorの「プロジェクト」→「バックアップ」でFM-1の内容をファイルに保存する。公式FWはSLOOPの曲・音色・サンプルを読めない。
2. M-VAVE公式サイトからFM-1 V15を取得し、同梱の変更していない `FM-1.fwsc` をSLOOPインストーラーの「公式ファームウェア（V15）に戻す」に指定する。インストーラーがファイルを検証してから書き込む。`README.md` の「Going back」も参照。
3. SLOOPへ戻る場合は再インストール後、保存したバックアップをWeb Editorで復元する。実機への書き込み・復帰操作は今回行っていない。
