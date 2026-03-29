from __future__ import annotations

import pytest

from llll_chart2sus.errors import UnsupportedMappingError
from llll_chart2sus.ir import (
    LinkLikeBeat,
    LinkLikeBpm,
    LinkLikeChart,
    LinkLikeFlags,
    LinkLikeHoldLink,
    LinkLikeNote,
)
from llll_chart2sus.mapper import map_to_sus_chart


def _map_lane_width(l1: float, r1: float) -> tuple[int, int]:
    left = (l1 / 59.0) * 12.0
    right = (r1 / 59.0) * 12.0
    width = max(1, int(round(right - left)))
    lane = 2 + int(round((left + right) / 2.0 - width / 2.0))
    lane = min(13, max(2, lane))
    width = min(14 - lane, max(1, width))
    return lane, width


def test_mapper_maps_hold_note_to_slide_chain():
    hold_note = LinkLikeNote(
        uid=99,
        timing=1.0,
        holds=(
            LinkLikeHoldLink(time=1.2),
            LinkLikeHoldLink(time=1.4),
        ),
        raw_flags=1,
        flags=LinkLikeFlags(note_type=1, r1=12, r2=12, l1=8, l2=8),
    )
    chart = LinkLikeChart(
        notes=(hold_note,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
    )

    sus = map_to_sus_chart(chart, strict=True)
    assert len(sus.taps) == 1
    assert sus.taps[0].tap_type == 7
    assert len(sus.slides) == 3
    assert [item.slide_type for item in sus.slides] == [1, 5, 2]


def test_mapper_merges_uid_linked_hold_notes_into_single_chain():
    first_hold = LinkLikeNote(
        uid=100,
        timing=1.0,
        holds=(
            LinkLikeHoldLink(time=1.2),
            LinkLikeHoldLink(time=1.4, uid=101),
        ),
        raw_flags=1,
        flags=LinkLikeFlags(note_type=1, r1=12, r2=24, l1=8, l2=20),
    )
    second_hold = LinkLikeNote(
        uid=101,
        timing=1.4,
        holds=(LinkLikeHoldLink(time=1.8),),
        raw_flags=1,
        flags=LinkLikeFlags(note_type=1, r1=24, r2=30, l1=20, l2=26),
    )
    chart = LinkLikeChart(
        notes=(first_hold, second_hold),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
        root_note_uids=(100,),
    )

    sus = map_to_sus_chart(chart, strict=True)
    slide_types = [item.slide_type for item in sus.slides]
    assert slide_types.count(1) == 1
    assert slide_types.count(2) == 1
    assert slide_types.count(5) == 2
    assert len({item.channel for item in sus.slides}) == 1

    expected_lane, expected_width = _map_lane_width(20, 24)
    assert any(
        item.slide_type == 5 and item.lane == expected_lane and item.width == expected_width
        for item in sus.slides
    )


def test_mapper_maps_flick_to_directional():
    flick = LinkLikeNote(
        uid=77,
        timing=1.0,
        holds=(),
        raw_flags=2,
        flags=LinkLikeFlags(note_type=2, r1=12, r2=12, l1=8, l2=8),
    )
    chart = LinkLikeChart(
        notes=(flick,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
    )

    sus = map_to_sus_chart(chart, strict=True)
    assert len(sus.taps) == 1
    assert sus.taps[0].tap_type == 3
    assert len(sus.directionals) == 1
    assert sus.directionals[0].directional_type == 1


def test_mapper_raises_on_hold_without_path_points():
    hold_note = LinkLikeNote(
        uid=100,
        timing=1.0,
        holds=(),
        raw_flags=1,
        flags=LinkLikeFlags(note_type=1, r1=12, r2=12, l1=8, l2=8),
    )
    chart = LinkLikeChart(
        notes=(hold_note,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
    )

    with pytest.raises(UnsupportedMappingError) as exc:
        map_to_sus_chart(chart, strict=True)

    assert "uid=100" in str(exc.value)


def test_mapper_raises_on_broken_hold_uid_link():
    hold_note = LinkLikeNote(
        uid=100,
        timing=1.0,
        holds=(LinkLikeHoldLink(time=1.4, uid=999),),
        raw_flags=1,
        flags=LinkLikeFlags(note_type=1, r1=12, r2=24, l1=8, l2=20),
    )
    chart = LinkLikeChart(
        notes=(hold_note,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
        root_note_uids=(100,),
    )

    with pytest.raises(UnsupportedMappingError) as exc:
        map_to_sus_chart(chart, strict=True)

    assert "target: 999" in str(exc.value)


def test_mapper_supports_multiple_bpm_sections():
    note = LinkLikeNote(
        uid=1,
        timing=3.0,
        holds=(),
        raw_flags=0,
        flags=LinkLikeFlags(note_type=0, r1=12, r2=12, l1=8, l2=8),
    )
    chart = LinkLikeChart(
        notes=(note,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0), LinkLikeBpm(bpm=180.0, time=2.0)),
        beats=(LinkLikeBeat(numerator=4, denominator=4, time=0.0),),
        offset=0.0,
    )

    sus = map_to_sus_chart(chart, strict=True)
    assert len(sus.bpm_changes) == 2


def test_mapper_accepts_non_quarter_beats_without_bar_length_failures():
    note = LinkLikeNote(
        uid=1,
        timing=2.0,
        holds=(),
        raw_flags=0,
        flags=LinkLikeFlags(note_type=0, r1=12, r2=12, l1=8, l2=8),
    )
    chart = LinkLikeChart(
        notes=(note,),
        bpms=(LinkLikeBpm(bpm=120.0, time=0.0),),
        beats=(
            LinkLikeBeat(numerator=4, denominator=4, time=0.0),
            LinkLikeBeat(numerator=7, denominator=8, time=1.3),
        ),
        offset=0.0,
    )

    sus = map_to_sus_chart(chart, strict=True)
    assert sus.bar_length == 4
    assert sus.bar_length_changes == ()
