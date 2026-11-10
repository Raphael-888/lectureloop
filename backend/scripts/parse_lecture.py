#!/usr/bin/env python3
"""CLI: merge a lecture PDF's text layer with its vision-model reading.

Usage:
    python scripts/parse_lecture.py PDF_PATH --vision VISION_JSON

Writes out/<pdf filename>/pages.json (PageRecord list) and pages.md (a
human-readable outline).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.merge import merge
from app.retrieval.pdf_parser import parse_pdf


def render_markdown(records) -> str:
    lines = [f"# Pages ({len(records)} total)", ""]

    for record in records:
        lines.append(f"## Page {record.page} — {record.page_type}")
        if record.title:
            lines.append(f"**Title:** {record.title}")
        lines.append("")
        lines.append(record.rich_text or "*(empty)*")
        lines.append("")

        if record.formulas:
            lines.append("**Formulas:**")
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

    pages_json = out_dir / "pages.json"
    pages_json.write_text(
        json.dumps(
            [record.model_dump() for record in records],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pages_md = out_dir / "pages.md"
    pages_md.write_text(render_markdown(records), encoding="utf-8")

    print(f"页数：{len(records)}")
    print(f"JSON：{pages_json}")
    print(f"Markdown：{pages_md}")


if __name__ == "__main__":
    main()
