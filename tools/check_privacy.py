#!/usr/bin/env python3
"""Check the complete Git index for private artifacts; Python stdlib + Git only.

Read indexed blobs, never working-tree documents, and never print blob contents.
This is a preventive filename/JSON policy, not a general secret or history scan.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ALLOWLIST = 'tools/privacy-allowlist.json'
MAX_JSON_BYTES = 4 * 1024 * 1024
PRIVATE_DIRECTORIES = {
    'private', 'research-output', 'research-assets', 'research-archive',
    'source-documents', 'extracted-documents', 'extracted-assets',
    'extracted-images', 'ocr-output', 'thumbnails', 'stock-originals',
    'web-variants',
}
CREDENTIAL_DIRECTORIES = {
    '.secrets', 'secrets', 'credentials', '.ssh', '.aws', '.azure', '.gcloud',
}
CREDENTIAL_NAMES = {
    '.git-credentials', '.netrc', '_netrc', '.npmrc', '.pypirc',
}
CREDENTIAL_PATTERNS = (
    'credentials*.json', 'service-account*.json', 'service_account*.json',
    'client_secret*.json', 'id_rsa*', 'id_dsa*', 'id_ecdsa*', 'id_ed25519*',
)
CREDENTIAL_SUFFIXES = {'.pem', '.key', '.p8', '.p12', '.pfx'}
DOCUMENT_SUFFIXES = {
    '.pdf', '.doc', '.docx', '.odt', '.rtf', '.xls', '.xlsx', '.xlsm', '.ods',
    '.csv', '.tsv', '.eml', '.msg', '.pst', '.zip', '.7z', '.rar', '.tar',
    '.gz', '.tgz', '.sqlite', '.sqlite3', '.db',
}
RESEARCH_PATTERNS = (
    'research-index*.json', 'maison-visual-manifest*.json', 'website-plan*.json',
    'asset-manifest*.json', 'image-audit*.json', 'candidates*.json', 'variants.json',
    'pdf-[0-9]*.*',
)
JSON_SUFFIXES = {'.json', '.jsonl', '.ndjson'}


class CheckError(Exception):
    """Fail closed without exposing subprocess output or private content."""


@dataclass(frozen=True)
class Entry:
    path: str
    mode: str
    oid: str
    stage: str


def git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            ['git', '-C', str(root), *args], input=data, capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise CheckError('Git is required and must be available on PATH.') from exc
    if result.returncode:
        raise CheckError('Git could not read the repository/index; run from a valid checkout.')
    return result.stdout


def repository_root(root: Path) -> Path:
    return Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve()


def index_entries(root: Path) -> list[Entry]:
    result = []
    for record in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if record:
            metadata, path = record.split(b'\t', 1)
            mode, oid, stage = metadata.decode('ascii').split()
            result.append(Entry(os.fsdecode(path), mode, oid, stage))
    return result


def blob_sizes(root: Path, entries: list[Entry]) -> dict[str, int]:
    oids = sorted({entry.oid for entry in entries if entry.mode in {'100644', '100755'}})
    if not oids:
        return {}
    output = git(root, 'cat-file', '--batch-check', data=('\n'.join(oids) + '\n').encode('ascii'))
    result = {}
    for line in output.splitlines():
        fields = line.decode('ascii').split()
        if len(fields) != 3 or fields[1] != 'blob':
            raise CheckError('An indexed object is missing or is not a readable blob.')
        result[fields[0]] = int(fields[2])
    return result


def label(path: str) -> str:
    # Escape newlines, control characters and non-ASCII to keep CI logs inert.
    return json.dumps(path, ensure_ascii=True)


def path_rules(path: str) -> tuple[list[str], list[str]]:
    parts = path.replace('\\', '/').casefold().split('/')
    name = parts[-1]
    suffix = PurePosixPath(name).suffix
    hard, reviewable = [], []
    if any(part in CREDENTIAL_DIRECTORIES for part in parts[:-1]):
        hard.append('credential directory')
    if any(part in PRIVATE_DIRECTORIES or part.startswith('private-') for part in parts[:-1]):
        hard.append('private/generated research directory')
    if (name in CREDENTIAL_NAMES or suffix in CREDENTIAL_SUFFIXES
            or (name.startswith('.env') and name != '.env.example')
            or any(fnmatch.fnmatchcase(name, pattern) for pattern in CREDENTIAL_PATTERNS)):
        hard.append('credential/key filename')
    if suffix in DOCUMENT_SUFFIXES:
        reviewable.append('source document, exported data, or archive requires review')
    if any(fnmatch.fnmatchcase(name, pattern) for pattern in RESEARCH_PATTERNS):
        reviewable.append('generated research/export filename')
    return hard, reviewable


def json_rules(value: object) -> tuple[list[str], list[str]]:
    hard, reviewable = set(), set()
    pending = [value]
    while pending:
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(node)
        elif isinstance(node, dict):
            fields = {key.casefold(): item for key, item in node.items()}
            for field in ('scope', 'publicationscope'):
                scope = fields.get(field)
                if isinstance(scope, str) and (scope.casefold() in {'private', 'confidential', 'internal-only'}
                        or scope.casefold().startswith(('private-', 'confidential-'))):
                    reviewable.add('private/confidential JSON scope')
            if fields.get('manifestkind') == 'maison-visual-review':
                reviewable.add('Visual Atelier review manifest')
            if isinstance(fields.get('document'), dict) and any(
                    isinstance(fields.get(key), list) for key in ('pages', 'chunks', 'images')):
                reviewable.add('document research index structure')
            if fields.get('type') == 'service_account' or any(
                    isinstance(fields.get(key), str) and fields[key].strip()
                    for key in ('private_key', 'client_secret', 'access_token', 'refresh_token')):
                hard.add('credential-bearing JSON structure')
            pending.extend(node.values())
    return sorted(hard), sorted(reviewable)


def parse_json(data: bytes) -> object:
    source = data.decode('utf-8-sig')
    depth, quoted, escaped = 0, False, False
    for character in source:
        if quoted:
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in '[{':
            depth += 1
            if depth > 128:
                raise ValueError('JSON nesting exceeds the inspection limit')
        elif character in ']}':
            depth -= 1
    # Duplicate fields must not hide a private scope behind a public value.
    def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        seen = set()
        for key, value in pairs:
            if key.casefold() in seen:
                raise ValueError('duplicate JSON field')
            seen.add(key.casefold())
            result[key] = value
        return result
    def reject_constant(value: str) -> object:
        raise ValueError('non-finite JSON number')
    return json.loads(source, object_pairs_hook=unique_fields, parse_constant=reject_constant)


def load_allowlist(root: Path, entries: dict[str, Entry], sizes: dict[str, int]) -> dict[str, dict]:
    entry = entries.get(ALLOWLIST)
    if entry is None:
        return {}
    if entry.stage != '0' or entry.mode not in {'100644', '100755'}:
        raise CheckError('The indexed privacy allowlist must be a regular, merged file.')
    if sizes[entry.oid] > MAX_JSON_BYTES:
        raise CheckError('The indexed privacy allowlist is too large.')
    try:
        value = parse_json(git(root, 'cat-file', 'blob', entry.oid))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CheckError('The indexed privacy allowlist must contain valid JSON.') from exc
    if (not isinstance(value, dict) or set(value) != {'version', 'entries'}
            or type(value['version']) is not int or value['version'] != 1
            or not isinstance(value['entries'], list)):
        raise CheckError('Privacy allowlist needs version 1 and an entries array.')
    result, seen = {}, set()
    for item in value['entries']:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256', 'kind', 'reason'}:
            raise CheckError('Each allowlist entry needs path, sha256, kind, and reason.')
        path = item['path']
        if (not isinstance(path, str) or not path or path != PurePosixPath(path).as_posix()
                or PurePosixPath(path).is_absolute() or '..' in path.split('/')
                or any(character in path for character in '*?[]\\:\x00\r\n')
                or path == ALLOWLIST):
            raise CheckError('Allowlist paths must be exact repository-relative POSIX paths; no globs.')
        if path.casefold() in seen:
            raise CheckError('Privacy allowlist contains a duplicate path.')
        if (not isinstance(item['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])
                or item['kind'] not in ('synthetic-fixture', 'reusable-resource')
                or not isinstance(item['reason'], str) or len(item['reason'].strip()) < 20):
            raise CheckError('Allowlist entries need a SHA-256, supported kind, and substantive reason.')
        if path not in entries:
            raise CheckError(f'Allowlist entry has no indexed file: {label(path)}')
        seen.add(path.casefold())
        result[path] = item
    return result


def check(root: Path) -> tuple[list[str], int, int]:
    root = repository_root(root)
    indexed = index_entries(root)
    entries = {entry.path: entry for entry in indexed}
    sizes = blob_sizes(root, indexed)
    allowed = load_allowlist(root, entries, sizes)
    errors = []
    for entry in indexed:
        if entry.stage != '0':
            errors.append(f'{label(entry.path)}: unresolved Git index conflict')
            continue
        if entry.mode not in {'100644', '100755'}:
            errors.append(f'{label(entry.path)}: symlinks and submodules are not reviewed by this guard')
            continue
        hard, reviewable = path_rules(entry.path)
        content = None
        is_json = PurePosixPath(entry.path.casefold()).suffix in JSON_SUFFIXES
        if (is_json or entry.path in allowed) and sizes[entry.oid] > MAX_JSON_BYTES:
            hard.append('JSON/review exception exceeds the 4 MiB inspection limit')
        elif is_json or entry.path in allowed:
            content = git(root, 'cat-file', 'blob', entry.oid)
        if is_json and content is not None:
            try:
                if entry.path.casefold().endswith(('.jsonl', '.ndjson')):
                    value = [parse_json(line) for line in content.splitlines() if line.strip()]
                else:
                    value = parse_json(content)
                content_hard, content_reviewable = json_rules(value)
                hard.extend(content_hard)
                reviewable.extend(content_reviewable)
            except (ValueError, UnicodeError, RecursionError):
                hard.append('invalid/ambiguous JSON cannot be inspected safely')
        exception = allowed.get(entry.path)
        if exception:
            if hard:
                hard.append('allowlist cannot exempt this rule')
            elif content is None or hashlib.sha256(content).hexdigest() != exception['sha256']:
                hard.append('allowlist SHA-256 does not match the indexed bytes; review changes')
            else:
                reviewable = []
        if hard or reviewable:
            errors.append(f'{label(entry.path)}: ' + '; '.join(hard + reviewable))
    return errors, len(indexed), len(allowed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1],
                        help='Git checkout to inspect (default: this tool\'s repository)')
    args = parser.parse_args()
    try:
        errors, count, exceptions = check(args.repo)
    except CheckError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    if errors:
        print('Keep private files outside Git. Unstage them or stage their removal; '
              'review docs/privacy-safeguards.md for synthetic/resource exceptions.', file=sys.stderr)
        return 1
    print(f'PASS: privacy guard checked {count} indexed files (tracked + staged); '
          f'{exceptions} documented exceptions')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
