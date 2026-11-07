#!/usr/bin/env python3
"""Translate Z8E's M80 source into z88dk-z80asm and assemble nothing itself.

M80 allows dots and question marks in names, single-quoted strings, word
operators (AND, EQ, HIGH, ...), REPT/ENDM, and bare INCLUDE names. z88dk-z80asm
does not. Listing directives (TITLE, PAGE, ASEG, END, .Z80, .XALL) are dropped.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "build"

SOURCES = [
    "z8e.asm",
    "terminal.inc",
    "config.inc",
    "ansi.tty",
    "adm3a.tty",
    "vt52.tty",
    "d8227.tty",
]

DIRECTIVES = {
    ".z80",
    ".xall",
    ".sall",
    ".lall",
    ".list",
    "title",
    "subttl",
    "page",
    "aseg",
    "end",
}

WORD_OPS = {
    "and", "or", "xor", "not",
    "eq", "ne", "lt", "le", "gt", "ge",
    "shl", "shr", "mod", "high", "low",
}

# M80 precedence, tightest first. Numbers are binding power.
BIN_PREC = {
    "shl": (6, "<<"),
    "shr": (6, ">>"),
    "mod": (6, "%"),
    "*": (6, "*"),
    "/": (6, "/"),
    "+": (5, "+"),
    "-": (5, "-"),
    "eq": (4, "="),
    "ne": (4, "<>"),
    "lt": (4, "<"),
    "le": (4, "<="),
    "gt": (4, ">"),
    "ge": (4, ">="),
    "and": (2, "&"),
    "or": (1, "|"),
    "xor": (1, "^"),
}

IDENT_RE = re.compile(r"[A-Za-z_.?][\w.?]*")


def apostrophe_opens_string(code, i):
    """M80 strings use quotes. A quote after a name is the Z80 AF' suffix."""
    if i > 0 and (code[i - 1].isalnum() or code[i - 1] == "_"):
        return False
    return True


def split_comment(line):
    """Split an M80 line into code and the ';...' comment, respecting quotes."""
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == ";":
            return line[:i], line[i:]
        if c == "'" and not apostrophe_opens_string(line, i):
            i += 1
            continue
        if c in "'\"":
            q = c
            i += 1
            while i < n:
                if line[i] == q:
                    if q == "'" and i + 1 < n and line[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        i += 1
    return line, ""


def convert_strings(code):
    """Turn M80 single-quoted strings into z80asm character or string literals."""
    out = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] != "'" or not apostrophe_opens_string(code, i):
            out.append(code[i])
            i += 1
            continue
        i += 1
        chars = []
        while i < n:
            if code[i] == "'":
                if i + 1 < n and code[i + 1] == "'":
                    chars.append("'")
                    i += 2
                    continue
                i += 1
                break
            chars.append(code[i])
            i += 1
        text = "".join(chars)
        if len(text) == 1 and text != "'":
            out.append("'" + text + "'")
        else:
            out.append('"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"')
    return "".join(out)


def mask_strings(code):
    """Replace double-quoted strings so later scans do not see their text."""
    parts = []
    saved = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] != '"':
            parts.append(code[i])
            i += 1
            continue
        j = i + 1
        buf = ['"']
        while j < n:
            if code[j] == "\\" and j + 1 < n:
                buf.append(code[j])
                buf.append(code[j + 1])
                j += 2
                continue
            buf.append(code[j])
            if code[j] == '"':
                j += 1
                break
            j += 1
        saved.append("".join(buf))
        parts.append("\x01S%d\x01" % (len(saved) - 1))
        i = j
    return "".join(parts), saved


def unmask_strings(code, saved):
    def repl(m):
        return saved[int(m.group(1))]

    return re.sub(r"\x01S(\d+)\x01", repl, code)


def first_opcode(code):
    """Return (opcode_lower, index where operands begin) or (None, None)."""
    i = 0
    n = len(code)
    while i < n and code[i].isspace():
        i += 1
    m = re.match(r"[A-Za-z_.?][\w.?]*\s*(?:::|:)", code[i:])
    if m:
        i += m.end()
        while i < n and code[i].isspace():
            i += 1
    m = re.match(r"[A-Za-z_.?][\w.?]*", code[i:])
    if not m:
        return None, None
    j = i + m.end()
    while j < n and code[j].isspace():
        j += 1
    return m.group(0).lower(), j


def sanitize(name):
    n = name.lower()
    if n.startswith("."):
        return "d_" + n[1:].replace(".", "_").replace("?", "q")
    return n.replace(".", "_").replace("?", "q")


