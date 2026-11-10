"""A rule-based stand-in for the model (LLM_PROVIDER=offline).

It lets the whole pipeline run with no API key and no cost: automated tests,
frontend integration and CI use it. Its concepts and questions are crude
(one concept per slide, chained in order), so never demo with it.
"""

from __future__ import annotations

import json
import re

from app.agent.search import tokenize

_PAGE_BLOCK = re.compile(r"\[p\.(\d+)\]\n(.*?)(?=\n\n\[p\.\d+\]\n|\n</lecture_content>)", re.DOTALL)
MAX_CONCEPTS = 8


class OfflineLLM:
    def complete_json(self, system: str, user: str) -> str:
        if system.startswith("TASK: quiz"):
            out = self._quiz(json.loads(user))
        elif system.startswith("TASK: grade"):
            out = self._grade(json.loads(user))
        elif system.startswith("TASK: explain"):
            out = self._explain(json.loads(user))
        elif system.startswith("TASK: plan"):
            options = json.loads(user)["options"]
            out = {"choice": next(o["id"] for o in options if o["default"]), "reason": ""}
        else:  # C's concept-extraction prompt
            out = self._extract(user)
        return json.dumps(out)

    def _extract(self, user: str) -> dict:
        concepts, used = [], set()
        for number, text in _PAGE_BLOCK.findall(user)[:MAX_CONCEPTS]:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if not lines:
                continue
            slug = "_".join(tokenize(lines[0])[:4]) or f"page_{number}"
            while slug in used:
                slug += "_x"
            used.add(slug)
            concepts.append(
                {
                    "id": slug,
                    "name": lines[0][:60],
                    "summary": " ".join(lines[1:3])[:300] or lines[0],
                    "pages": [int(number)],
                    "prerequisites": [concepts[-1]["id"]] if concepts else [],
                }
            )
        return {"concepts": concepts}

    def _quiz(self, payload: dict) -> dict:
        questions = []
        for c in payload["concepts"]:
            wrong = [
                "It is not covered anywhere in this lecture.",
                "It only matters when no data is available at all.",
                "It is a formatting rule for the slides, not a concept.",
            ]
            for prompt in (
                f"Which statement best describes: {c['name']}?",
                f"What is true about: {c['name']}?",
            ):
                questions.append(
                    {
                        "concept_id": c["id"],
                        "type": "multiple_choice",
                        "prompt": prompt,
                        "options": [c["summary"], *wrong],
                        "answer_index": 0,
                        "explanation": c["summary"],
                        "page": c["pages"][0],
                    }
                )
            questions.append(
                {
                    "concept_id": c["id"],
                    "type": "short_answer",
                    "prompt": f"In your own words, explain: {c['name']}.",
                    "reference_answer": c["summary"],
                    "key_points": [c["summary"]],
                    "page": c["pages"][0],
                }
            )
        return {"questions": questions}

    def _grade(self, payload: dict) -> dict:
        rubric = set(tokenize(payload["reference_answer"]))
        hit = len(rubric & set(tokenize(payload["student_answer"])))
        correct = bool(rubric) and hit / len(rubric) >= 0.5
        return {
            "correct": correct,
            "feedback": "Matches the model answer." if correct else "Key ideas are missing.",
        }

    def _explain(self, payload: dict) -> dict:
        concept = payload["concept"]
        slides = payload["slides"]
        quote = ""
        if slides:
            quote = next((ln.strip() for ln in slides[0]["text"].splitlines() if len(ln.strip()) >= 8), "")
        return {
            "explanation": f"{concept['name']}: {concept['summary']}",
            "page": slides[0]["page"] if slides else 0,
            "quote": quote,
        }
