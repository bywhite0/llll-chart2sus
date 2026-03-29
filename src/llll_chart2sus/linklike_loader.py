"""Load LinkLike chart JSON files into typed IR objects."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import LoaderError
from .ir import (
    LinkLikeBeat,
    LinkLikeBpm,
    LinkLikeChart,
    LinkLikeFlags,
    LinkLikeHoldLink,
    LinkLikeNote,
    LinkLikeNoteType,
)


_HOLD_NOTE_KEY_DIGITS = 2
_HOLD_NOTE_KEY_PRECISION = 10**_HOLD_NOTE_KEY_DIGITS


@dataclass(frozen=True)
class _RawNote:
    uid: int
    timing: float
    holds: tuple[str, ...]
    raw_flags: int
    flags: LinkLikeFlags


def decode_flags(raw_flags: int) -> LinkLikeFlags:
    return LinkLikeFlags(
        note_type=raw_flags & 0xF,
        r1=(raw_flags >> 4) & 0x3F,
        r2=(raw_flags >> 10) & 0x3F,
        l1=(raw_flags >> 16) & 0x3F,
        l2=(raw_flags >> 22) & 0x3F,
    )


def _require_key(container: dict[str, Any], key: str) -> Any:
    if key not in container:
        raise LoaderError(f"Missing required key: {key}")
    return container[key]


def _to_float(value: Any, *, field: str, note_uid: int | None = None) -> float:
    try:
        return float(value)
    except Exception as exc:  # pragma: no cover - delegated to error formatting
        if note_uid is None:
            raise LoaderError(f"Invalid numeric value for {field}: {value!r}") from exc
        raise LoaderError(f"Invalid numeric value for {field} at note uid={note_uid}: {value!r}") from exc


def _hold_note_key(value: str | float) -> str:
    # Matches llll-chart: ceil(seconds * 100) / 100 with 2 fixed decimals.
    seconds = float(value)
    normalized = math.ceil(seconds * _HOLD_NOTE_KEY_PRECISION) / _HOLD_NOTE_KEY_PRECISION
    return f"{normalized:.{_HOLD_NOTE_KEY_DIGITS}f}"


def _parse_raw_notes(raw_notes: list[dict[str, Any]]) -> list[_RawNote]:
    parsed: list[_RawNote] = []
    seen_uids: set[int] = set()
    for raw_note in raw_notes:
        uid = int(_require_key(raw_note, "Uid"))
        if uid in seen_uids:
            raise LoaderError(f"Duplicate note uid detected: {uid}")
        seen_uids.add(uid)

        raw_flags = int(_require_key(raw_note, "Flags"))
        holds_raw = raw_note.get("holds", [])
        if not isinstance(holds_raw, list):
            raise LoaderError(f"Invalid holds payload at note uid={uid}: expected list")

        parsed.append(
            _RawNote(
                uid=uid,
                timing=_to_float(_require_key(raw_note, "just"), field="just", note_uid=uid),
                holds=tuple(str(item) for item in holds_raw),
                raw_flags=raw_flags,
                flags=decode_flags(raw_flags),
            )
        )
    return parsed


def _build_hold_notes_by_time(raw_notes: list[_RawNote]) -> dict[str, list[_RawNote]]:
    hold_notes_by_time: dict[str, list[_RawNote]] = {}
    for raw_note in raw_notes:
        if raw_note.flags.note_type != LinkLikeNoteType.HOLD:
            continue
        key = _hold_note_key(raw_note.timing)
        hold_notes_by_time.setdefault(key, []).append(raw_note)
    return hold_notes_by_time


def _resolve_hold_links(
    raw_notes: list[_RawNote],
    hold_notes_by_time: dict[str, list[_RawNote]],
) -> tuple[list[LinkLikeNote], set[int]]:
    notes: list[LinkLikeNote] = []
    chained_note_uids: set[int] = set()

    for raw_note in raw_notes:
        resolved_holds: list[LinkLikeHoldLink] = []

        for index, hold_time_str in enumerate(raw_note.holds):
            hold_time = _to_float(hold_time_str, field="holds", note_uid=raw_note.uid)
            is_last_segment = index == len(raw_note.holds) - 1
            linked_uid: int | None = None

            if is_last_segment and raw_note.flags.note_type == LinkLikeNoteType.HOLD:
                key = _hold_note_key(hold_time_str)
                for target in hold_notes_by_time.get(key, []):
                    if target.uid in chained_note_uids:
                        continue
                    if raw_note.flags.l2 == target.flags.l1 and raw_note.flags.r2 == target.flags.r1:
                        linked_uid = target.uid
                        chained_note_uids.add(target.uid)
                        break

            resolved_holds.append(LinkLikeHoldLink(time=hold_time, uid=linked_uid))

        notes.append(
            LinkLikeNote(
                uid=raw_note.uid,
                timing=raw_note.timing,
                holds=tuple(resolved_holds),
                raw_flags=raw_note.raw_flags,
                flags=raw_note.flags,
            )
        )
    return notes, chained_note_uids


def load_linklike_chart(path: str | Path) -> LinkLikeChart:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - delegated to error handling
        raise LoaderError(f"Failed to read JSON: {path}") from exc

    try:
        raw_notes = _require_key(data, "Notes")
        raw_bpms = _require_key(data, "Bpms")
        raw_beats = _require_key(data, "Beats")
        raw_offset = data.get("Offset", 0.0)
    except LoaderError:
        raise
    except Exception as exc:  # pragma: no cover
        raise LoaderError("Malformed chart root object") from exc

    parsed_raw_notes = _parse_raw_notes(raw_notes)
    hold_notes_by_time = _build_hold_notes_by_time(parsed_raw_notes)
    notes, chained_note_uids = _resolve_hold_links(parsed_raw_notes, hold_notes_by_time)
    notes_by_uid = {note.uid for note in notes}
    for note in notes:
        for hold in note.holds:
            if hold.uid is not None and hold.uid not in notes_by_uid:
                raise LoaderError(f"Invalid hold UID link at note uid={note.uid}: target uid={hold.uid}")

    bpms = tuple(
        LinkLikeBpm(
            bpm=_to_float(_require_key(raw_bpm, "Bpm"), field="Bpm"),
            time=_to_float(_require_key(raw_bpm, "Time"), field="Time"),
        )
        for raw_bpm in raw_bpms
    )
    beats = tuple(
        LinkLikeBeat(
            numerator=int(_require_key(raw_beat, "Numerator")),
            denominator=int(_require_key(raw_beat, "Denominator")),
            time=_to_float(_require_key(raw_beat, "Time"), field="Time"),
        )
        for raw_beat in raw_beats
    )

    if not bpms:
        raise LoaderError("Chart has no BPM entries")
    if not beats:
        raise LoaderError("Chart has no beat entries")

    return LinkLikeChart(
        notes=tuple(notes),
        bpms=bpms,
        beats=beats,
        offset=_to_float(raw_offset, field="Offset"),
        root_note_uids=tuple(note.uid for note in notes if note.uid not in chained_note_uids),
    )
