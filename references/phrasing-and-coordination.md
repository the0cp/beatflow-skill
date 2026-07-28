# Phrasing and coordination

Use this guide when a line is quantized but detached, evenly filled, hesitant,
breathless, incomplete, or longer than its musical function.

## Contents

- [Establish the frame](#establish-the-frame)
- [Share one clock](#share-one-clock)
- [Separate phrase levels](#separate-phrase-levels)
- [Write memorable continuation](#write-memorable-continuation)
- [Plan foreground texture](#plan-foreground-texture)
- [Design the arrival](#design-the-arrival)
- [Use BeatFlow contracts selectively](#use-beatflow-contracts-selectively)
- [Run the listening pass](#run-the-listening-pass)

## Establish the frame

Choose tempo, time signature, tonic, mode, harmonic rhythm, and phrase grouping
before notes.

- In simple meter, organize around beats that divide in two.
- In compound meter, organize around dotted beats that divide in three.
- In irregular meter, state the intended grouping explicitly.
- Unless irregularity is requested, begin with regular whole-bar subphrases.

Use `song.at()` for meter-aware positions and `song.tactus()` or `song.bars()`
for perceptual durations. A `6/8` bar normally has two dotted-quarter tactus
beats; integer quarter-note offsets are not interchangeable with those beats.

## Share one clock

Exact quantization does not guarantee coordination. Before pitch, mark:

- bar downbeats and phrase entries;
- tactus anchors;
- harmony changes and bass arrivals;
- structural foreground attacks;
- planned pickups, suspensions, and their returns;
- shared releases and handoffs.

A foreground need not attack every anchor. It may sustain, rest, or syncopate,
but its entries, long notes, peaks, and resolutions must leave the same metric
frame recoverable. Syncopation should depart from an audible reference and
return to it; it should not become an unexplained permanent phase.

Render pulse, bass, and harmony first. Then audition the foreground rhythm on
one pitch. Fix a clock conflict before evaluating pitch.

## Separate phrase levels

Treat four levels independently:

- **phrase**: a span with a destination and completion;
- **stage**: a change of formal job or pressure;
- **gesture**: one locally complete utterance;
- **attack**: one event inside a gesture.

A stage is not automatically a boundary, and one stage may contain several
gestures. Change function through density, contour, register, harmony,
texture, or articulation without inserting a rest every time.

Use a tactus-sized gap only for an audible breath after a locally complete
gesture. Inside a connected gesture, let most note durations reach the next
onset. Avoid the same small gate gap after every attack; it makes a phrase
sound word-by-word even when the onset pattern is correct.

Vary short and long gestures. Avoid a long sparse middle that is neither
singable nor intense:

- make sparse writing carry sustained structural tones, contour, repetition,
  space, and destination;
- make intense writing concentrate subdivision, sequence, registral pressure,
  and decisive release locally.

## Write memorable continuation

Before expanding a theme:

1. establish a short rhythmic and contour identity;
2. confirm it with an exact or near-exact early return;
3. transform one structural relationship;
4. make the consequence audible through arrival, handoff, displacement,
   fragmentation, compression, expansion, or changed function.

Do not transform several dimensions before the source idea is recognizable.
An omitted expected attack must act as syncopation, fragmentation, breath,
handoff, or arrival; otherwise it sounds forgotten.

Write important pitches from anchors outward:

1. place the focus and arrival;
2. place identity-bearing attacks;
3. connect or separate gestures deliberately;
4. add passing and neighboring tones;
5. remove surplus attacks.

Pitch-class correctness alone does not make a line convincing. Prefer stable
tones at structural beats, and give strong non-chord tones audible preparation
or resolution.

## Plan foreground texture

Choose one attention owner per section. A bass hook, chord top line, rhythmic
figure, or texture can lead without a separate melody.

When `top_target` already creates a designed upper line, add another
foreground only for a clear answer, interruption, counterline, or handoff.
Inspect actual onset overlap before blaming an instrument.

A polyphony-capable foreground need not remain monophonic. Use selected dyads,
chordal stops, or a voiced arrival as punctuation. Do not harmonize every
attack or turn the line into continuous block chords.

## Design the arrival

A boundary marks where a span ends. An arrival marks where its musical work
becomes complete. A held tone, silence, echo, link, or afterglow may separate
the two.

Plan one primary arrival for each important phrase:

1. name the phrase's job;
2. choose the arrival onset;
3. choose open, partial, closed, or elided closure;
4. name the roles that articulate it;
5. decide whether harmony should be supported or resolved;
6. reserve its hold and permitted aftermath;
7. write the approach last.

Use a stop test when the ending feels short or excessive. Compare the earliest
plausible completion, the next plausible completion, and at most one named
echo or link. Keep the shortest version that completes the intended function
without sounding amputated.

## Use BeatFlow contracts selectively

Use `section.phrase(...)` to declare important phrase scope, grouping,
attention, maximum continuous activity, tension, and goal.

Use `section.phrase_stage(...)` when an internal job must be testable:

- `role`: initiate, develop, intensify, release, or link;
- attack budget;
- `min_connected_ratio` for joined gestures;
- `max_gesture` for sounding-run length;
- polyphonic-attack budget;
- metric role and entry anchor;
- tactus alignment and displaced-hold limits;
- continuation, breath, or arrival at the exit;
- at most one observable focus cue.

Use `section.arrival(...)` for articulation, closure, hold, harmonic support,
and post-arrival attack budget.

These fields describe authored intent. Leave them unset when the music does
not need the corresponding claim. Free rhythm, rubato, cadenzas, drones,
elision, and deliberate ambiguity remain valid.

## Run the listening pass

1. Listen to the rhythmic skeleton on one pitch.
2. Listen to the foreground alone.
3. Listen with only foreground and the time/harmony anchors.
4. Mark each gap as articulation, breath, handoff, arrival, or syncopation.
5. Check whether stage changes alter function without unnecessary stops.
6. Check whether the primary arrival is articulated, held, and allowed to
   stand.
7. Restore pitch and orchestration without changing an accepted rhythm.
8. Compare the full arrangement with optional foreground layers muted.

Do not repair phrase problems with random timing, blanket humanization, fixed
note-count formulas, or a genre rhythm template. See
[research-foundations.md](research-foundations.md) for the evidence behind
meter, grouping, continuation, accent, expectation, tension, and completion.
