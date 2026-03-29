from __future__ import annotations

from llll_chart2sus.ir import SusChart, SusTapEvent
from llll_chart2sus.sus_writer import write_sus


def test_sus_writer_is_deterministic():
    chart = SusChart(
        bpm=120.0,
        offset=0.0,
        bar_length=4,
        resolution=8,
        taps=(
            SusTapEvent(uid=2, bar=0, slot=2, lane=4, width=1, tap_type=1),
            SusTapEvent(uid=1, bar=0, slot=1, lane=4, width=1, tap_type=3),
        ),
    )

    first = write_sus(chart)
    second = write_sus(chart)

    assert first == second
    assert "#00014:" in first

