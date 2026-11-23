"""Block text: room shortening, wrapping, and line layout for event blocks."""

import itertools
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
ChoiceAlternative = tuple[str, list[str]]

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
    text_w: float,
    block_h: float,
    measure: BlockMeasure,
) -> list[BlockLine]:
    """Lay out one overlapping cluster: subject plus time variants.

    Times come sorted by start with counts (`14:40–17:05 ×3`). Callers sort;
    this only wraps the subject, truncates variants, and drops times when
    space is tight.
    """

    subject_options = _subject_options(subject, text_w, measure)

    def meta_width(text: str) -> float:
        return measure(text, "meta")

    time_lines: list[BlockLine] = [
        (_truncate(time, text_w, meta_width), "meta") for time in times
    ]

    for subj in subject_options:
        if _fits([*subj, *time_lines], block_h):
            return [*subj, *time_lines]
    subj_1 = subject_options[-1]
    return subj_1 if _fits(subj_1, block_h) else []


def layout_choice_block(
    alternatives: list[ChoiceAlternative],
    text_w: float,
    block_h: float,
    measure: BlockMeasure,
) -> list[list[BlockLine]]:
    """Lay out colliding classes as one combined block, one section per class.

    Each alternative is a (subject, time labels) pair; time labels already carry
    counts (`13:00–15:25 ×4`). Subjects wrap exactly like `layout_cluster`;
    sections share the block with a `SEPARATOR_GAP` divider between them.
    Falls back from full sections to subjects-only, then to an empty block.
    """

    if not alternatives:
        return []

    def meta_width(text: str) -> float:
        return measure(text, "meta")

    subject_options = [
        _subject_options(subject, text_w, measure) for subject, _ in alternatives
    ]
    time_lines: list[list[BlockLine]] = [
        [(_truncate(label, text_w, meta_width), "meta") for label in times]
        for _, times in alternatives
    ]

    for subjects in itertools.product(*subject_options):
        sections = [
            [*subj, *times] for subj, times in zip(subjects, time_lines, strict=True)
        ]
        if _fits_choice(sections, block_h):
            return sections
    for subjects in itertools.product(*subject_options):
        sections = [list(subj) for subj in subjects]
        if _fits_choice(sections, block_h):
            return sections
    return []


def place_choice_sections(
    sections: list[list[BlockLine]],
) -> list[list[tuple[str, LineKind, int]]]:
    """Assign each choice-block line a y offset, with gaps between sections."""
    placed_sections: list[list[tuple[str, LineKind, int]]] = []
    y = style.BLOCK_PAD_Y
    for index, section in enumerate(sections):
        if index > 0:
            y += style.SEPARATOR_GAP
        placed: list[tuple[str, LineKind, int]] = []
        for text, kind in section:
            placed.append((text, kind, y))
            y += _line_step(kind)
        placed_sections.append(placed)
    return placed_sections


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


def _fits_choice(sections: list[list[BlockLine]], block_h: float) -> bool:
    if not sections:
        return True
    placed = place_choice_sections(sections)
    non_empty = [section for section in placed if section]
    if not non_empty:
        return True
    _, kind, dy = non_empty[-1][-1]
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
