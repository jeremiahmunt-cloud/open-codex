# Repository instructions

This repository stores reusable Codex skills. Do not scaffold a website in it unless the user specifically requests a website here.

- Keep the canonical repository skill at `.agents/skills/website-development/`; do not add a second discoverable copy under another directory.
- Preserve concise `name` and `description` YAML frontmatter and update `agents/openai.yaml` when the skill's purpose changes.
- Keep the main workflow focused. Place optional industry/tool details in directly linked references and reusable templates in assets.
- Keep examples fictional. Do not commit credentials, private documents, real lender data, or confidential project records.
- Update the root README when installation or package structure changes. Use current official documentation for format changes.
- Run `python3 tools/check_package.py` after edits. For substantial workflow changes, exercise a realistic task and inspect the output; record what was actually tested.
- Before committing, stage the reviewed source and run `python3 tools/check_privacy.py` against the full Git index. Keep exceptions exact, hash-pinned, and documented in `tools/privacy-allowlist.json`; see `docs/privacy-safeguards.md`.
- Preserve unrelated work and review the complete diff before an authorized commit or push.
