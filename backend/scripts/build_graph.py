"""pages.json -> concept graph, from the command line.

Usage (run from backend/):
  python scripts/build_graph.py out/cs3151_m04/pages.json
  python scripts/build_graph.py out/cs3151_m04/pages.json --llm-file saved_answer.json   # offline

Reads the pages.json produced by scripts/parse_lecture.py. Only pages with
page_type == "content" are sent to the model (outcomes/quiz/outlook/references/
blank/title pages are not lecture content). Writes, next to pages.json:
  graph.json  the concept graph
  graph.md    Mermaid diagram of the graph (renders on GitHub / VS Code)
  raw/<prompt_version>_<n>.json   every raw model reply, for debugging/caching
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND / ".env")  # LLM_PROVIDER / LLM_MODEL / LLM_API_KEY; real env vars win
sys.path.insert(0, str(BACKEND))

from app.concepts.extract import PROMPT_VERSION, extract_graph  # noqa: E402
from app.concepts.graph_check import to_mermaid  # noqa: E402
from app.llm import FileLLM, make_llm  # noqa: E402
from app.retrieval.pdf_parser import Page  # noqa: E402


def records_to_content_pages(records: list[dict]) -> list[Page]:
    """PageRecord dicts (page_type == 'content' only) -> Page objects for extract_graph."""
    return [
        Page(
            page=r["page"],
            slide_no=r.get("slide_no"),
            title=r.get("title") or "",
            text=r["rich_text"],
            needs_vision=False,
        )
        for r in records
        if r.get("page_type") == "content" and r.get("rich_text")
    ]


def load_content_pages(pages_json: Path) -> list[Page]:
    records = json.loads(pages_json.read_text(encoding="utf-8"))
    return records_to_content_pages(records)


class CachingLLM:
    """Wraps an LLM: caches raw replies to raw/<prompt_version>_<n>.json.

    A cache hit requires the (pages_hash, prompt_version, model) key to also
    match what's recorded in the sidecar .meta.json -- otherwise the call is
    repeated and the file is overwritten.
    """

    def __init__(self, inner, raw_dir: Path, pages_hash: str, prompt_version: str, model: str):
        self.inner = inner
        self.raw_dir = raw_dir
        self.prompt_version = prompt_version
        self.key = {"pages_hash": pages_hash, "prompt_version": prompt_version, "model": model}
        self.n = 0

    def complete_json(self, system: str, user: str) -> str:
        self.n += 1
        raw_path = self.raw_dir / f"{self.prompt_version}_{self.n}.json"
        meta_path = self.raw_dir / f"{self.prompt_version}_{self.n}.meta.json"

        if raw_path.exists() and meta_path.exists():
            if json.loads(meta_path.read_text(encoding="utf-8")) == self.key:
                return raw_path.read_text(encoding="utf-8")

        raw = self.inner.complete_json(system, user)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(raw, encoding="utf-8")
        meta_path.write_text(json.dumps(self.key), encoding="utf-8")
        return raw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pages_json")
    ap.add_argument("--llm-file", help="use a saved LLM answer instead of calling the API")
    args = ap.parse_args()

    pages_json = Path(args.pages_json)
    out = pages_json.parent
    raw_dir = out / "raw"

    pages = load_content_pages(pages_json)
    print(f"{len(pages)} content pages sent to the model")

    pages_hash = hashlib.sha256(pages_json.read_bytes()).hexdigest()[:16]
    if args.llm_file:
        model = "offline"
        base_llm = FileLLM(args.llm_file)
    else:
        model = os.environ.get("LLM_MODEL", "unknown")
        base_llm = make_llm()
    llm = CachingLLM(base_llm, raw_dir, pages_hash, PROMPT_VERSION, model)

    graph = extract_graph(pages, llm)
    (out / "graph.json").write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    (out / "graph.md").write_text(
        f"# Concept graph ({PROMPT_VERSION})\n\n```mermaid\n{to_mermaid(graph)}\n```\n", encoding="utf-8"
    )
    n_edges = sum(len(c.prerequisites) for c in graph.concepts)
    print(f"{len(graph.concepts)} concepts, {n_edges} edges -> {out}/graph.json, graph.md")


if __name__ == "__main__":
    main()
