---
name: beatflow-skill
description: Compose, arrange, revise, validate, compare, and export original multi-track music as Standard MIDI with Codex and BeatFlow's bundled style-neutral Python DSL. Use for creating music in any genre, translating a musical brief into interacting instrumental roles, diagnosing weak rhythm or phrasing, or inspecting BeatFlow Composition 1.0 and MIDI files. Produces symbolic MIDI, not synthesized audio.
---

# BeatFlow

Use Codex as the composer. Use the bundled engine for exact timing, functional pitch realization, validation, diagnostics, deterministic MIDI rendering, and inspection. Do not call another LLM API and do not choose a style from engine templates.

## Runtime

Refer to this skill directory as `<skill-root>`. Run:

```text
python "<skill-root>/scripts/run.py" <command> ...
```

Python 3.10+ is required. The first run creates a cached virtual environment and installs pinned dependencies. Write every song script, JSON artifact, report, and MIDI file in the user's workspace, never in `<skill-root>`.

## Compose

1. Extract the brief's tempo range, meter, tonal language, instrumentation, form, energy path, priorities, and exclusions. Make reversible assumptions for missing details. Classify the instrument contract and record it in the script's intent, priorities, or exclusions:

   - `essential`: explicitly requested or identity-bearing; preserve the instrument and repair its writing or destination sound instead of deleting it;
   - `substitutable`: preserve the musical function, but allow another instrument to assume it when the brief permits;
   - `optional`: decoration, alternate color, or a developmental layer that may be muted after comparison.

   Treat genre conventions as evidence for this classification, not as fixed engine templates. Do not change an established contract without explaining the tradeoff and obtaining user approval.
2. Read [composition-guidance.md](references/composition-guidance.md), [meter-and-phrase.md](references/meter-and-phrase.md), and [composition-format.md](references/composition-format.md). Read [foreground-and-pulse.md](references/foreground-and-pulse.md) when writing a prominent melody, thematic variation, moving chord top voice, or timing experiment. For a complete song or a target longer than 90 seconds, also read [long-form.md](references/long-form.md). Read [diagnostics.md](references/diagnostics.md) when comparing or repairing candidates.
3. Design in this order:

   - frame: duration, form, tempo, meter, tactus, tonic, and mode;
   - phrase: phrase spans, endings, harmonic rhythm, and cadence or other goal;
   - skeleton: stable time reference, bass arrivals, harmony attacks, and intended rests;
   - foreground: rhythmic idea, structural tones, non-chord-tone preparation and resolution;
   - decoration: secondary attacks, fills, counterlines, articulation, and optional timing experiments.

   Treat `foreground` as optional. When the highest note of a voicing carries the line, declare it with `top_target` and do not add a separate lead without a clear handoff.

   Default every event to the written grid. Do not add humanizing onset drift, random jitter, or unrelated phase offsets unless the user explicitly requests a timing experiment. Even then, render and preserve a fully quantized baseline first.

   In simple meter, organize rhythm around beats that divide in two. In compound meter, organize it around dotted beats that divide in three. Establish important harmonic changes on a perceptible beat; use off-beat chord re-attacks as a deliberate relationship, not the default.

4. Author a trusted Python file with a `build()` function returning `Composition`. Use `SongBuilder` as the writing surface. Let genre affect Codex's musical choices—not the schema or compiler.
5. For long form, separate reusable section material from each timeline occurrence. Declare `statement`, `repeat`, `develop`, `contrast`, `climax`, or `release`; use `arrange()` to change active segments, register, velocity, or gate. Store alternative and decorative layers as `default_enabled=False` and enable only the intended occurrence. A single-note ornament track must earn its place in a comparison against the same arrangement with that track muted. Use mute-and-compare as a diagnostic for essential parts, not as authorization to remove them.
6. Give related parts purposeful dependence without forcing identical attacks. Use `interaction()` only when the brief implies an overlap range worth checking.
7. For quality-sensitive work, write at least two structurally different candidates. Include a lead-free or stable-anchor baseline when foreground or microtiming may be unnecessary. Vary phrase rhythm, role interaction, harmonic route, register, or form—not seeds or cosmetic velocity.
8. Render a candidate:

```text
python "<skill-root>/scripts/run.py" compose "<output>/<name>.py" "<output>/<name>.mid" --composition-output "<output>/<name>.composition.json" --project-output "<output>/<name>.project.json" --report "<output>/<name>.report.json"
```

9. Treat validation errors as hard failures. Treat diagnostics as observations, not taste scores or automatic rejection. For complete songs, repair target-duration conflicts, flat energy curves, unchanged developmental returns, and static repeated arrangements.
10. Report the musical design, material assumptions, diagnostic findings, MIDI facts, and symbolic-playback limitations. Ask for listening feedback when further artistic revision is useful.

## Repair

Diagnose before editing:

- arbitrary timing: return every part to the written grid, then rewrite the phrase rhythm against meter and other roles; inspect exact onsets and intentional rests;
- melody and accompaniment disagree: redesign their call, answer, support, or contrast before changing individual pitches;
- floating chords: restore the governing harmonic change on a primary beat, then keep only off-beat re-attacks that prepare, suspend, or answer it;
- rhythm is identical across sections: change density, rests, harmonic rhythm, or role; rotating the same bar-pattern set is not development;
- melody sounds harmonically arbitrary: place chord tones at phrase anchors and make structural non-chord tones prepare or resolve audibly;
- intrusive lead or ornament: identify its instrument contract first; rewrite an essential part's rhythm, register, voicing, or handoff, and remove the track only when it is optional;
- no direction: establish a phrase goal, motif identity, contour, tension point, and release;
- mechanical motif variation: rewrite a multi-bar subject with two cells, then transform their relationship instead of rotating or transposing one bar;
- unclear meter: restore one stable pulse anchor and keep the foreground quantized; reintroduce displacement only when the user explicitly asks for it and the baseline remains available;
- mechanical duration: use explicit short, connected, accented, and sustained values with intent;
- static harmony texture: vary placement, density, register, and silence while preserving harmonic function;
- copied candidates: change a structural dimension and run `compare`;
- poor General MIDI timbre: preserve essential instrumentation, prefer a clearer preview program or import the MIDI into a better sound library; do not confuse timbre with composition or use timbre as a reason to delete a required role.

Never repair weak music by adding genre-specific engine rules, random density, arbitrary note jitter, or blanket humanization.

## Commands

- `schema`: print Composition 1.0 JSON Schema
- `validate COMPOSITION`: hard structural and semantic checks
- `diagnose COMPOSITION`: non-gating musical observations
- `compare COMPOSITION...`: rhythmic and duration fingerprint comparison
- `compile COMPOSITION PROJECT`: create internal Project JSON
- `render COMPOSITION MIDI`: validate, diagnose, compile, render, inspect
- `compose SCRIPT MIDI`: execute trusted `build()` and run the full pipeline
- `project-schema`, `project-validate`, `render-project`: low-level engine boundary
- `inspect MIDI`: report MIDI structure, programs, ranges, and controllers
- `self-check`: end-to-end installation smoke test

## Boundaries

- Create original symbolic music; do not copy a reference melody or imitate a living artist.
- A notation corpus is optional analysis material, not a hidden dependency or template source. Verify licenses before importing any corpus.
- BeatFlow has no samples, synthesizer, mix engine, mastering, frontend, or audio renderer.
- Exact representation and valid relationships do not prove musical quality. Listening remains decisive.
- Keep Composition 1.0 as the stable boundary for future frontends, importers, alternate realizers, or an MCP wrapper.
