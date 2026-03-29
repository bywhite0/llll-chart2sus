"""Intermediate representations for source chart and SUS output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class LinkLikeNoteType(IntEnum):
    SINGLE = 0
    HOLD = 1
    FLICK = 2
    TRACE = 3


@dataclass(frozen=True)
class LinkLikeFlags:
    note_type: int
    r1: int
    r2: int
    l1: int
    l2: int


@dataclass(frozen=True)
class LinkLikeHoldLink:
    time: float
    uid: int | None = None


@dataclass(frozen=True)
class LinkLikeNote:
    uid: int
    timing: float
    holds: tuple[LinkLikeHoldLink, ...]
    raw_flags: int
    flags: LinkLikeFlags


@dataclass(frozen=True)
class LinkLikeBpm:
    bpm: float
    time: float


@dataclass(frozen=True)
class LinkLikeBeat:
    numerator: int
    denominator: int
    time: float


@dataclass(frozen=True)
class LinkLikeChart:
    notes: tuple[LinkLikeNote, ...]
    bpms: tuple[LinkLikeBpm, ...]
    beats: tuple[LinkLikeBeat, ...]
    offset: float
    root_note_uids: tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SusTapEvent:
    uid: int
    bar: int
    slot: int
    lane: int
    width: int
    tap_type: int


@dataclass(frozen=True)
class SusSlideEvent:
    uid: int
    bar: int
    slot: int
    lane: int
    width: int
    channel: int
    slide_type: int


@dataclass(frozen=True)
class SusDirectionalEvent:
    uid: int
    bar: int
    slot: int
    lane: int
    width: int
    directional_type: int


@dataclass(frozen=True)
class SusBpmChange:
    bar: int
    slot: int
    bpm: float


@dataclass(frozen=True)
class SusBarLengthChange:
    bar: int
    bar_length: int


@dataclass(frozen=True)
class SusChart:
    bpm: float
    offset: float
    bar_length: int
    resolution: int
    taps: tuple[SusTapEvent, ...] = field(default_factory=tuple)
    slides: tuple[SusSlideEvent, ...] = field(default_factory=tuple)
    directionals: tuple[SusDirectionalEvent, ...] = field(default_factory=tuple)
    bpm_changes: tuple[SusBpmChange, ...] = field(default_factory=tuple)
    bar_length_changes: tuple[SusBarLengthChange, ...] = field(default_factory=tuple)
