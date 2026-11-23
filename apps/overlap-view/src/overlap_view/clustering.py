"""Group weekly events into overlapping weekday clusters for the typical week."""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import time

from plan_parser import Event
from plan_render.text import format_room


@dataclass(frozen=True)
class TimeVariant:
    """One distinct class time with its weekly occurrence count."""

    start: time
    end: time
    count: int


@dataclass(frozen=True)
class RoomVariant:
    """One distinct room with its occurrence count."""

    room: str
    count: int


@dataclass(frozen=True)
class Cluster:
    """Overlapping instances of one class on one weekday.

    The block spans `start` to `end`; `times` lists the distinct time variants
    sorted by start, `rooms` the distinct rooms sorted by count. `lane` and
    `lanes` place colliding clusters side by side within the column.
    """

    weekday: int
    subject: str
    form: str
    start: time
    end: time
    times: tuple[TimeVariant, ...]
    rooms: tuple[RoomVariant, ...]
    count: int
    lane: int = 0
    lanes: int = 1


def cluster_events(events: list[Event]) -> list[Cluster]:
    """Merge each weekday's class instances into overlap clusters with lanes."""
    groups: dict[tuple[int, str, str], list[Event]] = {}
    for event in events:
        weekday = event.date.weekday()
        if weekday >= 5:
            continue
        groups.setdefault((weekday, event.subject, event.form), []).append(event)
    clusters = [
        cluster for key, group in groups.items() for cluster in _merge(key, group)
    ]
    return _assign_lanes(clusters)


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
    room_counts = Counter(format_room(e.room) for e in members if e.room.strip())
    rooms = tuple(
        RoomVariant(room, count)
        for room, count in sorted(room_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    )
    return Cluster(
        weekday=weekday,
        subject=subject,
        form=form,
        start=min(e.start for e in members),
        end=max(e.end for e in members),
        times=times,
        rooms=rooms,
        count=len(members),
    )


def _assign_lanes(clusters: list[Cluster]) -> list[Cluster]:
    """Split colliding clusters of each weekday into side-by-side lanes."""
    by_day: dict[int, list[Cluster]] = {}
    for cluster in clusters:
        by_day.setdefault(cluster.weekday, []).append(cluster)
    placed: list[Cluster] = []
    for weekday in sorted(by_day):
        day_clusters = sorted(
            by_day[weekday], key=lambda c: (c.start, c.end, c.subject)
        )
        for component in _components(day_clusters):
            lane_ends: list[time] = []
            assigned: list[tuple[Cluster, int]] = []
            for cluster in component:
                lane = next(
                    (
                        i
                        for i, occupied_until in enumerate(lane_ends)
                        if occupied_until <= cluster.start
                    ),
                    len(lane_ends),
                )
                if lane == len(lane_ends):
                    lane_ends.append(cluster.end)
                else:
                    lane_ends[lane] = cluster.end
                assigned.append((cluster, lane))
            for cluster, lane in assigned:
                placed.append(replace(cluster, lane=lane, lanes=len(lane_ends)))
    return sorted(placed, key=lambda c: (c.weekday, c.start, c.end, c.subject))


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
