# Long-document visual research pipeline

Run commands from this skill's `scripts/` folder. The companion files are [maison_visuals.py](../scripts/maison_visuals.py), [requirements.txt](../scripts/requirements.txt), and [maison-brief.json](../scripts/maison-brief.json).

Contents: Install; Commands; Local Visual Atelier; Optional stock research; Image quality and publication; Free hosting; Verification.

Turn a long local research PDF into a searchable, page-linked content index, an original-image inventory, a visual storyboard, and render briefs. Keep the private archive separate from the public website.

## Install on Windows

Install Python 3.10 or later. In PowerShell, from this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe maison_visuals.py analyze "C:\path\archive.pdf" --out "C:\path\private-output"
.\.venv\Scripts\python.exe maison_visuals.py plan "C:\path\private-output\research-index.json" --brief maison-brief.json --out "C:\path\private-output\website-plan.json"
```

macOS/Linux: use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, and `.venv/bin/python` for the commands below. No paid API or hosted language model is needed for local analysis. Text windows use explainable BM25 lexical ranking, not model embeddings or an automatic factual review.

## Commands

```text
python maison_visuals.py analyze archive.pdf --out private-output --thumbs 48
python maison_visuals.py search private-output/research-index.json "water irrigation landscape"
python maison_visuals.py plan private-output/research-index.json --brief maison-brief.json --out private-output/website-plan.json
python maison_visuals.py extract archive.pdf --index private-output/research-index.json --ids pdf-182 --out private-originals
python maison_visuals.py audit original.jpg --out image-audit.json
python maison_visuals.py variants original.jpg --out web-variants
python maison_visuals.py gate asset-manifest.json --hero
```

Choose `pdf-...` IDs from your own index; the example ID is not portable across PDFs. Extraction validates the source PDF's SHA-256 before using an xref. Original image bytes and any separate soft mask are retained. Thumbnails are only review aids.

## Local Visual Atelier

Open [the standalone Maison Noire Visual Atelier](../assets/visual-atelier/index.html) from your local skill installation in a current desktop browser. Double-click `assets/visual-atelier/index.html`; no server, npm installation, API key, account, or internet connection is needed. Download/clone the repository first: GitHub's source-code page is not the application. Keep this research tool separate from the public Maison Noire website project.

1. Choose **Import research index** and select the `research-index.json` produced by `analyze` (version 1, up to 96 MiB). It includes private text and raster thumbnails. The six editorial sections come directly from `scripts/maison-brief.json` at build time. **Explore a fictional sample** demonstrates the tool without a real archive.
2. In **Evidence**, use the theme's suggested lexical matches, search the entire archive with your own words, enter a page number such as `p. 401`, or select **Entire archive** to browse every passage. Click a page reference or **Browse pages** to inspect full extracted text, OCR flags, embedded-image references, and source URLs as non-navigating reference text. **Browse pages** also works when scans have no extracted passages. This is a text/source inspector, not a PDF renderer. Read the original PDF separately when necessary.
3. In **Image library**, filter by 4K canvas in either orientation, 4K landscape, 4K portrait, or available thumbnails. Dimensions are recalculated from the index's width/height, rather than trusting its qualification flags. A thumbnail is never treated as an original. A wide, short strip is not 4K, and a portrait is not a landscape hero.
4. Choose **Pair imagery** on a passage, inspect a candidate image, and save its editorial section, proposed role, linked passages, private notes, and optional unapproved caption. The initial image filter shows references from the passage's page; disable **Theme evidence pages** to explore other images. Same-page references are suggestions, not evidence of relevance or display. A candidate can link multiple passages and belong to multiple editorial sections. Selection never changes its archive provenance.
5. Use **Selection board** to edit/remove connections across all sections. **Export manifest** downloads `maison-visual-manifest.json`, containing selected exact passages, image IDs/xrefs, source page references, pixel metadata, editorial proposals, notes, and the source document SHA-256. It does not include image bytes or thumbnails. **Resume review** restores a manifest after you import the matching source index; a mismatched document is refused. Resume replaces the current selections after a local confirmation. Export first if you want both versions.

All imported content and review choices stay in memory in this browser tab. There are no uploads, analytics, external fonts, remote image URLs, browser storage, or external requests. Raster data thumbnails are the only accepted imported previews. All text uses DOM text nodes. A hash-based Content Security Policy independently blocks connections, remote images/scripts, forms, frames, and workers. Reloading or **Clear session** clears imported research. An export is the explicit local persistence mechanism; it contains confidential selected research and must stay private. Opening the local tool on a shared computer does not provide access control for the files on that computer.

Every export sets `rightsReviewed`, `visualReviewed`, `publicApproved`, `historicalClaimsApproved`, and `dimensionsVerifiedFromBytes` to **false**. Proposed roles do not relabel archive exhibits as actual-property photography. Imported approval flags and altered quotes are discarded; exact quotes are rebuilt from the current index. The existing CLI `gate` rejects the review manifest until a separate publication review creates an approved asset manifest. A 4K metadata threshold does not establish native detail, original-file dimensions, rights, historical accuracy, designation status, or public suitability.

The viewer is built from its template, scoped CSS, pure JavaScript data layer, UI code, fictional sample, and the canonical editorial brief. Rebuild after changing any source:

```text
python build_atelier.py
python build_atelier.py --check
node --test tests/atelier-core.test.cjs
```

The generated HTML is committed so installed skill copies run directly from disk. The builder uses only Python's standard library and emits exact script/style CSP hashes. System serif/sans fonts provide an offline fallback; the public website's Cormorant Garamond / Manrope brief remains unchanged.

The index flags image-heavy pages with little extracted text for OCR review. It does not invent text from scans or certify OCR accuracy. If needed, use an approved local OCR workflow, inspect its output, and analyze the resulting searchable PDF again. Maps, facsimiles and old photographs remain dated evidence, not current marketing photography.

## Optional free stock-image research

Get a Pexels API key through its official service and set `PEXELS_API_KEY` locally. Never commit it. Search only generic, approved visual descriptors; do not send private archive excerpts as queries.

```text
python maison_visuals.py research "limestone courtyard architecture" --allow-external-query --out candidates.json
python maison_visuals.py download candidates.json --out stock-originals --limit 3
```

This is a ranked research starting point, not a claim to have searched every image on the internet. Provider results initially carry reported dimensions; downloaded originals are decoded and measured. Downloads select candidates with a 4K-sized canvas. The free API has its own request limits and attribution conditions; retain required Pexels/photographer credits. General image licence terms and API conditions differ. No API credentials were available for a live end-to-end Pexels test during preparation; that path needs your key.

Use stock for material or atmosphere. Never label another property as Maison Noire. For original property photography, obtain approved source files from the owner/photographer. For proposed renders, supply real reference photographs when identity must be preserved and retain an adjacent concept label.

## Image quality and publication

`native4kCanvas` means stored pixels meet 3840×2160 in either orientation. It is a pixel threshold, not proof the source was never enlarged. `landscape4kHero` requires actual width ≥3840 and height ≥2160. Very wide short images do not qualify. The pipeline never enlarges a file to pretend it has native detail; web derivatives never exceed source width.

Resolution, relevance, crop/composition, colour, sharpness, provenance and legal usage all matter. `edgeEnergyDiagnostic` is not an aesthetic score. Review assets visually before selection. Publication checks require explicit rights, visual and public-content approval. Concept images need captions; API assets need required credits; scans and texture maps cannot pass as an actual-property hero.

The included `maison-brief.json` maps six editorial themes to evidence queries, safe generic visual queries, display/body typography, and render directions. It is a proposal; no property specifications or designation findings are inferred from it.

## Free hosting

Recommended target: **Cloudflare Pages**, project name `maisonnoirelhx`, desired URL `https://maisonnoirelhx.pages.dev`. Availability is confirmed only when Cloudflare creates the project; a name collision may add a suffix. The static build can use your own HTML/CSS with no free-plan badge or ads. The `.pages.dev` provider suffix remains visible in the address. A separately registered custom domain is not included.

