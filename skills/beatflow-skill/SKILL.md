---
name: beatflow-skill
description: Compose, arrange, revise, validate, compare, inspect, and export original multi-track music as Standard MIDI with Codex and BeatFlow's style-neutral Python DSL. Use for translating a musical brief into coordinated instrumental roles, writing complete songs in any genre, diagnosing rhythm or phrasing problems, or working with BeatFlow Composition 1.1 and MIDI files.
license: GPL-3.0-only
---

# BeatFlow

Use Codex for musical decisions. Use the bundled engine for exact timing,
functional pitch realization, voicing, validation, diagnostics, compilation,
MIDI rendering, and inspection.

## Runtime

Refer to this skill directory as `<skill-root>` and run:

```text
python "<skill-root>/scripts/run.py" <command> ...
```

Require Python 3.10 or newer. Write composition scripts and generated
artifacts in the user's workspace, never in `<skill-root>`.

## Workflow

1. Extract duration, form, tempo, meter, tonal language, instrumentation,
   energy path, priorities, and exclusions from the brief. Make reversible
   assumptions for missing details.
2. Classify each instrument as `essential`, `substitutable`, or `optional`.
   Separately classify its prominence as `primary`, `co-primary`, `support`,
   or `background`. Preserve essential instruments and repair their writing,
   balance, or playback program before considering a contract change.
3. Read [composition-guidance.md](references/composition-guidance.md) and
   [composition-format.md](references/composition-format.md). Read
   [phrasing-and-coordination.md](references/phrasing-and-coordination.md)
   for prominent melody, thematic development, complex meter, or timing
   repair. Read [long-form.md](references/long-form.md) for work longer than
   90 seconds. Read [diagnostics.md](references/diagnostics.md) when revising
   or comparing candidates. Load
   [research-foundations.md](references/research-foundations.md) only when
   methodological evidence is useful.
4. Plan before writing events:

   - frame: duration, sections, tempo, meter, tactus, tonic, and mode;
   - phrase: grouping, harmonic rhythm, attention, arrivals, and releases;
   - skeleton: pulse, bass, harmony, role entries, rests, and handoffs;
   - foreground: rhythmic identity, contour, density, texture, and structural
     tones;
   - decoration: fills, secondary attacks, counterlines, and articulation.

5. Render the quantized skeleton before adding foreground. Keep at least one
   stable time reference and make important harmony changes and arrivals
   perceptible. Treat foreground as optional; a bass hook, designed chord top
   line, or rhythmic texture may already lead attention.
6. Author a trusted Python file whose `build()` function returns
   `Composition`. Use `SongBuilder`; let style affect the authored music, not
   the schema or compiler.
7. For a complete song, separate reusable section material from timeline
   occurrences. Use occurrence development and `arrange()` treatments to
   create formal change without copying whole sections.
8. For quality-sensitive melody or thematic work, audition short,
   structurally different candidates before expanding the form. Compare
   rhythm and duration without pitch decoration, preserve an early
   recognizable statement, and select by listening.
9. Render the selected candidate:

```text
python "<skill-root>/scripts/run.py" compose "<output>/<name>.py" "<output>/<name>.mid" --composition-output "<output>/<name>.composition.json" --project-output "<output>/<name>.project.json" --report "<output>/<name>.report.json"
```

10. Treat validation errors as hard failures. Treat diagnostics as evidence
    against the written intent, not as taste scores. Revise the highest causal
    layer responsible, rerender, and listen again.
11. Report the musical design, assumptions, validation result, diagnostic
    findings, MIDI facts, and any decisions that still require listening
    judgment.

## Core constraints

- Keep the default timing exactly quantized. Add onset drift or humanization
  only when the user explicitly requests a timing experiment, and preserve a
  quantized baseline.
- Count the perceptual tactus rather than assuming every quarter note is a
  beat. Use `song.at()`, `song.tactus()`, and `song.bars()` for meter-aware
  plans.
- Use regular whole-bar phrase grouping unless irregularity has a named
  musical function.
- Give important foreground phrases a clear identity, internal contrast, and
  primary arrival. Use `phrase()`, `phrase_stage()`, and `arrival()` when
  their intent needs to be testable.
- Give related roles purposeful dependence without forcing identical attacks.
  Use `interaction()` when independence, interlocking, call-and-response, or
  handoff is central to the brief.
- Use `top_target` when the highest note of a chord voicing carries the line.
  Add a separate lead only when it has a clear complementary role.
- Keep every onset and duration explicit. Never infer note length from the
  next attack.

## Revision

Diagnose in this order:

1. meter and shared clock;
2. role ownership and instrument contracts;
3. phrase grouping, gesture continuity, and arrival;
4. harmonic rhythm, bass support, and voicing;
5. pitch contour and non-chord-tone behavior;
6. articulation, balance, and playback timbre.

Use three simple comparisons before adding rules:

- audition the foreground rhythm on one pitch;
- mute optional or competing layers one at a time;
- compare the earliest complete phrase ending with one later ending.

Repair causal structure rather than isolated notes. Do not use random density,
arbitrary jitter, blanket humanization, or a new genre-specific engine rule as
a shortcut.

## Commands

- `schema`: print the Composition 1.1 JSON Schema
- `validate COMPOSITION`: run hard structural and semantic checks
- `diagnose COMPOSITION`: report advisory musical observations
- `compare COMPOSITION...`: compare candidate fingerprints
- `compile COMPOSITION PROJECT`: compile to internal Project JSON
- `render COMPOSITION MIDI`: validate, diagnose, compile, render, and inspect
- `compose SCRIPT MIDI`: execute trusted `build()` and run the full pipeline
- `inspect MIDI`: report MIDI structure, programs, ranges, and controllers
- `self-check`: run the end-to-end installation smoke test

Use `project-schema`, `project-validate`, and `render-project` only for the
low-level compiled Project boundary.

## Boundaries

- Create original symbolic music. Do not copy a reference melody or imitate a
  living artist.
- Verify licenses before importing analytical corpora or reference files.
- Treat General MIDI playback as a preview; evaluate production timbre in the
  destination instruments or DAW.
- Keep listening as the final musical decision.
