# Composition 1.1 format

Composition 1.1 is the authored interchange format. Optional fields use
backward-compatible defaults when absent. The compiled Project is an internal
rendering model.

## Authoring boundary

Use `beatflow_core.composer.SongBuilder` in a trusted Python `build()` script. The builder returns a strict `Composition`; `compose` saves that object as canonical JSON before compilation.

Core helpers:

- `beat(n, d=1)`: exact quarter-note time;
- `song.tactus(n, d=1)`: duration in the current meter's perceptual beats;
- `song.bars(n, d=1)`: duration in measures of the current meter;
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

Use `section.silence(id, onset, duration, functions=[...])` to declare a section-relative window that selected musical functions must leave empty. Omit `functions` to require literal ensemble silence. This is an intent assertion, not an automatic rest generator: diagnostics report any event that attacks into or sustains through the window.

Use `section.phrase(id, onset, duration, ...)` to declare a perceptual phrase
over all pitched functions or a selected function set. Optional fields express:

- `attention`: the function expected to lead the phrase;
- `boundary_strength`: intended salience from `0.0` to `1.0`;
- `max_continuous`: the longest intended activity span without a
  tactus-sized release;
- `grouping`: `free`, `regular`, or `irregular`;
- `subphrase_bars`: positive whole-bar group lengths; required for regular or
  irregular grouping, with equal values required for regular grouping;
- `tension=(start, peak, end)`: a phrase-level perceptual intention;
- `goal`: the phrase's musical job or destination.

`phrase()` does not generate notes or rests. Diagnostics compare the intent
with temporal gap, final-note lengthening, terminal attack-density change,
and continuity evidence. These are contextual observations, not style rules
or a quality score.

Use `section.phrase_stage(id, phrase_id, onset, duration, ...)` to declare an
internal job inside a phrase. Stages for the same phrase cannot overlap and
must remain inside its span. Optional fields express:

- `functions`: selected roles, inheriting the phrase selection when omitted;
- `role`: `initiate`, `develop`, `intensify`, `release`, or `link`;
- `min_attacks` and `max_attacks`: the intended stage-local attack budget;
- `min_connected_ratio`: optional minimum proportion of adjacent event pairs
  whose first event reaches the next onset inside the same selected segment;
- `max_gesture`: optional maximum duration of one sounding run; a gap of at
  least the meter division separates gestures for this diagnostic;
- `min_polyphonic_attacks` and `max_polyphonic_attacks`: optional budget for
  dyadic or chordal events in the selected foreground;
- `metric_role`: `free`, `structural`, `pickup`, `extension`, or `elision`;
  a structural stage must enter on a tactus or bar downbeat and, for a grouped
  phrase, at its start or a declared subphrase boundary;
- `entry_anchor`: `free`, `division`, `tactus`, or `bar_downbeat`; non-free
  values declare the required metric position of the first realized attack;
- `min_tactus_attack_ratio`: optional minimum share of unique stage attacks
  that articulate the perceptual beat;
- `max_off_tactus_bridge_ratio`: optional maximum share of off-tactus events
  that sustain across the following tactus;
- `exit_behavior`: `free`, `continue`, `breathe`, or `arrive`; `free` makes no
  claim, `continue` expects less than a tactus of silence at the exit,
  `breathe` expects at least one tactus, and `arrive` delegates completion to
  the phrase's arrival plan;
- `focus`: whether this is the phrase's only declared focus stage;
- `focus_cue`: required for a focus stage and set to `salience`, `density`,
  or `duration`;
- `goal`: the stage's musical job.

`phrase_stage()` does not generate or redistribute events. Diagnostics compare
the phrase grouping, tactus activity, attack, gesture-span, and
polyphonic-attack budgets, metric role and entry, tactus alignment, displaced
holds, internal connected-pair ratio, exit gap, and selected focus cue with
realized events. These fields are authored expectations, not style defaults.
See [phrasing-and-coordination.md](phrasing-and-coordination.md) for metric
entry, gesture connection, density, foreground texture, and continuation.

Use `section.arrival(id, phrase_id, onset, ...)` to declare one primary point
of completion inside a phrase. Optional fields express:

- `functions`: the roles responsible for the arrival; omitted values inherit
  the phrase's selected functions;
- `closure`: `open`, `partial`, `closed`, or `elided`;
- `strength`: intended salience from `0.0` to `1.0`;
- `min_hold`: minimum duration for one structural arrival event;
- `harmonic_stability`: `free`, `supported`, or `resolved`;
- `post_action`: `stop`, `echo`, `link`, or `afterglow`;
- `max_post_attacks`: the permitted selected-role attacks after the arrival
  and before the phrase boundary; `stop` requires zero;
- `goal`: the arrival's musical job.

Each phrase may have at most one primary arrival. `arrival()` does not
generate or alter events. Diagnostics distinguish a missing or unarticulated
arrival, a short hold, surplus post-arrival attacks, and observable harmonic
support. See
[phrasing-and-coordination.md](phrasing-and-coordination.md).

## Events

`note(onset, duration, target, ...)` creates a pitched event with articulation, accent, contour, register hint, importance, function text, and optional motif label.

`chord(onset, duration, ...)` requests a voicing with a note count, optional root omission, optional range, articulation, and accent. Set `top_target` to a functional or absolute pitch target when the highest voice must trace a designed line; it may introduce a tension not already named by the chord symbol. A functional target chooses a smooth in-range octave; an absolute target fixes the exact MIDI pitch.

`drum(onset, duration, lane_or_pitch, ...)` creates a General MIDI percussion event. Named lanes are convenience aliases only; they contain no patterns.

Every duration is literal. The compiler never derives a gate from the next onset.

## Interactions

`interaction()` declares an expected range for the proportion of source-function onsets shared with a target function inside one section. It is an intent assertion and diagnostic aid, not a style rule.

Declare an interaction whenever the brief explicitly depends on independence, call-and-response, interlocking, or handoff. Choose its range from the intended relationship; the schema does not prescribe a genre-specific value.

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
