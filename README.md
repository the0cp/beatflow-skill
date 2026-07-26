# BeatFlow Skill

Compose complete, editable multi-track MIDI with Codex.

BeatFlow 2.0 turns Codex into a full-song symbolic music composer and
arranger. Give it a musical brief; Codex writes an original arrangement in a
small Python DSL, while the bundled style-neutral engine validates exact
musical relationships and phrase intent, realizes functional pitches and
chord voicings, and renders deterministic Standard MIDI.

The engine does not call Gemini, the OpenAI API, or another model service. It requires Codex, Python 3.10 or newer, and network access on the first run to install three pinned Python dependencies. It produces symbolic MIDI and structured diagnostics, not finished audio.

## Listen first

These are output snapshots for listening and inspection, not style templates or source material used by the engine.

| Composition | MP3 preview | MIDI | Focus |
| --- | --- | --- | --- |
| Neo Soul | [Listen or download](examples/neo-soul.mp3) | [Download MIDI](examples/neo-soul.mid) | Extended voicings, independent bass, and foreground space |
| Funk | [Listen or download](examples/funk.mp3) | [Download MIDI](examples/funk.mid) | Rhythm-guitar instrument contract and interlocking groove |
| Theme and Variation | [Listen or download](examples/theme-and-variation.mp3) | [Download MIDI](examples/theme-and-variation.mid) | Motivic development across contrasting variations |
| Velvet Crosswalk | [Listen or download](examples/velvet-crosswalk.mp3) | [Download MIDI](examples/velvet-crosswalk.mid) | Quantized pop-jazz pocket, a simple piano hook, and regular 2+2-bar phrasing |

## How it works

```text
musical brief
    -> Codex-authored Python composition plan
    -> timing, meter, harmony, role, and instrument validation
    -> deterministic pitch, voicing, and arrangement compilation
    -> Standard MIDI plus Composition, Project, and diagnostic JSON
```

Codex keeps the open-ended musical decisions. The engine keeps exact relationships reproducible and inspectable without encoding a library of genre templates.

