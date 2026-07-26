# Gesture length and foreground texture

Use this guidance when a melody is metrically correct but every thought has
the same length, the line remains monophonic for too long, or note density
sits between a singable melody and an intense instrumental passage.

## Separate four levels

- A **phrase** has a destination and completion.
- A **stage** changes formal job or pressure.
- A **gesture** is one locally complete audible utterance.
- An **attack** is one event inside that gesture.

A stage is not automatically one gesture. One long stage may contain two
short calls, while two stages may join into one long sentence. Plan gesture
boundaries explicitly instead of deriving them from bar lines.

## Avoid the long-sparse middle

Sparse and dense writing are both valid:

- a sparse, singable line earns space through sustained structural tones,
  contour, repetition, breath, and a clear destination;
- an intense instrumental line earns length through local subdivision,
  changing contour, sequence, registral pressure, and decisive release.

The weak middle is a long continuous span with too few events to create
instrumental momentum and too little space or sustain to sound vocal. Do not
repair it by sprinkling evenly spaced notes across the whole span.

Make a gesture map before pitch:

```text
short statement -> short answer -> breath
long connected ascent -> brief chordal punctuation
dense burst -> sustained arrival
```

Vary both gesture duration and attack density. Keep a long sentence when it
has a clear job, but contrast it with at least one shorter complete thought.
Do this inside the declared hypermetric scaffold first. Do not manufacture
contrast by repeatedly subtracting one tactus from an otherwise regular
phrase.

## Declare gesture and texture budgets

For a quality-sensitive `phrase_stage()`, optionally declare:

- `max_gesture`: the maximum intended sounding run inside the stage; a gap of
  at least the meter division separates gestures for this diagnostic;
- `min_polyphonic_attacks` and `max_polyphonic_attacks`: the intended count of
  dyadic or chordal foreground events.

```python
section.phrase_stage(
    "stg_reply",
    "phr_main",
    beat(3),
    beat(9, 2),
    functions=["foreground"],
    role="develop",
    min_attacks=8,
    max_attacks=11,
    max_gesture=beat(5, 2),
    min_polyphonic_attacks=1,
    max_polyphonic_attacks=2,
    exit_behavior="breathe",
    goal="Give two compact single-note replies and end with one dyadic stop.",
)
```

These are authored expectations, not style defaults. Leave the polyphonic
budget at zero for an intentionally monophonic voice, counterpoint line, or
solo wind instrument.

## Use polyphony as foreground punctuation

A piano, guitar, mallet instrument, or ensemble foreground can alternate:

- a single-note contour;
- a dyad that reinforces a structural interval;
- a short chordal answer;
- a designed chord top voice;
- a registral spread at the focus or arrival.

Do not turn every melody attack into a block chord. Polyphonic attacks should
change weight, color, or formal function. If the foreground track uses chord
events, declare it as non-monophonic. Use `segment.chord(..., notes=2,
top_target=...)` for a harmony-derived dyad with an explicit highest note.

## Create local intensity

Attack count matters together with duration. For an intense stage:

1. choose one short window for the fastest governing subdivision;
2. establish its entry and exit on audible metric or harmonic anchors;
3. make the contour or interval pattern change direction or register;
4. use a dyad or held tone to end the burst;
5. reduce density afterward.

A phrase should not remain at maximum density from beginning to end.
Likewise, one isolated sixteenth note does not create intensity.

## Revision test

1. Listen to foreground rhythm on one pitch.
2. Mark the start and end of every perceived gesture.
3. Compare their durations and attack counts.
4. Listen to the foreground alone and confirm that dyads sound like
   punctuation rather than accidental accompaniment.
5. Listen with pulse, bass, and harmony; confirm that short gestures still
   share the ensemble clock.
6. Remove one attack from each dense burst. Restore it only when direction,
   identity, or intensity becomes weaker.

Diagnostics expose continuous-span lengths, stage gesture spans, single-note
and polyphonic attack counts, and the declared budgets. They do not decide
whether the music should be vocal, virtuosic, homophonic, or contrapuntal.
