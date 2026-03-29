"""External validation helpers for scores and pjsekai-scores-rs."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import ToolchainError, ValidationError


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_command(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> CommandResult:
    try:
        process = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolchainError(f"Command not found: {command[0]}") from exc

    return CommandResult(
        command=tuple(command),
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )


def _require_tool(tool: str) -> str:
    path = shutil.which(tool)
    if path:
        return path

    home = Path.home()
    candidates = [
        home / ".cargo" / "bin" / f"{tool}.exe",
        home / ".cargo" / "bin" / tool,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise ToolchainError(f"Required tool not found: {tool}")


def python_scores_check() -> CommandResult:
    repo_root = _repo_root()
    scores_src = repo_root / "scores" / "src"
    if not scores_src.exists():
        raise ValidationError(f"Missing scores source directory: {scores_src}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(scores_src) + os.pathsep + env.get("PYTHONPATH", "")
    return _run_command([sys.executable, "-m", "pjsekai.scores", "--help"], cwd=repo_root, env=env)


def rust_scores_check() -> CommandResult:
    repo_root = _repo_root()
    rust_project = repo_root / "pjsekai-scores-rs"
    if not rust_project.exists():
        raise ValidationError(f"Missing Rust validator project: {rust_project}")
    cargo = _require_tool("cargo")
    return _run_command([cargo, "run", "--", "--help"], cwd=rust_project)


def validate_with_scores(sus_path: Path, output_svg: Path | None = None) -> CommandResult:
    repo_root = _repo_root()
    scores_src = repo_root / "scores" / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(scores_src) + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "pjsekai.scores", str(sus_path)]
    if output_svg is not None:
        command.extend(["-o", str(output_svg)])
    return _run_command(command, cwd=repo_root, env=env)


def validate_with_rust(sus_path: Path, svg_out: Path) -> CommandResult:
    repo_root = _repo_root()
    rust_project = repo_root / "pjsekai-scores-rs"
    cargo = _require_tool("cargo")
    return _run_command([cargo, "run", "--", str(sus_path), "-o", str(svg_out)], cwd=rust_project)


def run_doctor_checks() -> dict[str, str]:
    summary: dict[str, str] = {}

    _require_tool("python")
    pip_exe = _require_tool("pip")
    _require_tool("uv")
    cargo_exe = _require_tool("cargo")
    rustc_exe = _require_tool("rustc")

    py = _run_command([sys.executable, "--version"])
    pip = _run_command([pip_exe, "--version"])
    uv = _run_command(["uv", "--version"])
    cargo = _run_command([cargo_exe, "--version"])
    rustc = _run_command([rustc_exe, "--version"])

    summary["python"] = (py.stdout or py.stderr).strip()
    summary["pip"] = (pip.stdout or pip.stderr).strip()
    summary["uv"] = (uv.stdout or uv.stderr).strip()
    summary["cargo"] = (cargo.stdout or cargo.stderr).strip()
    summary["rustc"] = (rustc.stdout or rustc.stderr).strip()

    scores_result = python_scores_check()
    rust_result = rust_scores_check()
    if not scores_result.ok:
        raise ValidationError(
            "scores Python validator is not callable.\n"
            f"stdout:\n{scores_result.stdout}\n"
            f"stderr:\n{scores_result.stderr}"
        )
    if not rust_result.ok:
        raise ValidationError(
            "pjsekai-scores-rs validator is not callable.\n"
            f"stdout:\n{rust_result.stdout}\n"
            f"stderr:\n{rust_result.stderr}"
        )

    summary["scores"] = "ok"
    summary["pjsekai-scores-rs"] = "ok"
    return summary