def collect_bad(code):
    bad = set()
    for m in IDENT_RE.finditer(code):
        tok = m.group(0)
        if "." in tok or "?" in tok:
            bad.add(tok)
    return bad


def build_rename(bad_tokens, clean_tokens):
    """Map each odd M80 name to a z80asm identifier, case-insensitively."""
    clean = {t.lower() for t in clean_tokens}
    groups = {}
    for tok in bad_tokens:
        groups.setdefault(tok.lower(), tok)
    mapping = {}
    used = set(clean)
    for key in sorted(groups):
        base = sanitize(key)
        name = base
        n = 2
        while name in used:
            name = "%s_%d" % (base, n)
            n += 1
        used.add(name)
        mapping[key] = name
    return mapping


def apply_rename(code, mapping):
    if not mapping:
        return code
    alt = "|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True))
    pat = re.compile(
        r"(?<![A-Za-z0-9_])(?:%s)(?![A-Za-z0-9_.?])" % alt,
        re.I,
    )

    def repl(m):
        return mapping[m.group(0).lower()]

    return pat.sub(repl, code)


class Expr:
    def __init__(self, text):
        self.text = text
        self.i = 0
        self.n = len(text)
        self.tok = None
        self.advance()

    def advance(self):
        s = self.text
        i = self.i
        n = self.n
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            self.tok = None
            self.i = i
            return
        c = s[i]
        if c in "()+-*/":
            self.tok = ("op", c)
            self.i = i + 1
            return
        if c == "$" and (i + 1 >= n or not s[i + 1].isalnum()):
            self.tok = ("dol", "$")
            self.i = i + 1
            return
        if c == "'":
            j = i + 1
            if j < n and s[j] != "'" and j + 1 < n and s[j + 1] == "'":
                self.tok = ("chr", s[i:j + 2])
                self.i = j + 2
                return
        m = re.match(r"[A-Za-z_][\w]*", s[i:])
        if m:
            self.tok = ("id", m.group(0))
            self.i = i + m.end()
            return
        m = re.match(r"\$[0-9A-Fa-f]+|[0-9][0-9A-Fa-f]*[hHbBqQoOdD]?", s[i:])
        if m:
            self.tok = ("num", m.group(0))
            self.i = i + m.end()
            return
        raise ValueError("bad token at %r" % s[i:i + 20])

    def parse(self):
        node = self.parse_bin(1)
        if self.tok is not None:
            raise ValueError("trailing %r" % (self.tok,))
        return node

    def parse_bin(self, min_prec):
        left = self.parse_unary()
        while self.tok and self.tok[0] in ("op", "id"):
            op = self.tok[1].lower()
            info = BIN_PREC.get(op)
            if not info or info[0] < min_prec:
                break
            prec, spell = info
            self.advance()
            right = self.parse_bin(prec + 1)
            left = "((%s)%s(%s))" % (left, spell, right)
        return left

    def parse_unary(self):
        if self.tok and self.tok[0] == "op" and self.tok[1] in "+-":
            op = self.tok[1]
            self.advance()
            return "(%s%s)" % (op, self.parse_unary())
        if self.tok and self.tok[0] == "id" and self.tok[1].lower() == "not":
            self.advance()
            return "(~(%s))" % self.parse_unary()
        if self.tok and self.tok[0] == "id" and self.tok[1].lower() == "high":
            self.advance()
            return "((%s)>>8)" % self.parse_unary()
        if self.tok and self.tok[0] == "id" and self.tok[1].lower() == "low":
            self.advance()
            return "((%s)&255)" % self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        if self.tok is None:
            raise ValueError("truncated expression")
        kind, val = self.tok
        if kind in ("id", "num", "chr"):
            self.advance()
            return val
        if kind == "dol":
            self.advance()
            return "ASMPC"
        if kind == "op" and val == "(":
            self.advance()
            inner = self.parse_bin(1)
            if not (self.tok and self.tok[0] == "op" and self.tok[1] == ")"):
                raise ValueError("missing )")
            self.advance()
            return "(%s)" % inner
        raise ValueError("primary %r" % (self.tok,))


def has_word_op(text):
    for m in re.finditer(r"[A-Za-z_][\w]*", text):
        if m.group(0).lower() in WORD_OPS:
            return True
    return False


