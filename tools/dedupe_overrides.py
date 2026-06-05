"""Remove duplicate keys from the ui() override map in app_strings.dart.

After mojibake recovery, pairs of entries where the original file had both
a proper UTF-8 form and a mojibake form collapse to the same key. Dart
disallows duplicate keys in a const map literal so we drop the second
occurrence of each duplicate.

Each map entry can span multiple lines. An entry starts with `'<key>':`
at indentation level >= 6 and ends with `),` at the same indentation or
a single-line entry that ends with `),` on its own.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def dedupe_ui_overrides(content: str) -> tuple[str, int]:
    lines = content.split('\n')
    out: list[str] = []
    seen: set[str] = set()
    in_map = False
    skip_until_close = False
    removed = 0
    key_pat = re.compile(r"^\s+'([^']+)':")

    for line in lines:
        if 'const overrides = <String, ({String vi, String en})>' in line:
            in_map = True
            out.append(line)
            continue
        if in_map and line.strip() == '};':
            in_map = False
            skip_until_close = False
            out.append(line)
            continue

        if not in_map:
            out.append(line)
            continue

        if skip_until_close:
            stripped = line.strip()
            if stripped == '),' or stripped == ')':
                skip_until_close = False
            continue

        m = key_pat.match(line)
        if m:
            key = m.group(1)
            if key in seen:
                removed += 1
                stripped = line.strip()
                # If the entry fits on a single line ending in `),` we are
                # done after this line. Otherwise keep skipping until we
                # see a closing `),`.
                if stripped.endswith('),'):
                    continue
                skip_until_close = True
                continue
            seen.add(key)
        out.append(line)

    return '\n'.join(out), removed


def main() -> int:
    path = Path('flutter_frontend/lib/l10n/app_strings.dart')
    content = path.read_text(encoding='utf-8')
    fixed, removed = dedupe_ui_overrides(content)
    write = '--write' in sys.argv
    print(f'Duplicate entries removed: {removed}')
    if write and fixed != content:
        path.write_text(fixed, encoding='utf-8', newline='')
        print('Written.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
