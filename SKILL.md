---
name: beatflow-skill
description: Compose, arrange, revise, validate, compare, and export original multi-track music as Standard MIDI with Codex and BeatFlow's bundled style-neutral Python DSL. Use for creating music in any genre, translating a musical brief into interacting instrumental roles, diagnosing weak rhythm or phrasing, or inspecting BeatFlow Composition 1.1 and MIDI files. Produces symbolic MIDI, not synthesized audio.
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

   Separately classify each active part's intended prominence as `primary`,
   `co-primary`, `support`, or `background`. Essential does not mean loud or
   dense. Treat genre conventions as evidence for these classifications, not
   as fixed engine templates. Do not change an established contract without
   explaining the tradeoff and obtaining user approval.
2. Read [composition-guidance.md](references/composition-guidance.md), [meter-and-phrase.md](references/meter-and-phrase.md), and [composition-format.md](references/composition-format.md). Read [foreground-and-pulse.md](references/foreground-and-pulse.md), [temporal-coordination.md](references/temporal-coordination.md), [gesture-and-foreground-texture.md](references/gesture-and-foreground-texture.md), [internal-phrase-shape.md](references/internal-phrase-shape.md), [melodic-continuation.md](references/melodic-continuation.md), [arrival-and-closure.md](references/arrival-and-closure.md), and [research-foundations.md](references/research-foundations.md) when writing a prominent melody, thematic variation, or phrase/tension experiment. For a complete song or a target longer than 90 seconds, also read [long-form.md](references/long-form.md). Read [diagnostics.md](references/diagnostics.md) when comparing or repairing candidates.
3. Design in this order:

   - frame: duration, form, tempo, meter, tactus, tonic, and mode;
   - phrase: regular or explicitly irregular grouping, subphrase boundaries, perceptual focus, primary arrival points, closure strength, harmonic rhythm, and shared-release map;
   - skeleton: stable time reference, bass and harmony arrivals, arrival holds, post-arrival actions, role rests, and shared releases;
   - foreground: contrasting short and long gesture spans, local density path, single-note and polyphonic texture map, rhythmic idea, structural tones, non-chord-tone preparation and resolution;
   - decoration: secondary attacks, fills, counterlines, articulation, and optional timing experiments.

   Treat `foreground` as optional. When the highest note of a voicing carries the line, declare it with `top_target` and do not add a separate lead without a clear handoff.

   Default every event to the written grid. Do not add humanizing onset drift, random jitter, or unrelated phase offsets unless the user explicitly requests a timing experiment. Even then, render and preserve a fully quantized baseline first.

   In simple meter, organize rhythm around beats that divide in two. In compound meter, organize it around dotted beats that divide in three. Establish important harmonic changes on a perceptible beat; use off-beat chord re-attacks as a deliberate relationship, not the default.

   Unless the brief requests irregularity, declare `grouping="regular"` and
   `subphrase_bars` on important phrases. Build from whole-bar subphrases and
   place structural restarts on their boundaries. Count the meter's tactus,
   not raw quarter-note units; use `song.at()`, `song.tactus()`, and
   `song.bars()` in compound meter. Vary content inside a regular scaffold
   before changing its length.

   Before pitch generation, write a shared-clock map of bar downbeats, tactus
   anchors, harmony changes, bass arrivals, phrase entries, and intended
   displacements. A legal subdivision is not enough: foreground entries,
   longer notes, peaks, and resolutions must preserve the accent hierarchy
   established by the other roles. A pickup or suspension must have an
   audible return; do not begin every group on the same displaced phase.

   For quality-sensitive work, declare phrase scope, attention, boundary
   strength, maximum continuous activity, tension intention, and musical goal
   with `section.phrase(...)`. When an important line carries attention,
   declare a small number of non-overlapping internal jobs with
   `section.phrase_stage(...)`; contrast function, attack budget, contour,
   register, harmony, or texture and use at most one explicit focus cue
   instead of filling every bar evenly. Keep stage spans metrically regular
   unless an extension, compression, elision, pickup, or interruption has a
   named function. When
   notes should form one audible gesture, declare a minimum connected-pair
   ratio and join most internal note-offs to the following onset. Declare
   whether each stage exit should `continue`, `breathe`, or `arrive`; do not
   turn every change of function into a tactus-sized rest. For stages whose
   shared clock is quality-critical, declare `metric_role` and `entry_anchor`,
   `min_tactus_attack_ratio`, and `max_off_tactus_bridge_ratio`; derive the
   values from the phrase plan before writing notes, never from realized
   event positions or a genre preset. A `structural` stage must enter on a
   tactus or bar downbeat and at a declared subphrase boundary; use `pickup`,
   `extension`, `elision`, or `free` only when that displacement is intended.
   Give stages a
   `max_gesture` when one audible utterance must not run through the whole
   window. For a polyphony-capable foreground, declare a small
   `min_polyphonic_attacks` / `max_polyphonic_attacks` budget and use selected
   dyads or chordal punctuation; do not make a piano melody permanently
   monophonic or convert every attack into a block chord. Give each important phrase one primary
   completion point with `section.arrival(...)`; declare the responsible
   roles, closure kind, minimum hold, harmonic-stability expectation, and
   post-arrival attack budget. Use `section.silence(...)` only for
   structurally required empty windows. Render or inspect the skeleton before
   adding foreground. Record pitched attacks per bar, phrase boundary and
   arrival evidence, longest continuous phrase spans, the longest shared
   pitched silence, and role-onset overlap; repair accidental block joins,
   missed arrivals, and surplus post-arrival motion at this stage.

