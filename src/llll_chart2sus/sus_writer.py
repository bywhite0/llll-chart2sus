"""Serialize SUS IR into deterministic text output."""

from __future__ import annotations

from .errors import UnsupportedMappingError
from .ir import SusBpmChange, SusChart


_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _b36_digit(value: int) -> str:
    if not (0 <= value < 36):
        raise ValueError(f"Value out of base36 range: {value}")
    return _BASE36[value]


def _b36_2(value: int) -> str:
    if not (0 <= value < 36 * 36):
        raise ValueError(f"Value out of 2-digit base36 range: {value}")
    return _b36_digit(value // 36) + _b36_digit(value % 36)


def write_sus(chart: SusChart) -> str:
    # One lane line stores events as 2-char tokens; fixed resolution keeps timing deterministic.
    tap_buckets: dict[tuple[int, int], list[str]] = {}
    slide_buckets: dict[tuple[int, int, int], list[str]] = {}
    directional_buckets: dict[tuple[int, int], list[str]] = {}

    for tap in chart.taps:
        key = (tap.bar, tap.lane)
        if key not in tap_buckets:
            tap_buckets[key] = ["00"] * chart.resolution

        current = tap_buckets[key][tap.slot]
        payload = f"{_b36_digit(tap.tap_type)}{_b36_digit(tap.width)}"
        if current != "00" and current != payload:
            # Allow CANCEL taps (type 7/8) to coexist with real taps by preferring the real payload.
            current_type = current[0]
            incoming_type = payload[0]
            if incoming_type in ("7", "8") and current_type not in ("7", "8"):
                continue
            if current_type in ("7", "8") and incoming_type not in ("7", "8"):
                tap_buckets[key][tap.slot] = payload
                continue
            if current_type in ("7", "8") and incoming_type in ("7", "8"):
                # Hidden helper taps for invisible slide points can overlap; keep the first one.
                continue
            raise UnsupportedMappingError(
                note_uid=tap.uid,
                note_timing=0.0,
                note_type="collision",
                reason=(
                    f"Collision at bar={tap.bar}, lane={tap.lane}, slot={tap.slot}: "
                    f"existing={current}, incoming={payload}"
                ),
            )

        tap_buckets[key][tap.slot] = payload

    for slide in chart.slides:
        key = (slide.bar, slide.lane, slide.channel)
        if key not in slide_buckets:
            slide_buckets[key] = ["00"] * chart.resolution

        current = slide_buckets[key][slide.slot]
        payload = f"{_b36_digit(slide.slide_type)}{_b36_digit(slide.width)}"
        if current != "00" and current != payload:
            raise UnsupportedMappingError(
                note_uid=slide.uid,
                note_timing=0.0,
                note_type="slide-collision",
                reason=(
                    f"Collision at bar={slide.bar}, lane={slide.lane}, channel={slide.channel}, "
                    f"slot={slide.slot}: existing={current}, incoming={payload}"
                ),
            )

        slide_buckets[key][slide.slot] = payload

    for directional in chart.directionals:
        key = (directional.bar, directional.lane)
        if key not in directional_buckets:
            directional_buckets[key] = ["00"] * chart.resolution

        current = directional_buckets[key][directional.slot]
        payload = f"{_b36_digit(directional.directional_type)}{_b36_digit(directional.width)}"
        if current != "00" and current != payload:
            raise UnsupportedMappingError(
                note_uid=directional.uid,
                note_timing=0.0,
                note_type="directional-collision",
                reason=(
                    f"Collision at bar={directional.bar}, lane={directional.lane}, slot={directional.slot}: "
                    f"existing={current}, incoming={payload}"
                ),
            )

        directional_buckets[key][directional.slot] = payload

    bar_length_changes = tuple(sorted(chart.bar_length_changes, key=lambda item: item.bar))
    initial_bar_length = bar_length_changes[0].bar_length if bar_length_changes else chart.bar_length

    bpm_changes = tuple(sorted(chart.bpm_changes, key=lambda item: (item.bar, item.slot)))
    if not bpm_changes:
        bpm_changes = (SusBpmChange(bar=0, slot=0, bpm=chart.bpm),)

    bpm_id_map: dict[float, int] = {}
    for item in bpm_changes:
        if item.bpm not in bpm_id_map:
            bpm_id_map[item.bpm] = len(bpm_id_map) + 1
    if len(bpm_id_map) >= 36 * 36:
        raise UnsupportedMappingError(
            note_uid=0,
            note_timing=0.0,
            note_type="bpm",
            reason="Too many unique BPM values for 2-digit base36 definition IDs.",
        )

    bpm_buckets: dict[int, list[str]] = {}
    for item in bpm_changes:
        bar = item.bar
        slot = item.slot
        if bar not in bpm_buckets:
            bpm_buckets[bar] = ["00"] * chart.resolution
        bpm_buckets[bar][slot] = _b36_2(bpm_id_map[item.bpm])

    header = [
        "This file is generated by llll-chart2sus.",
        '#TITLE ""',
        '#ARTIST ""',
        '#DESIGNER "llll_chart2sus"',
        "#DIFFICULTY 0",
        '#PLAYLEVEL ""',
        '#SONGID ""',
        '#WAVE ""',
        f"#WAVEOFFSET {chart.offset:.6f}",
        '#JACKET ""',
        "",
        '#REQUEST "ticks_per_beat 480"',
        "",
        f"#00002: {initial_bar_length}",
        "",
    ]
    for bar_change in bar_length_changes:
        if bar_change.bar == 0:
            continue
        header.append(f"#{bar_change.bar:03d}02: {bar_change.bar_length}")
    if bar_length_changes:
        header.append("")

    for bpm_value, bpm_id in sorted(bpm_id_map.items(), key=lambda item: item[1]):
        header.append(f"#BPM{_b36_2(bpm_id)}: {bpm_value:.6f}")
    header.append("")

    lines = header
    for bar in sorted(bpm_buckets.keys()):
        data = "".join(bpm_buckets[bar])
        lines.append(f"#{bar:03d}08:{data}")

    for (bar, lane) in sorted(tap_buckets.keys()):
        data = "".join(tap_buckets[(bar, lane)])
        lane_char = _b36_digit(lane)
        lines.append(f"#{bar:03d}1{lane_char}:{data}")

    for (bar, lane, channel) in sorted(slide_buckets.keys()):
        data = "".join(slide_buckets[(bar, lane, channel)])
        lane_char = _b36_digit(lane)
        channel_char = _b36_digit(channel)
        lines.append(f"#{bar:03d}3{lane_char}{channel_char}:{data}")

    for (bar, lane) in sorted(directional_buckets.keys()):
        data = "".join(directional_buckets[(bar, lane)])
        lane_char = _b36_digit(lane)
        lines.append(f"#{bar:03d}5{lane_char}:{data}")

    lines.append("")
    return "\n".join(lines)
