from __future__ import annotations

import json

from llll_chart2sus.linklike_loader import load_linklike_chart


def _encode_flags(note_type: int, r1: int, r2: int, l1: int, l2: int) -> int:
    return note_type | (r1 << 4) | (r2 << 10) | (l1 << 16) | (l2 << 22)


def test_load_linklike_chart_parses_minimal_file(tmp_path):
    payload = {
        "Notes": [{"just": "1.5", "holds": [], "Uid": 7, "Flags": 464}],
        "Bpms": [{"Bpm": 120, "Time": 0.0}],
        "Offset": 0.0,
        "Beats": [{"Numerator": 4, "Denominator": 4, "Time": 0.0}],
    }
    src = tmp_path / "chart.json"
    src.write_text(json.dumps(payload), encoding="utf-8")

    chart = load_linklike_chart(src)

    assert chart.offset == 0.0
    assert len(chart.notes) == 1
    assert chart.notes[0].uid == 7
    assert chart.notes[0].flags.note_type == 0
    assert chart.notes[0].holds == ()
    assert chart.root_note_uids == (7,)


def test_load_linklike_chart_resolves_hold_uid_links_and_roots(tmp_path):
    hold_a_uid = 1
    hold_b_uid = 2
    hold_c_uid = 3
    payload = {
        "Notes": [
            {
                "just": "1.0",
                "holds": ["1.995"],
                "Uid": hold_a_uid,
                "Flags": _encode_flags(note_type=1, r1=12, r2=24, l1=8, l2=20),
            },
            {
                "just": "1.2",
                "holds": ["1.995"],
                "Uid": hold_c_uid,
                "Flags": _encode_flags(note_type=1, r1=10, r2=24, l1=6, l2=20),
            },
            {
                "just": "2.0",
                "holds": ["2.4"],
                "Uid": hold_b_uid,
                "Flags": _encode_flags(note_type=1, r1=24, r2=32, l1=20, l2=28),
            },
        ],
        "Bpms": [{"Bpm": 120, "Time": 0.0}],
        "Offset": 0.0,
        "Beats": [{"Numerator": 4, "Denominator": 4, "Time": 0.0}],
    }
    src = tmp_path / "chart_hold_chain.json"
    src.write_text(json.dumps(payload), encoding="utf-8")

    chart = load_linklike_chart(src)
    note_by_uid = {note.uid: note for note in chart.notes}

    assert note_by_uid[hold_a_uid].holds[-1].uid == hold_b_uid
    assert note_by_uid[hold_c_uid].holds[-1].uid is None
    assert chart.root_note_uids == (hold_a_uid, hold_c_uid)
