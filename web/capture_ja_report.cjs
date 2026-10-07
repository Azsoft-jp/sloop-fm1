/* Reproduce mobile scroll GIFs for docs/ja-ui-report.html.
 * PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome \
 * node web/capture_ja_report.cjs
 * Requires ffmpeg on PATH. Uses the Editor's existing mock connection and
 * an installer fixture; captures only browser UI, never device hardware. */
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'docs', 'ja-ui-evidence');
const tabs = ['sound', 'sequencer', 'tracks', 'library', 'samples', 'projects', 'settings'];
const viewport = { width: 375, height: 820 };
fs.mkdirSync(out, { recursive: true });

async function capture(page, label, frameRoot) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const maxScroll = Math.max(0, height - viewport.height);
  if (!maxScroll) return { label, height, frames: 0, gif: null };
  const frameDir = path.join(frameRoot, label);
  fs.mkdirSync(frameDir, { recursive: true });
  const steps = Math.max(7, Math.min(15, Math.ceil(maxScroll / 115)));
  let index = 0;
  for (let step = 0; step <= steps + 2; step++) {
    const y = step >= steps ? maxScroll : Math.round(maxScroll * step / steps);
    await page.evaluate((value) => window.scrollTo(0, value), y);
    await page.waitForTimeout(80);
    await page.screenshot({ path: path.join(frameDir, `${String(index++).padStart(3, '0')}.png`) });
  }
  const gif = `scroll-${label}.gif`;
  const result = spawnSync('ffmpeg', [
    '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '4',
    '-i', path.join(frameDir, '%03d.png'),
    '-filter_complex', '[0:v]split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer',
    '-loop', '0', path.join(out, gif),
  ], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`ffmpeg ${label}: ${result.stderr || result.error}`);
  return { label, height, frames: index, gif };
}

(async () => {
  const frameRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'sloop-ja-scroll-'));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME });
  try {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 1, reducedMotion: 'reduce' });
    await page.goto(pathToFileURL(path.join(root, 'web', 'editor.html')).href + '?mock=1#sound');
    await page.locator('#connect').click();
    await page.waitForFunction(() => document.querySelector('#status').textContent.includes('接続しました'));
    const results = [];
    for (const tab of tabs) {
      await page.locator(`#tabs [data-tab="${tab}"]`).click();
      results.push(await capture(page, tab, frameRoot));
    }
    await page.close();

    const installer = fs.readFileSync(path.join(root, 'web', 'index_pkg.html'), 'utf8')
      .replace('/*META*/', '{pkg:"missing.fwsc",product:"FM-1",version:"test"}');
    const fixture = path.join(frameRoot, 'installer.html');
    fs.writeFileSync(fixture, installer);
    const installPage = await browser.newPage({ viewport, deviceScaleFactor: 1, reducedMotion: 'reduce' });
    await installPage.goto(pathToFileURL(fixture).href);
    results.push(await capture(installPage, 'installer', frameRoot));
    await installPage.close();
    fs.writeFileSync(path.join(out, 'scroll-capture.json'), JSON.stringify({ viewport, results }, null, 2) + '\n');
    console.log(results.map(({ label, height, frames, gif }) => `${label}: ${height}px, ${frames} frames${gif ? `, ${gif}` : ', no scrolling'}`).join('\n'));
  } finally {
    await browser.close();
    fs.rmSync(frameRoot, { recursive: true, force: true });
  }
})().catch((e) => { console.error(e); process.exitCode = 1; });
