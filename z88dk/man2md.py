#!/usr/bin/env python3
"""Replicate src/z8e.man as markdown without justification padding."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "z8e.man"
DST = ROOT / "z8e.md"

PAGE_NO = re.compile(r"^\s*-\s*\d+\s*-\s*$")
HEADER = re.compile(
    r"Z8E REFERENCE MANUAL|X  file the user should first load the file",
)
SECTION = re.compile(
    r"^(?:[IVX]+\.?\s+[A-Z][A-Z0-9 ,'/()-]*|APPENDIX\s+[A-E]\s+-\s+.+)$"
)
COMMAND = re.compile(r"^([A-Z?>]|>>)\s{2,}(\S.*)$")
TOC_LINE = re.compile(r"^(\s*)(.+?)\s*\.{3,}\s*(\d+)\s*$")
# CP/M console prompt. A leading "1." is an example number, not part of the command.
# A leading digit on the prompt itself (3A>) is the optional user number.
CONSOLE = re.compile(r"^(?:\d+\.\s+)?(?:\d+)?[A-P]>\S")
# A numbered console message under STATUS MESSAGES or ERROR MESSAGES.
# "1. Loading: USERFILE.COM", "4. Syntax Error". The number is the example label.
STATUS_MSG = re.compile(r"^\d+\.\s+\S")
MEM_LINE = re.compile(
    r"^(?:Total Symbols|Symbol Table|Z8E relocated|Top of memory):\s+\S"
)
# "where ARG1" / "where each" introduces the argument definitions that follow.
WHERE_ARG = re.compile(r"^where\s+(?:ARG\d|each)\b", re.I)
# A definition label. ARG/If/Any count only near the "where" line's indent:
# a deeper "ARG3 is evaluated..." is the previous definition wrapping.
DEF_HEAD = re.compile(
    r"^(?:ARG\d\b|arguments\b|each\b|NOTE:|\d+\)|If\b|Any\b)",
    re.I,
)
DEF_LABEL = re.compile(r"^(?:arguments\b|NOTE:|\d+\))", re.I)
# A whole line typed at the Z8E "*" prompt. A sentence that merely starts
# with an example ("*J P to resume") is not one of these.
Z8E_CMD = re.compile(r"^\*(?:[A-Z?>])(?:\s.*)?$")
Z8E_CMD_OR = re.compile(r"^or\s+\*(?:[A-Z?>])(?:\s.*)?$", re.I)
Z8E_PROSE = re.compile(
    r"\b(the|to|where|and|which|when|this|that|with|from|into|resume|execution)\b",
    re.I,
)
RULE = re.compile(r"^_+$")
HEXROW = re.compile(r"^\s*[0-9A-F]{4}\s+[0-9A-F]{2}")
# Opcode at the start of the line (a label may precede it). A sentence that
# only mentions CALL or MACRO-80 is not an instruction.
ASM_HEAD = re.compile(
    r"^(?:[A-Za-z_.$][\w.$]*\s+)?"
    r"(?:ld|call|defb|defw|org|equ|macro|endm|emdm|jr|djnz)(?![A-Za-z0-9-])(?:\s|$)",
    re.I,
)


def split_lines(text):
    """Split on newlines only. str.splitlines() also splits on WordStar 0x1E."""
    return text.split("\n")


def strip_page(page):
    lines = split_lines(page)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and HEADER.search(lines[0]):
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and PAGE_NO.match(lines[-1]):
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


TABLE_ROW = re.compile(
    r"^\s*(?:CMD|[A-Z?>]|\[\]|\[/\]|\[\*\]|\[\(\]\s*\[\)\])\s{3,}\S"
)


def dehyphen_line(line):
    """Join a word split by a WordStar soft hyphen or by justification."""
    line = re.sub(r"\x1e +", "", line)
    line = line.replace("\x1e", "")
    return re.sub(r"(?<=[A-Za-z])- +(?=[a-z])", "", line)


def wide_gaps(line):
    """Two wide gaps means columns, not justification."""
    return len(re.findall(r" {4,}", line.strip())) >= 2


# A short key, a wide gap, and a short action. "space    read next address",
# "1. A>Z8E" is not this (that is a console command). A justified sentence
# such as "HEX:    A 16 bit hex number may be entered..." has too many words.
TABLE_KEY = re.compile(r"^(\S(?:.{0,18}?\S)?)\s{8,}(\S.*?)\s*$")


def table_key_row(line):
    s = line.strip()
    if not s or len(s) > 64:
        return False
    m = TABLE_KEY.match(s)
    if not m:
        return False
    right = re.sub(r" {2,}", " ", m.group(2))
    return len(right.split()) <= 6


def unjustify(line):
    if not line.strip():
        return ""
    line = dehyphen_line(line)
    stripped = line.strip()
    if (
        HEXROW.match(line)
        or line.count("|") >= 2
        or "||" in line
        or TABLE_ROW.match(line)
        or wide_gaps(line)
        or table_key_row(line)
        or (COMMAND.match(stripped) and len(stripped) < 70)
        or is_command_line(stripped)
    ):
        return line.rstrip()
    if RULE.match(line.strip()):
        return line.strip()
    m = re.match(r"^(\s*)(.*)$", line.rstrip())
    indent, rest = m.group(1), m.group(2)
    # A full line of body text has spaces inserted to reach the right margin.
    if len(line.rstrip()) >= 68 and "  " in rest and not rest.startswith("|"):
        rest = re.sub(r" {2,}", " ", rest)
    return indent + rest


def is_command_line(s):
    """A console command, or one Z8E command, not a sentence about a command."""
    if CONSOLE.match(s):
        return True
    if Z8E_CMD_OR.match(s):
        return True
    if Z8E_CMD.match(s) and not Z8E_PROSE.search(s):
        return True
    return False


def kind_of(line):
    s = line.strip()
    if not s:
        return "blank"
    if RULE.match(s):
        return "rule"
    if TOC_LINE.match(line):
        return "toc"
    if SECTION.match(s):
        return "section"
    if COMMAND.match(s) and len(s) < 70:
        return "command"
    if is_command_line(s):
        return "pre"
    if HEXROW.match(line) or line.count("|") >= 2 or "||" in line:
        return "pre"
    if len(line) - len(line.lstrip(" ")) >= 8 and ASM_HEAD.match(s):
        return "pre"
    if re.match(r"^\s{8,}(\||[|]{2,}|\|)", line) or s.startswith("|||||"):
        return "pre"
    return "text"


def heading(text, level):
    text = re.sub(r"\s+", " ", text.strip())
    return "#" * level + " " + text


def words_of(text):
    text = text.lower().replace("—", " ").replace("–", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [w for w in text.split() if w]


def slug_of(text):
    return "-".join(words_of(text))


def command_key(text):
    """Single command letter. APPENDIX does not match: the letter must stand alone."""
    m = re.match(r"^\s*([A-Z?>])\s+\S", text, re.I)
    if not m:
        return None
    return m.group(1).upper()


def phrase_in(hay, needle):
    n = len(needle)
    if not n or len(hay) < n:
        return False
    for i in range(len(hay) - n + 1):
        if hay[i:i + n] == needle:
            return True
    return False


def heading_score(title, heading):
    tw = words_of(title)
    hw = words_of(heading)
    score = 0
    if tw == hw:
        score = 100
    elif phrase_in(hw, tw):
        score = 80
    tk = command_key(title)
    hk = command_key(heading)
    if tk and hk == tk:
        score = max(score, 90)
    return score


def find_promote(title, lines):
    """A contents entry with no heading. Short lines become headings; a long
    line that ends with the title gets a heading after it."""
    tw = words_of(title)
    fence = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            fence = not fence
            continue
        if fence or not line.strip():
            continue
        if line.startswith("#") or line.startswith("- ") or line.startswith("<"):
            continue
        lw = words_of(line)
        if len(lw) < len(tw) or lw[-len(tw):] != tw:
            continue
        extra = len(lw) - len(tw)
        if extra == 0 or (extra == 1 and (lw[0].isdigit() or lw[0] == "important")):
            return i, "replace"
        if len(line) > 80:
            return i, "after"
    return None


def link_contents(out, toc_items):
    """Turn the printed contents list into links.

    CommonMark has no index and no heading anchors. An explicit <a id>
    is what GitHub, GitLab, and the usual previews follow.
    """
    if not toc_items:
        return
    used = set()
    for item in toc_items:
        base = slug_of(item["title"]) or "section"
        slug = base
        n = 2
        while slug in used:
            slug = "%s-%d" % (base, n)
            n += 1
        used.add(slug)
        item["slug"] = slug

    def headings():
        found = []
        for i, line in enumerate(out):
            m = re.match(r"^(#{2,3}) +(.+)$", line)
            if m:
                found.append({"index": i, "text": m.group(2)})
        return found

    heads = headings()
    unmatched = []
    taken = set()
    for item in toc_items:
        best = None
        best_score = 0
        for i, h in enumerate(heads):
            if i in taken:
                continue
            score = heading_score(item["title"], h["text"])
            if score > best_score:
                best_score = score
                best = i
        if best is not None and best_score >= 80:
            taken.add(best)
            item["heading"] = heads[best]
        else:
            unmatched.append(item)

    promotions = []
    for item in unmatched:
        found = find_promote(item["title"], out)
        if not found:
            raise SystemExit("contents entry has no target: %s" % item["title"])
        promotions.append((found[0], found[1], item))
    for index, kind, item in sorted(promotions, key=lambda p: p[0], reverse=True):
        if kind == "replace":
            text = out[index].strip()
            out[index:index + 1] = [
                '<a id="%s"></a>' % item["slug"],
                "### " + text,
                "",
            ]
        else:
            block = [
                "",
                '<a id="%s"></a>' % item["slug"],
                "### " + item["title"],
                "",
            ]
            at = index + 1
            if at < len(out) and out[at] == "":
                out[at:at + 1] = block
            else:
                out[at:at] = block
        item["anchored"] = True

    heads = headings()
    inserts = []
    taken = set()
    for item in toc_items:
        if item.get("anchored"):
            continue
        best = None
        best_score = 0
        for i, h in enumerate(heads):
            if i in taken:
                continue
            score = heading_score(item["title"], h["text"])
            if score > best_score:
                best_score = score
                best = i
        if best is None or best_score < 80:
            raise SystemExit("contents entry lost its heading: %s" % item["title"])
        taken.add(best)
        inserts.append((heads[best]["index"], item["slug"]))
    for index, slug in sorted(inserts, reverse=True):
        out.insert(index, '<a id="%s"></a>' % slug)

    for item in toc_items:
        level = 0 if item["indent"] < 2 else 1
        pad = "  " * level
        title = item["title"]
        if title.startswith(">"):
            title = "`>`" + title[1:]
        out[item["index"]] = "%s- [%s](#%s)" % (pad, title, item["slug"])
    last = max(item["index"] for item in toc_items)
    if last + 1 < len(out) and out[last + 1] != "":
        out.insert(last + 1, "")


# A left-column label and the sentence after it. "SYMBOL: Any symbol...".
# A wrapped label has no colon on the first line ("REGISTER" / "INDIRECT:",
# "ARGUMENT-" / "STRINGS:", "CARRIAGE" / "RETURN").
LAB_COLON = re.compile(
    r"^([=A-Z][A-Z0-9+'-]*(?:[ /-][A-Z0-9+'-]+)*)(:)\s+(\S.*)$"
)
LAB_PLAIN = re.compile(
    r"^([=A-Z][A-Z0-9+'-]*(?:[ /-][A-Z0-9+'-]+)*)\s+(\S.*)$"
)
MENU_ITEM = re.compile(
    r"^[A-Z][A-Z0-9+'-]*(?:\s+[A-Z0-9+'-]+)*(?:\s+\([^)]+\))?$"
)
CAPS_TITLE = re.compile(r"^[A-Z][A-Z0-9 '()*.:+/-]*$")
CAUTION_BANNER = re.compile(r"(?:\*\s*){3}CAUTION(?:\s*\*){3}")


def collapse_ws(text):
    return re.sub(r"\s+", " ", text.strip())


def split_label(text, indent):
    """Return (label, has_colon, body) or None.

    A caps word that starts the sentence ("REGISTER Z8E allows...") is given
    back to the body so the label stays the column name. A left-margin line
    such as "IMPORTANT: Coding caveat" is a section title, not a definition.
    """
    if indent < 4:
        return None
    s = collapse_ws(text)
    # "AF - Accumulator and Flag" is a register list, not a heading.
    if re.match(r"^[A-Z0-9+]+\s+-\s+", s):
        return None

    def accept(label, colon, body):
        if (
            not label
            or len(label) > 24
            or len(label.split()) > 4
            or re.search(r"[a-z]", label)
            or ";" in body
            or body.lower().startswith("copyright")
        ):
            return None
        # "LABEL: OPCODE OPERAND" is a column header.
        if not re.search(r"[a-z]", body) and len(body.split()) <= 3 and len(body) < 24:
            return None
        return label, colon, body

    m = LAB_COLON.match(s)
    if m:
        return accept(m.group(1), True, m.group(3))
    m = LAB_PLAIN.match(s)
    if not m:
        return None
    label, body = m.group(1), m.group(2)
    while label and not body[:1].isupper() and " " in label:
        head, _, tail = label.rpartition(" ")
        body = tail + " " + body
        label = head
    return accept(label, False, body)


def is_menu_item(text):
    s = collapse_ws(text)
    return 3 <= len(s) <= 42 and bool(MENU_ITEM.fullmatch(s))


def caps_title(text):
    """A standalone all-caps line used as a title. None when it is a sentence."""
    s = collapse_ws(text)
    if CAUTION_BANNER.fullmatch(s):
        return "CAUTION"
    if len(s) < 3 or len(s) > 52 or s.endswith("."):
        return None
    # "LABEL: OPCODE OPERAND" is a column header, not a title.
    if ":" in s and not s.endswith(":"):
        return None
    if any(c.islower() for c in s):
        return None
    # An address or an opcode byte run. "V3.44" is a version, not a dump.
    if re.search(r"\d{3,}", s) and "V" not in s:
        return None
    if not CAPS_TITLE.fullmatch(s) or not re.search(r"[A-Z]{2,}", s):
        return None
    return s.rstrip(":")


def join_labels(left, right):
    if left.endswith("-"):
        return left + right
    return left + " " + right


def main():
    raw = SRC.read_text(encoding="latin1").replace("\r\n", "\n").replace("\r", "\n")
    # 0x1E is a WordStar soft hyphen. Remove it before any line split.
    raw = re.sub(r"\x1e +", "", raw).replace("\x1e", "")
    pages = [strip_page(p) for p in raw.split("\f")]
    lines = []
    for i, page in enumerate(pages):
        if i:
            lines.append("")
        lines.extend(unjustify(l) for l in page)

    out = [
        heading("Z8E", 1),
        "",
        "Z80/HD64180 assembly language debugging tool. "
        "User's manual, formatted from `z8e.man`. "
        "In this tree the assembly source is `z8e.asm`.",
        "",
    ]
    i = 0
    n = len(lines)
    # Skip the centered title block; the markdown title replaces it.
    while i < n and (not lines[i].strip() or lines[i].strip() in {
        "Z8E",
        "Z80/HD64180 ASSEMBLY LANGUAGE DEBUGGING TOOL",
        "USER'S MANUAL",
    } or lines[i].startswith(" " * 10) and len(lines[i].strip()) < 40):
        # Keep the copyright block once real sentences start. Stop at TOC.
        if lines[i].strip() == "TABLE OF CONTENTS":
            break
        if lines[i].strip().startswith("Copyright") or lines[i].strip().startswith("This document"):
            break
        i += 1

    para = []
    past_toc = False
    in_summary = False
    in_messages = False
    toc_items = []

    def flush_para():
        if not para:
            return
        parts = []
        for chunk in para:
            if parts and parts[-1].endswith("-") and chunk.lstrip()[:1].islower():
                parts[-1] = parts[-1][:-1] + chunk.lstrip()
            else:
                if parts:
                    parts.append(chunk.strip())
                else:
                    parts.append(chunk.strip())
        text = " ".join(parts)
        text = re.sub(r" +", " ", text)
        out.append(text)
        out.append("")
        para.clear()

    def heading_command(at):
        if kind_of(lines[at]) != "command":
            return False
        j = at + 1
        while j < n and not lines[j].strip():
            j += 1
        return j < n and kind_of(lines[j]) == "rule"

    def keep_literal(at):
        """A display row: instruction, console command, or a column that is
        not a command-section heading."""
        if at >= n or not lines[at].strip():
            return False
        if heading_command(at):
            return False
        knd = kind_of(lines[at])
        if knd == "pre":
            return True
        # A single letter followed by a wide gap is a table row (error flag,
        # flag bit, disassembly format). A letter that merely starts a
        # wrapped sentence is not.
        if knd == "command" and re.search(r" {4,}", lines[at].strip()):
            return True
        if table_key_row(lines[at]):
            return True
        return wide_gaps(lines[at])

    while i < n:
        line = lines[i]
        k = kind_of(line)
        if k == "blank":
            nxt = i + 1
            while nxt < n and not lines[nxt].strip():
                nxt += 1
            if (
                para
                and nxt < n
                and kind_of(lines[nxt]) == "text"
                and lines[nxt].strip()[:1].islower()
                and not re.search(r"[.!?:)\"]$", para[-1].rstrip())
            ):
                i += 1
                continue
            flush_para()
            i += 1
            continue
        if k == "rule":
            flush_para()
            i += 1
            continue
        if k == "section":
            flush_para()
            title = re.sub(r"\s+", " ", line.strip())
            if title.upper().endswith("COMMAND SUMMARY"):
                title = "APPENDIX E - COMMAND SUMMARY"
                in_summary = True
            out.append(heading(title, 2))
            out.append("")
            i += 1
            continue
        if in_summary:
            flush_para()
            block = []
            while i < n:
                s = lines[i].strip()
                if "COPYRIGHT" in s.upper():
                    break
                if s:
                    block.append(lines[i].rstrip())
                i += 1
            out.append("```")
            out.extend(block)
            out.append("```")
            out.append("")
            in_summary = False
            continue
        if k == "command":
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n and kind_of(lines[j]) == "rule":
                flush_para()
                m = COMMAND.match(line.strip())
                letter = m.group(1)
                # ">" starts a Markdown blockquote, so the command character
                # has to be code or the heading and the contents entry lose it.
                if letter == ">":
                    letter = "`>`"
                out.append(heading("%s — %s" % (letter, m.group(2).strip()), 2))
                out.append("")
                i = j + 1
                continue
        if k == "toc":
            flush_para()
            m = TOC_LINE.match(line)
            title = re.sub(r"\s+", " ", m.group(2).strip())
            toc_items.append({
                "index": len(out),
                "title": title,
                "indent": len(m.group(1).replace("\t", "    ")),
            })
            out.append("- " + title)
            i += 1
            continue
        if keep_literal(i):
            flush_para()
            block = []
            while i < n and keep_literal(i):
                row_indent = len(lines[i]) - len(lines[i].lstrip(" "))
                # A *Q (or *E, *N) sample is the command plus the lines under
                # it: the port or memory read, and the key or string typed.
                # Those lines share the command's indent, so they are not a
                # new paragraph.
                sample = lines[i].strip()
                if (
                    is_command_line(sample)
                    and sample.startswith("*")
                    and i + 1 < n
                    and lines[i + 1].strip()
                    and (len(lines[i + 1]) - len(lines[i + 1].lstrip(" "))) >= row_indent
                ):
                    def shift(text, n=row_indent):
                        text = text.rstrip()
                        if text.startswith(" " * n):
                            return text[n:]
                        return text.lstrip()

                    block.append(shift(lines[i]))
                    i += 1
                    while i < n and lines[i].strip():
                        ind = len(lines[i]) - len(lines[i].lstrip(" "))
                        if ind < row_indent or kind_of(lines[i]) in ("section", "toc", "rule"):
                            break
                        block.append(shift(lines[i]))
                        i += 1
                    continue
                # Hex and instruction rows stay as they are. A command or
                # column row may wrap onto more-indented lines.
                row_wraps = not HEXROW.match(lines[i]) and (
                    kind_of(lines[i]) == "command"
                    or wide_gaps(lines[i])
                    or table_key_row(lines[i])
                )
                raw = lines[i].rstrip()
                if is_command_line(raw.strip()):
                    raw = re.sub(r" {2,}", " ", raw.strip())
                was_hex = bool(HEXROW.match(lines[i]))
                block.append(raw)
                i += 1
                if row_wraps:
                    while i < n and lines[i].strip() and not keep_literal(i):
                        ind = len(lines[i]) - len(lines[i].lstrip(" "))
                        kk = kind_of(lines[i])
                        if ind <= row_indent or kk in ("section", "toc", "rule", "command"):
                            break
                        tail = lines[i].rstrip()
                        pad, rest = re.match(r"^(\s*)(.*)$", tail).groups()
                        block.append(pad + re.sub(r" {2,}", " ", rest))
                        i += 1
                # Up to two blanks: a page break is one extra blank line.
                if was_hex:
                    continue
                blanks = 0
                j = i
                while j < n and not lines[j].strip() and blanks < 3:
                    blanks += 1
                    j += 1
                if (
                    blanks
                    and j < n
                    and keep_literal(j)
                    and not HEXROW.match(lines[j])
                ):
                    block.append("")
                    i = j
            out.append("```")
            out.extend(block)
            out.append("```")
            out.append("")
            continue
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if stripped in ("STATUS MESSAGES", "ERROR MESSAGES"):
            flush_para()
            in_messages = True
            out.append(heading(stripped, 3))
            out.append("")
            i += 1
            continue
        if in_messages and STATUS_MSG.match(stripped) and len(stripped) <= 45:
            flush_para()
            out.append("```")
            out.append(re.sub(r" {2,}", " ", stripped))
            out.append("```")
            out.append("")
            i += 1
            continue
        if in_messages and stripped and indent == 0:
            in_messages = False
        if MEM_LINE.match(stripped):
            flush_para()
            block = []
            while i < n and MEM_LINE.match(lines[i].strip()):
                block.append(re.sub(r" {2,}", " ", lines[i].strip()))
                i += 1
            out.append("```")
            out.extend(block)
            out.append("```")
            out.append("")
            continue
        if stripped == "TABLE OF CONTENTS":
            flush_para()
            past_toc = True
            out.append(heading("TABLE OF CONTENTS", 2))
            out.append("")
            i += 1
            continue
        if (
            not past_toc
            and indent >= 10
            and 0 < len(stripped) < 45
            and not stripped.startswith("*")
        ):
            flush_para()
            out.append(stripped)
            out.append("")
            i += 1
            continue
        if WHERE_ARG.match(stripped):
            flush_para()
            base = indent

            def row_indent(at):
                return len(lines[at]) - len(lines[at].lstrip(" "))

            def row_text(at):
                return re.sub(r" +", " ", lines[at].strip())

            # Names line up at most 9 columns past the "where" line.
            # "1)", "NOTE:", and "arguments" are labels even when deeper.
            def is_def(text, ind):
                if not DEF_HEAD.match(text):
                    return False
                if DEF_LABEL.match(text):
                    return True
                return ind <= base + 9

            def leaves_where(at):
                s = lines[at].strip()
                if not s:
                    return False
                ind = row_indent(at)
                if ind < base:
                    return True
                if s.startswith("*") or "CAUTION" in s:
                    return True
                if kind_of(lines[at]) in ("section", "command", "toc", "rule", "pre"):
                    return True
                return keep_literal(at)

            def join_wrap(prev, row):
                if prev.endswith("-") and row[:1].islower():
                    return prev[:-1] + row
                if prev.endswith("-") and row[:1].isupper():
                    return prev + row
                return prev + " " + row

            rows = []
            while i < n:
                if not lines[i].strip():
                    j = i
                    while j < n and not lines[j].strip():
                        j += 1
                    if j >= n or leaves_where(j):
                        break
                    # A blank, then prose at the paragraph margin, ends the
                    # definitions. "Note that..." is that prose.
                    if row_indent(j) <= base and not is_def(row_text(j), row_indent(j)):
                        break
                    rows.append(None)
                    i = j
                    continue
                if rows and leaves_where(i):
                    break
                rows.append((row_text(i), row_indent(i)))
                i += 1
            if rows and rows[0][0].lower().startswith("where "):
                rows[0] = (rows[0][0].split(" ", 1)[1].strip(), rows[0][1])
            items = []
            for row in rows:
                if row is None:
                    if items and not items[-1].endswith("\n"):
                        items[-1] += "\n"
                    continue
                text, ind = row
                if not items or is_def(text, ind):
                    if items and items[-1].endswith("\n"):
                        items[-1] = items[-1][:-1]
                    items.append(text)
                    continue
                if items[-1].endswith("\n"):
                    items[-1] = items[-1][:-1] + "\n\n" + text
                else:
                    items[-1] = join_wrap(items[-1], text)
            if items and items[-1].endswith("\n"):
                items[-1] = items[-1][:-1]
            out.append("where:")
            out.append("")
            for item in items:
                parts = item.split("\n\n")
                out.append("- " + parts[0])
                for part in parts[1:]:
                    out.append("")
                    out.append("  " + part)
                out.append("")
            continue
        # Four resident-size rows. They are a table, not one sentence.
        if re.search(r"\bkBytes\s*$", stripped, re.I) and indent >= 4:
            flush_para()
            block = []
            while i < n and re.search(r"\bkBytes\s*$", lines[i].strip(), re.I):
                block.append(re.sub(r" {2,}", "  ", lines[i].strip()))
                i += 1
            out.append("```")
            out.extend(block)
            out.append("```")
            out.append("")
            continue
        # Titles and definition labels only at the start of a paragraph, so a
        # wrapped all-caps sentence is not split into headings.
        if not para:
            if is_menu_item(stripped):
                j = i
                items = []
                while j < n and lines[j].strip() and is_menu_item(lines[j].strip()):
                    items.append(collapse_ws(lines[j]))
                    j += 1
                if len(items) >= 2:
                    flush_para()
                    for item in items:
                        out.append("- " + item)
                    out.append("")
                    i = j
                    continue
            got = split_label(stripped, indent)
            if got and got[2][:1].isupper():
                label, colon, body = got
                nxt = i + 1
                if not colon and nxt < n and lines[nxt].strip():
                    more = split_label(
                        lines[nxt].strip(),
                        len(lines[nxt]) - len(lines[nxt].lstrip(" ")),
                    )
                    if more and more[2][:1].islower():
                        label = join_labels(label, more[0])
                        body = body + " " + more[2]
                        i = nxt
                flush_para()
                out.append(heading(label, 3))
                out.append("")
                para.append(body)
                i += 1
                continue
            title = caps_title(stripped)
            if title:
                flush_para()
                out.append(heading(title, 3))
                out.append("")
                i += 1
                continue
        # Body text. Drop a pure indent that is only spacing around a heading.
        para.append(line.strip())
        i += 1
    flush_para()
    link_contents(out, toc_items)

    # Collapse 3+ blank lines and a blank line before a list that got split.
    text = "\n".join(out)
    text = text.replace('the ">" command', "the `>` command")
    text = re.sub(r"\n{3,}", "\n\n", text)
    # The command summary header is a one-line block above the rows.
    text = re.sub(r"```\n\n```\n(?=CMD | [A-Z?>] |\[)", "", text)
    text = text.rstrip() + "\n"
    missing = [
        item["title"] for item in toc_items
        if ('<a id="%s"></a>' % item["slug"]) not in text
    ]
    if missing:
        raise SystemExit("contents anchors missing: %s" % ", ".join(missing))
    DST.write_text(text, encoding="utf-8")
    print("wrote %s (%d lines, %d contents links)" % (
        DST, text.count("\n") + 1, len(toc_items)))


if __name__ == "__main__":
    main()
