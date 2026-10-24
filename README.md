# open-codex

Reusable Codex workflows for building polished, working websites.

The `website-development` skill covers discovery, visual direction, content and imagery, implementation, responsive and accessibility checks, and delivery. Luxury real estate is an optional profile; the same workflow supports service businesses, portfolios, landing pages, and internal dashboards.

## Use in this repository

Clone this repository, open it in Codex, and invoke the skill:

```text
Use $website-development to build a responsive website for [project].
Audience: [who it serves]. Primary action: [what visitors should do].
Use the existing stack and approved assets. Implement it and verify the main journey.
```

The skill is located at `.agents/skills/website-development/SKILL.md`. Current Codex discovery includes repository `.agents/skills` directories. Merely adding this repository to GitHub does not install the skill on every computer or in unrelated projects.

## Install for other projects

Choose one scope to avoid duplicate entries with the same skill name.

### Through Codex's skill installer

In Codex, request:

```text
Use $skill-installer to install the website-development skill from
https://github.com/jeremiahmunt-cloud/open-codex/tree/main/.agents/skills/website-development
```

Review the skill before enabling it. The installer chooses its supported destination. Newly added local skills are detected automatically; restart Codex if the entry does not appear.

### Windows PowerShell: manual user-wide installation

With Git installed, run from a directory where you want the checkout. If already cloned, enter that checkout instead of cloning again.

```powershell
git clone https://github.com/jeremiahmunt-cloud/open-codex.git
Set-Location open-codex
$skillSource = Join-Path (Get-Location) '.agents/skills/website-development'
$skillParent = Join-Path $env:USERPROFILE '.agents/skills'
$skillDestination = Join-Path $skillParent 'website-development'
if (Test-Path $skillDestination) { throw 'Skill already exists; review and back it up before updating.' }
New-Item -ItemType Directory -Force -Path $skillParent | Out-Null
Copy-Item -Recurse -Path $skillSource -Destination $skillDestination
```

Run these commands in the same environment where Codex runs. For Codex inside WSL, use the Linux commands inside WSL rather than installing only into the Windows profile.

### macOS / Linux / WSL: manual user-wide installation

```bash
git clone https://github.com/jeremiahmunt-cloud/open-codex.git
cd open-codex
python3 - <<'PY'
from pathlib import Path
import shutil
source = Path('.agents/skills/website-development')
destination = Path.home() / '.agents/skills/website-development'
if destination.exists() or destination.is_symlink():
    raise SystemExit('Skill already exists; review and back it up before updating.')
destination.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, destination)
print(f'Installed: {destination}')
PY
```

For project-only use, copy the entire `website-development` folder into the target repository's `.agents/skills/` directory instead. Preserve all relative paths. No Node packages or credentials are required to install the skill itself; each website has its own runtime requirements.

## Included package

| Path within the skill | Purpose |
| --- | --- |
| `SKILL.md` | Main workflow and trigger metadata |
| `agents/openai.yaml` | Codex display name, description, and invocation prompt |
| `references/design-and-architecture.md` | Stack selection and visual implementation |
| `references/luxury-real-estate.md` | Optional property presentation profile |
| `references/integrations.md` | Optional tools and safe data/service boundaries |
| `references/visual-production.md` | Image production and a reusable concept prompt |
| `references/quality-checklist.md` | Behavioral, visual, accessibility, and content checks |
| `references/examples.md` | Five reusable request examples |
| `assets/site-brief.md` | Project intake template |
| `assets/verification-handoff.md` | Evidence and delivery template |
| `assets/content-record.example.json` | Fictional property content and provenance example |
| `assets/editorial-tokens.css` | Optional scoped design-token starting point |
| `assets/visual-atelier/index.html` | Standalone local research viewer; open directly in a browser |
| `assets/visual-atelier/atelier-core.js` | Validated imports, search, image filtering, and review manifests |
| `scripts/build_atelier.py` | Dependency-free viewer build with the canonical editorial brief and CSP hashes |

The examples include a Blessed Homes AZ collection brief, a fictional residence, a ceramics studio, an internal dashboard, and a small site repair. All property fixture facts are synthetic or explicitly unknown. The package includes no private documents or actual property financial data. The tokens are illustrative, not an official brand standard.

The visual prompt can generate a concept hero when image generation is available. No generated bitmap is required to install or use the skill.

## Long-document visual research

The skill includes a local Python pipeline for long PDFs: page-linked text search, original-image extraction, 4K pixel checks, optional Pexels research/downloads, responsive derivatives, and a proposed visual storyboard. Confidential indexes stay separate from website exports.

