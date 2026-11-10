"""Turn one page's vision-model elements into rich text + extracted fields."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class VisionPageContent:
    rich_text: str
    title: str | None
    slide_no: int | None
    formulas: list[str] = field(default_factory=list)
    figures: list[str] = field(default_factory=list)
    uncertain: list[str] = field(default_factory=list)


def _is_slide_number(element: dict) -> bool:
    if element.get("type") != "text":
        return False
    content = (element.get("content") or "").strip()
    return content.isdigit()


_NO_SPACE_BEFORE = ",.;:!?)]}’”"


def _append_piece(current_line: list[str], piece: str) -> None:
    if not piece:
        return
    if not current_line:
        current_line.append(piece)
        return

    prev = current_line[-1]
    needs_space = not (
        prev.endswith((" ", "\n")) or piece.startswith((" ", "\n")) or piece[0] in _NO_SPACE_BEFORE
    )
    if needs_space:
        current_line.append(" ")
    current_line.append(piece)


def merge_page_elements(elements: list[dict]) -> VisionPageContent:
    ordered = sorted(elements, key=lambda el: el.get("order", 0))

    lines: list[str] = []
    current_line: list[str] = []
    title: str | None = None
    slide_no: int | None = None
    formulas: list[str] = []
    figures: list[str] = []
    uncertain: list[str] = []
    previous_type: str | None = None

    def flush_line() -> None:
        if current_line:
            lines.append("".join(current_line))
            current_line.clear()

    for element in ordered:
        kind = element.get("type")
        uncertain.extend(element.get("uncertain") or [])

        if kind == "uncertain":
            uncertain.append(element.get("content", ""))
            continue

        if kind == "code_marker":
            continue

        if _is_slide_number(element):
            if slide_no is None:
                slide_no = int(element["content"].strip())
            continue

        if kind == "heading":
            flush_line()
            heading_text = element.get("content", "")
            lines.append(heading_text)
            if title is None:
                title = heading_text
            previous_type = kind
            continue

        if kind == "formula":
            flush_line()
            latex = element.get("latex", "")
            formulas.append(latex)
            lines.append(f"$${latex}$$")
            previous_type = kind
            continue

        if kind == "figure":
            flush_line()
            description = element.get("description", "")
            figures.append(description)
            lines.append(f"[Figure: {description}]")
            previous_type = kind
            continue

        if kind == "code":
            flush_line()
            lines.append(f"```\n{element.get('content', '')}\n```")
            previous_type = kind
            continue

        if kind in ("text", "inline_formula"):
            if kind == "inline_formula":
                piece = f"${element.get('latex', '')}$"
                formulas.append(element.get("latex", ""))
            else:
                piece = element.get("content", "")

            if kind == "text" and previous_type != "inline_formula":
                flush_line()

            _append_piece(current_line, piece)
            previous_type = kind
            continue

        previous_type = kind

    flush_line()

    return VisionPageContent(
        rich_text="\n".join(lines),
        title=title,
        slide_no=slide_no,
        formulas=formulas,
        figures=figures,
        uncertain=uncertain,
    )
