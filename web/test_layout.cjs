/* Optional browser layout smoke test for Japanese UI. Run from the repository
 * root after installing playwright-core separately, for example:
 * PLAYWRIGHT_CORE=/path/to/node_modules/playwright-core \
 * CHROME=/path/to/Chrome \
 * node web/test_layout.cjs
 * Screenshots and the measured result are written to docs/ja-ui-evidence/. */
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'docs', 'ja-ui-evidence');
fs.mkdirSync(out, { recursive: true });
const tabs = ['sound', 'sequencer', 'tracks', 'library', 'samples', 'projects', 'settings'];
const results = [];
function ensure(ok, reason) { if (!ok) throw new Error(reason); }

(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME });
  try {
    for (const width of [375, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 820 }, deviceScaleFactor: 1 });
      const url = pathToFileURL(path.join(root, 'web', 'editor.html')).href + '?mock=1#sound';
      await page.goto(url);
      ensure(await page.title() === 'SLOOP エディタ', 'Japanese editor title');
      await page.locator('#connect').click();
      await page.waitForFunction(() => document.querySelector('#status').textContent.includes('接続しました'));
      for (const tab of tabs) {
        await page.locator(`#tabs [data-tab="${tab}"]`).click();
        const report = await page.evaluate((tab) => {
          const rows = [...document.querySelectorAll(`#p-${tab} .row > span:first-child`)]
            .filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent);
          return {
            tab, lang: document.documentElement.lang, pageWidth: document.documentElement.scrollWidth,
            viewport: innerWidth, pageHeight: document.documentElement.scrollHeight,
            viewportHeight: innerHeight, visible: !document.querySelector(`#p-${tab}`).hidden,
            clippedParameterLabels: rows,
          };
        }, tab);
        ensure(report.visible && report.lang === 'ja', `Japanese ${tab} panel`);
        ensure(report.pageWidth <= report.viewport, `${width}px ${tab}: horizontal overflow ${report.pageWidth}`);
        ensure(!report.clippedParameterLabels.length, `${width}px ${tab}: clipped ${report.clippedParameterLabels}`);
        results.push({ width, ...report });
        if (width === 375)
          await page.screenshot({ path: path.join(out, `editor-${width}-${tab}.png`), fullPage: true });
        if (width === 1280 && tab === 'sound')
          await page.screenshot({ path: path.join(out, 'editor-1280-sound.png'), fullPage: true });
      }
      if (width === 375) {
        await page.locator('#tabs [data-tab="sound"]').click();
        ensure(await page.locator('.row > span').first().textContent() === 'アタック', 'Japanese descriptor');
        const tooltip = await page.locator('.row input[title]').first().getAttribute('title');
        ensure(tooltip && /[^\x00-\x7f]/.test(tooltip), 'Japanese parameter tooltip');
        let confirmText = '';
        page.once('dialog', async (d) => { confirmText = d.message(); await d.dismiss(); });
        await page.locator('#init').click();
        ensure(confirmText.includes('音色'), 'Japanese confirmation dialog');
        await page.locator('#lang').click();
        ensure(await page.title() === 'SLOOP Editor', 'English switching preserved');
        ensure(await page.locator('.row > span').first().textContent() === 'ATK', 'English descriptors restored');
      }
      await page.close();
    }
    const installer = fs.readFileSync(path.join(root, 'web', 'index_pkg.html'), 'utf8')
      .replace('/*META*/', '{pkg:"missing.fwsc",product:"FM-1",version:"test"}');
    const installerPath = path.join(root, 'build', 'installer-layout.html');
    fs.mkdirSync(path.dirname(installerPath), { recursive: true });
    fs.writeFileSync(installerPath, installer);
    const page = await browser.newPage({ viewport: { width: 375, height: 820 } });
    await page.goto(pathToFileURL(installerPath).href);
    ensure(await page.title() === 'SLOOP インストーラー', 'Japanese installer title');
    ensure(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'installer horizontal overflow');
    await page.screenshot({ path: path.join(out, 'installer-375.png'), fullPage: true });
    await page.locator('#lang').click();
    ensure(await page.title() === 'SLOOP installer', 'English installer switching preserved');
    const installerHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    results.push({ width: 375, tab: 'installer', visible: true, lang: 'ja', pageWidth: 375,
      viewport: 375, pageHeight: installerHeight, viewportHeight: 820 });
    fs.writeFileSync(path.join(out, 'browser-layout.json'), JSON.stringify(results, null, 2) + '\n');
    console.log(`Japanese browser layout: ${results.length} views, 375/1280px, no horizontal overflow or clipped parameter labels; tooltip, dialog and EN switch passed`);
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exitCode = 1; });
