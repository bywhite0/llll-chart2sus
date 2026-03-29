# AGENTS.md — llll-chart2sus

Guidance for AI coding agents working in this repository.

## What this repository is

This is a Python-first repository focused on converting Link! Like! LoveLive! private chart data into Project SEKAI community `.sus` charts.

Treat `.sus` output correctness as the primary product goal. Keep conversion behavior deterministic, inspectable, and reproducible.

## Repository map and responsibilities

- `LinkLikeToolBox/`: Data acquisition and decryption toolkit for Link! Like! LoveLive! game assets, including chart JSON generation.
- `LinkLikeToolBox/charts/`: Source chart storage location (binary chart files and their decrypted JSON files).
- `LinkLikeToolBox/ChartFile.md`: Chart format and parsing reference document.
- `LinkLikeToolBox/chart_analyzer.py`: JSON chart analyzer that exports CSV and statistics for verification.
- `LinkLikeToolBox/example/`: Example chart files for local experimentation and regression checks.
- `llll-chart/`: Frontend-based Link! Like! LoveLive! chart preview site artifacts (compiled static pages, scripts, and assets).
- `pjsekai-scores-rs/`: Rust `.sus` parser and SVG renderer, rewritten based on `scores` and `SekaiMusicChart`.
- `scores/`: Upstream/reference Python `.sus` parser and renderer.
- `SekaiMusicChart/`: Upstream/reference chart rendering and related logic.

Default editing target for conversion work is Python conversion logic in this repository's conversion pipeline. Use reference projects for validation and behavior comparison.

## Data sources and file locations

- LinkLike chart source of truth:
  - Decrypted JSON charts from `LinkLikeToolBox/charts/`
  - Binary and decoded format details in `LinkLikeToolBox/ChartFile.md`
- Analysis and inspection:
  - `LinkLikeToolBox/chart_analyzer.py`
  - `LinkLikeToolBox/example/`
- Preview artifacts:
  - `llll-chart/index.html` (entry page)
  - `llll-chart/<music_id>/index.html` and `index.pageContext.json` (per-chart pages)
  - `llll-chart/assets/` (compiled JS/CSS chunks and static assets)
- Parser/renderer validation targets:
  - Python parser: `scores/src/pjsekai/scores/`
  - Rust parser/renderer: `pjsekai-scores-rs/src/`

When mapping fields (timing, lane, width, hold chains, slide transitions), record assumptions directly in code comments or commit notes so the mapping can be audited later.

## Standard conversion workflow

1. Acquire and decrypt source charts with `LinkLikeToolBox`.
   - Example:
     - `cd LinkLikeToolBox`
     - Build or run toolbox commands according to its README.
2. Inspect source chart JSON and flags/timing semantics before changing conversion logic.
   - Example:
     - `cd LinkLikeToolBox`
     - `python chart_analyzer.py`
3. Implement or adjust Python conversion logic to produce `.sus`.
   - Keep lane mapping, timing conversion, and hold/slide linking explicit.
4. Generate `.sus` output from the conversion pipeline.
5. Validate `.sus` with both parser stacks:
   - Python flow:
     - `cd scores`
     - `python -m pjsekai.scores <file.sus>`
   - Rust flow:
     - `cd pjsekai-scores-rs`
     - `cargo run -- <file.sus> -o <file.svg>`
6. Compare against source JSON:
   - note counts
   - major timing anchors (start/end/tempo sections)
   - hold and slide continuity
7. If preview pages must be refreshed, regenerate frontend artifacts from the corresponding frontend source project, then sync output into `llll-chart/` as an artifact update.

## Hard boundaries (must follow)

- Do not modify `scores/`, `SekaiMusicChart/`, or `pjsekai-scores-rs/` unless the task scope explicitly requires it.
- Do not refactor imported/reference projects for convenience.
- Treat `llll-chart/` as compiled output by default: do not hand-edit minified bundles, sourcemaps, or hashed asset filenames unless explicitly required for an emergency fix.
- When `llll-chart/` needs updates, prefer full or coherent artifact regeneration and replacement to avoid broken hash references.
- Keep conversion logic and mapping decisions explicit and traceable.
- Do not hide behavior changes in broad cleanup commits; isolate conversion logic changes.
- If protected subprojects must be touched, state why and keep the edit surface minimal.

## Validation checklist

- `.sus` is consumable by the Python `scores` flow:
  - `python -m pjsekai.scores <file.sus>` in `scores/`.
- `.sus` is parsable/renderable by the Rust tool:
  - `cargo run -- <file.sus> -o <file.svg>` in `pjsekai-scores-rs/`.
- Note counts are checked against the source JSON chart.
- Major timings (including BPM section alignment) are checked against source JSON.
- Hold/slide continuity is checked for broken links, missing tails, and invalid transitions.
- Any accepted mismatch is documented with rationale.
- If `llll-chart/` is updated, verify at least:
  - `llll-chart/index.html` loads
  - one representative `llll-chart/<music_id>/index.html` page loads
  - no missing asset 404s from `llll-chart/assets/`

## Working rules for agents

- Prefer minimal, targeted changes over broad rewrites.
- Preserve existing repository conventions unless task scope says otherwise.
- Document assumptions when source format interpretation is uncertain.
- Include reproducible verification commands in task summaries.
- Fail loudly on ambiguous data conversions; do not silently guess.
- Keep commits and patches focused on one behavioral goal at a time.
- Communicate with users in Chinese for status updates, explanations, and final responses.
- Follow Conventional Commits for Git history (for example: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`).
- Write Git commit messages in English.
- Split commits by logical change points; avoid bundling unrelated changes into a single commit.

## Subproject AGENTS precedence

This root `AGENTS.md` defines global policy for the repository.

If a deeper directory includes its own `AGENTS.md`, that deeper file takes precedence for files in its subtree.

Example: work under `pjsekai-scores-rs/` must follow `pjsekai-scores-rs/AGENTS.md` first, while still respecting root-level intent unless explicitly overridden there.
