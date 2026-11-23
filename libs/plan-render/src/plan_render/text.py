"""Block text: room shortening, wrapping, and line layout for event blocks."""

import re
from collections.abc import Callable
from typing import Literal

from PIL import ImageDraw

from plan_render import style
from plan_render.fonts import font

LineKind = Literal["subject", "meta", "room"]
BlockLine = tuple[str, LineKind]
BlockMeasure = Callable[[str, LineKind], float]
WidthMeasure = Callable[[str], float]

_BUILDING_RE = re.compile(r"^bud\.\S+\s*")
_GENERIC_ROOM_WORDS = {"SALA", "SALE", "PRACOWNIA", "AULA", "HALA"}


def block_measure(draw: ImageDraw.ImageDraw) -> BlockMeasure:
    """Width measurer for block text, using the block subject/meta fonts."""

    subject_font = font("bold", style.SUBJECT_SIZE)
    meta_font = font("italic", style.META_SIZE)

    def measure(text: str, kind: LineKind) -> float:
        return draw.textlength(
            text, font=subject_font if kind == "subject" else meta_font
        )

    return measure


def format_room(raw: str) -> str:
    """Shorten a raw room cell (`bud.D D - 02 - SALA BALETOWA`) for display."""
    if " - " not in raw:
        return f"sala {_clean_code(raw)}"
    code, _, descriptor = raw.rpartition(" - ")
    code = _clean_code(code)
    words = [w for w in descriptor.split() if w not in _GENERIC_ROOM_WORDS]
    detail = " ".join(words).lower()
    if "-" in code and detail:
        return f"sala {code} · {detail}"
    return f"sala {code}"


def layout_block(
    subject: str,
    time_range: str,
    room: str,
    text_w: float,
    block_h: float,
    measure: BlockMeasure,
) -> list[BlockLine]:
    """Lay out one dated class: subject lines plus time/room metadata lines."""

    def meta_width(text: str) -> float:
        return measure(text, "meta")

    time_line = _truncate(time_range, text_w, meta_width)
    room_line = _truncate(room, text_w, meta_width) if room else ""
    combined_line = _truncate(
        f"{time_range} · {room}" if room else time_range, text_w, meta_width
    )

    # Separate time/room beats a combined line; a truncated subject beats
    # combined or dropped metadata. The second subject line is only the
    # wraparound continuation, so it vanishes when the subject fits in one.
    subject_options = _subject_options(subject, text_w, measure)
    separate: list[BlockLine] = [(time_line, "meta"), (room_line, "meta")]
    meta_options: list[list[BlockLine]] = (
        [separate, [(combined_line, "meta")]] if room else [[(time_line, "meta")]]
    )
    for meta in meta_options:
        for subj in subject_options:
            candidate = [*subj, *meta]
            if _fits(candidate, block_h):
                return candidate
    subj_1 = subject_options[-1]
    return subj_1 if _fits(subj_1, block_h) else []


def layout_cluster(
    subject: str,
    times: list[str],
    rooms: list[str],
    text_w: float,
    block_h: float,
    measure: BlockMeasure,
) -> list[BlockLine]:
    """Lay out one overlapping cluster: subject, time variants, room variants.

    Times come sorted by start with counts (`14:40–17:05 ×3`); rooms are
    separate lines with counts (`sala D 319 ×4`). Callers sort; this only wraps
    the subject, truncates variants, and drops rooms when space is tight.
    """

    subject_options = _subject_options(subject, text_w, measure)

    def meta_width(text: str) -> float:
        return measure(text, "meta")

    def room_width(text: str) -> float:
        return measure(text, "room")

    time_lines: list[BlockLine] = [
        (_truncate(time, text_w, meta_width), "meta") for time in times
    ]
    room_lines: list[BlockLine] = [
        (_truncate(room, text_w, room_width), "room") for room in rooms
    ]

    for subj in subject_options:
        if _fits([*subj, *time_lines, *room_lines], block_h):
            return [*subj, *time_lines, *room_lines]
    for subj in subject_options:
        if _fits([*subj, *time_lines], block_h):
            return [*subj, *time_lines]
    subj_1 = subject_options[-1]
    return subj_1 if _fits(subj_1, block_h) else []


def place_lines(lines: list[BlockLine]) -> list[tuple[str, LineKind, int]]:
    """Assign each line a y offset from the block top, with a gap before rooms."""
    placed: list[tuple[str, LineKind, int]] = []
    y = style.BLOCK_PAD_Y
    previous: LineKind | None = None
    for text, kind in lines:
        if kind == "room" and previous != "room":
            y += style.ROOM_GAP
        placed.append((text, kind, y))
        y += _line_step(kind)
        previous = kind
    return placed


def _fits(lines: list[BlockLine], block_h: float) -> bool:
    if not lines:
        return True
    _, kind, dy = place_lines(lines)[-1]
    return dy + _line_step(kind) - style.LINE_SLACK <= block_h - style.BLOCK_PAD_Y


def _line_step(kind: LineKind) -> int:
    return style.SUBJECT_STEP if kind == "subject" else style.META_STEP


def _clean_code(code: str) -> str:
    code = _BUILDING_RE.sub("", code)
    return re.sub(r"-\s+", "-", code).strip()


def _subject_options(
    subject: str, text_w: float, measure: BlockMeasure
) -> list[list[BlockLine]]:
    """One- and two-line subject layouts, preferring two lines when they differ."""
    one: list[BlockLine] = [
        (line, "subject")
        for line in _wrap(subject, text_w, 1, lambda text: measure(text, "subject"))
    ]
    two: list[BlockLine] = [
        (line, "subject")
        for line in _wrap(subject, text_w, 2, lambda text: measure(text, "subject"))
    ]
    return [two, one] if two != one else [one]


def _wrap(
    text: str, max_width: float, max_lines: int, measure: WidthMeasure
) -> list[str]:
    out: list[str] = []
    for word in text.split():
        if out and measure(out[-1] + " " + word) <= max_width:
            out[-1] += " " + word
        elif len(out) < max_lines:
            out.append(word)
        else:
            out[-1] += " " + word
    if out:
        out[-1] = _truncate(out[-1], max_width, measure)
    return out


def _truncate(text: str, max_width: float, measure: WidthMeasure) -> str:
    if measure(text) <= max_width:
        return text
    while text and measure(text + "…") > max_width:
        text = text[:-1]
    return text + "…"
