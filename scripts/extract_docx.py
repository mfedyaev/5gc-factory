#!/usr/bin/env python3
# stdlib-2026-09-16 — no python-docx. If this file still has "from docx import", it is a stale Context copy.
"""Turn a 3GPP DOCX into Markdown extracts (pipeline artifact).

Writes to 5gc-factory/extracts/. Ollama cannot open Word; this is the cut step.
Stdlib only (zipfile + XML). No python-docx.

Examples (from 5gc-factory/):
  python scripts/extract_docx.py corpus/29510-ib0.docx --outline --out 29510-headings.md
  python scripts/extract_docx.py corpus/29510-ib0.docx --keep 5.2.2.2,5.3.2.2 --out nrf-register.md
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W_VAL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"


def p_text(p) -> str:
    return "".join(t.text or "" for t in p.findall(".//w:t", NS)).strip()


def p_style(p) -> str:
    s = p.find("w:pPr/w:pStyle", NS)
    return (s.get(W_VAL) or "") if s is not None else ""


def heading_level(style: str) -> int | None:
    s = (style or "").replace("Heading", "Heading ").replace("  ", " ").strip()
    if s.startswith("Heading"):
        try:
            return int(s.split()[-1])
        except ValueError:
            return None
    if s == "H6":
        return 6
    return None


def tidy_heading(text: str) -> str:
    t = re.sub(r" {2,}", " ", text.replace("\t", " ").strip())
    # "4.2.2Network" / "6.2.1AMF" — dotted clause number glued to title
    return re.sub(r"^(\d+(?:\.\d+)+[a-z]?)([A-Z].*)$", r"\1 \2", t)


def clause_num(heading_text: str) -> str:
    t = tidy_heading(heading_text)
    m = re.match(r"^(\d+(?:\.\d+)*[a-zA]?)\b", t)
    return m.group(1) if m else t.split(" ", 1)[0]


def tbl_text(tbl) -> str:
    rows: list[str] = []
    for tr in tbl.findall("w:tr", NS):
        cells = []
        for tc in tr.findall("w:tc", NS):
            cell = " ".join(p_text(p) for p in tc.findall("w:p", NS) if p_text(p))
            cells.append(cell.replace("|", "/"))
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    cols = rows[0].count("|") - 1
    sep = "| " + " | ".join(["---"] * max(cols, 1)) + " |"
    return "\n".join([rows[0], sep, *rows[1:]])


def parse_docx(path: Path) -> list[tuple[str, str, str, int | None]]:
    """Return blocks: (kind, style, text, heading_level). Skip TOC paragraphs."""
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as e:
        raise SystemExit(f"not a DOCX (need word/document.xml): {path}: {e}") from e
    root = ET.fromstring(xml)
    body = root.find("w:body", NS)
    if body is None:
        raise SystemExit(f"no w:body in {path}")
    blocks: list[tuple[str, str, str, int | None]] = []
    for child in list(body):
        tag = child.tag.split("}")[-1]
        if tag == "p":
            st = p_style(child)
            if st.lower().startswith("toc"):
                continue
            tx = p_text(child)
            if not tx:
                continue
            lvl = heading_level(st)
            if lvl:
                blocks.append(("h", st, tidy_heading(tx), lvl))
            else:
                blocks.append(("p", st, tx, None))
        elif tag == "tbl":
            tx = tbl_text(child)
            if tx:
                blocks.append(("tbl", "", tx, None))
    return blocks


def md_heading(text: str, lvl: int) -> str:
    return "#" * min(lvl, 6) + " " + text


def render_body(kind: str, style: str, text: str) -> str:
    if kind == "tbl":
        return text
    if style == "B1" and not text.startswith("-"):
        return f"- {text.lstrip('-').strip()}"
    if style == "NO" or text.startswith("NOTE"):
        return f"> {text}"
    return text


def wanted(num: str, keep: list[str]) -> bool:
    for prefix in keep:
        if num == prefix or num.startswith(prefix + "."):
            return True
    return False


FACTORY = Path(__file__).resolve().parents[1]
EXTRACTS = FACTORY / "extracts"


def resolve_out_file(name: Path, out_dir: Path) -> Path:
    """--out file. Bare name lands in out-dir; paths with a parent stay as given."""
    p = name.expanduser()
    if p.suffix.lower() != ".md":
        p = p.with_name(p.name + ".md")
    if p.parent == Path("."):
        dest = (out_dir / p.name).resolve()
    else:
        dest = p.resolve()
    if dest.exists() and dest.is_dir():
        raise SystemExit(f"--out is a directory; pass a file name: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def main() -> None:
    print("extract_docx stdlib-2026-09-16", Path(__file__).resolve(), flush=True)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("docx", type=Path)
    ap.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="Default: 5gc-factory/extracts",
    )
    ap.add_argument(
        "--outline",
        action="store_true",
        help="Write only {stem}-outline.md (heading tree). Do not write full or slice.",
    )
    ap.add_argument(
        "--keep",
        default="",
        help="Comma-separated clause prefixes for a slice file, e.g. 5.2.2.2,5.3.2.2",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output Markdown file for this run (outline, slice if --keep, else full). "
        "Bare name goes in --out-dir. Does not rewrite other extract files.",
    )
    args = ap.parse_args()

    src = args.docx.expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"not found: {src}")

    keep = [k.strip() for k in args.keep.split(",") if k.strip()]
    if args.outline and keep:
        raise SystemExit(
            "--outline is outline-only; pick clauses, then run again with --keep (no --outline)"
        )

    out_dir = (args.out_dir or EXTRACTS).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    blocks = parse_docx(src)

    named = resolve_out_file(args.out, out_dir) if args.out else None

    if args.outline:
        headings = [(lvl, tx) for kind, _st, tx, lvl in blocks if kind == "h" and lvl]
        outline = [
            f"# {stem} — heading outline",
            "",
            f"Derived from `{src.name}`. Open in an editor; do not open the DOCX in Word.",
            "",
        ]
        for lvl, tx in headings:
            outline.append("  " * (lvl - 1) + f"- {tx}")
        path = named or (out_dir / f"{stem}-outline.md")
        path.write_text("\n".join(outline) + "\n", encoding="utf-8")
        print(f"outline  {path}")
        return

    def write_full(path: Path) -> None:
        full = [
            f"# {stem} — text extract",
            "",
            f"Derived from `{src.name}`. Figures omitted. Tables as markdown.",
            "© 3GPP Organizational Partners — local PoC copy only, do not publish.",
            "",
        ]
        for kind, st, tx, lvl in blocks:
            if kind == "h":
                full.extend(["", md_heading(tx, lvl or 1), ""])
            else:
                full.extend([render_body(kind, st, tx), ""])
        path.write_text("\n".join(full) + "\n", encoding="utf-8")

    def write_slice(path: Path) -> None:
        slice_lines = [
            f"# {stem} — clause slice",
            "",
            "Kept prefixes: " + ", ".join(keep),
            "",
        ]
        in_want = False
        want_lvl = 99
        for kind, st, tx, lvl in blocks:
            if kind == "h":
                if wanted(clause_num(tx), keep):
                    in_want = True
                    want_lvl = lvl or 1
                    slice_lines.extend(["", md_heading(tx, min(lvl or 1, 6)), ""])
                elif in_want and lvl is not None and lvl <= want_lvl:
                    in_want = False
                continue
            if in_want:
                slice_lines.extend([render_body(kind, st, tx), ""])
        path.write_text("\n".join(slice_lines) + "\n", encoding="utf-8")

    if named is not None:
        if keep:
            write_slice(named)
            print(f"slice    {named}")
        else:
            write_full(named)
            print(f"full     {named}")
        return

    full_path = out_dir / f"{stem}.md"
    write_full(full_path)
    print(f"full     {full_path}")
    if keep:
        slice_path = out_dir / f"{stem}-slice.md"
        write_slice(slice_path)
        print(f"slice    {slice_path}")


if __name__ == "__main__":
    main()
