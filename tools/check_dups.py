"""Check for duplicate keys in app_strings.dart ui()/exactOverrides after recovery."""

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
from fix_mojibake import recover_text

p = Path('flutter_frontend/lib/l10n/app_strings.dart')
orig = p.read_text(encoding='utf-8')
fixed = recover_text(orig)
lines = fixed.splitlines()

in_ui = False
in_exact = False
seen_ui = {}
seen_exact = {}
dups_ui = []
dups_exact = []
key_pat = re.compile(r"^\s*'([^']+)':")

for i, line in enumerate(lines, 1):
    if 'const overrides = <String, ({String vi, String en})>' in line:
        in_ui = True
        continue
    if 'final exactOverrides = <String, String>' in line:
        in_exact = True
        continue
    if in_ui and line.strip() == '};':
        in_ui = False
    if in_exact and line.strip() == '};':
        in_exact = False
    m = key_pat.match(line)
    if m:
        key = m.group(1)
        if in_ui:
            if key in seen_ui:
                dups_ui.append((seen_ui[key], i, key))
            else:
                seen_ui[key] = i
        elif in_exact:
            if key in seen_exact:
                dups_exact.append((seen_exact[key], i, key))
            else:
                seen_exact[key] = i

print('ui dups:', len(dups_ui))
for first, second, key in dups_ui:
    print(f'  L{first} & L{second}: {key[:80]}')
print('exact dups:', len(dups_exact))
for first, second, key in dups_exact:
    print(f'  L{first} & L{second}: {key[:80]}')
