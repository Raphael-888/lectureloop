#!/usr/bin/env python3
"""CLI: run the DeepSeek vision parser over a lecture PDF, resumably.

Usage:
    python scripts/run_vision.py PDF_PATH --output OUT.json [--model MODEL] [--prompt-version V]

Reads the DeepSeek API key from the DEEPSEEK_API_KEY environment variable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval.vision import MODEL_NAME, PROMPT_VERSION, run_vision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path, help="Path to the lecture PDF")
    parser.add_argument("--output", type=Path, required=True, help="Path to write the vision JSON")
    parser.add_argument("--model", default=MODEL_NAME, help="Vision model name")
    parser.add_argument("--prompt-version", default=PROMPT_VERSION, help="Prompt version tag")
    args = parser.parse_args()

    result = run_vision(
        pdf_path=args.pdf_path,
        output_path=args.output,
        model=args.model,
        prompt_version=args.prompt_version,
    )

    success = sum(1 for p in result["pages"] if p.get("status") == "success")
    failed = [p["page"] for p in result["pages"] if p.get("status") == "failed"]

    print(f"PDF 总页数：{result['total_pages']}")
    print(f"成功页数：{success}")
    print(f"失败页数：{len(failed)}")
    if failed:
        print(f"失败页码：{failed}")
    print(f"结果文件：{args.output}")


if __name__ == "__main__":
    main()