The **Maison Noire Visual Atelier** is included at
`.agents/skills/website-development/assets/visual-atelier/index.html`.
Open that file locally in your browser, import `research-index.json`, inspect
page-linked evidence and extracted-image thumbnails, filter 4K candidates, and
connect passages to proposed imagery across the six editorial sections.
Export or resume a private visual review manifest with source hashes, exact
passages, notes, and candidate associations. Selection does not approve rights,
historical claims, or publication. The viewer makes no external requests and
retains imported data only until the tab reloads/closes. There is no server or
runtime dependency. It is separate from the public Maison Noire website.

The source, build decisions, and verification record are in
[the implementation notes](docs/visual-atelier.md). Rebuild the committed viewer
after editing its sources or `maison-brief.json`:

```bash
python3 .agents/skills/website-development/scripts/build_atelier.py
python3 .agents/skills/website-development/scripts/build_atelier.py --check
node --test .agents/skills/website-development/scripts/tests/atelier-core.test.cjs
```

See [the workflow and Windows instructions](.agents/skills/website-development/references/document-visual-pipeline.md). The script, dependency list, example brief, and focused tests are bundled in the skill's `scripts/` folder. Local analysis needs no paid API; live Pexels research needs your own free API key.

## Optional tools

The skill can use Context7, Writing Style, image generation, Amazing Drawing, Zillow, SharePoint, Upstash Redis, Presentations, Sites, and GitHub when they are available and useful. They are not mandatory dependencies. Installing this skill does not connect those services, provide a production backend, or authorize publishing.

## Verify or update the package

GitHub Actions runs the package validator and visual pipeline tests on pushes
and pull requests through [Validate package](.github/workflows/validate-package.yml). The `Package validator`
job uses Python 3.12, Node 22, and read-only repository permissions. It preserves the
dependency-free package check, installs the pipeline's declared PyMuPDF
and Pillow dependencies, and discovers its `unittest` suite. It also verifies
the generated viewer, runs dependency-free JavaScript tests, and installs the
locked development-only Playwright package and Chromium for offline browser tests.
The tests use synthetic fixtures and need no API keys or custom secrets. The official actions are pinned
to release commit SHAs. To make passing validation a merge requirement, require
`Package validator` in the
repository's branch protection or ruleset settings.

Run the dependency-free package smoke check from this repository:

```bash
python3 tools/check_package.py
```

On Windows, `py tools/check_package.py` is equivalent. This checks required files, this package's simple metadata layout, local reference links, JSON validity, and unfinished placeholders. It is not a general YAML schema validator or a website audit. The package was also checked with the skill creator's `quick_validate.py` during creation.

Run the complete visual pipeline test suite from the repository root with the
same commands used in CI:

```bash
python3 -m pip install -r .agents/skills/website-development/scripts/requirements.txt
python3 -m unittest discover -s .agents/skills/website-development/scripts/tests -v
```

This covers 401-page PDF ingestion, page-linked source traceability, 4K resolution
rules and preventing upscaling, publication restrictions, and external-request safeguards.

To run browser verification locally after the commands above:

```bash
npm ci --ignore-scripts --prefix .agents/skills/website-development/scripts/tests/browser
npm exec --prefix .agents/skills/website-development/scripts/tests/browser -- playwright install --with-deps --only-shell chromium
node --test --test-concurrency=1 .agents/skills/website-development/scripts/tests/browser/atelier-browser.test.cjs
```

Development-time dependency/browser installation uses the network. The viewer
and its imported research do not. Browser tests open the committed HTML with a
`file:` URL, reject any external request, and exercise a pipeline-generated
401-page fixture. The workflow also checks that the committed HTML matches its
sources and canonical editorial brief. Neither private indexes nor screenshots
belong in the repository or public website export.

After changing instructions, try a real website request and inspect its output. Keep factual data and external-service testing separate from synthetic examples. To update a manual installation, pull the reviewed repository changes, back up the installed folder, then replace that folder with the full updated package. Do not merge partial copies blindly.

## Format verification

Verified against the current official documentation on **October 23, 2026**:

- [Build skills](https://learn.chatgpt.com/docs/build-skills): required `name` and `description` frontmatter, supporting resources, optional `agents/openai.yaml`, invocation, and local discovery.
- [Codex skills documentation entry point](https://developers.openai.com/codex/skills/): currently redirects to the guide above.

Current documented local scopes are repository `.agents/skills/` and user `~/.agents/skills/`. Some installer/older Codex versions also use `~/.codex/skills/`; prefer the installed client's supported installer or the current documented paths rather than maintaining duplicate copies. UI metadata is optional; the core workflow is in `SKILL.md`.
