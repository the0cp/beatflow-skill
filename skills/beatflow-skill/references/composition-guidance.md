# Composition guidance

Use this guide for the decisions that remain musical rather than mechanical.
BeatFlow supplies an authoring language and verification pipeline; it does not
choose a style.

## Plan causality

Write one short intent paragraph before events. Name:

- the role that makes time legible;
- the role that leads attention;
- the source of motion;
- the main contrast;
- the important arrival;
- the intended energy path.

Independence is not randomness. Parts may use different attack sets while
sharing meter, harmonic time, and structural arrivals.

## Protect the instrument contract

Classify instrumentation before writing:

- `essential`: explicitly requested or identity-bearing;
- `substitutable`: preserve the function, but allow another instrument;
- `optional`: decoration, alternate color, or developmental material.

Classify prominence separately as `primary`, `co-primary`, `support`, or
`background`. Essential does not imply loud or dense.

When a part fails, distinguish weak function, weak writing, weak balance, and
weak playback timbre. Mute it for diagnosis, but do not remove an essential
role merely because its preview sound is poor. First revise rhythm, register,
voicing, density, velocity, volume, handoff, or MIDI program.

## Compose by layers

1. Fix duration, form, tempo, meter, key, and harmonic route.
2. Mark phrase spans, grouping, attention, and arrival points.
3. Write pulse, bass, harmony, role entries, and releases.
4. Render the skeleton and confirm one recoverable clock.
5. Add foreground rhythm before foreground pitch.
6. Add passing detail, fills, counterlines, and articulation last.

Every decoration should strengthen identity, direction, tension, release, or
role interaction. If removing an attack changes none of those, remove it.

## Write relationships

Use explicit intent when the relationship matters:

- `phrase()` for scope, grouping, attention, tension, and continuity;
- `phrase_stage()` for internal jobs, density, connection, metric role, and
  foreground texture;
- `arrival()` for the primary completion point and permitted aftermath;
- `silence()` for a required empty window;
- `interaction()` for onset overlap between roles;
- `top_target` for a designed chord upper line.

Do not declare every available field. Add a contract only when violating it
would change the intended music.

## Build distinct candidates

Change a causal layer rather than a cosmetic parameter:

- phrase rhythm or rest placement;
- role relationship;
- harmonic path or harmonic rhythm;
- formal route;
- register, density, or texture trajectory.

Do not treat transposition, a different seed, or minor velocity edits as a new
candidate. For identity-bearing material, audition short candidates before
developing a complete form.

## Diagnose the responsible layer

| Symptom | Revise first |
| --- | --- |
| Timing feels arbitrary | Meter, tactus, and role anchor map |
| Melody implies another tempo | Foreground attack-and-duration skeleton |
| Chords float between beats | Harmonic change and performed re-attack placement |
| Melody hesitates | Gesture connection and boundary placement |
| Phrase feels unfinished | Arrival articulation, hold, and harmonic support |
| Phrase overruns | Post-arrival function and earliest complete stopping point |
| Melody is flat | Stage jobs, density, contour, register, and focus |
| Parts move as one block | Role ownership, handoff, and interaction intent |
| Sections sound alike | Form, active layers, density, and harmonic rhythm |
| Harmony feels arbitrary | Structural chord tones and audible resolutions |
| Support masks the anchor | Register, note count, velocity, and volume |
| Sound is harsh or weak | MIDI program or destination instrument |

Repair the highest row of causality that explains the failure. Do not start
with individual pitch substitutions when the rhythm, role, or phrase plan is
wrong.

## Listen in layers

Compare:

1. pulse, bass, and harmony;
2. foreground rhythm on one pitch;
3. foreground alone;
4. full arrangement;
5. full arrangement with each optional layer muted.

Diagnostics expose measurable conflicts and degeneration signals. They do not
decide taste. Preserve unusual meter, continuous motor rhythm, dense
counterpoint, sparse melody, or syncopation when the brief and listening result
support them.

For detailed phrase, timing, melody, and arrival work, read
[phrasing-and-coordination.md](phrasing-and-coordination.md). For the
underlying evidence and its limits, read
[research-foundations.md](research-foundations.md).
