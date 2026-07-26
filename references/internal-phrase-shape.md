# Internal phrase shape

Use this guidance when a prominent melody, chord top line, bass hook, or
counterline sounds evenly filled despite having legal notes and clear phrase
boundaries.

## Diagnose the right layer

Exact quantization and duration variety do not create hierarchy by themselves.
A line can use several note values yet still place one to three similarly
weighted attacks in every small window. The result has rests at the edges but
no internal change of pressure.

Before changing pitches, ask:

- Which event should remain in memory as the phrase's focus?
- Where does the idea begin rather than merely continue?
- Where does information accumulate?
- Where does the line withdraw, sustain, hand off, or redirect?
- Does every stage need the same number of attacks or the same duration?

If those questions have no distinct answers, the failure is phrase design, not
JSON expressivity.

## Plan stages before notes

For an important foreground phrase, divide its time into a small number of
non-overlapping stages. A stage is a change of musical job, not automatically
a grouping boundary. Keep the hypermetric scaffold regular unless a named
extension, compression, elision, pickup, or interruption changes it. Connect adjacent stages by
default; leave a tactus-sized gap only when the preceding gesture is locally
complete and the phrase needs a perceptible breath. Assign each stage one
general job:

A gesture is smaller than a stage: it is one locally complete utterance. One
stage may contain several short gestures, and one gesture may cross a stage
handoff. Use `max_gesture` and the optional polyphonic-attack budget when that
distinction matters. See
[gesture-and-foreground-texture.md](gesture-and-foreground-texture.md).

- `initiate`: expose identity with minimal material;
- `develop`: continue or reinterpret the idea;
- `intensify`: increase pressure through one or more musical dimensions;
- `release`: reduce or redirect pressure toward completion;
- `link`: connect the completed thought to what follows.

These are formal jobs, not fixed positions or genre patterns. Omit roles that
the phrase does not need, and do not reuse one stage layout mechanically.

Declare the plan with `section.phrase_stage(...)`:

```python
section.phrase_stage(
    "stg_open",
    "phr_main",
    beat(0),
    beat(3),
    functions=["foreground"],
    role="initiate",
    min_attacks=3,
    max_attacks=4,
    min_connected_ratio=0.67,
    exit_behavior="continue",
    goal="Expose the hook and carry its momentum into development.",
)
section.phrase_stage(
    "stg_focus",
    "phr_main",
    beat(4),
    beat(5, 2),
    functions=["foreground"],
    role="intensify",
    min_attacks=5,
    max_attacks=7,
    exit_behavior="arrive",
    focus=True,
    focus_cue="salience",
    goal="Make one contour turn the memorable point.",
)
```

`min_attacks` and `max_attacks` are stage-local attack budgets. They do not
generate notes. Choose contrasting budgets when the intended pacing needs
them. Equal budgets and equal spans are valid when function, contour, register,
harmony, texture, or articulation makes the stages distinct.

Use `metric_role="structural"` only for a stage that owns the phrase start or
a declared subphrase boundary. It must enter on a tactus or bar downbeat. Use
`pickup`, `extension`, `elision`, or `free` for an intentional exception; do
not choose `division` merely because the notes were already written there.

`min_connected_ratio` optionally declares how many adjacent event pairs inside
the same selected segment should touch or overlap. Use it when the stage should
sound like one joined gesture. Do not set it on material whose identity depends
on detached attacks or internal rests.

`exit_behavior` makes the handoff testable:

- `continue`: the selected line sustains or reattacks before a tactus-sized
  silence appears;
- `breathe`: the line leaves at least one perceptual beat of silence after a
  locally complete gesture;
- `arrive`: the primary arrival contract governs the exit;
- `free`: no diagnostic claim, useful when another role or an intentionally
  ambiguous grouping controls the handoff.

Do not alternate jobs by inserting one full-beat hole after each stage. A
continuation may change density, contour, harmony, register, or motivic unit
while remaining temporally connected.

At most one stage in a phrase may set `focus=True`. Select the observable cue
that should distinguish it:

- `salience`: a larger accent or `importance` value;
- `density`: more attacks per beat;
- `duration`: a longer structural event.

The focus is not always the loudest or busiest point. Select the cue that the
written phrase actually uses. Harmony, contour, register, orchestration, and
expectation remain listening judgments beyond this small diagnostic contract.

## Write from anchors outward

After the stage plan:

1. Place the focus event and primary arrival.
2. Place the identity-bearing attacks that lead to them.
3. Give each stage a different internal job and, when useful, a different
   density or duration profile.
4. Add passing or neighboring events only when they strengthen that motion.
5. Remove any attack whose deletion preserves identity, direction, focus, and
   completion.

Do not make every note equally accented. Do not interpret an attack budget as a
request to fill every subdivision. A stage may contain a sustained tone,
silence, or a handoff to another role.

## Revise with evidence

Diagnostics report each stage's attacks, density, duration vocabulary,
maximum duration, gesture spans, single-note and polyphonic attack counts,
salience, connected-pair ratio, micro-gap count, median gate ratio, and exit
gap. They warn when:

- the realized attack count misses its declared budget;
- a sounding run exceeds its declared gesture-span maximum;
- the realized dyadic or chordal attacks miss their declared budget;
- the realized internal connection misses its declared minimum;
- a declared continuation is interrupted by a tactus-sized gap;
- a declared breath has no tactus-sized gap;
- the declared focus does not exceed the other stages through its selected
  cue.

These warnings test the authored plan, not universal melodic quality. Listen
for whether the stages produce one coherent trajectory. If a phrase still
sounds flat, change its causal layout before adding ornaments or random timing.

## Research basis and limits

Perceptual evidence supports treating meter, grouping, accent, density, and
tension as interacting but non-identical dimensions. Boltz found that temporal
expectancy depends jointly on periodic accent and the highlighting of melodic
relations and phrase endings. Krumhansl's Mozart study found tension related to
contour, note density, dynamics, harmony, and tonality. Farbood modeled tension
as a temporal combination of multiple parameters. Katz distinguishes the
metrical grid from event hierarchy, while local accent research identifies
contour turns and leaps as possible attention cues.

These findings justify an explicit hierarchy and multidimensional listening
loop; they do not provide a universal melody formula.

Sources:

- Boltz, M. G. (1993). The generation of temporal and melodic expectancies
  during musical listening. *Perception & Psychophysics, 53*(6), 585-600.
  [DOI](https://doi.org/10.3758/BF03211736)
- Krumhansl, C. L. (1996). A perceptual analysis of Mozart's Piano Sonata
  K. 282: Segmentation, tension, and musical ideas. *Music Perception, 13*(3),
  401-432. [DOI](https://doi.org/10.2307/40286177)
- Farbood, M. M. (2012). A parametric, temporal model of musical tension.
  *Music Perception, 29*(4), 387-428.
  [DOI](https://doi.org/10.1525/mp.2012.29.4.387)
- Katz, J. (2022). Metre, grouping, and event hierarchies in music.
  *Language and Linguistics Compass, 16*(1).
  [DOI](https://doi.org/10.1111/lnc3.12472)
- Bisesi, E., Friberg, A., & Parncutt, R. (2019). A computational model of
  immanent accent salience in tonal music. *Frontiers in Psychology, 10*, 317.
  [DOI](https://doi.org/10.3389/fpsyg.2019.00317)
