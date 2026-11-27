"""Event mapping tests: stable IDs, readable bodies, and pure diffs."""

from datetime import date, time

from gcal_sync.events import (
    MARKER_KEY,
    MARKER_VALUE,
    TIMEZONE,
    bodies_equal,
    diff_bodies,
    event_id,
    events_to_bodies,
    to_google_event,
)


def test_event_id_is_stable(make_event):
    assert event_id(make_event()) == event_id(make_event())


def test_event_id_is_valid(make_event):
    ident = event_id(make_event())
    assert ident.startswith("uafm") and len(ident) >= 5
    assert all(char in "abcdefghijklmnopqrstuvwxyz0123456789" for char in ident)


def test_event_id_distinguishes_time_slots(make_event):
    assert event_id(make_event(start=time(8, 0))) != event_id(
        make_event(start=time(10, 0))
    )


def test_event_id_ignores_display_fields(make_event):
    assert event_id(make_event(room="s. 101")) == event_id(make_event(room="s. 202"))


def test_to_google_event_fields(make_event):
    body = to_google_event(make_event())
    assert body["id"] == event_id(make_event())
    assert body["summary"] == "Algebra (Wykład)"
    assert body["location"] == "s. 101"
    assert "dr Nowak" in body["description"] and "Grupy: A" in body["description"]
    assert body["start"] == {
        "dateTime": "2026-10-19T08:00:00",
        "timeZone": TIMEZONE,
    }
    assert body["end"]["dateTime"] == "2026-10-19T09:30:00"
    assert body["extendedProperties"] == {"private": {MARKER_KEY: MARKER_VALUE}}


def test_description_skips_empty_fields(make_event):
    body = to_google_event(
        make_event(lecturer="", groups="", form="", credit_form="", tracks="")
    )
    assert body["summary"] == "Algebra"
    assert body["description"] == ""


def test_diff_splits_insert_update_delete(make_event):
    old = make_event(room="s. 101")
    changed = make_event(room="s. 202")
    new = make_event(start=time(10, 0), end=time(11, 30))
    desired = events_to_bodies([changed, new])
    existing = events_to_bodies([old])
    stale_id = event_id(make_event(date=date(2026, 10, 20)))
    existing[stale_id] = to_google_event(make_event(date=date(2026, 10, 20)))

    plan = diff_bodies(desired, existing)

    assert [body["id"] for body in plan.insert] == [event_id(new)]
    assert [body["id"] for body in plan.update] == [event_id(changed)]
    assert plan.update[0]["location"] == "s. 202"
    assert plan.delete_ids == (stale_id,)


def test_diff_is_noop_when_equal(make_event):
    bodies = events_to_bodies([make_event(), make_event(start=time(10, 0))])
    plan = diff_bodies(bodies, dict(bodies))
    assert plan.insert == () and plan.update == () and plan.delete_ids == ()


def test_bodies_equal_tolerates_missing_empty_location(make_event):
    body = to_google_event(make_event(room=""))
    other = to_google_event(make_event(room=""))
    del other["location"]
    assert bodies_equal(body, other)
