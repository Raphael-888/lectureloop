"""Vision-model PDF reading (DeepSeek), resumable per page.

Moved here from the repo-root `parse_pdf.py` prototype. Resume matching now
keys on the PDF's sha256 + model name + prompt version instead of the PDF's
filename, so renaming or moving the source file doesn't throw away progress.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pymupdf
from openai import OpenAI

MODEL_NAME = "deepseek-flash"
PROMPT_VERSION = "1.1-deepseek"
MAX_IMAGE_SIZE = 30 * 1024 * 1024

PROMPT = """你是一名专业的 PDF 页面视觉解析助手。

你的任务是完整识别当前页面中的文字、数学公式、图表和代码内容。

【一、数学公式识别规则】

1. 严格区分相似的数学符号，例如 w_1、w_0、w_q、v_1。
2. 不得根据上下文擅自修改公式符号。
3. 保留所有上下标、求和符号、分数、括号和运算符。
4. 独立公式使用 formula 类型。
5. 句子中的公式使用 inline_formula 类型。
6. 公式使用 LaTeX 格式。
7. 无法确认的符号不得猜测，必须在 uncertain 字段中说明。

【二、图表识别规则】

1. 分别识别横轴和纵轴标签。
2. 不得混淆坐标轴及其变量。
3. 尽可能识别标题、图例、颜色、数据点和曲线。
4. 描述图表表达的主要信息。
5. 无法准确读取的内容标记为 uncertain。
6. 不得编造图表中没有显示的数据。

【三、内容分类】

每个元素必须属于以下类型之一：

heading：标题
text：普通文字
formula：独立数学公式
inline_formula：行内数学公式
figure：图表或示意图
code_marker：代码区域标记
code：实际可见的代码内容

不得把折叠的代码标记推断成实际代码。

【四、阅读顺序】

1. 按照页面自然阅读顺序排列。
2. 双栏页面注意左右栏的布局关系。
3. 每个元素必须包含 order，从 1 开始连续编号。
4. 不得遗漏页面中可见的文字、公式和图表。

【五、输出要求】

只返回合法 JSON，不得添加 Markdown 或额外解释。

必须使用以下顶层结构：

{
  "elements": [
    {
      "type": "heading",
      "order": 1,
      "content": "页面标题"
    },
    {
      "type": "text",
      "order": 2,
      "content": "普通文字"
    },
    {
      "type": "formula",
      "order": 3,
      "latex": "数学公式",
      "uncertain": []
    },
    {
      "type": "inline_formula",
      "order": 4,
      "latex": "行内公式"
    },
    {
      "type": "figure",
      "order": 5,
      "description": "图表描述",
      "labels": {
        "x_axis": "横轴标签",
        "y_axis": "纵轴标签",
        "legend": []
      },
      "uncertain": []
    },
    {
      "type": "code_marker",
      "order": 6,
      "content": "Code",
      "visibility": "collapsed"
    },
    {
      "type": "code",
      "order": 7,
      "content": "实际可见的代码"
    }
  ]
}

注意：

- 示例仅用于说明结构，不代表每页必须包含所有类型。
- 不适用的字段可以省略。
- uncertain 只在存在无法确认的内容时填写。
- 所有内容必须来自当前页面。
- 不得自行补充或推断页面中不存在的信息。
"""


def sha256_of_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_client() -> OpenAI:
    import os

    return OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
        timeout=120.0,
        max_retries=2,
    )


def is_resumable(
    old_result: dict,
    pdf_sha256: str,
    model: str,
    prompt_version: str,
) -> bool:
    return (
        old_result.get("pdf_sha256") == pdf_sha256
        and old_result.get("parser") == model
        and old_result.get("prompt_version") == prompt_version
    )


def load_previous_result(output_path: Path) -> dict | None:
    if not output_path.exists():
        return None
    try:
        return json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_result(result: dict, output_path: Path) -> None:
    temp_path = output_path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(output_path)


def upsert_page(result: dict, page_result: dict) -> None:
    page_number = page_result["page"]
    result["pages"] = [item for item in result["pages"] if item.get("page") != page_number]
    result["pages"].append(page_result)
    result["pages"].sort(key=lambda item: item["page"])


def render_page_png(doc: pymupdf.Document, page_index: int) -> bytes:
    pix = doc[page_index].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    image_bytes = pix.tobytes("png")

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValueError(f"页面图片过大：{len(image_bytes) / 1024 / 1024:.2f} MB，超过 30 MB 安全阈值。")

    return image_bytes


def parse_elements(ai_content: str) -> list[dict]:
    if not ai_content or not ai_content.strip():
        raise ValueError("模型返回了空内容。")

    ai_result = json.loads(ai_content)
    elements = ai_result.get("elements")

    if not isinstance(elements, list):
        raise TypeError("模型返回的 elements 不是列表。")

    for index, element in enumerate(elements, start=1):
        if not isinstance(element, dict):
            raise TypeError(f"第 {index} 个元素不是 JSON 对象。")
        element["order"] = index

    return elements


def call_vision_model(client: OpenAI, model: str, image_bytes: bytes) -> str:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": "original",
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


def run_vision(
    pdf_path: str | Path,
    output_path: str | Path,
    model: str = MODEL_NAME,
    prompt_version: str = PROMPT_VERSION,
) -> dict:
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到 PDF 文件：{pdf_path}")

    pdf_sha256 = sha256_of_file(pdf_path)

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)

    result = {
        "source": pdf_path.name,
        "pdf_sha256": pdf_sha256,
        "parser": model,
        "prompt_version": prompt_version,
        "total_pages": total_pages,
        "pages": [],
    }

    old_result = load_previous_result(output_path)
    if old_result and is_resumable(old_result, pdf_sha256, model, prompt_version):
        result["pages"] = old_result.get("pages", [])

    completed_pages = {
        item["page"]: item
        for item in result["pages"]
        if item.get("status") == "success" and isinstance(item.get("page"), int)
    }

    client: OpenAI | None = None

    try:
        for page_index in range(total_pages):
            page_number = page_index + 1

            if page_number in completed_pages:
                continue

            try:
                if client is None:
                    client = build_client()

                image_bytes = render_page_png(doc, page_index)
                ai_content = call_vision_model(client, model, image_bytes)
                elements = parse_elements(ai_content)

                page_result = {
                    "page": page_number,
                    "status": "success",
                    "elements": elements,
                }

            except Exception as error:  # noqa: BLE001 - recorded, not re-raised
                page_result = {
                    "page": page_number,
                    "status": "failed",
                    "error": str(error),
                    "elements": [],
                }

            upsert_page(result, page_result)
            save_result(result, output_path)
            completed_pages[page_number] = page_result
    finally:
        doc.close()

    return result
