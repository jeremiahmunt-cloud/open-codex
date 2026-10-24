# Visual Atelier implementation and verification

## Brief

Build the missing private research and visual-selection interface inside the
canonical website-development skill. The audience is a researcher reviewing a
long local PDF index before proposing public website copy or imagery. The primary
journey is import → evidence → source page → image candidate → editorial
association → private review export. Resume an export against its matching index.

The public Maison Noire website is a separate project and is not modified.
No actual property claims, source archives, private passages, or project financial
data are bundled. The interactive sample and test fixtures are explicitly fictional.

## Scope and design decisions

- One self-contained static HTML file opens directly from disk. No server,
  database, authentication service, API key, npm runtime, or hosting is needed.
- Six editorial sections are generated from the existing `maison-brief.json`.
  The source brief remains the single authority for section names and directions.
- Warm ivory work surfaces, dark green navigation, restrained bronze accents,
  system serif display and system sans body typography. No external font requests.
- Evidence, image library, selection board, page inspector, and candidate editor
  provide the main views. Keyboard tabs, file controls, dialogs, focus states,
  reduced motion, empty/error states, and responsive layouts are included.
- Imports are validated before replacing the current workspace. Text is rendered
  with DOM text nodes; thumbnails must be raster base64 data. Search runs locally
  with precomputed lexical statistics; numbered pages remain traceable.
- Image quality filters recompute thresholds from stored width/height, distinguish
  landscape and portrait, and never infer visual quality or rights from pixels.
- An asset may have several section associations, each with exact source passage
  IDs, pages, text, notes, proposed roles, and a source SHA-256. The export contains
  selected private text but no image bytes or unselected archive contents.
- Imported approval flags are discarded. All export approval flags are false.
  Resumed quotes are rebuilt from the loaded index; document hashes must match.
  The CLI publication gate continues to reject an Atelier review export.
- Hash-based CSP blocks connections, remote media, forms, frames, workers, and
  unapproved scripts. The application uses no browser storage. Tab reload clears
  imported data; only an explicit downloaded manifest persists the review.

## Source and commands

Viewer sources live under
`.agents/skills/website-development/assets/visual-atelier/`.
`index.html` is generated and committed for immediate offline use. Edit the
template, CSS, JavaScript, fictional sample, or canonical brief; then run:

```bash
python3 .agents/skills/website-development/scripts/build_atelier.py
python3 .agents/skills/website-development/scripts/build_atelier.py --check
python3 tools/check_package.py
node --test .agents/skills/website-development/scripts/tests/atelier-core.test.cjs
python3 -m unittest discover -s .agents/skills/website-development/scripts/tests -v
```

The browser tests use a locked, development-only Playwright installation. See the
root README for installation and the exact CI commands. `ATELIER_SCREENSHOTS`
optionally writes screenshots of fictional fixtures to a local directory.
`ATELIER_BROWSER_EXECUTABLE` permits an already installed Chromium executable for
local verification. The default CI run uses Playwright's matching Chromium.

## Verification record

Verified locally on 24 October 2026 using Python 3.12.14, Node 24.22.1,
Playwright 1.62.1, and Chromium 153.0.8010.0 supplied through
`ATELIER_BROWSER_EXECUTABLE`. The normal CI configuration uses Node 22 and
Playwright's matching Chromium, installed by the workflow.

| Check | Result | Evidence and scope |
| --- | --- | --- |
| Package and skill validation | passed | `tools/check_package.py` and skill creator `quick_validate.py` |
| Standalone build | passed | Generated HTML matches its sources and all six canonical sections; all script/style CSP hashes match |
| JavaScript data operations | passed | 11 tests: validation, source search, quality filters, selection, export/resume, and hostile inputs |
| Python pipeline/build integration | passed | 7 tests: existing pipeline suite plus build parity, CSP, and publication-gate rejection |
| Actual browser journeys | passed | 11 tests opening a local `file:` URL, including a pipeline-generated 401-page PDF with actual 3840×2160 and 2160×3840 embedded rasters |
| Review and provenance | passed | Exact page/quote/hash retention, multiple editorial associations, notes/captions, export/resume, source mismatch rejection, false approval flags |
| Network and content boundaries | passed | Every browser scenario watches/rejects HTTP requests; none attempted. Separate CSP probe blocks `fetch`; markup/remote thumbnail inputs remain inert. No unexpected browser exceptions |
| Empty/error/OCR states | passed | Broken JSON and invalid references retain the current session; OCR-only pages remain inspectable; absent/broken previews have fallbacks |
| Keyboard/focus | passed | Keyboard file picker, tab arrow/Home/End controls, search shortcut, dialog Escape, and page-dialog focus restoration |
| Responsive visual review | passed | Inspected actual fictional-fixture screenshots at 1440, 768, and 390 px; candidate editor and selection board inspected on desktop/mobile. Automated overflow checks also cover 320 and 720 px |
| Independent realistic use | passed | Separate synthetic PDF with measured landscape/portrait images and exact associations across all six sections; no private archive accessed |
| Public deployment | not run | This is an offline research tool; no public site was changed or deployed |

All 29 automated tests passed locally. The existing push/pull-request workflow
now includes these checks and the standalone build check. Remote results appear
on the resulting commit's GitHub Actions checks. No screenshot, private index,
actual source document, or exported private manifest is committed.

These checks cover the workflows and boundaries listed above. Full screen-reader
testing, other browser engines, maximum-size import benchmarking, and a
comprehensive security/accessibility audit were not performed.
