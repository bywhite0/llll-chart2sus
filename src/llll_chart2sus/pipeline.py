"""High-level orchestration for convert/doctor/validate commands."""

from __future__ import annotations

from pathlib import Path

from .linklike_loader import load_linklike_chart
from .mapper import map_to_sus_chart
from .sus_writer import write_sus
from .validators import run_doctor_checks, validate_with_rust, validate_with_scores


def convert_chart_file(input_path: str | Path, output_path: str | Path, strict: bool = False) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chart = load_linklike_chart(input_path)
    sus_chart = map_to_sus_chart(chart, strict=strict)
    sus_text = write_sus(sus_chart)
    output_path.write_text(sus_text, encoding="utf-8", newline="\n")
    return output_path


def run_doctor() -> dict[str, str]:
    return run_doctor_checks()


def validate_sus_file(sus_path: str | Path, svg_out: str | Path) -> tuple[bool, str]:
    sus_path = Path(sus_path).resolve()
    svg_out = Path(svg_out).resolve()
    svg_out.parent.mkdir(parents=True, exist_ok=True)
    scores_svg_out = svg_out.with_name(f"{svg_out.stem}.scores.svg")

    py_res = validate_with_scores(sus_path, scores_svg_out)
    if not py_res.ok:
        details = (
            "Python scores validation failed.\n"
            f"Command: {' '.join(py_res.command)}\n"
            f"stdout:\n{py_res.stdout}\n"
            f"stderr:\n{py_res.stderr}"
        )
        return False, details

    rust_res = validate_with_rust(sus_path, svg_out)
    if not rust_res.ok:
        details = (
            "Rust pjsekai-scores-rs validation failed.\n"
            f"Command: {' '.join(rust_res.command)}\n"
            f"stdout:\n{rust_res.stdout}\n"
            f"stderr:\n{rust_res.stderr}"
        )
        return False, details

    return True, f"Validation succeeded. SVG written to {svg_out}"
