"""Runs the regression set of the classification prompt by hand (issue 157).

From backend/, with its environment active and OPENAI_API_KEY set:

    python -m evals.classification.run            # says how many calls, and calls nothing
    python -m evals.classification.run --run      # calls the model and keeps the report

Every run costs money, with the same key the demo may use: say how many calls before running.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

from app.adapters.outbound.llm_client.openai_llm import OpenAILLM
from app.constants import LLM_MODEL, EnvVar
from app.domain.ports.llm_port import LLMPort
from app.shared.clock import SystemClock
from evals.classification import constants
from evals.classification.cases import CASES
from evals.classification.regression import (
    Comparison,
    RegressionReport,
    compare,
    estimated_cost,
    latest_other,
    run_regression,
)
from evals.classification.regression_case import RegressionCase

RESULTS_DIR = Path(__file__).parent / constants.RESULTS_DIR_NAME


def main(
    argv: Sequence[str],
    *,
    cases: Sequence[RegressionCase],
    llm_factory: Callable[[], LLMPort],
    out: TextIO,
    results_dir: Path,
) -> int:
    parser = argparse.ArgumentParser(prog="evals.classification.run")
    parser.add_argument("--runs", type=int, default=constants.DEFAULT_RUNS)
    parser.add_argument("--run", action="store_true")
    arguments = parser.parse_args(argv)
    calls = len(cases) * arguments.runs
    print(
        constants.ANNOUNCEMENT.format(
            cases=len(cases),
            runs=arguments.runs,
            calls=calls,
            cost=estimated_cost(calls, LLM_MODEL),
        ),
        file=out,
    )
    if not arguments.run:
        print(constants.RUN_HINT, file=out)
        return 0
    report = run_regression(llm_factory(), cases, arguments.runs)
    previous = latest_other(_saved(results_dir), report.prompt_version)
    path = _save(report, results_dir)
    _print_report(report, out)
    if previous is not None:
        _print_comparison(compare(report, previous), previous.prompt_version, out)
    print(constants.REPORT_SAVED.format(path=path), file=out)
    return 0


def _saved(results_dir: Path) -> list[RegressionReport]:
    paths = sorted(results_dir.glob(f"*{constants.REPORT_SUFFIX}"))
    return [RegressionReport.from_json(path.read_text(encoding="utf-8")) for path in paths]


def _save(report: RegressionReport, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = SystemClock().now().strftime(constants.STAMP_FORMAT)
    name = constants.REPORT_NAME.format(stamp=stamp, prompt_version=report.prompt_version)
    path = results_dir / f"{name}{constants.REPORT_SUFFIX}"
    path.write_text(report.to_json(), encoding="utf-8")
    return path


def _print_report(report: RegressionReport, out: TextIO) -> None:
    if report.stopped_at is not None:
        print(constants.STOPPED.format(case=report.stopped_at), file=out)
    print(
        constants.SUMMARY.format(
            prompt_version=report.prompt_version,
            calls=report.calls,
            blocked=report.blocked,
            input_tokens=report.input_tokens,
            output_tokens=report.output_tokens,
            cost=report.cost.quantize(constants.ESTIMATE_QUANTUM),
        ),
        file=out,
    )
    print(constants.OUTCOMES_TITLE, file=out)
    for outcome, count in sorted(report.outcomes.items()):
        print(constants.OUTCOME_LINE.format(outcome=outcome, count=count), file=out)
    print(constants.FIELDS_TITLE, file=out)
    for name, (hits, checked) in sorted(report.field_hits.items()):
        print(constants.FIELD_LINE.format(field=name, hits=hits, checked=checked), file=out)
    if report.misses:
        print(constants.MISSES_TITLE, file=out)
    for miss in report.misses:
        print(
            constants.MISS_LINE.format(
                case=miss.case, field=miss.field, expected=miss.expected, got=miss.got
            ),
            file=out,
        )


def _print_comparison(comparison: Comparison, prompt_version: str, out: TextIO) -> None:
    print(constants.COMPARISON_TITLE.format(prompt_version=prompt_version), file=out)
    for name, (before, after) in comparison.field_changes.items():
        if before == after:
            continue
        print(
            constants.CHANGE_LINE.format(
                field=name,
                before_hits=before[0],
                before_checked=before[1],
                after_hits=after[0],
                after_checked=after[1],
            ),
            file=out,
        )
    if comparison.worse_cases:
        print(constants.WORSE_TITLE, file=out)
    for case in comparison.worse_cases:
        print(constants.WORSE_LINE.format(case=case), file=out)


def _real_model() -> LLMPort:
    return OpenAILLM(api_key=os.environ[EnvVar.OPENAI_API_KEY])


if __name__ == "__main__":
    sys.exit(
        main(
            sys.argv[1:],
            cases=CASES,
            llm_factory=_real_model,
            out=sys.stdout,
            results_dir=RESULTS_DIR,
        )
    )
