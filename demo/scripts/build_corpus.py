"""Build demo/data/field_guide_docs.json from the AI Engineering Field Guide repo.

The corpus has two kinds of documents, distinguished by the ``section``
keyword field so the agent can filter guide knowledge from raw postings:

- ``guide``   curated chapters, question banks, research exports, the 51
              per-company interview-process YAMLs, and awesome.md
- ``job``     every raw posting from the newest job-market snapshot
              (company, role, location, and the full description)

Usage (from demo/):

    uv run python scripts/build_corpus.py
    uv run python scripts/build_corpus.py --source /path/to/ai-engineering-field-guide
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT.parents[1] / "ai-engineering-field-guide"
OUTPUT = PROJECT / "data" / "field_guide_docs.json"

MAX_CHUNK_CHARS = 4000
MAX_JOB_CHARS = 5000

# Curated markdown, relative to the source repo. questions/questions.md is
# skipped: the numbered files under interview/questions/ are the same bank
# split by category.
GUIDE_FILES = [
    "interview/01-interview-process.md",
    "interview/02-questions.md",
    "interview/03-get-hired.md",
    "interview/04-after-the-interview.md",
    "interview/05-trends.md",
    "interview/questions/01-theory.md",
    "interview/questions/02-coding.md",
    "interview/questions/03-project-deep-dive.md",
    "interview/questions/04-ai-system-design.md",
    "interview/questions/05-behavioral.md",
    "interview/questions/06-home-assignments.md",
    "interview/data/research-exports/home-assignments.md",
    "interview/data/research-exports/interview-experiences.md",
    "interview/data/research-exports/recruitment-evolution.md",
    "interview/data/research-exports/role-analysis.md",
    "interview/data/research-exports/trends.md",
    "awesome.md",
]


def slug(text: str) -> str:
    keep = [c if c.isalnum() else "-" for c in text.lower()]
    return "".join(keep).strip("-")[:60] or "untitled"


def split_markdown(rel_path: str, source: Path) -> list[dict]:
    """One document per `## ` heading, with the file title as a prefix."""
    text = (source / rel_path).read_text(encoding="utf-8")
    file_title = next(
        (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")),
        rel_path,
    )
    chunks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())

    docs = []
    for chunk in chunks:
        if len(chunk) < 80:
            continue
        heading = chunk.splitlines()[0].lstrip("# ").strip()
        title = file_title if heading == file_title else f"{file_title} — {heading}"
        docs.append(
            {
                "id": f"{slug(rel_path)}::{slug(heading)}",
                "section": "guide",
                "title": title,
                "source_file": rel_path,
                "text": chunk[:MAX_CHUNK_CHARS],
            }
        )
    return docs


def guide_job_docs(source: Path) -> list[dict]:
    """The 51 curated per-company interview-process YAMLs."""
    docs = []
    for path in sorted((source / "interview/data/job-descriptions").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        parts = [f"Interview process at {data.get('company')}: {data.get('role')}."]
        if data.get("process_summary"):
            parts.append(str(data["process_summary"]))
        if data.get("notable"):
            parts.append(f"Notable: {data['notable']}")
        docs.append(
            {
                "id": f"interview-company::{path.stem}",
                "section": "guide",
                "title": f"{data.get('company')} — interview process",
                "source_file": path.relative_to(source).as_posix(),
                "text": " ".join(parts)[:MAX_CHUNK_CHARS],
            }
        )
    return docs


def job_docs(source: Path) -> tuple[list[dict], str]:
    """Every posting in the newest job-market snapshot."""
    snapshots = sorted((source / "job-market/data_raw").iterdir())
    if not snapshots:
        raise SystemExit(f"no job-market snapshots under {source}")
    newest = max(snapshots, key=lambda p: p.name)
    docs = []
    for path in sorted(newest.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        locations = ", ".join(dict.fromkeys(data.get("locations") or []))
        text = str(data.get("description") or "")[:MAX_JOB_CHARS]
        docs.append(
            {
                "id": f"job::{data.get('job_id', path.stem)}",
                "section": "job",
                "title": str(data.get("title") or path.stem),
                "company": str(data.get("company") or ""),
                "location": locations or str(data.get("location") or ""),
                "remote": bool(data.get("remote")),
                "work_type": str(data.get("work_type") or ""),
                "source_file": path.relative_to(source).as_posix(),
                "text": text,
            }
        )
    return docs, newest.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / "interview").is_dir():
        raise SystemExit(
            f"{source} does not look like the ai-engineering-field-guide repo. "
            "Clone it and pass --source."
        )

    docs: list[dict] = []
    for rel in GUIDE_FILES:
        if (source / rel).is_file():
            docs.extend(split_markdown(rel, source))
    docs.extend(guide_job_docs(source))
    jobs, snapshot = job_docs(source)
    docs.extend(jobs)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    print(
        f"{datetime.now().isoformat(timespec='seconds')} wrote {OUTPUT} "
        f"({len(docs)} docs: {len(docs) - len(jobs)} guide, {len(jobs)} jobs "
        f"from snapshot {snapshot}, {OUTPUT.stat().st_size / 1e6:.1f} MB)"
    )


if __name__ == "__main__":
    main()
