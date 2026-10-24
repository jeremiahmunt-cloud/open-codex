#!/usr/bin/env python3
"""Dependency-free smoke checks for this package, not a general YAML validator."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys


def check(root: Path) -> list[str]:
    errors: list[str] = []
    skill = root / '.agents/skills/website-development'
    required = [
        'SKILL.md', 'agents/openai.yaml',
        'references/design-and-architecture.md',
        'references/luxury-real-estate.md', 'references/integrations.md',
        'references/visual-production.md', 'references/quality-checklist.md',
        'references/examples.md', 'assets/site-brief.md',
        'assets/verification-handoff.md', 'assets/content-record.example.json',
        'assets/editorial-tokens.css',
        'assets/visual-atelier/index.html', 'assets/visual-atelier/index.template.html',
        'assets/visual-atelier/atelier-core.js', 'assets/visual-atelier/atelier.js',
        'assets/visual-atelier/atelier.css', 'assets/visual-atelier/sample-index.json',
        'scripts/build_atelier.py',
    ]
    for relative in required:
        if not (skill / relative).is_file():
            errors.append(f'Missing required file: {relative}')
    if errors:
        return errors

    manifest = (skill / 'SKILL.md').read_text(encoding='utf-8')
    header = re.match(r'\A---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n', manifest)
    if not header:
        errors.append('SKILL.md must retain this package\'s two single-line metadata fields.')
    else:
        if header[1] != skill.name or len(header[1]) > 64:
            errors.append('Skill name must match its folder and be at most 64 characters.')
        if not 20 <= len(header[2]) <= 1024:
            errors.append('Description must be specific and at most 1024 characters.')
    if len(manifest.splitlines()) >= 500:
        errors.append('Move optional detail out of SKILL.md; keep it below 500 lines.')

    # The generated UI file intentionally uses only quoted JSON-compatible scalars.
    ui = (skill / 'agents/openai.yaml').read_text(encoding='utf-8')
    values: dict[str, str] = {}
    if not ui.startswith('interface:\n'):
        errors.append('UI metadata must start with interface:.')
    for field in ('display_name', 'short_description', 'default_prompt'):
        match = re.search(r'^  ' + field + r': (.+)$', ui, re.MULTILINE)
        try:
            value = json.loads(match[1]) if match else None
            if not isinstance(value, str) or not value:
                raise ValueError('empty/non-string value')
            values[field] = value
        except (ValueError, TypeError):
            errors.append(f'UI {field} must be a nonempty double-quoted string.')
    if 'short_description' in values and not 25 <= len(values['short_description']) <= 64:
        errors.append('UI short_description must be 25–64 characters.')
    if '$website-development' not in values.get('default_prompt', ''):
        errors.append('UI default_prompt must mention $website-development.')

    for path in sorted(skill.rglob('*')):
        if any(part in {'node_modules', '__pycache__', '.venv'} for part in path.relative_to(skill).parts):
            continue
        if not path.is_file():
            continue
        if path.suffix == '.json':
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except ValueError as exc:
                errors.append(f'Invalid JSON in {path.name}: {exc}')
        if path.suffix != '.md':
            continue
        content = path.read_text(encoding='utf-8')
        if re.search(r'\b(?:TODO|TBD|FIXME)\b', content):
            errors.append(f'Unfinished placeholder in {path.relative_to(skill)}')
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', content):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                continue
            target = (path.parent / link.split('#', 1)[0]).resolve()
            if not target.is_relative_to(skill.resolve()) or not target.is_file():
                errors.append(f'Broken or out-of-package link in {path.name}: {link}')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = check(root)
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    if errors:
        return 1
    print('PASS: package files, metadata, local links, JSON, and placeholder checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
