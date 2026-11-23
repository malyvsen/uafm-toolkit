"""Shared graphite-frost visuals: palette, geometry, and timetable labels."""

OFF_WHITE = (244, 245, 246)
SOFT_GREY = (185, 192, 201)
ROOM_GREY = (150, 157, 168)
AXIS_LABEL = (244, 245, 246, 160)
HOUR_LINE = (255, 255, 255, 14)
EVENT_BORDER = (255, 255, 255, 90)
UNKNOWN_SPINE = (154, 163, 175)
WAR_YELLOW = (233, 202, 110)
WYK_ORANGE = (216, 142, 93)
KON_PINK = (229, 168, 178)

START_HOUR = 8
END_HOUR = 22
HOUR_H = 100
# Hour rows stop this far from event-block edges so lines never touch blocks.
HOUR_CLEARANCE = 4
COL_W = 300
GUTTER = 24
AXIS_W = 76
MARGIN_X = 36
MARGIN_TOP = 48
MARGIN_BOTTOM = 48
TITLE_SIZE = 64
SUBTITLE_SIZE = 30
DAY_SIZE = 26
AXIS_SIZE = 20
SUBJECT_SIZE = 24
META_SIZE = 21
LEGEND_SIZE = 24

# Header geometry mirrors draw_header: title line, gap, subtitle line,
# then day labels and gaps before the grid. Fixed offsets keep renders stable.
TITLE_H = 76
TITLE_GAP = 8
SUBTITLE_H = 40
DAY_LABEL_H = 30
DAY_LABEL_GAP = 36
GRID_GAP = 12
GRID_TOP = (
    MARGIN_TOP
    + TITLE_H
    + TITLE_GAP
    + SUBTITLE_H
    + DAY_LABEL_H
    + DAY_LABEL_GAP
    + GRID_GAP
)

# Class-block geometry: inset from the column edge, thick spine on the left,
# then text with a right inset. Text lines use 6pt leading.
BLOCK_PAD_X = 5
SPINE_W = 8
TEXT_GAP = 12
TEXT_PAD_RIGHT = 6
BLOCK_PAD_Y = 10
SUBJECT_STEP = 30
META_STEP = 27
# Extra space between the time lines and the room lines of a cluster block.
ROOM_GAP = 7
LINE_SLACK = 8

# Frosted glass for event blocks: blur and white overlay, plus corner radius.
EVENT_BLUR_RADIUS = 14
EVENT_WHITE_ALPHA = 32
EVENT_RADIUS = 12

# Legend: bare spine bar plus label at a fixed gap, rows stacked with the same gap.
LEGEND_SPINE_W = 7
LEGEND_BAR_H = 28
LEGEND_GAP = 12

DAY_NAMES = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]
MONTHS = [
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
]
FORM_STYLES = {
    "War": ("Warsztaty", WAR_YELLOW),
    "Wyk": ("Wykład", WYK_ORANGE),
    "Kon": ("Konwersatorium", KON_PINK),
}


def spine_for(form: str) -> tuple[int, ...]:
    """Spine color for a class form, muted for unknown forms."""
    return FORM_STYLES.get(form, ("", UNKNOWN_SPINE))[1]


def text_width(column: float) -> float:
    """Usable text width inside a block filling `column` pixels."""
    return column - 2 * BLOCK_PAD_X - SPINE_W - TEXT_GAP - TEXT_PAD_RIGHT
