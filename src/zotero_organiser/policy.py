from __future__ import annotations

from collections.abc import Set
from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    accepted: set[str]
    held: set[str]
    ignored: set[str]


def decide(
    scores: dict[str, float],
    *,
    auto_threshold: float,
    triage_threshold: float,
    suppressed: Set[str] = frozenset(),
) -> Decision:
    accepted, held, ignored = set(), set(), set()
    for tag, confidence in scores.items():
        if tag in suppressed or confidence < triage_threshold:
            ignored.add(tag)
        elif confidence >= auto_threshold:
            accepted.add(tag)
        else:
            held.add(tag)
    return Decision(accepted, held, ignored)
