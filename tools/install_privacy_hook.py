#!/usr/bin/env python3
"""Opt in to the repository hook without replacing an existing hook setup."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


def install(root: Path) -> str:
    def git(*args: str, missing_ok: bool = False) -> str:
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=False)
        if result.returncode and not (missing_ok and result.returncode == 1):
            raise RuntimeError('Git could not inspect/configure this checkout.')
        return os.fsdecode(result.stdout).strip()

    root = Path(git('rev-parse', '--show-toplevel')).resolve()
    for relative in ('.githooks/pre-commit', 'tools/check_privacy.py'):
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('The repository hook and checker must be present as regular files.')
    current = git('config', '--get', 'core.hooksPath', missing_ok=True)
    if current == '.githooks':
        return 'Privacy hook directory is already enabled for this checkout.'
    if current:
        raise RuntimeError('Existing core.hooksPath preserved. Call the privacy checker from your existing hook.')
    hooks = Path(git('rev-parse', '--git-path', 'hooks'))
    if not hooks.is_absolute():
        hooks = root / hooks
    if hooks.exists() and any(not path.name.endswith('.sample') for path in hooks.iterdir()):
        raise RuntimeError('Existing hooks preserved. Call the privacy checker from your existing hook.')
    hook = root / '.githooks/pre-commit'
    hook.chmod(hook.stat().st_mode | 0o111)
    git('config', '--local', 'core.hooksPath', '.githooks')
    return 'Enabled privacy pre-commit check for this checkout only.'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(install(args.repo))
    except (OSError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
