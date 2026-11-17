"""Runs the regression set against a model and scores what it answers (issue 157).

The model is the real adapter in a run, and a double in the tests. What the code would drop is
decided by the same check the worker uses, so the rate of blocked answers says what would
happen in the product.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from app.constants import LLM_PRICES_USD_PER_MILLION_TOKENS, TOKENS_PER_MILLION
from app.domain.entities.classification import Classification, ModelUsage
from app.domain.entities.llm_call import LlmOutcome
from app.domain.errors import ModelAnswerCutError, ModelCallFailedError, ModelRefusedError
from app.domain.ports.llm_port import LLMPort
from app.domain.services.transactions.movement_resolution import rejects_output
from evals.classification import constants
from evals.classification.regression_case import RegressionCase

# A rate: how many runs got the field right, out of how many checked it.
Rate = tuple[int, int]
_NO_RATE: Rate = (0, 0)
# What a path gives when the answer has nothing there, as a list shorter than the position.
_ABSENT = "<ausente>"


@dataclass(frozen=True)
class Miss:
    """One field of one run that did not say what the case expects."""

    case: str
    field: str
    expected: object
    got: object


@dataclass(frozen=True)
class RegressionReport:
    """What a run of the set gave: by field, by case, by outcome, and what it cost."""

    prompt_version: str
    runs: int
    calls: int
    blocked: int
    outcomes: Mapping[str, int]
    field_hits: Mapping[str, Rate]
    case_hits: Mapping[str, Rate]
    misses: tuple[Miss, ...]
    input_tokens: int
    output_tokens: int
    cost: Decimal
    # The case where the provider failed and the run stopped, or None if it ended.
    stopped_at: str | None = None

    def field_rate(self, name: str) -> Rate:
        return self.field_hits.get(name, _NO_RATE)

    def case_rate(self, name: str) -> Rate:
        return self.case_hits.get(name, _NO_RATE)

    def to_json(self) -> str:
        return json.dumps(
            {
                "prompt_version": self.prompt_version,
                "runs": self.runs,
                "calls": self.calls,
                "blocked": self.blocked,
                "outcomes": dict(self.outcomes),
                "field_hits": {name: list(rate) for name, rate in self.field_hits.items()},
                "case_hits": {name: list(rate) for name, rate in self.case_hits.items()},
                "misses": [
                    {
                        "case": miss.case,
                        "field": miss.field,
                        "expected": str(miss.expected),
                        "got": str(miss.got),
                    }
                    for miss in self.misses
                ],
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cost": str(self.cost),
                "stopped_at": self.stopped_at,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> RegressionReport:
        data = json.loads(text)
        return cls(
            prompt_version=data["prompt_version"],
            runs=data["runs"],
            calls=data["calls"],
            blocked=data["blocked"],
            outcomes=data["outcomes"],
            field_hits={name: (rate[0], rate[1]) for name, rate in data["field_hits"].items()},
            case_hits={name: (rate[0], rate[1]) for name, rate in data["case_hits"].items()},
            misses=tuple(Miss(**miss) for miss in data["misses"]),
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
            cost=Decimal(data["cost"]),
            stopped_at=data["stopped_at"],
        )


@dataclass(frozen=True)
class Comparison:
    """Two runs side by side: the rate of each field before and after, and what got worse."""

    field_changes: Mapping[str, tuple[Rate, Rate]]
    worse_cases: tuple[str, ...]


@dataclass
class _Tally:
    """What a run adds up while it goes."""

    prompt_version: str = ""
    calls: int = 0
    blocked: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)
    field_hits: dict[str, Rate] = field(default_factory=dict)
    case_hits: dict[str, Rate] = field(default_factory=dict)
    misses: list[Miss] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost: Decimal = Decimal(0)

    def charge(self, usage: ModelUsage | None) -> None:
        if usage is None:
            return
        self.prompt_version = self.prompt_version or usage.prompt_version
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost += cost_of(usage.model, input_tokens, output_tokens)

    def score(self, case: RegressionCase, answer: Classification) -> None:
        for path, expected in case.expected.items():
            got = value_at(answer, path)
            hit = got == expected
            self.field_hits[path] = _added(self.field_hits.get(path, _NO_RATE), hit)
            self.case_hits[case.name] = _added(self.case_hits.get(case.name, _NO_RATE), hit)
            if not hit:
                self.misses.append(Miss(case.name, path, expected, got))

    def report(self, runs: int, stopped_at: str | None) -> RegressionReport:
        return RegressionReport(
            prompt_version=self.prompt_version,
            runs=runs,
            calls=self.calls,
            blocked=self.blocked,
            outcomes=dict(self.outcomes),
            field_hits=dict(self.field_hits),
            case_hits=dict(self.case_hits),
            misses=tuple(self.misses),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost=self.cost,
            stopped_at=stopped_at,
        )


def run_regression(llm: LLMPort, cases: Sequence[RegressionCase], runs: int) -> RegressionReport:
    """Asks the model each case `runs` times and scores every answer.

    A provider error stops the run: a used-up balance would fail every call after it.
    """
    tally = _Tally()
    for case in cases:
        for _ in range(runs):
            tally.calls += 1
            try:
                answer = llm.classify(case.request)
            except ModelCallFailedError as error:
                tally.charge(error.usage)
                if error.outcome is LlmOutcome.PROVIDER_ERROR:
                    return tally.report(runs, stopped_at=case.name)
                tally.outcomes[error.outcome.value] += 1
                continue
            except ModelRefusedError as error:
                tally.charge(error.usage)
                tally.outcomes[LlmOutcome.REFUSED.value] += 1
                continue
            except ModelAnswerCutError as error:
                tally.charge(error.usage)
                tally.outcomes[LlmOutcome.TRUNCATED.value] += 1
                continue
            tally.charge(answer.usage)
            blocked = rejects_output(answer, case.request.text, case.previous)
            tally.blocked += int(blocked)
            outcome = constants.OUTCOME_BLOCKED if blocked else constants.OUTCOME_OK
            tally.outcomes[outcome] += 1
            tally.score(case, answer)
    return tally.report(runs, stopped_at=None)


def compare(current: RegressionReport, previous: RegressionReport) -> Comparison:
    """Each field with its rate in both runs, and the cases that got fewer fields right."""
    names = list(dict.fromkeys([*previous.field_hits, *current.field_hits]))
    changes = {name: (previous.field_rate(name), current.field_rate(name)) for name in names}
    worse = tuple(
        name
        for name in current.case_hits
        if name in previous.case_hits
        and _share(current.case_rate(name)) < _share(previous.case_rate(name))
    )
    return Comparison(field_changes=changes, worse_cases=worse)


def estimated_cost(calls: int, model: str) -> Decimal:
    """What a run of that many calls would cost, before it starts."""
    cost = cost_of(
        model, calls * constants.ESTIMATED_INPUT_TOKENS, calls * constants.ESTIMATED_OUTPUT_TOKENS
    )
    return cost.quantize(constants.ESTIMATE_QUANTUM)


def cost_of(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """In dollars, with the prices the application records each call with (ADR 0023)."""
    input_price, output_price = LLM_PRICES_USD_PER_MILLION_TOKENS[model]
    total = input_tokens * Decimal(input_price) + output_tokens * Decimal(output_price)
    return total / TOKENS_PER_MILLION


def value_at(answer: Classification, path: str) -> object:
    """What the answer says at a path, as "more_movements.0.amount" or "more_movements.length".

    A reply by number keeps its fields in its reading, so a path reaches them through it.
    """
    value: object = answer
    for part in path.split(constants.PATH_SEPARATOR):
        value = _step(value, part)
        if value is _ABSENT:
            return _ABSENT
    return value


def _step(value: object, part: str) -> object:
    if isinstance(value, tuple):
        if part == constants.LENGTH_PART:
            return len(value)
        position = int(part)
        return value[position] if position < len(value) else _ABSENT
    if hasattr(value, part):
        return getattr(value, part)
    reading = getattr(value, "reading", None)
    if reading is not None and hasattr(reading, part):
        return getattr(reading, part)
    return _ABSENT


def _added(rate: Rate, hit: bool) -> Rate:
    return (rate[0] + int(hit), rate[1] + 1)


def _share(rate: Rate) -> Decimal:
    return Decimal(rate[0]) / Decimal(rate[1]) if rate[1] else Decimal(0)


def latest_other(
    reports: Iterable[RegressionReport], prompt_version: str
) -> RegressionReport | None:
    """The last report of another prompt, the one a new run is compared with."""
    others = [report for report in reports if report.prompt_version != prompt_version]
    return others[-1] if others else None
