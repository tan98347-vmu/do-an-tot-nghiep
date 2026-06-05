"""Recover Vietnamese mojibake from Dart source files.

The source files were encoded as UTF-8 but the Vietnamese text inside was
already double-encoded (original UTF-8 -> interpreted as Windows-1252 ->
re-encoded as UTF-8). This script reverses the second step so that the
Vietnamese text becomes correct UTF-8 again.

Strategy: find every string literal and comment in the file, attempt to
treat each one as mojibake, and replace it with the recovered text if the
recovery reduces the mojibake-marker count. Each region is processed
independently so mixed files (with both proper and mojibake Vietnamese)
work correctly.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Windows-1252 -> Unicode mapping for the 0x80..0x9F slots that differ
# from Latin-1.
_W1252_TO_UNICODE = {
    0x80: 0x20AC, 0x82: 0x201A, 0x83: 0x0192, 0x84: 0x201E,
    0x85: 0x2026, 0x86: 0x2020, 0x87: 0x2021, 0x88: 0x02C6,
    0x89: 0x2030, 0x8A: 0x0160, 0x8B: 0x2039, 0x8C: 0x0152,
    0x8E: 0x017D, 0x91: 0x2018, 0x92: 0x2019, 0x93: 0x201C,
    0x94: 0x201D, 0x95: 0x2022, 0x96: 0x2013, 0x97: 0x2014,
    0x98: 0x02DC, 0x99: 0x2122, 0x9A: 0x0161, 0x9B: 0x203A,
    0x9C: 0x0153, 0x9E: 0x017E, 0x9F: 0x0178,
}
_UNICODE_TO_W1252 = {v: k for k, v in _W1252_TO_UNICODE.items()}

_MOJIBAKE_MARKERS = set('ÃÂÄÆâ') | set(chr(c) for c in _UNICODE_TO_W1252)


def _char_to_w1252_byte(ch: str) -> int | None:
    cp = ord(ch)
    if cp <= 0xFF:
        return cp
    return _UNICODE_TO_W1252.get(cp)


def _mojibake_score(text: str) -> int:
    return sum(1 for ch in text if ch in _MOJIBAKE_MARKERS)


def _try_recover(text: str) -> str | None:
    """Attempt mojibake recovery on `text`. Return recovered text or None.

    We attempt recovery on any string that contains characters in the
    Latin-1 supplement range (0x80..0xFF) or Win-1252 specials, since
    those are the telltale signs of double-encoding. The recovery is
    accepted only when it produces strictly valid UTF-8 *and* the
    resulting string has fewer Latin-1-supplement characters than the
    original -- mojibake bloats every Vietnamese letter into multiple
    characters, so a proper recovery shrinks that count.
    """
    if not any(0x80 <= ord(ch) <= 0xFF or ord(ch) in _UNICODE_TO_W1252
               for ch in text):
        return None
    out = bytearray()
    for ch in text:
        byte = _char_to_w1252_byte(ch)
        if byte is None:
            return None
        out.append(byte)
    try:
        recovered = out.decode('utf-8')
    except UnicodeDecodeError:
        return None
    if _latin1_supp_count(recovered) >= _latin1_supp_count(text):
        return None
    return recovered


def _latin1_supp_count(text: str) -> int:
    return sum(
        1 for ch in text
        if 0x80 <= ord(ch) <= 0xFF or ord(ch) in _UNICODE_TO_W1252
    )


# Tokens we care about: comments and string literals. We use a tokenizer
# walk so we never replace inside one form while accidentally consuming
# delimiters of another.
_TOKEN_RE = re.compile(
    r"""
    (?P<line_comment>   //[^\n]* )
  | (?P<block_comment>  /\*[\s\S]*?\*/ )
  | (?P<triple_str_s>   r?'''[\s\S]*?''' )
  | (?P<triple_str_d>   r?\"\"\"[\s\S]*?\"\"\" )
  | (?P<single_str>     r?'(?:\\.|[^'\\\n])*' )
  | (?P<double_str>     r?\"(?:\\.|[^\"\\\n])*\" )
    """,
    re.VERBOSE,
)


def recover_text(content: str) -> str:
    out: list[str] = []
    last = 0
    for m in _TOKEN_RE.finditer(content):
        out.append(content[last:m.start()])
        token = m.group(0)
        fixed = _try_recover(token)
        out.append(fixed if fixed is not None else token)
        last = m.end()
    out.append(content[last:])
    return ''.join(out)


def process_file(path: Path, write: bool) -> tuple[bool, int]:
    original = path.read_text(encoding='utf-8')
    fixed = recover_text(original)
    if fixed == original:
        return False, 0
    saved = _mojibake_score(original) - _mojibake_score(fixed)
    if write:
        # Preserve original newline style (LF). Writing with newline='' so
        # Python does not translate '\n' to '\r\n' on Windows.
        path.write_text(fixed, encoding='utf-8', newline='')
    return True, saved


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--ext', default='.dart')
    args = parser.parse_args()

    targets: list[Path] = []
    for p in args.paths:
        path = Path(p)
        if path.is_file():
            targets.append(path)
        elif path.is_dir():
            targets.extend(path.rglob('*' + args.ext))

    changed = 0
    total_saved = 0
    for path in targets:
        try:
            modified, saved = process_file(path, args.write)
        except Exception as exc:
            print(f'ERROR {path}: {exc}', file=sys.stderr)
            continue
        if modified:
            changed += 1
            total_saved += saved
            print(f'{"FIXED" if args.write else "WOULD FIX"} {path} '
                  f'(markers removed: {saved})')

    print(f'\nFiles changed: {changed}, total markers removed: {total_saved}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
