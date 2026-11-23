"""Text tests: room shortening plus week and cluster block layout."""

from plan_render.style import BLOCK_PAD_Y, HOUR_H, META_STEP, ROOM_GAP, SUBJECT_STEP
from plan_render.text import (
    BlockLine,
    LineKind,
    layout_block,
    layout_cluster,
    place_lines,
)


def _fake_measure(text: str, kind: LineKind) -> float:
    return float(len(text) * (10 if kind == "subject" else 8))


def _layout(
    subject: str, time_range: str, room: str, text_w: float, minutes: float
) -> list[BlockLine]:
    return layout_block(
        subject, time_range, room, text_w, minutes * HOUR_H / 60, _fake_measure
    )


def _cluster_layout(
    subject: str, times: list[str], rooms: list[str], text_w: float, minutes: float
) -> list[BlockLine]:
    return layout_cluster(
        subject, times, rooms, text_w, minutes * HOUR_H / 60, _fake_measure
    )


def test_short_subject_uses_separate_meta():
    lines = _layout("Wymowa", "10:00–11:30", "sala D 319", 200, 145)
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]
    assert lines[0][0] == "Wymowa"
    assert lines[1][0] == "10:00–11:30"
    assert lines[2][0] == "sala D 319"


def test_long_subject_wraps_to_two_lines_with_separate_meta():
    lines = _layout(
        "Elementarne zadania aktorskie", "10:00–12:25", "sala D 319", 150, 145
    )
    kinds = [kind for _, kind in lines]
    assert kinds == ["subject", "subject", "meta", "meta"]
    assert lines[0][0] == "Elementarne"
    assert lines[2][0] == "10:00–12:25"
    assert lines[3][0] == "sala D 319"


def test_medium_block_keeps_separate_meta():
    # Fitting is purely visual: a 95-minute block still separates time and
    # room when the lines fit.
    lines = _layout("Wymowa", "10:00–11:35", "sala D 319", 200, 95)
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]


def test_tight_block_falls_back_to_combined_meta():
    lines = _layout(
        "Elementarne zadania aktorskie", "10:00–10:45", "sala D 319", 150, 45
    )
    assert [kind for _, kind in lines] == ["subject", "meta"]
    assert "·" in lines[1][0]


def test_tiny_block_yields_no_lines():
    assert _layout("Wymowa", "10:00–10:20", "sala D 319", 200, 20) == []


def test_subject_only_when_meta_does_not_fit():
    lines = _layout("Wymowa", "10:00–10:30", "sala D 319", 200, 30)
    assert [kind for _, kind in lines] == ["subject"]


def test_empty_room_renders_time_only():
    lines = _layout("Wymowa", "10:00–11:30", "", 200, 145)
    assert [kind for _, kind in lines] == ["subject", "meta"]
    assert lines[1][0] == "10:00–11:30"


def test_cluster_lists_times_then_rooms():
    lines = _cluster_layout(
        "Świadomość ciała",
        ["14:40–17:05 ×3", "15:00–17:25 ×1"],
        ["sala D -02 ×4"],
        200,
        165,
    )
    assert [kind for _, kind in lines] == ["subject", "meta", "meta", "room"]
    assert lines[1][0] == "14:40–17:05 ×3"
    assert lines[2][0] == "15:00–17:25 ×1"
    assert lines[3][0] == "sala D -02 ×4"


def test_cluster_drops_rooms_before_times_when_tight():
    lines = _cluster_layout(
        "Świadomość ciała",
        ["14:40–17:05 ×3", "15:00–17:25 ×1"],
        ["sala D -02 ×4"],
        200,
        70,
    )
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]


def test_cluster_tiny_block_yields_no_lines():
    assert (
        _cluster_layout("Wymowa", ["10:00–10:20 ×1"], ["sala D 319 ×1"], 200, 15) == []
    )


def test_room_lines_start_after_a_gap():
    placed = place_lines(
        [("Wymowa", "subject"), ("12:10–13:45 ×4", "meta"), ("sala D 319 ×5", "room")]
    )
    subject_dy = placed[0][2]
    time_dy = placed[1][2]
    room_dy = placed[2][2]
    assert subject_dy == BLOCK_PAD_Y
    assert time_dy == BLOCK_PAD_Y + SUBJECT_STEP
    assert room_dy == BLOCK_PAD_Y + SUBJECT_STEP + META_STEP + ROOM_GAP
