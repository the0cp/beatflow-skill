# BeatFlow Skill

BeatFlow 2.0 is a self-contained Codex music-composition skill. Codex writes an original arrangement through a small Python DSL; the bundled, style-neutral engine validates exact musical relationships, realizes functional pitches and chord voicings, and renders deterministic Standard MIDI.

The engine does not call Gemini, the OpenAI API, or another model service. It requires Codex, Python 3.10 or newer, and network access on the first run to install three pinned Python dependencies.

## Install

The repository root is the skill directory. The default branch is `master`.

### Ask Codex to install it

Give Codex this request:

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

After installation, ask Codex to use `$beatflow-skill` with a musical brief. The skill writes every song script and generated artifact in the current workspace, not inside the installed skill.

Run a trusted composition script directly:

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

These commands apply to a manual Git clone installation.

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

## Composition 1.0

The canonical representation provides:

- exact rational beat positions, including tuplets;
- explicit onset and duration for every event;
- functional or absolute pitch targets;
- optional highest-note targets for designed chord voice leading;
- general musical roles instead of genre-specific parts;
- target duration and occurrence-level arrangement changes;
- deterministic compilation and Standard MIDI rendering;
- advisory diagnostics for meter, phrasing, role interaction, repetition, attention competition, and structural non-chord tones.

There is no global swing field, groove library, cadence requirement, or genre template. Swing, straight time, rubato, polymeter, and other feels are authored as musical event timing.

The engine deliberately ships no notation corpus, samples, synthesizer, mix engine, mastering, or frontend. General MIDI playback is a symbolic preview; production timbre depends on the destination instruments, sound library, or DAW.

## Repository layout

- `SKILL.md`: Codex composition and revision workflow
- `agents/openai.yaml`: Codex skill interface metadata
- `scripts/beatflow_core`: models, DSL, compiler, validators, diagnostics, and MIDI renderer
- `scripts/run.py`: dependency-aware cached launcher
- `references`: format, architecture, and musical decision guidance
- `tests`: unit and end-to-end behavior tests

## License

GPL-3.0-only. See [LICENSE](LICENSE).