4. Author a trusted Python file with a `build()` function returning `Composition`. Use `SongBuilder` as the writing surface. Let genre affect Codex's musical choices—not the schema or compiler.
5. For long form, separate reusable section material from each timeline occurrence. Declare `statement`, `repeat`, `develop`, `contrast`, `climax`, or `release`; use `arrange()` to change active segments, register, velocity, or gate. Store alternative and decorative layers as `default_enabled=False` and enable only the intended occurrence. A single-note ornament track must earn its place in a comparison against the same arrangement with that track muted. Use mute-and-compare as a diagnostic for essential parts, not as authorization to remove them.
6. Give related parts purposeful dependence without forcing identical attacks. Use `interaction()` whenever the brief explicitly requires independence, call-and-response, interlocking, or handoff, and whenever another overlap range is central to the design. Choose the range from the written intent, not a genre preset.
7. For quality-sensitive work, write at least two structurally different candidates. When a theme or melody carries the work, first render at least three short subjects or 8-16 bar sketches with different rhythmic identities, contours, interruptions, or phrase layouts. Write and audition the attack-and-duration skeleton before pitch decoration. Require an exact or near-exact early restatement before heavy transformation. An omitted expected attack must function as an audible syncopation, fragmentation, handoff, arrival, or breath; otherwise connect the cell before adding more pitch detail. Select the subject by listening before expanding beyond 90 seconds. Include a lead-free or stable-anchor baseline when foreground or microtiming may be unnecessary. Vary phrase rhythm, role interaction, harmonic route, register, or form—not seeds or cosmetic velocity.
8. Render a candidate:

```text
python "<skill-root>/scripts/run.py" compose "<output>/<name>.py" "<output>/<name>.mid" --composition-output "<output>/<name>.composition.json" --project-output "<output>/<name>.project.json" --report "<output>/<name>.report.json"
```

9. Treat validation errors as hard failures. Treat diagnostics as observations, not taste scores or automatic rejection. For complete songs, repair target-duration conflicts, flat energy curves, unchanged developmental returns, static repeated arrangements, grouped-phrase duration mismatches, structural stages outside declared subphrase boundaries, unplanned hypermetric restarts, repeated one-tactus subtraction patterns, missed phrase-stage attack, gesture-span, or polyphonic-attack budgets, uniformly long phrase gestures, weak metric entry or tactus alignment, excessive displaced holds, weak internal connection, interrupted declared continuation, missing declared breaths, unrealized phrase focus, weak declared phrase boundaries, excessive continuous phrase spans, occupied declared silences, accidental density cliffs, and unplanned continuous pitched texture. Inspect rendered per-track note counts and average velocities, then audition primary/support pairs so a dense essential support part does not mask the intended anchor.
10. Report the musical design, material assumptions, diagnostic findings, MIDI facts, and symbolic-playback limitations. Ask for listening feedback when further artistic revision is useful.

## Repair

Diagnose before editing:

- arbitrary timing: return every part to the written grid, then rewrite the phrase rhythm against meter and other roles; inspect exact onsets and intentional rests;
- melody and accompaniment disagree: redesign their call, answer, support, or contrast before changing individual pitches;
- melody and accompaniment imply different tempos: audition the melody rhythm
  on one pitch, map its entries, long notes, peaks, and resolutions against
  bar downbeats, tactus, harmony changes, and bass arrivals, then preserve
  only displacements with an audible return; use phrase-stage metric
  contracts instead of forcing every note onto a beat;
