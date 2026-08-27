from __future__ import annotations

from collections.abc import Set
from dataclasses import dataclass


STATUS_PREFIX = "status/"


@dataclass(frozen=True)
class Reconciliation:
    tags: set[str]
    auto_tags: set[str]
    suppressed_tags: set[str]


def reconcile(
    current: set[str],
    previous_auto: set[str],
    accepted: set[str],
    *,
    suppressed_tags: Set[str] = frozenset(),
    allow_tag_removal: bool = True,
) -> Reconciliation:
    # Workflow status is exclusively human-owned. Ignore any status ownership
    # left in state by an older release and defensively reject classifier output.
    previous_auto = {tag for tag in previous_auto if not tag.startswith(STATUS_PREFIX)}
    accepted = {tag for tag in accepted if not tag.startswith(STATUS_PREFIX)}
    suppressed_tags = {tag for tag in suppressed_tags if not tag.startswith(STATUS_PREFIX)}
    # Absence of a formerly-owned tag is a durable human suppression.
    suppressed = set(suppressed_tags) | (previous_auto - current)
    retained_auto = previous_auto & current
    # Tags that already exist but are not ours remain human-owned.  In
    # particular, seeing an accepted taxonomy tag must not make it ours.
    new_auto = accepted - current
    desired_auto = ((retained_auto & accepted) | new_auto) - suppressed
    if not allow_tag_removal:
        desired_auto |= retained_auto
    final = (current - retained_auto) | desired_auto
    return Reconciliation(final, desired_auto, suppressed)