BeatFlow was originally inspired by [TOMI](https://arxiv.org/abs/2506.23094), then evolved through listening tests toward a style-neutral Codex-plus-engine workflow.

## What's new in Composition 1.1

Composition 1.1 is a backward-compatible extension of Composition 1.0. It adds:

- explicit phrase scope, attention, boundary, continuity, tension, and goal
  intent;
- phrase stages with attack, connection, gesture-span, and polyphonic-attack
  budgets;
- one observable phrase focus through salience, density, or duration;
- explicit musical arrivals with closure, hold, harmonic-support, and
  post-arrival contracts;
- regular or intentionally irregular subphrase grouping, plus structural,
  pickup, extension, and elision metric roles;
- meter-aware `song.tactus()` and `song.bars()` authoring helpers;
- metric-entry, tactus-alignment, and displaced-hold diagnostics;
- diagnostics for unplanned hypermetric restarts and repeated one-tactus
  subtraction patterns;
- declared silence and role-interaction contracts for phrasing and
  arrangement checks.

These contracts describe authored intent without adding a genre template.
They let diagnostics distinguish incomplete phrases, overrun endings,
breathless streams, detached foreground clocks, and accidental odd-length
grouping instead of treating every legal note as equally successful.

## Versioning

- BeatFlow product version: `2.0`
- Composition interchange schema: `1.1` by default; `1.0` remains readable
- Compiled Project schema: `1.0`

The diagnostic report is advisory engine output rather than a stable
interchange format, so it does not have a separate public schema version.

## Install

The repository root is the skill directory. The default branch is `master`.

### Install with the skills CLI

If Node.js is available, install BeatFlow globally for Codex with one command:

```bash
npx skills add the0cp/beatflow-skill --global --agent codex --yes
```

### Ask Codex to install it

Node.js is optional. With Codex and Python installed, give Codex this request:

```text
Install the Codex skill from https://github.com/the0cp/beatflow-skill.
Use repository path ".", destination name "beatflow-skill", and ref "master".
```

### Clone it manually

Cloning is the simplest installation method when you want later upgrades with `git pull`.

macOS or Linux:

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$codex_home/skills"
git clone --branch master https://github.com/the0cp/beatflow-skill.git \
  "$codex_home/skills/beatflow-skill"
python3 "$codex_home/skills/beatflow-skill/scripts/run.py" self-check
```

Windows PowerShell:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$skillsDir = Join-Path $codexHome "skills"
$skillPath = Join-Path $skillsDir "beatflow-skill"
New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
git clone --branch master https://github.com/the0cp/beatflow-skill.git $skillPath
python (Join-Path $skillPath "scripts\run.py") self-check
```

The first command that uses `scripts/run.py` creates an isolated runtime under the user cache directory and installs the exact versions in `requirements.txt`. Set `BEATFLOW_CACHE_DIR` to override the cache location.

## Use

Open a working directory and give Codex a brief such as:

```text
Use $beatflow-skill to compose a 2-3 minute neo-soul piece in 4/4 at about
88 BPM. Use Rhodes voicings with a designed top-note line, an independent
electric bass, restrained drums, and deliberate melodic space. Validate the
composition, diagnose structural issues, revise weak sections, and export
MIDI plus Composition and Project JSON.
```

The skill writes every song script and generated artifact in the current workspace, not inside the installed skill.

Developers can run a trusted composition script directly from the repository root:

```bash
python scripts/run.py compose song.py song.mid \
  --composition-output song.composition.json \
  --project-output song.project.json \
  --report song.report.json
```

Inspect or validate artifacts:

```bash
python scripts/run.py --version
python scripts/run.py schema --output composition.schema.json
python scripts/run.py validate song.composition.json
python scripts/run.py diagnose song.composition.json
python scripts/run.py inspect song.mid
python scripts/run.py self-check
```

## Upgrade

For a skills CLI installation:

```bash
npx skills update beatflow-skill --global --yes
```

For a manual Git clone installation:

macOS or Linux:

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
git -C "$codex_home/skills/beatflow-skill" pull --ff-only origin master
python3 "$codex_home/skills/beatflow-skill/scripts/run.py" self-check
```

Windows PowerShell:

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$skillPath = Join-Path $codexHome "skills\beatflow-skill"
git -C $skillPath pull --ff-only origin master
python (Join-Path $skillPath "scripts\run.py") self-check
```

If `requirements.txt` changed, the launcher updates its isolated runtime automatically.

## Develop and test

Create a development environment from the repository root.

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/run.py self-check
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python scripts\run.py self-check
```

The test suite covers models, exact rational timing, meter-aware addressing, validation, diagnostics, deterministic compilation, occurrence arrangements, MIDI rendering, and controller output.

## Composition 1.1

The canonical representation provides:

- exact rational beat positions, including tuplets;
- explicit onset and duration for every event;
- functional or absolute pitch targets;
- optional highest-note targets for designed chord voice leading;
- general musical roles instead of genre-specific parts;
- optional phrase scope, attention, boundary, continuity, and tension intent;
- optional internal phrase stages, attack budgets, and one observable focus
  cue;
- optional regular or irregular subphrase grouping and structural metric
  roles;
- optional gesture-span and polyphonic-attack budgets for foreground texture;
- optional phrase-linked arrival, hold, harmonic-stability, and post-action
  intent;
- optional declared silence windows and role-onset interaction contracts;
- target duration and occurrence-level arrangement changes;
- deterministic compilation and Standard MIDI rendering;
- advisory diagnostics for meter, shared release, bar density, phrasing, role interaction, repetition, attention competition, and structural non-chord tones.

There is no global swing field, groove library, cadence requirement, or genre template. Swing, straight time, rubato, polymeter, and other feels are authored as musical event timing.

Phrase diagnostics are informed by research on perceptual boundaries,
melodic completion, formal function, melodic memory, expectation, tension,
metrical and event hierarchy, and hierarchical musical structure.
See [Research foundations](references/research-foundations.md). The metrics
expose evidence; they do not assign a taste score.

The engine deliberately ships no notation corpus, samples, synthesizer, mix engine, mastering, or frontend. General MIDI playback is a symbolic preview; production timbre depends on the destination instruments, sound library, or DAW.

## Repository layout

- `SKILL.md`: Codex composition and revision workflow
- `agents/openai.yaml`: Codex skill interface metadata
- `scripts/beatflow_core`: models, DSL, compiler, validators, diagnostics, and MIDI renderer
- `scripts/run.py`: dependency-aware cached launcher
- `examples`: four MIDI snapshots with matching MP3 previews
- `references`: format, architecture, and musical decision guidance
- `tests`: unit and end-to-end behavior tests

## License

GPL-3.0-only. See [LICENSE](LICENSE).
