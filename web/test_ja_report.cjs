/* Check the standalone HTML report and its local image assets.
 * PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome \
 * node web/test_ja_report.cjs */
const path = require('node:path');
const fs = require('node:fs');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

(async () => {
  const evidence = path.resolve(__dirname, '..', 'docs', 'ja-ui-evidence');
  const manifest = JSON.parse(fs.readFileSync(path.join(evidence, 'lcd-manifest.json'), 'utf8'));
  const capture = JSON.parse(fs.readFileSync(path.join(evidence, 'scroll-capture.json'), 'utf8'));
  const gifCount = capture.results.filter((x) => x.gif).length;
  const expectedImages = 6 + manifest.length + 9 + gifCount;
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME });
  try {
    const url = pathToFileURL(path.resolve(__dirname, '..', 'docs', 'ja-ui-report.html')).href;
    for (const width of [375, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: 820 }, deviceScaleFactor: 1 });
      await page.goto(url);
      await page.evaluate(async () => {
        for (const img of document.images) {
          img.loading = 'eager';
          await img.decode();
        }
      });
      const result = await page.evaluate(() => ({
        title: document.title,
        viewport: innerWidth,
        pageWidth: document.documentElement.scrollWidth,
        images: document.images.length,
        broken: [...document.images].filter((img) => !img.complete || !img.naturalWidth).map((img) => img.src),
        gifs: [...document.images].filter((img) => img.src.endsWith('.gif')).length,
        nativeLcd: [...document.images].filter((img) => img.src.includes('/lcd/')).length,
        wrongLcdSize: [...document.images].filter((img) => img.src.includes('/lcd/') &&
          (img.naturalWidth !== 240 || img.naturalHeight !== 240)).map((img) => img.src),
        wrongGifSize: [...document.images].filter((img) => img.src.endsWith('.gif') &&
          (img.naturalWidth !== 375 || img.naturalHeight !== 820)).map((img) => img.src),
      }));
      if (result.pageWidth > width || result.broken.length || result.images !== expectedImages ||
          result.gifs !== gifCount || result.nativeLcd !== manifest.length + 6 || result.wrongLcdSize.length ||
          result.wrongGifSize.length)
        throw new Error(`${width}px report layout: ${JSON.stringify(result)}`);
      console.log(`${width}px: ${result.images} images (${result.nativeLcd} native LCD, ${result.gifs} GIFs), no broken images or horizontal overflow`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exitCode = 1; });
