# Long-document visual research pipeline

Run commands from this skill's `scripts/` folder. The companion files are [maison_visuals.py](../scripts/maison_visuals.py), [requirements.txt](../scripts/requirements.txt), and [maison-brief.json](../scripts/maison-brief.json).

Contents: Install; Commands; Optional stock research; Image quality and publication; Free hosting; Verification.

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

Open the Maison Noire Visual Atelier and import `research-index.json`. The index includes private text and thumbnails. Its file picker reads locally in the browser tab; the site has no upload endpoint or persistent archive storage. The default hosted preview does not contain the private PDF or index. Reloading the tab clears imported data.

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

Run `python -m unittest discover -s tests -v`. Tests cover 401-page ingestion, page-linked search, pixel/crop rules, preventing enlargement, publication boundaries, and external-query/host restrictions. These are focused behavior tests, not a full security or accessibility audit.
