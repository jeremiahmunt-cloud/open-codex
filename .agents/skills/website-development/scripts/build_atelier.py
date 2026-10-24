#!/usr/bin/env python3
"""Build the standalone, offline Visual Atelier from canonical local sources."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
ASSETS = SKILL / 'assets/visual-atelier'


def script_json(path):
    # JSON can contain HTML closing tags; never let them escape a script element.
    return json.dumps(json.loads(path.read_text(encoding='utf-8')), ensure_ascii=True, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def build():
    sources = {
        'BRIEF': script_json(SKILL / 'scripts/maison-brief.json'),
        'SAMPLE': script_json(ASSETS / 'sample-index.json'),
        'STYLE': (ASSETS / 'atelier.css').read_text(encoding='utf-8'),
        'CORE': (ASSETS / 'atelier-core.js').read_text(encoding='utf-8'),
        'APP': (ASSETS / 'atelier.js').read_text(encoding='utf-8'),
    }
    for key in ('STYLE', 'CORE', 'APP'):
        if '</style' in sources[key].lower() or '</script' in sources[key].lower():
            raise ValueError(f'Unsafe closing element in {key}')
    digest = lambda value: "'sha256-" + base64.b64encode(hashlib.sha256(value.encode('utf-8')).digest()).decode('ascii') + "'"
    sources['CSP'] = "; ".join((
        "default-src 'none'", "base-uri 'none'", "form-action 'none'", "connect-src 'none'",
        "object-src 'none'", "frame-src 'none'", "worker-src 'none'", "font-src 'none'",
        "img-src data: blob:", "style-src " + digest(sources['STYLE']),
        "script-src " + ' '.join(digest(sources[key]) for key in ('BRIEF', 'SAMPLE', 'CORE', 'APP')),
    ))
    result = (ASSETS / 'index.template.html').read_text(encoding='utf-8')
    for key, value in sources.items():
        result = result.replace('{{' + key + '}}', value)
    if '{{' in result:
        raise ValueError('Unexpanded template marker')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if the committed viewer needs rebuilding.')
    args = parser.parse_args()
    output = ASSETS / 'index.html'
    expected = build()
    if args.check:
        if not output.is_file() or output.read_text(encoding='utf-8') != expected:
            print('FAIL: Visual Atelier is stale. Run python3 .agents/skills/website-development/scripts/build_atelier.py', file=sys.stderr)
            return 1
        print('PASS: standalone viewer matches sources and canonical editorial brief')
    else:
        output.write_text(expected, encoding='utf-8')
        print('Built assets/visual-atelier/index.html (no runtime dependencies)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
