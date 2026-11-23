"""Text tests: room shortening plus week and cluster block layout."""

from PIL import Image, ImageDraw

from plan_render import canvas, style
from plan_render.style import BLOCK_PAD_Y, HOUR_H, META_STEP, ROOM_GAP, SUBJECT_STEP
from plan_render.text import (
    BlockLine,
    CombinedAlternative,
    LineKind,
    layout_block,
    layout_cluster,
    layout_combined,
    place_lines,
    place_sections,
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
    subject: str, times: list[str], text_w: float, minutes: float
) -> list[BlockLine]:
    return layout_cluster(subject, times, text_w, minutes * HOUR_H / 60, _fake_measure)


def _combined_layout(
    alternatives: list[CombinedAlternative], text_w: float, minutes: float
) -> list[list[BlockLine]]:
    return layout_combined(alternatives, text_w, minutes * HOUR_H / 60, _fake_measure)


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


def test_cluster_lists_times():
    lines = _cluster_layout(
        "Świadomość ciała",
        ["14:40–17:05 ×3", "15:00–17:25 ×1"],
        200,
        165,
    )
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]
    assert lines[1][0] == "14:40–17:05 ×3"
    assert lines[2][0] == "15:00–17:25 ×1"


def test_cluster_drops_times_when_tight():
    lines = _cluster_layout(
        "Świadomość ciała",
        ["14:40–17:05 ×3", "15:00–17:25 ×1"],
        200,
        40,
    )
    assert [kind for _, kind in lines] == ["subject"]


def test_cluster_tiny_block_yields_no_lines():
    assert _cluster_layout("Wymowa", ["10:00–10:20 ×1"], 200, 15) == []


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


def test_combined_fits_all_sections_with_times():
    sections = _combined_layout(
        [("Wymowa", ["10:00–11:30 ×2"]), ("Interpretacja prozy", ["9:40–12:05 ×8"])],
        200,
        165,
    )
    assert len(sections) == 2
    assert [kind for _, kind in sections[0]] == ["subject", "meta"]
    assert [kind for _, kind in sections[1]] == ["subject", "meta"]
    assert sections[0][0][0] == "Wymowa"
    assert sections[0][1][0] == "10:00–11:30 ×2"
    assert sections[1][1][0] == "9:40–12:05 ×8"


def test_combined_falls_back_to_subjects_only_when_tight():
    sections = _combined_layout(
        [("Wymowa", ["10:00–11:30 ×2"]), ("Interpretacja prozy", ["9:40–12:05 ×8"])],
        200,
        70,
    )
    assert len(sections) == 2
    assert [kind for _, kind in sections[0]] == ["subject"]
    assert [kind for _, kind in sections[1]] == ["subject"]


def test_combined_tiny_block_yields_no_sections():
    assert _combined_layout([("Wymowa", ["10:00–10:20 ×1"])], 200, 15) == []


def test_combined_truncates_overlong_lines():
    sections = _combined_layout(
        [("Elementarne zadania aktorskie w teatrze lalek", ["10:00–11:30 ×2"])],
        50,
        165,
    )
    assert sections
    assert any(line[0].endswith("…") for line in sections[0])


def test_combined_sections_separated_by_gap():
    placed = place_sections([[("Wymowa", "subject")], [("Głos", "subject")]])
    assert placed[0][0][2] == BLOCK_PAD_Y
    assert placed[1][0][2] == BLOCK_PAD_Y + SUBJECT_STEP + style.SECTION_GAP


def test_combined_chips_use_section_colors():
    base = Image.new("RGB", (300, 300), (20, 25, 30))
    overlay = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    box = (5, 10, 295, 200)
    canvas.draw_combined(
        base,
        draw,
        box,
        [
            (style.WAR_YELLOW, [("Wymowa", "subject")]),
            (style.UNKNOWN_SPINE, [("Głos", "subject")]),
        ],
    )
    left = int(box[0])
    first_chip_y = (
        int(box[1]) + BLOCK_PAD_Y + (SUBJECT_STEP - style.SECTION_CHIP_H) // 2 + 2
    )
    first_chip = overlay.getpixel((left + 4, first_chip_y))
    assert isinstance(first_chip, tuple) and first_chip[:3] == style.WAR_YELLOW
    second_chip_y = (
        int(box[1])
        + BLOCK_PAD_Y
        + SUBJECT_STEP
        + style.SECTION_GAP
        + (SUBJECT_STEP - style.SECTION_CHIP_H) // 2
        + 2
    )
    second_chip = overlay.getpixel((left + 4, second_chip_y))
    assert isinstance(second_chip, tuple) and second_chip[:3] == style.UNKNOWN_SPINE


def test_combined_divider_is_dashed():
    base = Image.new("RGB", (300, 300), (20, 25, 30))
    overlay = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    box = (5, 10, 295, 200)
    canvas.draw_combined(
        base,
        draw,
        box,
        [
            (style.WAR_YELLOW, [("Wymowa", "subject")]),
            (style.WYK_ORANGE, [("Głos", "subject")]),
        ],
    )
    divider_y = int(box[1]) + BLOCK_PAD_Y + SUBJECT_STEP + style.SECTION_GAP // 2
    text_x = int(box[0]) + style.SPINE_W + style.TEXT_GAP
    dash_pixel = overlay.getpixel((text_x + 1, divider_y))
    gap_pixel = overlay.getpixel((text_x + style.DIVIDER_DASH + 1, divider_y))
    assert isinstance(dash_pixel, tuple) and dash_pixel[3] > 0
    assert isinstance(gap_pixel, tuple) and gap_pixel[3] == 0