For a buildless website, prepare a `dist/` export containing static HTML/CSS/JS. The skill itself contains the research pipeline; a website export is a separate deliverable. Create a Cloudflare Pages Direct Upload project, choose the name above if available, and upload only `dist/`. Do not upload this repository root, the source archive, `private-output`, indexes, financial records, or environment files. The archive's originals/index are private research materials. Before a public launch, review all selected copy and images.

Cloudflare currently documents 500 builds/month on its Free plan, free/unlimited static asset requests, and a 25 MiB per-file limit. Keep deployment static; adding paid server features or other providers can change costs. No Cloudflare account was connected or project reserved by this package. The free private Sites preview is a separate hosted output, not proof that the Pages address is registered.

Official references checked 23 October 2026:

- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/pages/platform/limits/
- https://developers.cloudflare.com/pages/functions/pricing/
- https://www.pexels.com/api/documentation/
- https://www.pexels.com/license/
- https://polyhaven.com/license
- https://github.com/google/fonts

## Verification

Run `python -m unittest discover -s tests -v` and `node --test tests/atelier-core.test.cjs`. Tests cover 401-page ingestion, page-linked search, pixel/crop rules, preventing enlargement, publication boundaries, external-query/host restrictions, viewer/brief build parity, CSP hashes, hostile thumbnail inputs, and manifest round trips. Node 22 is used in CI; the browser is a development-only test dependency.

For the actual offline browser journey, from the repository root:

```bash
npm ci --ignore-scripts --prefix .agents/skills/website-development/scripts/tests/browser
npm exec --prefix .agents/skills/website-development/scripts/tests/browser -- playwright install --with-deps --only-shell chromium
node --test --test-concurrency=1 .agents/skills/website-development/scripts/tests/browser/atelier-browser.test.cjs
```

Install the Python pipeline dependencies first for the browser test that generates a synthetic 401-page archive. Browser tests cover local-file launch/import, search and page navigation, filters, pairing, export/resume, rejected imports, markup injection, network isolation, reload clearing, keyboard controls, and responsive widths. Set `ATELIER_SCREENSHOTS` to a local output directory to capture fictional-fixture screenshots. Screenshots are not committed. These checks are not a full security or accessibility audit.
