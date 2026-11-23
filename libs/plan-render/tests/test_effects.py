"""Effects tests: deterministic grain that adds texture to flat areas."""

from datetime import date

from PIL import ImageStat

from plan_render.background import background_for_date
from plan_render.effects import apply_grain


def test_grain_is_deterministic():
    bare = background_for_date(date(2026, 10, 19), 800, 600)
    seed = date(2026, 10, 19).toordinal()
    assert apply_grain(bare, seed).tobytes() == apply_grain(bare, seed).tobytes()


def test_grain_raises_variance_on_background_patch():
    bare = background_for_date(date(2026, 10, 19), 800, 600)
    grained = apply_grain(bare, date(2026, 10, 19).toordinal())
    patch = (8, 8, 40, 40)
    grained_std = sum(ImageStat.Stat(grained.crop(patch)).stddev)
    bare_std = sum(ImageStat.Stat(bare.crop(patch)).stddev)
    assert grained_std > bare_std