- floating chords: restore the governing harmonic change on a primary beat, then keep only off-beat re-attacks that prepare, suspend, or answer it;
- rhythm is identical across sections: change density, rests, harmonic rhythm, or role; rotating the same bar-pattern set is not development;
- melody sounds harmonically arbitrary: place chord tones at phrase anchors and make structural non-chord tones prepare or resolve audibly;
- intrusive lead or ornament: identify its instrument contract first; rewrite an essential part's rhythm, register, voicing, or handoff, and remove the track only when it is optional;
- no direction: establish a phrase goal, motif identity, contour, tension point, and release;
- mechanical motif variation: rewrite a multi-bar subject with two cells, then transform their relationship instead of rotating or transposing one bar;
- unclear meter: restore one stable pulse anchor and keep the foreground quantized; reintroduce displacement only when the user explicitly asks for it and the baseline remains available;
- mechanical duration: use explicit short, connected, accented, and sustained values with intent;
- flat or evenly filled melody: stop editing isolated pitches; keep a metrically grounded phrase scaffold, give `phrase_stage()` jobs different functions or attack budgets, choose one observable focus cue, and write from that focus and the arrival outward; vary density, contour, register, harmony, or texture before changing stage length;
- unexpected odd-length phrasing: count the perceptual tactus, declare regular subphrase bars, and move structural entries and restarts to their boundaries; do not create variety by repeatedly subtracting one tactus from an otherwise regular phrase, and do not mark an accidental off-tactus start as `division` after writing it;
- long and sparse foreground: decide whether the passage should be singable or intense; shorten it into complete gestures or sustain vocal structural tones for the first case, and concentrate subdivision, contour change, registral pressure, and a decisive release into one local burst for the second; do not distribute medium-spaced attacks across the whole phrase;
- permanently monophonic piano or ensemble foreground: use selected dyads, chordal stops, or a designed top voice as punctuation under a declared polyphonic-attack budget; do not harmonize every melody note;
- hesitant or forgotten-sounding motif: inspect the attack-and-duration skeleton without pitch; if a stage is meant to continue, sustain or begin the next cell before a tactus-sized gap, and reserve a true breath for a locally complete gesture; do not repair an unexplained hole by appending an unrelated note;
- squeezed or word-by-word melody: inspect duration divided by the next inter-onset interval; join notes inside each gesture, reserve separation for group boundaries, and declare `min_connected_ratio` on stages whose cohesion matters; do not distribute the same micro-gap after nearly every attack;
- breathless texture: declare each important span with `section.phrase(...)`, set a realistic maximum continuous gesture, and shape the ending before the stream becomes exhausting; combine space or handoff with lengthening, thinning, contour closure, harmonic arrival, register, or dynamics, and use `section.silence(...)` only for required empty windows; do not scatter arbitrary micro-rests or repeat one gap formula at fixed bar intervals;
- unfinished phrase: declare its expected completion with `section.arrival(...)`, then rewrite the terminal gesture so at least one selected role articulates and holds that point; do not count unused beats after an early cutoff as successful closure;
- overrun phrase: compare the earliest plausible stopping points, keep the shortest one that completes the intended function, and budget every later attack as `echo`, `link`, or `afterglow`; do not let a flourish continue merely because the scale remains legal;
- independent parts move as one block: declare their expected overlap with `interaction()`, preserve coordinated structural arrivals, and rewrite the intervening attack sets as genuine handoff or counterpoint;
- abrupt density: inspect pitched attacks per bar and reshape the transition across neighboring bars unless the jump marks a planned formal event;
- static harmony texture: vary placement, density, register, and silence while preserving harmonic function;
- accompaniment masks the harmonic anchor: preserve both instrument contracts, then compare rendered note count, average velocity, volume, register, and attack density; reduce or redistribute the support part before weakening the intended primary harmony;
- copied candidates: change a structural dimension and run `compare`;
- poor General MIDI timbre: preserve essential instrumentation, prefer a clearer preview program or import the MIDI into a better sound library; do not confuse timbre with composition or use timbre as a reason to delete a required role.

Never repair weak music by adding genre-specific engine rules, random density, arbitrary note jitter, or blanket humanization.

## Commands

- `schema`: print Composition 1.1 JSON Schema
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
- Keep Composition 1.1 as the stable boundary for future frontends, importers, alternate realizers, or an MCP wrapper. Accept legacy Composition 1.0 artifacts.
