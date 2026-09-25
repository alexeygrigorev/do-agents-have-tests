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
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[2]
    corpus_path = project_root / "data" / "field_guide_docs.json"
    return corpus_path


def _get_index() -> Index:
    global _index
    if _index is None:
        text_fields = ["title", "company", "text"]
        keyword_fields = ["section"]
        new_index = Index(text_fields=text_fields, keyword_fields=keyword_fields)
        corpus_path = _corpus_path()
        corpus_text = corpus_path.read_text(encoding="utf-8")
        documents = json.loads(corpus_text)
        new_index.fit(documents)
        _index = new_index
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
    stripped_query = query.strip()
    if not stripped_query:
        empty_query_response = {
            "ok": False,
            "error": "empty_query",
            "hint": "Provide a short keyword query, e.g. 'RAG skills' or 'who is hiring'.",
        }
        return ToolResult(llm_response=empty_query_response)

    stripped_section = section.strip()
    filter_dict = {}
    if stripped_section:
        filter_dict["section"] = stripped_section

    num_to_fetch = _NUM_RESULTS * _FETCH_FACTOR
    search_index = _get_index()
    raw_hits = search_index.search(
        stripped_query, filter_dict=filter_dict, num_results=num_to_fetch
    )

    filtered_hits: list[dict] = []
    hits_per_company: dict[str, int] = {}
    for hit in raw_hits:
        company_name = hit.get("company")
        if company_name:
            dedup_key = company_name
        else:
            dedup_key = hit["id"]

        current_count = hits_per_company.get(dedup_key, 0)
        if current_count >= _MAX_PER_COMPANY:
            continue

        updated_count = current_count + 1
        hits_per_company[dedup_key] = updated_count
        filtered_hits.append(hit)

        if len(filtered_hits) == _NUM_RESULTS:
            break

    context.memory.set("last_query", stripped_query)
    hit_count_text = str(len(filtered_hits))
    context.memory.set("last_hit_count", hit_count_text)

    results = []
    for hit in filtered_hits:
        section_name = hit["section"]
        title = hit["title"]
        full_text = hit["text"]
        snippet = full_text[:_SNIPPET_CHARS]

        entry = {}
        entry["section"] = section_name
        entry["title"] = title
        entry["text"] = snippet

        if section_name == "job":
            company = hit.get("company", "")
            location = hit.get("location", "")
            is_remote = hit.get("remote", False)
            entry["company"] = company
            entry["location"] = location
            entry["remote"] = is_remote
        else:
            source_file = hit.get("source_file", "")
            entry["source_file"] = source_file

        results.append(entry)

    if not results:
        no_match_response = {
            "ok": False,
            "query": stripped_query,
            "results": [],
            "hint": "No matches. Try different keywords or drop the section filter.",
        }
        return ToolResult(llm_response=no_match_response)

    success_response = {
        "ok": True,
        "query": stripped_query,
        "results": results,
    }
    return ToolResult(llm_response=success_response)
