/* Check the standalone HTML report and its local image assets.
 * PLAYWRIGHT_CORE=/path/to/playwright-core CHROME=/path/to/Chrome \
 * node web/test_ja_report.cjs */
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');

(async () => {
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
        wrongGifSize: [...document.images].filter((img) => img.src.endsWith('.gif') &&
          (img.naturalWidth !== 375 || img.naturalHeight !== 820)).map((img) => img.src),
      }));
      if (result.pageWidth > width || result.broken.length || result.gifs !== 7 || result.wrongGifSize.length)
        throw new Error(`${width}px report layout: ${JSON.stringify(result)}`);
      console.log(`${width}px: ${result.images} images (${result.gifs} GIFs), no broken images or horizontal overflow`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exitCode = 1; });
