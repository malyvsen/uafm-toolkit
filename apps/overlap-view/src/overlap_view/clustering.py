"""Group weekly events into overlapping weekday clusters for the typical week."""

from collections import Counter
from dataclasses import dataclass
from datetime import time

from plan_parser import Event


@dataclass(frozen=True)
class TimeVariant:
    """One distinct class time with its weekly occurrence count."""

    start: time
    end: time
    count: int


@dataclass(frozen=True)
class Cluster:
    """Overlapping instances of one class on one weekday.

    The block spans `start` to `end`; `times` lists the distinct time variants
    sorted by start.
    """

    weekday: int
    subject: str
    form: str
    start: time
    end: time
    times: tuple[TimeVariant, ...]
    count: int


def cluster_events(events: list[Event]) -> list[Cluster]:
    """Merge each weekday's class instances into overlap clusters."""
    groups: dict[tuple[int, str, str], list[Event]] = {}
    for event in events:
        weekday = event.date.weekday()
        if weekday >= 5:
            continue
        groups.setdefault((weekday, event.subject, event.form), []).append(event)
    clusters = [
        cluster for key, group in groups.items() for cluster in _merge(key, group)
    ]
    return sorted(clusters, key=lambda c: (c.weekday, c.start, c.end, c.subject))


def overlap_components(clusters: list[Cluster]) -> list[list[Cluster]]:
    """Group clusters by weekday into transitively overlapping components."""
    by_day: dict[int, list[Cluster]] = {}
    for cluster in clusters:
        by_day.setdefault(cluster.weekday, []).append(cluster)
    components: list[list[Cluster]] = []
    for weekday in sorted(by_day):
        day_clusters = sorted(
            by_day[weekday], key=lambda c: (c.start, c.end, c.subject)
        )
        components.extend(_components(day_clusters))
    return components


def _merge(key: tuple[int, str, str], instances: list[Event]) -> list[Cluster]:
    """Merge a start-sorted run while instances overlap or touch; a gap splits."""
    weekday, subject, form = key
    ordered = sorted(instances, key=lambda e: (e.start, e.end))
    clusters: list[Cluster] = []
    members: list[Event] = []
    span_end = time.min
    for event in ordered:
        if members and event.start > span_end:
            clusters.append(_build(weekday, subject, form, members))
            members = []
            span_end = time.min
        members.append(event)
        span_end = max(span_end, event.end)
    clusters.append(_build(weekday, subject, form, members))
    return clusters


def _build(weekday: int, subject: str, form: str, members: list[Event]) -> Cluster:
    time_counts = Counter((e.start, e.end) for e in members)
    times = tuple(
        TimeVariant(start, end, count)
        for (start, end), count in sorted(time_counts.items())
    )
    return Cluster(
        weekday=weekday,
        subject=subject,
        form=form,
        start=min(e.start for e in members),
        end=max(e.end for e in members),
        times=times,
        count=len(members),
    )


def _components(day_clusters: list[Cluster]) -> list[list[Cluster]]:
    """Split a weekday's start-sorted clusters into transitively overlapping groups."""
    components: list[list[Cluster]] = []
    for cluster in day_clusters:
        if components and any(_overlaps(cluster, other) for other in components[-1]):
            components[-1].append(cluster)
        else:
            components.append([cluster])
    return components


def _overlaps(left: Cluster, right: Cluster) -> bool:
    return left.start < right.end and right.start < left.end
