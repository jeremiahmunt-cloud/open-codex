const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const assets = path.resolve(__dirname, '../../assets/visual-atelier');
const C = require(path.join(assets, 'atelier-core.js'));
const source = JSON.parse(fs.readFileSync(path.join(assets, 'sample-index.json'), 'utf8'));
const brief = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../maison-brief.json'), 'utf8'));
const copy = () => structuredClone(source);
const index = () => C.normalizeIndex(copy());
const candidate = (overrides = {}) => ({sectionId:'water', imageId:'pdf-demo-3', evidenceIds:['p0003-0000'], proposedRole:'concept-render', notes:'Review water context.', publicCaption:'Proposed concept; not existing conditions.', ...overrides});

test('loads the actual index schema, retains page references, and recomputes dimensions', () => {
  const raw = copy();
  raw.images[2].native4kCanvas = true;
  raw.images[1].landscape4kHero = true;
  raw.images[0].rightsReviewed = raw.images[0].publicApproved = true;
  const data = C.normalizeIndex(raw);
  assert.equal(data.pages.length, 6);
  assert.equal(data.images[2].native4kCanvas, false);
  assert.equal(data.images[1].landscape4kHero, false);
  assert.equal(data.images[0].publicApproved, undefined);
  assert.deepEqual(data.images[0].referencedOnPages, [1]);
});

test('rejects unsupported schemas, duplicate IDs, and dangling page references', () => {
  for (const mutate of [
    (d) => d.schemaVersion = 2,
    (d) => d.scope = 'public',
    (d) => d.document.sha256 = 'missing',
    (d) => d.pages.push(d.pages[0]),
    (d) => d.chunks.push(d.chunks[0]),
    (d) => d.images.push(d.images[0]),
    (d) => d.chunks[0].page = 999,
    (d) => d.images[0].referencedOnPages = [999],
    (d) => d.images[0].width = -1,
    (d) => d.images[0].height = Infinity,
  ]) {
    const raw = copy(); mutate(raw);
    assert.throws(() => C.normalizeIndex(raw));
  }
});

test('only accepts raster data thumbnails and never accepts a URL or SVG', () => {
  for (const unsafe of ['https://example.invalid/private', 'file:///secret.png', 'javascript:alert(1)', 'data:image/svg+xml;base64,PHN2Zz4=', 'data:text/html;base64,PGh0bWw+', 'data:image/png;base64,not base64', 'a'.repeat(800001)]) assert.equal(C.safeThumbnail(unsafe), null);
  assert.equal(C.safeThumbnail(source.images[0].thumbnail), source.images[0].thumbnail);
  const raw = copy(); raw.images[0].thumbnail = 'https://example.invalid/image.jpg';
  assert.equal(C.normalizeIndex(raw).images[0].thumbnail, null);
});

test('quality filters distinguish portrait, landscape, and very wide short images', () => {
  const data = index();
  assert.equal(C.filterImages(data, {quality:'4k'}).length, 3);
  assert.equal(C.filterImages(data, {quality:'landscape'}).length, 2);
  assert.equal(C.filterImages(data, {quality:'portrait'}).length, 1);
  assert.deepEqual(C.filterImages(data, {query:'pdf-demo-3'}).map((i) => i.id), ['pdf-demo-3']);
  assert.deepEqual(C.filterImages(data, {pages:new Set([3])}).map((i) => i.id), ['pdf-demo-3']);
  assert.equal(C.filterImages(data, {pages:new Set([3]), quality:'4k'}).length, 0);
});

test('search handles page numbers, exact source IDs, historical dates, and Unicode text', () => {
  const raw = copy(); raw.chunks[2].text += ' Cypress façade';
  const data = C.normalizeIndex(raw); const search = C.makeSearch(data);
  assert.equal(search('water irrigation')[0].page, 3);
  assert.equal(search('p. 6')[0].page, 6);
  assert.equal(search('1973')[0].page, 1);
  assert.equal(search('p0003-0000')[0].page, 3);
  assert.equal(search('façade')[0].page, 3);
  assert.equal(search('zyxwvu-nohits').length, 0);
  assert.equal(search('').length, data.chunks.length);
});

