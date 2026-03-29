"""Map LinkLike chart IR to a minimal SUS IR."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .errors import UnsupportedMappingError
from .ir import (
    LinkLikeChart,
    LinkLikeNote,
    LinkLikeNoteType,
    SusBpmChange,
    SusChart,
    SusDirectionalEvent,
    SusSlideEvent,
    SusTapEvent,
)


_FLOAT_EPSILON = 1e-6


def _map_tap_type(note_type: int, uid: int, timing: float) -> int:
    # Tap type values follow scores/src/pjsekai/scores/notes/tap.py.
    if note_type == LinkLikeNoteType.SINGLE:
        return 1  # TAP
    if note_type == LinkLikeNoteType.TRACE:
        return 5  # TREND/TRACE-like placeholder
    raise UnsupportedMappingError(
        note_uid=uid,
        note_timing=timing,
        note_type=str(note_type),
        reason="Not a tap-mappable LinkLike note type.",
    )


def _map_lane_width(l1: float, r1: float) -> tuple[int, int]:
    left = (l1 / 59.0) * 12.0
    right = (r1 / 59.0) * 12.0
    width = max(1, int(round(right - left)))
    lane = 2 + int(round((left + right) / 2.0 - width / 2.0))
    lane = min(13, max(2, lane))
    width = min(14 - lane, max(1, width))
    return lane, width


def _bar_slot_from_float(bar_float: float, resolution: int) -> tuple[int, int]:
    bar = int(math.floor(bar_float))
    frac = bar_float - bar
    slot = int(round(frac * resolution))
    if slot >= resolution:
        bar += 1
        slot = 0
    return bar, slot


@dataclass(frozen=True)
class _BpmPoint:
    time: float
    bpm: float


class _TimingMap:
    """BPM-only timing conversion aligned with llll-chart ChartRenderer."""

    def __init__(self, chart: LinkLikeChart):
        self.offset = float(chart.offset)
        self.bpms = self._normalize_bpms(chart)
        self.initial_bar_length = int(chart.beats[0].numerator)

    def _normalize_bpms(self, chart: LinkLikeChart) -> list[_BpmPoint]:
        points = sorted(
            (_BpmPoint(time=float(item.time), bpm=float(item.bpm)) for item in chart.bpms),
            key=lambda item: item.time,
        )
        if not points:
            raise UnsupportedMappingError(
                note_uid=0,
                note_timing=0.0,
                note_type="bpm",
                reason="Chart has no BPM entries.",
            )
        return points

    def bpm_at_chart_start(self) -> float:
        # Follows llll-chart: last bpm with Time <= Offset, else first bpm.
        current_bpm = self.bpms[0].bpm
        for point in self.bpms:
            if point.time <= self.offset + _FLOAT_EPSILON:
                current_bpm = point.bpm
            else:
                break
        return current_bpm

    def beat_at(self, chart_relative_seconds: float) -> float:
        absolute_target_seconds = float(chart_relative_seconds) + self.offset
        current_beat = 0.0
        current_time_pointer = self.offset

        current_bpm = self.bpms[0].bpm
        next_bpm_event_index = 0
        for i, point in enumerate(self.bpms):
            if point.time <= current_time_pointer + _FLOAT_EPSILON:
                current_bpm = point.bpm
                next_bpm_event_index = i + 1
            else:
                break

        while current_time_pointer < absolute_target_seconds:
            if current_bpm == 0:
                next_change_time = absolute_target_seconds
                if next_bpm_event_index < len(self.bpms):
                    next_change_time = min(next_change_time, self.bpms[next_bpm_event_index].time)
                current_time_pointer = next_change_time
                if (
                    next_bpm_event_index < len(self.bpms)
                    and current_time_pointer >= self.bpms[next_bpm_event_index].time
                ):
                    current_bpm = self.bpms[next_bpm_event_index].bpm
                    next_bpm_event_index += 1
                continue

            seconds_per_beat = 60.0 / current_bpm
            time_of_next_bpm_change = absolute_target_seconds
            if next_bpm_event_index < len(self.bpms):
                time_of_next_bpm_change = self.bpms[next_bpm_event_index].time

            end_of_segment = min(absolute_target_seconds, time_of_next_bpm_change)
            time_delta = end_of_segment - current_time_pointer
            if time_delta > _FLOAT_EPSILON:
                current_beat += time_delta / seconds_per_beat
            current_time_pointer = end_of_segment

            if (
                current_time_pointer >= time_of_next_bpm_change - _FLOAT_EPSILON
                and next_bpm_event_index < len(self.bpms)
            ):
                current_bpm = self.bpms[next_bpm_event_index].bpm
                next_bpm_event_index += 1

        return current_beat

    def bar_float_at(self, chart_relative_seconds: float) -> float:
        return self.beat_at(chart_relative_seconds) / float(self.initial_bar_length)

    def bar_slot_at(self, chart_relative_seconds: float, resolution: int) -> tuple[int, int]:
        return _bar_slot_from_float(self.bar_float_at(chart_relative_seconds), resolution)


@dataclass(frozen=True)
class _HoldSegment:
    owner_uid: int
    start_time: float
    end_time: float
    start_l: float
    start_r: float
    end_l: float
    end_r: float


@dataclass(frozen=True)
class _HoldChain:
    root_uid: int
    start_time: float
    end_time: float
    segments: tuple[_HoldSegment, ...]


def _collect_hold_roots(chart: LinkLikeChart, hold_notes_by_uid: dict[int, LinkLikeNote]) -> list[int]:
    if chart.root_note_uids:
        return [uid for uid in chart.root_note_uids if uid in hold_notes_by_uid]

    linked_uids = {
        hold.uid
        for note in hold_notes_by_uid.values()
        for hold in note.holds
        if hold.uid is not None
    }
    return [
        note.uid
        for note in chart.notes
        if note.uid in hold_notes_by_uid and note.uid not in linked_uids
    ]


def _build_hold_segments_for_note(
    note: LinkLikeNote,
    hold_notes_by_uid: dict[int, LinkLikeNote],
) -> tuple[list[_HoldSegment], int | None]:
    if not note.holds:
        raise UnsupportedMappingError(
            note_uid=note.uid,
            note_timing=note.timing,
            note_type="hold",
            reason="Hold note has no hold timing points.",
        )

    current_segment_start_time = note.timing
    note_hold_start_time = note.timing
    overall_initial_lane_l = float(note.flags.l1)
    overall_initial_lane_r = float(note.flags.r1)
    overall_final_lane_l = float(note.flags.l2)
    overall_final_lane_r = float(note.flags.r2)
    current_segment_start_lane_l = overall_initial_lane_l
    current_segment_start_lane_r = overall_initial_lane_r

    last_hold_target = note.holds[-1]
    if last_hold_target.uid is None:
        note_hold_end_time = last_hold_target.time
    else:
        linked_tail_note = hold_notes_by_uid.get(last_hold_target.uid)
        if linked_tail_note is None:
            raise UnsupportedMappingError(
                note_uid=note.uid,
                note_timing=note.timing,
                note_type="hold",
                reason=f"Invalid hold uid link target: {last_hold_target.uid}",
            )
        note_hold_end_time = linked_tail_note.timing

    total_note_hold_duration = note_hold_end_time - note_hold_start_time
    segments: list[_HoldSegment] = []
    next_note_uid: int | None = None

    for hold_end in note.holds:
        linked_note: LinkLikeNote | None = None
        if hold_end.uid is None:
            segment_end_time = hold_end.time
        else:
            linked_note = hold_notes_by_uid.get(hold_end.uid)
            if linked_note is None:
                raise UnsupportedMappingError(
                    note_uid=note.uid,
                    note_timing=note.timing,
                    note_type="hold",
                    reason=f"Invalid hold uid link target: {hold_end.uid}",
                )
            segment_end_time = linked_note.timing

        if linked_note is not None:
            segment_end_lane_l = float(linked_note.flags.l1)
            segment_end_lane_r = float(linked_note.flags.r1)
        elif segment_end_time <= current_segment_start_time:
            segment_end_lane_l = current_segment_start_lane_l
            segment_end_lane_r = current_segment_start_lane_r
        elif total_note_hold_duration < _FLOAT_EPSILON:
            segment_end_lane_l = overall_final_lane_l
            segment_end_lane_r = overall_final_lane_r
        elif segment_end_time <= note_hold_start_time:
            segment_end_lane_l = overall_initial_lane_l
            segment_end_lane_r = overall_initial_lane_r
        elif segment_end_time >= note_hold_end_time:
            segment_end_lane_l = overall_final_lane_l
            segment_end_lane_r = overall_final_lane_r
        else:
            fraction = (segment_end_time - note_hold_start_time) / total_note_hold_duration
            segment_end_lane_l = overall_initial_lane_l + (
                overall_final_lane_l - overall_initial_lane_l
            ) * fraction
            segment_end_lane_r = overall_initial_lane_r + (
                overall_final_lane_r - overall_initial_lane_r
            ) * fraction

        segments.append(
            _HoldSegment(
                owner_uid=note.uid,
                start_time=current_segment_start_time,
                end_time=segment_end_time,
                start_l=current_segment_start_lane_l,
                start_r=current_segment_start_lane_r,
                end_l=segment_end_lane_l,
                end_r=segment_end_lane_r,
            )
        )

        current_segment_start_time = segment_end_time
        current_segment_start_lane_l = segment_end_lane_l
        current_segment_start_lane_r = segment_end_lane_r

        if linked_note is not None and next_note_uid is None:
            next_note_uid = linked_note.uid

    return segments, next_note_uid


def _build_hold_chains(chart: LinkLikeChart) -> list[_HoldChain]:
    hold_notes_by_uid = {
        note.uid: note for note in chart.notes if note.flags.note_type == LinkLikeNoteType.HOLD
    }
    if not hold_notes_by_uid:
        return []

    roots = _collect_hold_roots(chart, hold_notes_by_uid)
    chains: list[_HoldChain] = []
    consumed_uids: set[int] = set()

    for root_uid in roots:
        if root_uid in consumed_uids:
            continue

        current_uid: int | None = root_uid
        chain_uids: set[int] = set()
        chain_segments: list[_HoldSegment] = []

        while current_uid is not None:
            if current_uid in chain_uids:
                note = hold_notes_by_uid[current_uid]
                raise UnsupportedMappingError(
                    note_uid=current_uid,
                    note_timing=note.timing,
                    note_type="hold",
                    reason="Cyclic hold uid links detected.",
                )

            chain_uids.add(current_uid)
            consumed_uids.add(current_uid)
            current_note = hold_notes_by_uid.get(current_uid)
            if current_note is None:
                raise UnsupportedMappingError(
                    note_uid=root_uid,
                    note_timing=0.0,
                    note_type="hold",
                    reason=f"Linked hold note uid not found: {current_uid}",
                )

            segments, next_uid = _build_hold_segments_for_note(current_note, hold_notes_by_uid)
            chain_segments.extend(segments)
            current_uid = next_uid

        if not chain_segments:
            continue

        chains.append(
            _HoldChain(
                root_uid=root_uid,
                start_time=chain_segments[0].start_time,
                end_time=chain_segments[-1].end_time,
                segments=tuple(chain_segments),
            )
        )

    # Align with llll-chart root-based rendering: hold notes that are not reachable
    # from any root (e.g. self-loop-only chains) are ignored.

    return chains


@dataclass(frozen=True)
class _HoldInterval:
    uid: int
    start_key: int
    end_key: int


def _assign_hold_channels(
    hold_chains: list[_HoldChain],
    timing_map: _TimingMap,
    resolution: int,
    max_channels: int = 36,
) -> dict[int, int]:
    intervals: list[_HoldInterval] = []
    for chain in hold_chains:
        start_bar, start_slot = timing_map.bar_slot_at(chain.start_time, resolution)
        end_bar, end_slot = timing_map.bar_slot_at(chain.end_time, resolution)
        intervals.append(
            _HoldInterval(
                uid=chain.root_uid,
                start_key=start_bar * resolution + start_slot,
                end_key=end_bar * resolution + end_slot,
            )
        )

    intervals.sort(key=lambda item: (item.start_key, item.uid))
    active: list[tuple[int, int]] = []
    assignments: dict[int, int] = {}

    for interval in intervals:
        # Keep channel occupied when end and next start share the same quantized slot.
        active = [(end_key, channel) for (end_key, channel) in active if end_key >= interval.start_key]
        used_channels = {channel for _, channel in active}
        free_channels = [channel for channel in range(max_channels) if channel not in used_channels]
        if not free_channels:
            raise UnsupportedMappingError(
                note_uid=interval.uid,
                note_timing=0.0,
                note_type="hold",
                reason=f"Too many overlapping hold chains (>{max_channels}).",
            )
        channel = free_channels[0]
        active.append((interval.end_key, channel))
        assignments[interval.uid] = channel

    return assignments


def _build_hold_slide_events(
    chain: _HoldChain,
    channel: int,
    timing_map: _TimingMap,
    resolution: int,
) -> tuple[list[SusSlideEvent], list[SusTapEvent]]:
    nodes: list[tuple[float, float, float]] = [
        (chain.segments[0].start_time, chain.segments[0].start_l, chain.segments[0].start_r)
    ]
    for segment in chain.segments:
        nodes.append((segment.end_time, segment.end_l, segment.end_r))

    events: list[SusSlideEvent] = []
    hidden_mid_taps: list[SusTapEvent] = []
    for index, (timing, lane_l, lane_r) in enumerate(nodes):
        lane, width = _map_lane_width(lane_l, lane_r)
        bar, slot = timing_map.bar_slot_at(timing, resolution)

        if index == 0:
            slide_type = 1  # START
        elif index == len(nodes) - 1:
            slide_type = 2  # END
        else:
            slide_type = 5  # INVISIBLE

        events.append(
            SusSlideEvent(
                uid=chain.root_uid,
                bar=bar,
                slot=slot,
                lane=lane,
                width=width,
                channel=channel,
                slide_type=slide_type,
            )
        )
        if slide_type == 5:
            hidden_mid_taps.append(
                SusTapEvent(
                    uid=chain.root_uid,
                    bar=bar,
                    slot=slot,
                    lane=lane,
                    width=width,
                    tap_type=7,  # CANCEL
                )
            )

    compacted: list[SusSlideEvent] = []
    for event in events:
        if compacted:
            prev = compacted[-1]
            if (prev.bar, prev.slot, prev.lane, prev.channel) == (event.bar, event.slot, event.lane, event.channel):
                # Same quantized point on the same line: keep the later state.
                compacted[-1] = event
                continue
        compacted.append(event)

    compact_keys = {
        (item.bar, item.slot, item.lane, item.width)
        for item in compacted
        if item.slide_type == 5
    }
    compact_hidden = [
        item
        for item in hidden_mid_taps
        if (item.bar, item.slot, item.lane, item.width) in compact_keys
    ]
    return compacted, compact_hidden


def _build_bpm_changes(chart: LinkLikeChart, timing_map: _TimingMap, resolution: int) -> tuple[SusBpmChange, ...]:
    changes = sorted(chart.bpms, key=lambda item: item.time)
    dedup: dict[tuple[int, int], float] = {}
    for item in changes:
        chart_relative_seconds = float(item.time) - float(chart.offset)
        bar, slot = timing_map.bar_slot_at(chart_relative_seconds, resolution)
        dedup[(bar, slot)] = float(item.bpm)
    if (0, 0) not in dedup:
        dedup[(0, 0)] = timing_map.bpm_at_chart_start()
    result = [
        SusBpmChange(bar=bar, slot=slot, bpm=bpm)
        for (bar, slot), bpm in sorted(dedup.items(), key=lambda item: (item[0][0], item[0][1]))
    ]
    return tuple(result)


def _get_initial_bar_length(chart: LinkLikeChart) -> int:
    if not chart.beats:
        raise UnsupportedMappingError(
            note_uid=0,
            note_timing=0.0,
            note_type="time-signature",
            reason="Chart has no beat entries.",
        )
    first_numerator = int(chart.beats[0].numerator)
    if first_numerator <= 0:
        raise UnsupportedMappingError(
            note_uid=0,
            note_timing=float(chart.beats[0].time),
            note_type="time-signature",
            reason=f"Invalid initial numerator: {first_numerator}",
        )
    return first_numerator


def map_to_sus_chart(chart: LinkLikeChart, strict: bool = False) -> SusChart:
    timing_map = _TimingMap(chart)
    bar_length = _get_initial_bar_length(chart)
    resolution = max(1920, 480 * bar_length)

    bpm_changes = _build_bpm_changes(chart, timing_map, resolution)
    bar_length_changes = tuple()

    taps: list[SusTapEvent] = []
    slides: list[SusSlideEvent] = []
    directionals: list[SusDirectionalEvent] = []

    hold_chains = _build_hold_chains(chart)
    hold_channel_map = _assign_hold_channels(
        hold_chains=hold_chains,
        timing_map=timing_map,
        resolution=resolution,
    )
    for chain in hold_chains:
        channel = hold_channel_map[chain.root_uid]
        hold_slides, hidden_taps = _build_hold_slide_events(
            chain=chain,
            channel=channel,
            timing_map=timing_map,
            resolution=resolution,
        )
        slides.extend(hold_slides)
        taps.extend(hidden_taps)

    for note in chart.notes:
        if note.flags.note_type == LinkLikeNoteType.HOLD:
            continue

        bar, slot = timing_map.bar_slot_at(note.timing, resolution)
        lane, width = _map_lane_width(note.flags.l1, note.flags.r1)

        if strict:
            if not (2 <= lane <= 13):
                raise UnsupportedMappingError(
                    note_uid=note.uid,
                    note_timing=note.timing,
                    note_type=str(note.flags.note_type),
                    reason=f"Mapped lane out of range: {lane}",
                )
            if width < 1:
                raise UnsupportedMappingError(
                    note_uid=note.uid,
                    note_timing=note.timing,
                    note_type=str(note.flags.note_type),
                    reason=f"Mapped width out of range: {width}",
                )

        if note.flags.note_type == LinkLikeNoteType.FLICK:
            # Keep directional for renderer compatibility, and add TapType.FLICK
            # so consumers that count flicks from tap type can recognize them.
            taps.append(
                SusTapEvent(
                    uid=note.uid,
                    bar=bar,
                    slot=slot,
                    lane=lane,
                    width=width,
                    tap_type=3,  # FLICK
                )
            )
            directionals.append(
                SusDirectionalEvent(
                    uid=note.uid,
                    bar=bar,
                    slot=slot,
                    lane=lane,
                    width=width,
                    directional_type=1,  # UP
                )
            )
            continue

        tap_type = _map_tap_type(note.flags.note_type, note.uid, note.timing)
        taps.append(
            SusTapEvent(
                uid=note.uid,
                bar=bar,
                slot=slot,
                lane=lane,
                width=width,
                tap_type=tap_type,
            )
        )

    taps_sorted = tuple(sorted(taps, key=lambda item: (item.bar, item.slot, item.lane, item.uid)))
    slides_sorted = tuple(
        sorted(
            slides,
            key=lambda item: (item.channel, item.bar, item.slot, item.slide_type, item.uid),
        )
    )
    directionals_sorted = tuple(
        sorted(directionals, key=lambda item: (item.bar, item.slot, item.lane, item.uid))
    )
    return SusChart(
        bpm=float(chart.bpms[0].bpm),
        offset=chart.offset,
        bar_length=bar_length,
        resolution=resolution,
        taps=taps_sorted,
        slides=slides_sorted,
        directionals=directionals_sorted,
        bpm_changes=bpm_changes,
        bar_length_changes=bar_length_changes,
    )
