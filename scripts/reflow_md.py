#!/usr/bin/env python3
import sys
from pathlib import Path

def reflow(md_text):
    out_lines = []
    in_code = False
    in_fm = False
    buffer = []

    def flush_buf():
        if not buffer:
            return
        # join buffer with single spaces then wrap conservatively
        joined = " ".join(line.strip() for line in buffer)
        out_lines.append(joined)
        buffer.clear()

    for line in md_text.splitlines():
        stripped = line.rstrip("\n")
        if stripped.startswith("```"):
            flush_buf()
            in_code = not in_code
            out_lines.append(stripped)
            continue
        if in_code:
            out_lines.append(stripped)
            continue
        if stripped.startswith("---") and not in_fm:
            # toggle frontmatter (simple heuristic)
            in_fm = True
            flush_buf()
            out_lines.append(stripped)
            continue
        if in_fm:
            out_lines.append(stripped)
            if stripped.strip() == "---":
                in_fm = False
            continue

        # preserve headings, lists, blockquotes, tables, html tags
        if stripped.strip() == "" or stripped.lstrip().startswith(("#", "-", "*", ">", "|", "<")):
            flush_buf()
            out_lines.append(stripped)
            continue

        # normal paragraph line -> buffer
        buffer.append(stripped)

    flush_buf()
    return "\n".join(out_lines) + "\n"


def process_file(p: Path, inplace=True):
    text = p.read_text(encoding="utf-8")
    new = reflow(text)
    if text != new:
        if inplace:
            p.write_text(new, encoding="utf-8")
            print(f"Reflowed: {p}")
        else:
            print(new)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reflow_md.py <file-or-dir> ...")
        sys.exit(1)
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            for f in p.rglob("*.md"):
                process_file(f)
        elif p.is_file():
            process_file(p)
        else:
            print("Not found:", arg)
