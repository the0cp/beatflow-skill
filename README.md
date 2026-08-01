# BeatFlow Skill

Compose complete, editable multi-track MIDI with Codex.

BeatFlow turns a musical brief into an explicit Python composition plan,
validates its timing and musical relationships, realizes functional pitches
and chord voicings, and exports deterministic Standard MIDI. The result stays
inspectable and editable: every onset, duration, role, phrase, and arrangement
decision is represented as data rather than hidden inside an audio model.

BeatFlow 2.0 requires Codex and Python 3.10 or newer. It produces symbolic
MIDI, Composition JSON, Project JSON, and diagnostic reports; the included MP3
files are listening previews.

## Listen

The examples are output snapshots, not templates or source material used by
the engine.

| Composition | MP3 | MIDI | Focus |
| --- | --- | --- | --- |
| Neo Soul | [Listen](examples/neo-soul.mp3) | [Download](examples/neo-soul.mid) | Extended voicings, independent bass, and foreground space |
| Funk | [Listen](examples/funk.mp3) | [Download](examples/funk.mid) | Rhythm-guitar instrument contract and interlocking groove |
| Theme and Variation | [Listen](examples/theme-and-variation.mp3) | [Download](examples/theme-and-variation.mid) | Motivic development across contrasting variations |
| Pop-Jazz | [Listen](examples/pop-jazz.mp3) | [Download](examples/pop-jazz.mid) | Quantized pocket, a simple piano hook, and regular 2+2-bar phrasing |

## Why BeatFlow

- **Codex composes; code keeps relationships exact.** Codex makes the open
  musical decisions while the engine handles rational timing, pitch
  realization, voicing, validation, and MIDI serialization.
- **The representation is editable.** A small Python DSL compiles to strict
  Composition 1.1 JSON and an internal Project before MIDI rendering.
- **Diagnostics test intent, not genre conformity.** Phrase, arrival, meter,
  role, silence, repetition, and arrangement checks compare the written plan
  with the realized events.
- **The engine stays style-neutral.** Genre affects the authored harmony,
  rhythm, form, instrumentation, and phrasing rather than selecting an engine
  template.

## Pipeline

```text
musical brief
    -> Codex-authored Python composition plan
    -> strict Composition 1.1
    -> validation and advisory diagnostics
    -> deterministic pitch, voicing, and arrangement compilation
    -> Standard MIDI + Composition, Project, and report JSON
```

Composition 1.1 supports:

- exact rational positions and literal durations, including tuplets;
- meter-aware bar and tactus addressing;
- functional, relative, or absolute pitch targets;
- designed chord top lines and deterministic voice leading;
- reusable sections with occurrence-level arrangement changes;
- instrument contracts and general musical roles;
- phrase grouping, stages, focus, arrivals, silence, and role interactions;
- diagnostics for timing, continuity, completion, density, repetition,
  masking, and structural non-chord tones.

## Install

### Skills CLI

With Node.js available:

```bash
npx skills add the0cp/beatflow-skill --skill beatflow-skill --global --agent codex --yes
```

Run the installation smoke test from the installed skill directory:

```bash
python scripts/run.py self-check
```

### GitHub CLI

With GitHub CLI 2.90 or newer:

```bash
gh skill install the0cp/beatflow-skill beatflow-skill --agent codex --scope user
```

### Codex skill installer

From a Codex conversation:

```text
$skill-installer install https://github.com/the0cp/beatflow-skill/tree/master/skills/beatflow-skill
```

The launcher creates an isolated cached runtime and installs the pinned
packages in `requirements.txt`. Set `BEATFLOW_CACHE_DIR` to choose another
cache location.

## Use

Open a workspace and give Codex a concrete brief:

```text
Use $beatflow-skill to compose a 2-3 minute neo-soul piece in 4/4 at about
88 BPM. Use Rhodes voicings with a designed top-note line, an independent
electric bass, restrained drums, and deliberate melodic space. Validate the
composition, revise structural problems, and export MIDI plus Composition,
Project, and diagnostic JSON.
```

BeatFlow writes the composition script and generated files in the workspace,
not in the installed skill directory.

To run a trusted composition script directly from the repository checkout:

```bash
python skills/beatflow-skill/scripts/run.py compose song.py song.mid \
  --composition-output song.composition.json \
  --project-output song.project.json \
  --report song.report.json
```

Useful commands:

```bash
python skills/beatflow-skill/scripts/run.py --version
python skills/beatflow-skill/scripts/run.py schema --output composition.schema.json
python skills/beatflow-skill/scripts/run.py validate song.composition.json
python skills/beatflow-skill/scripts/run.py diagnose song.composition.json
python skills/beatflow-skill/scripts/run.py inspect song.mid
python skills/beatflow-skill/scripts/run.py self-check
```

## Upgrade

Skills CLI installation:

```bash
npx skills update beatflow-skill --global --yes
```

GitHub CLI installation:

```bash
gh skill update beatflow-skill
```

For a Codex skill-installer installation, run the installation prompt again.

## Develop and test

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
python3 skills/beatflow-skill/scripts/run.py self-check
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
python skills\beatflow-skill\scripts\run.py self-check
```

The tests cover exact timing, models, validation, diagnostics, compilation,
arrangement occurrences, MIDI rendering, inspection, and controller output.

## Repository layout

- `skills/beatflow-skill/SKILL.md`: composition and revision workflow for Codex
- `skills/beatflow-skill/agents/openai.yaml`: skill interface metadata
- `skills/beatflow-skill/scripts/beatflow_core`: DSL, models, compiler,
  validators, diagnostics, and MIDI renderer
- `skills/beatflow-skill/scripts/run.py`: dependency-aware launcher
- `skills/beatflow-skill/references`: format, architecture, musical guidance,
  and research
- `examples`: listening snapshots used to evaluate the generated arrangements
- `tests`: unit and end-to-end tests

## License

GPL-3.0-only. See [LICENSE](LICENSE).
