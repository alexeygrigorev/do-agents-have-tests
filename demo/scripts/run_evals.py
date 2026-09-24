"""Run every scenario under eval/scenarios against a local Rasa server.

Usage (from demo/, after `rasa train` and `rasa run`):

    ../.venv-pro/bin/python scripts/run_evals.py
    ../.venv-pro/bin/python scripts/run_evals.py eval/scenarios/joke_starts_nothing.yml
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from rasa.builder.copilot.mcp_server.tools.artifact_writer import (
    write_experiment_summary,
)
from rasa.builder.copilot.mcp_server.tools.eval_config import (
    build_llm_client,
    load_conftest,
)
from rasa.builder.copilot.mcp_server.tools.evaluate_agent import run_scenario
from rasa.builder.copilot.mcp_server.tools.scenario import load_scenario

PROJECT = Path(__file__).resolve().parents[1]
SERVER = "http://127.0.0.1:5005"


async def main(paths: list[Path]) -> int:
    conftest = load_conftest(PROJECT)
    simulation = build_llm_client(conftest.simulation.llm)
    judge = build_llm_client(conftest.evaluation.llm)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    entries = []
    failed = False
    for path in paths:
        scenario = load_scenario(path)
        print(f"running {path.name}: {scenario.name}", flush=True)
        entry = await run_scenario(
            scenario=scenario,
            project_path=PROJECT,
            experiment_timestamp=stamp,
            run_count=1,
            rasa_server_url=SERVER,
            simulation_llm_client=simulation,
            eval_llm_client=judge,
            eval_llm_config=conftest.evaluation.llm,
        )
        entries.append(entry)
        print(
            f"  -> {entry.runs_passed}/{entry.runs_total} {entry.scenario_name}",
            flush=True,
        )
        if entry.runs_passed < entry.runs_total:
            failed = True
    write_experiment_summary(PROJECT, stamp, entries)
    print(f"results: {PROJECT / 'eval' / 'results' / stamp}")
    return 1 if failed else 0


if __name__ == "__main__":
    args = [Path(p) for p in sys.argv[1:]] or sorted(
        (PROJECT / "eval" / "scenarios").glob("*.yml")
    )
    raise SystemExit(asyncio.run(main(args)))
