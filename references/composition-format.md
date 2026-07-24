# Composition 1.0 format

## Authoring boundary

Use `beatflow_core.composer.SongBuilder` in a trusted Python `build()` script. The builder returns a strict `Composition`; `compose` saves that object as canonical JSON before compilation.

Core helpers:

- `beat(n, d=1)`: exact quarter-note time;
- `chord(degree, alter=0)`: ordered chord function;
- `chord_index(index, alter=0)`: literal indexed chord pitch;
- `scale(degree, alter=0)`: key-scale degree;
- `next_chord(degree, alter=0)`: target from the following harmony span;
- `midi(pitch)`: absolute MIDI pitch;
- `relative(semitones)`: interval from the previous realized pitch.

## Structure

`SongBuilder` declares metadata, target duration, meter, key, PPQ, tracks, sections, timeline occurrences, and optional interactions.

`SongBuilder.at(bar, beat_number, offset=0)` addresses the meter's perceptual beat: quarter notes in `4/4`, dotted quarters in `6/8`, and so on. `beat()` remains an exact quarter-note unit for low-level event timing.

Tracks declare MIDI program/channel, register, monophonic behavior, volume, and one generic performance kind:

- `neutral`
- `percussive`
- `plucked`
- `sustained`

Sections contain contiguous harmony spans when functional targets or chord events need harmony. Segments place one track in one or more general functions:

- `pulse`
- `low`
- `harmony`
- `foreground`
- `counterline`
- `texture`
- `support`

Segment `start` and `duration` define its boundary. Event onsets are absolute within the section, not relative to the segment start.

Set `default_enabled=False` on an alternative or climax-only segment. Such material remains part of the reusable section but is silent until an occurrence enables it.

## Events

`note(onset, duration, target, ...)` creates a pitched event with articulation, accent, contour, register hint, importance, function text, and optional motif label.

`chord(onset, duration, ...)` requests a voicing with a note count, optional root omission, optional range, articulation, and accent. Set `top_target` to a functional or absolute pitch target when the highest voice must trace a designed line; it may introduce a tension not already named by the chord symbol. A functional target chooses a smooth in-range octave; an absolute target fixes the exact MIDI pitch.

`drum(onset, duration, lane_or_pitch, ...)` creates a General MIDI percussion event. Named lanes are convenience aliases only; they contain no patterns.

Every duration is literal. The compiler never derives a gate from the next onset.

## Interactions

`interaction()` declares an expected range for the proportion of source-function onsets shared with a target function inside one section. It is an intent assertion and diagnostic aid, not a style rule.

## Timeline arrangement

`play()` declares an occurrence with optional `development`, `energy`, and intent text. The development values are `statement`, `repeat`, `develop`, `contrast`, `climax`, and `release`.

After `play()`, call `arrange(occurrence, segment, ...)` to:

- enable or disable a segment;
- transpose pitched material;
- shift pitched material by octaves;
- scale velocity;
- scale note gates.

Treatments are occurrence-local. They do not modify the reusable section or another return. Alternative monophonic segments may overlap in source time when no occurrence enables them together.

## Compiler behavior

The compiler:

- realizes connected pitches within track register and contour constraints;
- resolves functional targets against the active harmony;
- chooses deterministic chord voicings with small voice-leading motion;
- preserves explicit event timing;
- maps sections to reusable internal Project clips;
- realizes each occurrence's layer state and treatment;
- adds generic CC11/CC1 shaping for `sustained` tracks;
- renders type-1 MIDI.

Hard validation checks references, bounds, exact PPQ representation, track/event compatibility, harmony availability, and monophonic overlap. It does not require drums, cadences, swing, a chord vocabulary, or any genre.