# (($+255) and 0ff00h) - label, then masked to a page. z88dk asserts on
# (address & mask) - address. The label in this source is page-aligned
# (ORG 100h and align 256), so the subtract-first form is the same value.
PAGE_SPAN = re.compile(
    r"(?i)^\(\(\(\$\s*\+\s*255\)\s+and\s+0ff00h\)\s*-\s*"
    r"([A-Za-z_][\w]*)\)\s+and\s+0ff00h$"
)


def rewrite_page_span(text):
    m = PAGE_SPAN.match(text.strip())
    if not m:
        return None
    return "((ASMPC - %s) + 255) & 0ff00h" % m.group(1)


def rewrite_expr(text):
    if not has_word_op(text):
        return text
    try:
        return Expr(text).parse()
    except ValueError as exc:
        print("expr keep %r (%s)" % (text.strip(), exc), file=sys.stderr)
        return text


def split_operands(text):
    """Split assembler operands on commas that are outside parentheses and quotes."""
    parts = []
    buf = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "'":
            buf.append(c)
            i += 1
            if i < n:
                buf.append(text[i])
                i += 1
            if i < n and text[i] == "'":
                buf.append(text[i])
                i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")" and depth:
            depth -= 1
        elif c == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def align_org(code):
    """M80 page and dword alignment. z88dk rejects a second computed ORG."""
    m = re.match(r"^(\s*)org\b(.*)$", code, re.I)
    if not m:
        return None
    expr = re.sub(r"[\s()]", "", m.group(2).lower())
    if expr in ("$+255and0ff00h", "asmpc+255and0ff00h"):
        return m.group(1) + "align 256"
    if expr in ("$+3and0fffch", "asmpc+3and0fffch"):
        return m.group(1) + "align 4"
    return None


def rewrite_expressions(code):
    masked, saved = mask_strings(code)
    equ = re.match(
        r"(\s*[A-Za-z_.?][\w.?]*\s+(?:equ|defl)\s+)(.*)$",
        masked,
        re.I | re.S,
    )
    if equ:
        body = rewrite_page_span(equ.group(2))
        if body is None:
            body = rewrite_expr(equ.group(2))
        return unmask_strings(equ.group(1) + body, saved)

    op, j = first_opcode(masked)
    if op is None:
        return code
    if op in ("if", "elif", "org"):
        body = rewrite_expr(masked[j:])
        return unmask_strings(masked[:j] + body, saved)
    if op in ("and", "or", "xor"):
        return code

    rest = masked[j:]
    if not has_word_op(rest):
        return code
    pieces = split_operands(rest)
    new_pieces = []
    for p in pieces:
        if has_word_op(p):
            lead = re.match(r"\s*", p).group(0)
            body = rewrite_expr(p.strip())
            # sub (expr) is a memory operand. A leading + keeps it immediate.
            if body.startswith("("):
                body = "+" + body
            new_pieces.append(lead + body)
        else:
            new_pieces.append(p)
    return unmask_strings(masked[:j] + ",".join(new_pieces), saved)


def transform_line(code, stack, mapping):
    inc = re.match(r"(\s*include\s+)(\S+)(.*)$", code, re.I)
    if inc:
        name = inc.group(2).strip("\"'").lower()
        return inc.group(1) + '"%s"' % name + inc.group(3), False

    code = convert_strings(code)
    op, _ = first_opcode(code)
    if op in DIRECTIVES:
        return "; " + code, False

    masked, saved = mask_strings(code)
    tokens = [t.lower() for t in IDENT_RE.findall(masked)]
    if "macro" in tokens:
        stack.append("macro")
    elif tokens and tokens[0] == "rept":
        # opcode may be preceded by a label; the keyword is enough
        stack.append("rept")
    elif op == "rept":
        stack.append("rept")
    elif op == "endm" and stack:
        kind = stack.pop()
        if kind == "rept":
            masked = re.sub(r"(?i)\bendm\b", "endr", masked, count=1)
    elif op == "mend" and stack and stack[-1] == "macro":
        stack.pop()

    # A labelled REPT still has the keyword later in the token list.
    if op != "rept" and "rept" in tokens and "macro" not in tokens:
        if not stack or stack[-1] != "rept":
            stack.append("rept")

    masked = apply_rename(masked, mapping)
    code = unmask_strings(masked, saved)
    aligned = align_org(code)
    if aligned is not None:
        return aligned, False
    code = rewrite_expressions(code)
    return code, False


def lines_of(path):
    text = path.read_text(encoding="latin1")
    return text.splitlines()


