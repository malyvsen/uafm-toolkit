"""Clustering tests: merging, splitting, and counting."""

from datetime import date, time

from overlap_view.clustering import (
    Cluster,
    TimeVariant,
    cluster_events,
    overlap_components,
)
from plan_parser import Event

MONDAY = date(2026, 10, 19)


def make_event(
    day: int,
    start: time,
    end: time,
    subject: str = "Wymowa",
    form: str = "War",
    room: str = "bud.D D 319 - PRACOWNIA AKTORSKA",
    week: int = 0,
) -> Event:
    return Event(
        date=date.fromordinal(MONDAY.toordinal() + day + 7 * week),
        start=start,
        end=end,
        duration="",
        subject=subject,
        form=form,
        groups="",
        room=room,
        lecturer="",
        credit_form="",
        tracks="",
        notes="",
    )


def test_stable_class_merges_into_one_counted_cluster():
    events = [
        make_event(0, time(9, 40), time(12, 5)),
        make_event(0, time(9, 40), time(12, 5), week=1),
        make_event(0, time(9, 40), time(12, 5), week=2),
    ]
    assert cluster_events(events) == [
        Cluster(
            weekday=0,
            subject="Wymowa",
            form="War",
            start=time(9, 40),
            end=time(12, 5),
            times=(TimeVariant(time(9, 40), time(12, 5), 3),),
            count=3,
        )
    ]


def test_gap_splits_clusters_sorted_by_start():
    events = [
        make_event(1, time(18, 0), time(20, 25), subject="Świadomość ciała"),
        make_event(1, time(14, 40), time(17, 5), subject="Świadomość ciała"),
    ]
    clusters = cluster_events(events)
    assert [(c.start, c.end) for c in clusters] == [
        (time(14, 40), time(17, 5)),
        (time(18, 0), time(20, 25)),
    ]


def test_touching_and_chained_instances_merge():
    events = [
        make_event(1, time(14, 50), time(15, 50)),
        make_event(1, time(14, 0), time(15, 0)),
        make_event(1, time(15, 50), time(16, 0)),
    ]
    clusters = cluster_events(events)
    assert len(clusters) == 1
    assert (clusters[0].start, clusters[0].end) == (time(14, 0), time(16, 0))
    assert [(v.start, v.end, v.count) for v in clusters[0].times] == [
        (time(14, 0), time(15, 0), 1),
        (time(14, 50), time(15, 50), 1),
        (time(15, 50), time(16, 0), 1),
    ]


def test_weekend_events_are_skipped():
    events = [
        make_event(0, time(9, 40), time(12, 5)),
        make_event(5, time(10, 0), time(11, 30)),
    ]
    assert len(cluster_events(events)) == 1


def test_empty_events_yield_no_clusters():
    assert cluster_events([]) == []


def test_overlapping_clusters_form_one_component_transitively():
    events = [
        make_event(3, time(13, 0), time(14, 0), subject="A"),
        make_event(3, time(13, 30), time(14, 30), subject="B"),
        make_event(3, time(14, 15), time(15, 0), subject="C"),
    ]
    clusters = cluster_events(events)
    components = overlap_components(clusters)
    assert len(components) == 1
    assert {c.subject for c in components[0]} == {"A", "B", "C"}


def test_separate_clusters_stay_in_their_own_components():
    events = [
        make_event(0, time(9, 40), time(12, 5), subject="Wymowa"),
        make_event(0, time(14, 0), time(15, 0), subject="Głos"),
    ]
    clusters = cluster_events(events)
    components = overlap_components(clusters)
    assert len(components) == 2
    assert all(len(component) == 1 for component in components)
