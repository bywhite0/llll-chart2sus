# llll-chart2sus

Python-first converter scaffold for transforming Link! Like! LoveLive! chart JSON into Project SEKAI community `.sus` charts.

This repository keeps conversion logic in the local project while using reference subprojects only for validation:

- `scores/` (Python `.sus` parser/renderer)
- `pjsekai-scores-rs/` (Rust `.sus` parser/renderer)
- `SekaiMusicChart/` (reference rendering logic)

## Install

```powershell
pwsh ./scripts/bootstrap_toolchain.ps1
```

What this script does:

1. Installs/checks `rustup` stable toolchain.
2. Creates `.venv` with Python 3.10 via `uv`.
3. Installs this project in editable mode with dev dependencies.

## Convert

```powershell
uv run python -m llll_chart2sus convert --input .\LinkLikeToolBox\charts\rhythmgame_chart_103103_01.bytes.json --output .\tmp\103103_01.sus
```

Notes:

- Current scaffold supports basic `Single/Flick/Trace` mapping.
- Hold-chain mapping is intentionally not implemented yet and fails loudly with note `uid/timing`.

## Validate

```powershell
uv run python -m llll_chart2sus validate --sus .\0642_master.sus --svg-out .\tmp\0642_master.svg
```

Validation flow:

1. Python validation through `scores` (`python -m pjsekai.scores`).
2. Rust validation/render through `pjsekai-scores-rs` (`cargo run -- <sus> -o <svg>`).

## Doctor

```powershell
uv run python -m llll_chart2sus doctor
pwsh ./scripts/doctor.ps1
```

