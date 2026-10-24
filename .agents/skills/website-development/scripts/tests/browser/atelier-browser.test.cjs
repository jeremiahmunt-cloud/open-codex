const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const {chromium} = require('playwright');
const assets = path.resolve(__dirname, '../../../assets/visual-atelier');
const url = pathToFileURL(path.join(assets, 'index.html')).href;
const source = JSON.parse(fs.readFileSync(path.join(assets, 'sample-index.json'), 'utf8'));
const C = require(path.join(assets, 'atelier-core.js'));
const brief = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../../maison-brief.json'), 'utf8'));
let browser;
before(async () => {
  browser = await chromium.launch({headless:true, ...(process.env.ATELIER_BROWSER_EXECUTABLE ? {executablePath:process.env.ATELIER_BROWSER_EXECUTABLE} : {})});
});
after(async () => { if (browser) await browser.close(); });

async function open(t, viewport = {width:1440,height:1000}) {
  const context = await browser.newContext({viewport, acceptDownloads:true, reducedMotion:'reduce'});
  const page = await context.newPage();
  const remote = []; const errors = [];
  await context.route('**/*', (route) => {
    if (/^https?:/i.test(route.request().url())) { remote.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  page.on('request', (request) => { if (/^https?:/i.test(request.url())) remote.push(request.url()); });
  page.on('pageerror', (error) => errors.push(error.message));
  t.after(async () => { await context.close(); assert.deepEqual(remote, [], 'The viewer attempted an external request'); assert.deepEqual(errors, [], 'Unexpected browser exception'); });
  await page.goto(url);
  await page.locator('#section-title').waitFor();
  assert.equal(await page.locator('#section-nav button').count(), 6);
  return page;
}
async function upload(page, data = source, field = '#index-file') {
  await page.locator(field).setInputFiles({name: field === '#index-file' ? 'research-index.json' : 'maison-visual-manifest.json', mimeType:'application/json', buffer:Buffer.from(JSON.stringify(data))});
}
async function imported(page, data = source) {
  await upload(page, data);
  await page.locator('#archive-bar:not([hidden])').waitFor();
}
async function waitNotice(page, fragment) {
  await page.waitForFunction((text) => document.getElementById('notice').textContent.includes(text), fragment);
}
async function exportReview(page) {
  const pending = page.waitForEvent('download');
  await page.locator('#export-manifest').click();
  const download = await pending;
  assert.equal(download.suggestedFilename(), 'maison-visual-manifest.json');
  return JSON.parse(await fsp.readFile(await download.path(), 'utf8'));
}
async function selectFirst(page) {
  await page.locator('#tab-images').click();
  await page.locator('[data-image-id="pdf-demo-1"] [data-action="candidate"]').click();
  await page.locator('#candidate-note').fill('Private composition note.');
  await page.locator('#save-candidate').click();
}

test('opens directly from disk, supports keyboard navigation, and clears imported data on reload', async (t) => {
  const page = await open(t);
  assert.equal(await page.locator('#export-manifest').isDisabled(), true);
  const chooser = page.waitForEvent('filechooser');
  await page.getByRole('button', {name:'Import research index'}).focus();
  await page.keyboard.press('Enter');
  await (await chooser).setFiles({name:'research-index.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(source))});
  await page.locator('#archive-bar:not([hidden])').waitFor();
  await page.reload();
  await page.getByRole('button', {name:'Explore a fictional sample'}).click();
  assert.match(await page.locator('#archive-label').textContent(), /FICTIONAL SAMPLE/);
  await page.locator('#tab-evidence').focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#tab-images').getAttribute('aria-selected'), 'true');
  await page.keyboard.press('End');
  assert.equal(await page.locator('#tab-review').getAttribute('aria-selected'), 'true');
  await page.keyboard.press('/');
  assert.equal(await page.locator('#search-input').evaluate((e) => e === document.activeElement), true);
  await page.reload();
  assert.equal(await page.locator('#archive-bar').isHidden(), true);
  assert.equal(await page.locator('#search-input').isDisabled(), true);
});

test('imports a local file, searches all passages, and opens full page text and source references', async (t) => {
  const page = await open(t); await imported(page);
  await page.locator('#search-input').fill('water irrigation');
  assert.equal(await page.locator('.evidence-card').count(), 1);
  await page.locator('.evidence-card .page-link').click();
  await page.locator('#page-dialog[open]').waitFor();
  assert.match(await page.locator('#page-dialog-title').textContent(), /Page 3/);
  assert.match(await page.locator('.page-text').textContent(), /Salt River Project/);
  assert.equal(await page.locator('.source-reference a').count(), 0);
  await page.locator('#page-jump').fill('6');
  await page.locator('#page-jump').press('Tab');
  assert.match(await page.locator('#page-dialog-title').textContent(), /Page 6/);
  assert.equal(await page.locator('#next-page').isDisabled(), true);
  await page.locator('#previous-page').click();
  assert.match(await page.locator('#page-dialog-title').textContent(), /Page 5/);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#page-dialog').isHidden(), true);
  assert.equal(await page.locator('.evidence-card .page-link').evaluate((e) => e === document.activeElement), true);
  await page.locator('#search-input').fill('nohitszyxwvu');
  assert.match(await page.locator('#view-panel').textContent(), /No matching evidence/);
  await page.getByRole('button',{name:'Browse the entire archive'}).click();
  assert.equal(await page.locator('.evidence-card').count(), 6);
});

test('filters real index dimensions without mistaking a portrait or wide strip for a landscape hero', async (t) => {
  const page = await open(t); await imported(page);
  await page.locator('#tab-images').click();
  assert.equal(await page.locator('.image-card').count(), 6);
  await page.locator('#quality-filter').selectOption('4k');
  assert.equal(await page.locator('.image-card').count(), 3);
  await page.locator('#quality-filter').selectOption('landscape');
  assert.equal(await page.locator('.image-card').count(), 2);
  await page.locator('#quality-filter').selectOption('portrait');
  assert.deepEqual(await page.locator('.image-card').evaluateAll((items) => items.map((i) => i.dataset.imageId)), ['pdf-demo-2']);
  await page.locator('#search-input').fill('nonexistentimage');
  assert.match(await page.locator('#view-panel').textContent(), /No images in this view/);
  await page.getByRole('button',{name:'Reset image filters'}).click();
  assert.equal(await page.locator('.image-card').count(), 6);
});

test('source pages remain inspectable when OCR produces no passages or images', async (t) => {
  const raw = structuredClone(source);
  raw.pages = [{page:1,section:'Fictional scanned page',text:''}];
  raw.chunks = []; raw.images = []; raw.sourceLinks = [];
  raw.stats.pagesNeedingOcrCheck = [1];
  const page = await open(t); await imported(page,raw);
  await page.getByRole('button',{name:'Browse pages'}).click();
  assert.match(await page.locator('.page-text').textContent(), /No text extracted/);
  assert.match(await page.locator('#page-dialog-body .review-warning').textContent(), /OCR review/);
  assert.equal(await page.locator('#previous-page').isDisabled(), true);
  assert.equal(await page.locator('#next-page').isDisabled(), true);
});

test('pairs exact passages with imagery, edits notes, exports, and resumes a review without granting approvals', async (t) => {
  const page = await open(t); await imported(page);
  await page.locator('[data-action="section"][data-value="water"]').click();
  await page.locator('#search-input').fill('water irrigation');
  await page.locator('.evidence-card [data-action="pair"]').click();
  assert.equal(await page.locator('.image-card').count(), 1);
  await page.locator('.image-card [data-action="candidate"]').click();
  assert.match(await page.locator('#linked-evidence').textContent(), /p0003-0000/);
  await page.locator('#candidate-note').fill('Pair the passage with a clearly labelled proposal.');
  await page.locator('#candidate-caption').fill('Concept direction only; not existing conditions.');
  await page.locator('#save-candidate').click();
  await page.locator('#tab-review').click();
  assert.equal(await page.locator('.review-entry').count(), 1);
  const manifest = await exportReview(page);
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.assets[0].associations[0].evidence[0].quote, source.chunks[2].text);
  assert.equal(manifest.assets[0].associations[0].evidence[0].page, 3);
  for (const key of ['publicApproved','rightsReviewed','visualReviewed','dimensionsVerifiedFromBytes','historicalClaimsApproved']) assert.equal(manifest.assets[0][key], false);
  manifest.assets[0].publicApproved = true;
  manifest.assets[0].associations[0].evidence[0].quote = 'Forged quote';
  await page.reload(); await imported(page);
  await upload(page, manifest, '#manifest-file');
  await page.locator('.review-entry').waitFor();
  const restored = await exportReview(page);
  assert.equal(restored.assets[0].publicApproved, false);
  assert.equal(restored.assets[0].associations[0].evidence[0].quote, source.chunks[2].text);
});

test('one image can serve multiple editorial sections and each connection can be removed', async (t) => {
  const page = await open(t); await imported(page); await selectFirst(page);
  await page.locator('[data-action="section"][data-value="water"]').click();
  await page.locator('[data-image-id="pdf-demo-1"] [data-action="candidate"]').click();
  await page.locator('#candidate-role').selectOption('material-mood');
  await page.locator('#candidate-evidence').selectOption('p0003-0000');
  await page.locator('#save-candidate').click();
  const manifest = await exportReview(page);
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.assets[0].associations.length, 2);
  await page.locator('#tab-review').click();
  await page.locator('.review-entry [data-action="remove"]').first().click();
  assert.equal(await page.locator('.review-entry').count(), 1);
  await page.locator('.review-entry [data-action="edit-candidate"]').click();
  await page.locator('#linked-evidence [data-action="unlink"]').click();
  await page.locator('#save-candidate').click();
  assert.match(await page.locator('.review-entry').textContent(), /No evidence linked/);
});

test('invalid imports and mismatched review sources preserve the working session; replacement can be cancelled', async (t) => {
  const page = await open(t); await imported(page); await selectFirst(page);
  await page.locator('#index-file').setInputFiles({name:'broken.json',mimeType:'application/json',buffer:Buffer.from('{invalid')});
  await waitNotice(page, 'not valid JSON');
  assert.match(await page.locator('#notice').textContent(), /not valid JSON/);
  assert.equal(await page.locator('#review-count').textContent(), '1');
  const invalid = structuredClone(source); invalid.chunks[0].page = 999;
  await upload(page, invalid);
  await waitNotice(page, 'missing page');
  assert.match(await page.locator('#notice').textContent(), /missing page/);
  const manifest = await exportReview(page); manifest.sourceDocument.sha256 = 'f'.repeat(64);
  await upload(page, manifest, '#manifest-file');
  await waitNotice(page, 'different source document');
  assert.match(await page.locator('#notice').textContent(), /different source document/);
  assert.equal(await page.locator('#review-count').textContent(), '1');
  await upload(page);
  await page.locator('#confirm-dialog[open]').waitFor();
  await page.getByRole('button',{name:'Cancel', exact:true}).click();
  assert.equal(await page.locator('#review-count').textContent(), '1');
  await upload(page);
  await page.locator('#confirm-replace').click();
  await page.waitForFunction(() => document.getElementById('review-count').textContent === '0');
  assert.equal(await page.locator('#review-count').textContent(), '0');
});

test('untrusted research, image paths, and source URLs cannot create markup or external requests', async (t) => {
  const page = await open(t);
  const malicious = structuredClone(source);
  const payload = '<img src="https://example.invalid/leak" onerror="window.__injected=true">';
  malicious.document.filename = payload;
  malicious.pages[0].text = payload;
  malicious.chunks[0].text = 'Integrity material ' + payload;
  malicious.images[0].caption = payload;
  malicious.images[0].thumbnail = 'https://example.invalid/private-thumbnail';
  malicious.images[1].thumbnail = 'data:image/svg+xml;base64,' + Buffer.from('<svg onload="window.__injected=true"></svg>').toString('base64');
  malicious.images[2].thumbnail = 'data:image/png;base64,AAAA';
  malicious.sourceLinks = [{page:1,url:'javascript:window.__injected=true'}];
  await imported(page, malicious);
  await page.locator('#all-evidence').check();
  assert.match(await page.locator('#document-name').textContent(), /<img/);
  assert.equal(await page.locator('#document-name img, .evidence-text img').count(), 0);
  await page.locator('.evidence-card .page-link').first().click();
  assert.equal(await page.locator('.source-reference a').count(), 0);
  await page.keyboard.press('Escape');
  await page.locator('#tab-images').click();
  assert.equal(await page.locator('img[src^="https:"], img[src^="data:image/svg"]').count(), 0);
  await page.locator('[data-image-id="pdf-demo-3"] .no-thumbnail:not([hidden])').waitFor();
  assert.equal(await page.evaluate(() => window.__injected), undefined);
  assert.equal(await page.evaluate(() => localStorage.length), 0);
});

test('the CSP blocks script connections independently of the interface', async (t) => {
  const page = await open(t);
  const result = await page.evaluate(async () => {
    const violations = [];
    document.addEventListener('securitypolicyviolation', (e) => violations.push(e.effectiveDirective));
    try { await fetch('https://example.invalid/should-be-blocked'); } catch {}
    await new Promise((resolve) => setTimeout(resolve, 20));
    return violations;
  });
  assert.ok(result.includes('connect-src'));
});

test('imports an actual pipeline-generated 401-page index and paginates without losing page 401', async (t) => {
  const temp = await fsp.mkdtemp(path.join(os.tmpdir(), 'atelier-pipeline-'));
  t.after(() => fsp.rm(temp, {recursive:true,force:true}));
  const script = `
import sys, fitz, io
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, sys.argv[1])
from maison_visuals import analyze
root=Path(sys.argv[2]); document=fitz.open()
for n in range(401):
    p=document.new_page()
    p.insert_text((40,40), 'Unique irrigation evidence.' if n == 400 else 'Architectural design materials integrity.')
    if n in (0,400):
        image=Image.new('RGB',(3840,2160) if n==0 else (2160,3840),'#d4d8ca')
        ImageDraw.Draw(image).rectangle((100,100,1000,1800),fill='#5d6b56')
        stream=io.BytesIO(); image.save(stream,'PNG')
        p.insert_image(fitz.Rect(40,90,400,500),stream=stream.getvalue())
document.save(root/'fictional.pdf'); document.close()
analyze(root/'fictional.pdf',root/'index',2)
`;
  const result = spawnSync(process.env.PYTHON || 'python3', ['-c',script,path.resolve(__dirname,'../..'),temp],{encoding:'utf8'});
  assert.equal(result.status, 0, result.stderr);
  const data = JSON.parse(await fsp.readFile(path.join(temp,'index/research-index.json'),'utf8'));
  const page = await open(t); await imported(page, data);
  assert.equal(await page.locator('.evidence-card').count(), 24);
  await page.getByRole('button',{name:/Show 24 more/}).click();
  assert.equal(await page.locator('.evidence-card').count(), 48);
  await page.locator('#search-input').fill('irrigation');
  assert.equal(await page.locator('.evidence-card').count(), 1);
  await page.locator('.evidence-card .page-link').click();
  assert.match(await page.locator('#page-dialog-title').textContent(), /Page 401/);
  await page.keyboard.press('Escape');
  await page.locator('#tab-images').click();
  await page.locator('#search-input').fill('');
  assert.equal(await page.locator('.image-card').count(), 2);
  await page.locator('#quality-filter').selectOption('landscape');
  assert.equal(await page.locator('.image-card').count(), 1);
  assert.match(await page.locator('.image-card .dimensions').textContent(), /3,840 × 2,160/);
  await page.locator('#quality-filter').selectOption('portrait');
  assert.equal(await page.locator('.image-card').count(), 1);
  assert.match(await page.locator('.image-card .dimensions').textContent(), /2,160 × 3,840/);
  await page.waitForFunction(() => {const img=document.querySelector('.image-card img'); return img && img.complete && img.naturalWidth > 0;});
});

test('responsive layouts fit 390, 768, and 1440 pixels plus narrow 320 and 720 pixel viewports', async (t) => {
  const page = await open(t);
  for (const width of [390,768,1440]) {
    await page.setViewportSize({width,height:1000});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Empty layout overflow at ${width}`);
    if (width === 390) {
      assert.match(await page.locator('.import-panel p').innerText(), /json\.\s+Text/);
      assert.match(await page.locator('.import-panel p').innerText(), /thumbnails\s+stay/);
      assert.match(await page.locator('.empty-state p').innerText(), /evidence,\s+compare/);
    }
    if (process.env.ATELIER_SCREENSHOTS) {
      await fsp.mkdir(process.env.ATELIER_SCREENSHOTS,{recursive:true});
      await page.screenshot({path:path.join(process.env.ATELIER_SCREENSHOTS,`empty-${width}.png`),fullPage:true});
    }
  }
  await imported(page);
  await page.locator('#tab-images').click();
  for (const width of [390,768,1440,320]) {
    await page.setViewportSize({width,height:1000});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, `Gallery overflow at ${width}`);
    if (process.env.ATELIER_SCREENSHOTS) await page.screenshot({path:path.join(process.env.ATELIER_SCREENSHOTS,`gallery-${width}.png`),fullPage:true});
  }
  await page.setViewportSize({width:390,height:1000});
  await page.locator('.image-card [data-action="candidate"]').first().click();
  assert.equal(await page.locator('#candidate-dialog').evaluate((e) => e.scrollWidth <= e.clientWidth), true);
  await page.keyboard.press('Escape');
  await page.setViewportSize({width:720,height:500});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
});
