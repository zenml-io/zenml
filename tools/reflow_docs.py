import sys
from pathlib import Path

def reflow(text):
    out = []
    buf = []
    in_code = False

    def flush():
        if buf:
            out.append(" ".join(line.strip() for line in buf))
            buf.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            flush()
            in_code = not in_code
            out.append(line)
            continue

        if in_code:
            out.append(line)
            continue

        # keep headers, lists, tables, empty lines
        if (
            line.strip() == ""
            or line.lstrip().startswith(("#", "-", "*", ">", "|"))
        ):
            flush()
            out.append(line)
            continue

        # otherwise, part of a paragraph
        buf.append(line)

    flush()
    return "\n".join(out) + "\n"


def process(path):
    text = path.read_text(encoding="utf-8")
    new = reflow(text)
    if text != new:
        path.write_text(new, encoding="utf-8")
        print("FIXED:", path)


if __name__ == "__main__":
    docs_dir = Path("docs")
    for md in docs_dir.rglob("*.md"):
        process(md)
PY
