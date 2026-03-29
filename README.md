# llll-chart2sus

`llll-chart2sus` is a Python-first converter for transforming Link! Like! LoveLive! chart JSON into Project SEKAI community `.sus` charts.

The repository focuses on conversion logic, command-line usage, and reproducible local validation for `.sus` output.

## Key Goals

- Deterministic, reproducible conversion output
- Inspectable mapping from source JSON to `.sus` events
- Validation through both Python and Rust parser stacks

## Repository Layout

- `src/llll_chart2sus/`: conversion pipeline and CLI
- `tests/`: converter tests
- `scripts/`: bootstrap and doctor scripts
- `examples/`: sample source JSON and generated `.sus/.svg`

## Quick Start

### 1. Bootstrap toolchain

```powershell
pwsh ./scripts/bootstrap_toolchain.ps1
```

The bootstrap script:

1. Installs/checks the `rustup` stable toolchain.
2. Creates `.venv` with Python 3.10 via `uv`.
3. Installs this project in editable mode with dev dependencies.

### 2. Convert chart JSON to `.sus`

```powershell
uv run python -m llll_chart2sus convert --input .\examples\rhythmgame_chart_203115_04.bytes.json --output .\tmp\203115_04.sus
```

Current implementation status:

- Basic `Single/Flick/Trace` mapping is supported.
- Hold-chain mapping is intentionally not implemented yet.
- Unsupported hold-chain data fails loudly with note `uid/timing`.

### 3. Validate generated `.sus`

```powershell
uv run python -m llll_chart2sus validate --sus .\tmp\103103_01.sus --svg-out .\tmp\103103_01.svg
```

Validation path:

1. Parse and sanity-check generated `.sus`.
2. Render to SVG for visual inspection.

Optional cross-check with reference validators:

`scores` (Python parser):

Repository: [pjsekai/scores](https://gitlab.com/pjsekai/scores)

```powershell
cd .\scores
python -m pjsekai.scores ..\tmp\203115_04.sus
```

`pjsekai-scores-rs` (Rust parser/renderer):

Repository: [Team-Haruki/pjsekai-scores-rs](https://github.com/Team-Haruki/pjsekai-scores-rs)

```powershell
cd .\pjsekai-scores-rs
cargo run -- ..\tmp\203115_04.sus -o ..\tmp\203115_04.rust.svg
```

### 4. Run environment checks

```powershell
uv run python -m llll_chart2sus doctor
pwsh ./scripts/doctor.ps1
```

## Development Notes

- Keep conversion behavior explicit and traceable.
- Prefer adding focused tests for each mapping behavior change.

## Disclaimer

- This project is a fan-made reverse-engineering/conversion tool for research and interoperability purposes.
- This repository is not affiliated with, endorsed by, or sponsored by the rights holders of Link! Like! LoveLive! or Project SEKAI.
- Game assets, charts, names, and related intellectual property belong to their respective owners.
- Users are responsible for complying with local laws, platform terms, and copyright/licensing requirements.
- Do not use this project for unauthorized commercial distribution of copyrighted content.

## License

This project is licensed under the MIT License. See [LICENSE](./LICENSE).
