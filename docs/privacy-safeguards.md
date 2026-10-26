# Privacy safeguards

This public repository contains reusable skills and fictional demonstrations.
Keep original research, project records, lender data, extracted documents, and
credentials outside the checkout. These safeguards reduce accidental commits;
they do not establish that a document is public or authorized for publication.
The implementation and its tests use synthetic data; no private archive is needed.

## Check before committing

From the repository root, with Git and Python 3.10 or later:

```powershell
py -3 tools/check_privacy.py
py -3 tools/check_package.py
py -3 -m unittest discover -s tools/tests -v
```

On macOS/Linux/WSL, replace `py -3` with `python3`. The privacy checker needs
only Python's standard library and Git. It makes no network requests, opens no
working-tree research documents, and prints paths/reasons rather than file
contents. Paths are escaped to prevent control characters affecting terminal logs.
Exit codes are 0 for pass, 1 for policy violations, and 2 for invalid configuration
or a Git/runtime error. Use `--repo PATH` to inspect another checkout.

The checker reads **the entire Git index**, including previously tracked files
and new/staged changes, with NUL-delimited filenames. In CI this is the checked-out
commit; locally it is the snapshot Git would commit. It inspects indexed blobs,
not unstaged replacements. Staged removals are excluded so a prohibited file can
be untracked. Untracked/ignored files and arbitrary working-tree documents are
never scanned. An unreadable index, unresolved merge, symlink, or submodule fails
closed rather than leaving an unexamined file in the proposed snapshot.

## What is blocked

- Private directories (`private/`, `private-*`), research output/assets/archives,
  source documents, extracted documents/images/assets, OCR, thumbnails,
  stock originals, and web variants. Directory matches apply at any depth.
- Generated filenames such as `research-index*.json`,
  `maison-visual-manifest*.json`, `website-plan*.json`, `asset-manifest*.json`,
  `image-audit*.json`, `candidates*.json`, `variants.json`, and `pdf-<number>.*`.
  Prefix patterns also catch common copied/downloaded export names.
- PDF/Office documents, exported CSV/TSV records, mail exports, databases, and
  archives, pending explicit review as synthetic or reusable material.
- Environment files except the empty/template `.env.example`, credential
  directories, common account configuration, SSH key names, key/certificate
  containers, and credential JSON filenames. Keep real values out of examples too.
- Renamed JSON/JSONL/NDJSON containing private/confidential scope markers,
  document-index structures, or a Visual Atelier review manifest marker. Nested
  objects are inspected. Credential JSON structures such as service accounts,
  nonempty private keys, client secrets, access tokens, and refresh tokens are
  always blocked. JSON must use UTF-8 (an optional BOM is accepted). Malformed,
  duplicate-field, non-finite-number, or over-128-level JSON is rejected; field
  matching is case insensitive. JSON/review exceptions larger than 4 MiB are rejected
  rather than skipped. Non-JSON documents are classified by path, not opened.

`.gitignore` prevents normal accidental additions of those output/document/key
paths; it does not untrack existing files, stop `git add -f`, or implement the
JSON checks. The independent checker catches those cases and uses case-insensitive
path comparisons even when Git's ignore matching is case sensitive. Generic
source code, documentation, editorial briefs, reusable CSS/JS/HTML, and ordinary
public example JSON remain usable. Existing package/build/pipeline/viewer checks
continue to run separately.

## Documented synthetic and reusable exceptions

`tools/privacy-allowlist.json` contains **exact repository-relative paths**,
SHA-256 hashes of their indexed bytes, a `synthetic-fixture` or
`reusable-resource` kind, and a substantive reason for each exception. There are
no directory-wide or wildcard exemptions. Changing fixture bytes requires a new
review and hash. The initial exception is the existing fictional Atelier sample
index; its private schema is intentional and its text/illustrations are synthetic.

Only reviewed synthetic fixtures or legitimately reusable public resources may
receive exceptions. Do not use this mechanism to publish confidential records.
Credentials, reserved private/output directories, invalid/oversized JSON,
symlinks, and submodules cannot be exempted. Put approved examples under an
ordinary fixture/resource path instead. Remove an exception when removing its file.

For a reviewed new example, stage the file and hash the **indexed bytes**. This
avoids differences from Windows checkout line-ending conversion. Add its exact
path/hash/kind/reason to the entries array and stage the exception:

```powershell
git add -f -- tests/fixtures/synthetic-example.pdf
py -3 -c "import hashlib, subprocess; print(hashlib.sha256(subprocess.check_output(['git', 'show', ':tests/fixtures/synthetic-example.pdf'])).hexdigest())"
git add tools/privacy-allowlist.json
py -3 tools/check_privacy.py
```

Store the hash as lowercase hex. The allowlist must have `version: 1` and an
`entries` array; each entry has only `path`, `sha256`, `kind`, and `reason`.
Editing only the working-tree allowlist does not authorize an indexed artifact.
Review exception diffs with the same care as the fixture contents.

## Optional Windows pre-commit protection

With Git for Windows and Python installed, opt in for this checkout:

```powershell
py -3 tools/install_privacy_hook.py
```

The installer enables the committed `.githooks/pre-commit` through the repository's
local `core.hooksPath`. It is idempotent, changes no global settings, and refuses
to replace an existing hook directory or any existing nonsample default hook.
If you already use hooks, add a call to `py -3 tools/check_privacy.py` (Windows)
or `python3 tools/check_privacy.py` (Unix) in your existing pre-commit hook and
propagate its nonzero exit status. Review that integration in your own hook setup.

The hook runs in Git's supplied shell, tries `py -3`, `python3`, then `python`,
and blocks a commit if Python/Git/the checker is unavailable or the check fails.
`.gitattributes` keeps its line endings LF on Windows. Installation is optional;
cloning does not enable hooks automatically. After reviewing the setup, disable
the opt-in directory with `git config --local --unset core.hooksPath`.

## CI, testing, and limits

The existing validation workflow runs privacy checks and functional tests before
installing the visual pipeline dependencies. A separate Windows job runs the same
dependency-free guard and tests, including a real commit accepted/rejected by
the optional hook. Temporary repositories contain only generated synthetic
filenames, sentinel text, and fictional JSON; tests do not inspect real documents
or use API keys. Existing package, 401-page pipeline, build, JavaScript, and
offline browser tests are preserved. Require `Package validator` and
`Windows privacy safeguards` in branch rules if you want these CI results to gate
merges; this change does not modify repository administration settings.

A local hook can be bypassed with `--no-verify`, and CI runs after a push has
already reached GitHub. These checks are **not** an exhaustive content/secret
scanner, history audit, access-control system, or publication approval. Private
text renamed as arbitrary code/images or stripped of all recognized JSON markers
can evade this policy. Allowlists and the checker itself still need code review.
Keep original archives outside the repository and review `git diff --cached`
before committing. Consider separate managed secret scanning where appropriate.

For an accidental addition, unstage a new file with `git restore --staged -- PATH`
(or `git rm --cached -- PATH` before the first commit). For an already tracked
file, stage its removal with `git rm --cached -- PATH`; this preserves the local
copy. Removing a file from the index does not remove prior commits. If a real
credential was pushed, revoke/rotate it promptly; assess history removal separately.
No existing disclosure is claimed by this preventive change.
