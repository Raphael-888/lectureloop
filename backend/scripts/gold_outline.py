#!/usr/bin/env python3
"""CLI: list content-page titles and formulas, to help hand-write a gold outline.

Usage:
    python scripts/gold_outline.py PDF_PATH --vision VISION_JSON

Writes out/<pdf filename>/gold_outline.md. Concepts are never written here —
the gold standard (tests/fixtures/gold/<name>.json) must be authored by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.merge import merge
from app.retrieval.pdf_parser import parse_pdf


def render_outline(records) -> str:
    lines = ["# Gold outline (content pages only)", ""]

    for record in records:
        if record.page_type != "content":
            continue

        lines.append(f"## Page {record.page} — {record.title or '(untitled)'}")
        for formula in record.formulas:
            lines.append(f"- `{formula}`")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path, help="Path to the lecture PDF")
    parser.add_argument("--vision", type=Path, required=True, help="Path to the vision-model JSON")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: out/<pdf filename>)",
    )
    args = parser.parse_args()

    pages = parse_pdf(args.pdf_path)
    vision = json.loads(args.vision.read_text(encoding="utf-8"))
    records = merge(pages, vision)

    out_dir = args.out_dir or (Path(__file__).resolve().parents[1] / "out" / args.pdf_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    outline_path = out_dir / "gold_outline.md"
    outline_path.write_text(render_outline(records), encoding="utf-8")

    print(f"内容页数：{sum(1 for r in records if r.page_type == 'content')}")
    print(f"大纲文件：{outline_path}")


if __name__ == "__main__":
    main()
