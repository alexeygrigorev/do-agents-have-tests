"""Keyword search over the AI Engineering Field Guide corpus.

The index is built once from ``data/field_guide_docs.json``, which
``scripts/build_corpus.py`` generates from the field guide repo: curated
guide chapters (``section='guide'``) and every posting in the newest
job-market snapshot (``section='job'``).

The corpus lives in the project, not in the trained model archive, so the
path is resolved at call time: at server start the skill module is imported
from an extracted snapshot temp dir where the project-relative path does not
exist.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from minsearch import Index

from rasa.mantle.tools.decorator import ToolContext, tool
from rasa.mantle.tools.result import ToolResult

_NUM_RESULTS = 5
_FETCH_FACTOR = 3
# A who-is-hiring query otherwise returns five postings from one company.
_MAX_PER_COMPANY = 2
_SNIPPET_CHARS = 800

_index: Index | None = None


def _corpus_path() -> Path:
    env = os.environ.get("FIELD_GUIDE_CORPUS")
    candidates = (
        [Path(env)]
        if env
        else [
            Path.cwd() / "data" / "field_guide_docs.json",
            Path(__file__).resolve().parents[2] / "data" / "field_guide_docs.json",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    looked = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"field_guide_docs.json not found (looked in: {looked}). "
        "Run `uv run python scripts/build_corpus.py` from demo/ first, or set FIELD_GUIDE_CORPUS."
    )


def _get_index() -> Index:
    global _index
    if _index is None:
        index = Index(text_fields=["title", "company", "text"], keyword_fields=["section"])
        index.fit(json.loads(_corpus_path().read_text(encoding="utf-8")))
        _index = index
    return _index


@tool(
    description=(
        "Keyword-search the AI Engineering Field Guide: curated chapters on "
        "interviews, skills, and trends (section='guide'), and current "
        "AI-engineer job postings (section='job'). Call this before answering "
        "any question about hiring, companies, skills, or interviews. Leave "
        "section empty when unsure."
    )
)
async def search_field_guide(
    query: str, section: str = "", context: ToolContext = None
) -> ToolResult:
    """Return the top corpus matches for query, optionally within one section."""
    query = query.strip()
    if not query:
        return ToolResult(
            llm_response={
                "ok": False,
                "error": "empty_query",
                "hint": "Provide a short keyword query, e.g. 'RAG skills' or 'who is hiring'.",
            }
        )

    section = section.strip()
    filter_dict = {"section": section} if section else {}
    hits = _get_index().search(
        query, filter_dict=filter_dict, num_results=_NUM_RESULTS * _FETCH_FACTOR
    )

    kept: list[dict] = []
    per_company: dict[str, int] = {}
    for hit in hits:
        key = hit.get("company") or hit["id"]
        if per_company.get(key, 0) >= _MAX_PER_COMPANY:
            continue
        per_company[key] = per_company.get(key, 0) + 1
        kept.append(hit)
        if len(kept) == _NUM_RESULTS:
            break
    hits = kept

    context.memory.set("last_query", query)
    context.memory.set("last_hit_count", str(len(hits)))

    results = []
    for hit in hits:
        entry = {
            "section": hit["section"],
            "title": hit["title"],
            "text": hit["text"][:_SNIPPET_CHARS],
        }
        if hit["section"] == "job":
            entry["company"] = hit.get("company", "")
            entry["location"] = hit.get("location", "")
            entry["remote"] = hit.get("remote", False)
        else:
            entry["source_file"] = hit.get("source_file", "")
        results.append(entry)

    if not results:
        return ToolResult(
            llm_response={
                "ok": False,
                "query": query,
                "results": [],
                "hint": "No matches. Try different keywords or drop the section filter.",
            }
        )
    return ToolResult(llm_response={"ok": True, "query": query, "results": results})