test('large archives search across all 401 pages without losing source traceability', () => {
  const raw = copy();
  raw.images = []; raw.sourceLinks = [];
  raw.pages = Array.from({length:401}, (_,n) => ({page:n+1, section:'Fictional archive', text:n === 400 ? 'Unique irrigation evidence.' : 'Building material study.'}));
  raw.chunks = raw.pages.map((p) => ({...p, id:`p${p.page}-0000`}));
  const data = C.normalizeIndex(raw);
  assert.equal(C.makeSearch(data)('irrigation')[0].page, 401);
});

test('candidate selection is idempotent within a theme and independent between themes', () => {
  const data = index(); const selections = new Map();
  C.saveCandidate(data, brief, selections, candidate());
  C.saveCandidate(data, brief, selections, candidate({notes:'Updated.'}));
  C.saveCandidate(data, brief, selections, candidate({sectionId:'architecture'}));
  assert.equal(selections.size, 2);
  assert.equal(selections.get(C.selectionKey('water','pdf-demo-3')).notes, 'Updated.');
  assert.throws(() => C.saveCandidate(data, brief, selections, candidate({evidenceIds:['missing']})));
  assert.throws(() => C.saveCandidate(data, brief, selections, candidate({sectionId:'missing'})));
  assert.throws(() => C.saveCandidate(data, brief, selections, candidate({imageId:'missing'})));
  assert.throws(() => C.saveCandidate(data, brief, selections, candidate({proposedRole:'approved-photo'})));
});

test('export deduplicates assets, retains exact source passages, and cannot approve anything', () => {
  const data = index(); const selections = new Map();
  C.saveCandidate(data, brief, selections, {...candidate(), publicApproved:true});
  C.saveCandidate(data, brief, selections, candidate({sectionId:'architecture'}));
  const manifest = C.exportManifest(data, brief, selections, new Date('2026-01-01T00:00:00Z'));
  assert.equal(manifest.scope, 'private-review');
  assert.equal(manifest.editorialSections.length, 6);
  assert.equal(manifest.assets.length, 1);
  assert.equal(manifest.assets[0].associations.length, 2);
  assert.equal(manifest.assets[0].associations[0].evidence[0].quote, data.chunks[2].text);
  assert.equal(manifest.assets[0].associations[0].evidence[0].documentSha256, data.document.sha256);
  for (const key of ['rightsReviewed','visualReviewed','publicApproved','historicalClaimsApproved','dimensionsVerifiedFromBytes']) assert.equal(manifest.assets[0][key], false);
  assert.equal(manifest.assets[0].thumbnail, undefined);
  assert.equal(manifest.assets[0].kind, 'archive-exhibit-unreviewed');
});

test('review round-trip restores choices and uses original quotes, never imported approvals', () => {
  const data = index(); const selections = new Map();
  C.saveCandidate(data, brief, selections, candidate());
  const manifest = C.exportManifest(data, brief, selections);
  manifest.assets[0].publicApproved = true;
  manifest.assets[0].rightsReviewed = true;
  manifest.assets[0].associations[0].evidence[0].quote = 'An invented historical conclusion.';
  const restored = C.importManifest(manifest, data, brief);
  const exported = C.exportManifest(data, brief, restored);
  assert.equal(exported.assets[0].publicApproved, false);
  assert.equal(exported.assets[0].associations[0].evidence[0].quote, data.chunks[2].text);
  manifest.sourceDocument.sha256 = 'f'.repeat(64);
  assert.throws(() => C.importManifest(manifest, data, brief), /different source/);
});

test('rejects forged associations, missing evidence, and mismatched evidence pages', () => {
  const data = index(); const selections = new Map();
  C.saveCandidate(data, brief, selections, candidate());
  for (const mutate of [
    (d) => d.assets[0].id = 'missing',
    (d) => d.assets[0].associations[0].sectionId = 'missing',
    (d) => d.assets[0].associations[0].evidence[0].page = 99,
    (d) => d.assets[0].associations[0].evidence[0].chunkId = 'missing',
    (d) => d.assets[0].associations.push(d.assets[0].associations[0]),
  ]) {
    const manifest = C.exportManifest(data, brief, selections); mutate(manifest);
    assert.throws(() => C.importManifest(manifest, data, brief));
  }
});

test('empty archives remain searchable and export no invented findings', () => {
  const raw = copy(); raw.pages=[]; raw.chunks=[]; raw.images=[]; raw.sourceLinks=[];
  const data = C.normalizeIndex(raw);
  assert.deepEqual(C.makeSearch(data)('water'), []);
  assert.deepEqual(C.filterImages(data), []);
  assert.deepEqual(C.exportManifest(data, brief, new Map()).assets, []);
});
