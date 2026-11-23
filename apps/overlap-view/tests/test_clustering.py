"""Clustering tests: merging, splitting, counting, and lane assignment."""

from datetime import date, time

from overlap_view.clustering import (
    Cluster,
    RoomVariant,
    TimeVariant,
    cluster_events,
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
            rooms=(RoomVariant("sala D 319", 3),),
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


def test_rooms_counted_separately_sorted_by_count():
    events = [
        make_event(0, time(9, 40), time(12, 5), room="bud.D D - 02 - SALA BALETOWA"),
        make_event(0, time(9, 40), time(12, 5), week=1),
        make_event(0, time(9, 40), time(12, 5), week=2),
    ]
    (cluster,) = cluster_events(events)
    assert [(v.room, v.count) for v in cluster.rooms] == [
        ("sala D 319", 2),
        ("sala D -02 · baletowa", 1),
    ]


def test_colliding_subjects_share_the_column_side_by_side():
    events = [
        make_event(3, time(13, 0), time(15, 25), subject="Antropologia", form="Wyk"),
        make_event(
            3,
            time(14, 30),
            time(16, 30),
            subject="Bezpieczeństwo lokalne",
            form="",
        ),
    ]
    first, second = cluster_events(events)
    assert (first.lane, first.lanes) == (0, 2)
    assert (second.lane, second.lanes) == (1, 2)


def test_non_colliding_days_keep_full_width():
    events = [make_event(0, time(9, 40), time(12, 5))]
    (cluster,) = cluster_events(events)
    assert (cluster.lane, cluster.lanes) == (0, 1)


def test_weekend_events_are_skipped():
    events = [
        make_event(0, time(9, 40), time(12, 5)),
        make_event(5, time(10, 0), time(11, 30)),
    ]
    assert len(cluster_events(events)) == 1


def test_empty_events_yield_no_clusters():
    assert cluster_events([]) == []