def code_of_line(line):
    code, _comment = split_comment(line)
    inc = re.match(r"\s*include\s+(\S+)", code, re.I)
    if inc:
        return ""
    code = convert_strings(code)
    op, _ = first_opcode(code)
    if op in DIRECTIVES:
        return ""
    masked, _saved = mask_strings(code)
    return masked


def collect_all():
    bad = set()
    clean = set()
    for name in SOURCES:
        for line in lines_of(SRC / name):
            code = code_of_line(line)
            for tok in IDENT_RE.findall(code):
                if ("." in tok or "?" in tok) and any(c.isalnum() for c in tok):
                    bad.add(tok)
                else:
                    clean.add(tok)
    return bad, clean


MACRO_HEAD = re.compile(
    r"^(\s*)([A-Za-z_.?][\w.?]*)(?::\s*|\s+)macro\b",
    re.I,
)
MACRO_END = re.compile(r"^\s*(?:endm|endr|mend)\b", re.I)


def wrap_macro_guards(lines):
    """M80 may redefine a macro. z88dk rejects the second definition."""
    out = []
    stack = []
    for line in lines:
        code = line.split(";", 1)[0]
        if stack and MACRO_END.match(code):
            out.append(line)
            stack.pop()
            indent = re.match(r"\s*", line).group(0)
            out.append(indent + "endif")
            continue
        head = MACRO_HEAD.match(code)
        if head and "ifndef" not in code.lower():
            out.append("%sifndef %s" % (head.group(1), head.group(2)))
            out.append(line)
            stack.append(head.group(2))
            continue
        out.append(line)
    if stack:
        print("macro guard unclosed: %s" % stack, file=sys.stderr)
    return out


def translate_file(name, mapping):
    stack = []
    endr = 0
    out_lines = []
    for line in lines_of(SRC / name):
        code, comment = split_comment(line)
        if code.strip() == "":
            out_lines.append(line)
            continue
        new_code, _ = transform_line(code, stack, mapping)
        if re.search(r"(?i)\bendr\b", new_code) and re.search(r"(?i)\brept\b", ""):
            pass
        if "endr" in new_code.lower() and "endm" in code.lower():
            endr += 1
        if comment:
            if new_code.endswith(" ") or new_code == "":
                out_lines.append(new_code + comment)
            else:
                out_lines.append(new_code + "\t" + comment if not new_code[-1].isspace() else new_code + comment)
        else:
            out_lines.append(new_code.rstrip())
    out_lines = wrap_macro_guards(out_lines)
    if stack:
        print("%s: unclosed macro/rept %s" % (name, stack), file=sys.stderr)
    return out_lines, endr


def dest_name(src_name):
    if src_name.endswith(".z80"):
        return src_name[:-4] + ".asm"
    return src_name


def self_test():
    samples = [
        ("m80 or slr", "|"),
        ("'X' and 1Fh", "&"),
        ("-(high z8eorg)", ">>8"),
        ("z8eorg shr 8", ">>"),
        ("m80 and auxterm ne none", "<>"),
        ("($+255) and 0ff00h", "&"),
        ("((($+255) and 0ff00h)-z8eorg) and 0ff00h", "z8eorg"),
        ("ix__ or iy__", "|"),
    ]
    for src, needle in samples:
        got = Expr(src).parse()
        if needle not in got:
            raise SystemExit("expr %r -> %r missing %r" % (src, got, needle))
    span = "((($+255) and 0ff00h)-z8eorg) and 0ff00h"
    got = rewrite_page_span(span)
    want = "((ASMPC - z8eorg) + 255) & 0ff00h"
    if got != want:
        raise SystemExit("page span %r -> %r" % (span, got))


def main():
    self_test()
    bad, clean = collect_all()
    mapping = build_rename(bad, clean)
    # bcde is a z80asm register token (TK_BCDE), so it cannot be a label.
    mapping.setdefault("bcde", "bcde_")
    OUT.mkdir(parents=True, exist_ok=True)
    report = OUT / "rename.map"
    report.write_text(
        "\n".join("%s %s" % (k, mapping[k]) for k in sorted(mapping)) + "\n",
        encoding="ascii",
    )
    print("renamed %d identifiers" % len(mapping))
    for name in SOURCES:
        lines, endr = translate_file(name, mapping)
        dest = OUT / dest_name(name)
        dest.write_text("\n".join(lines) + "\n", encoding="latin1")
        print("wrote %s (%d lines, rept %d)" % (dest.name, len(lines), endr))


if __name__ == "__main__":
    main()
