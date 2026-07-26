# Meter, harmony, and phrase workflow

Use this workflow as a reliable default, not as a universal aesthetic law. Establish conventional hearing before introducing ambiguity.

## 1. Fix the frame

Choose target duration, section order, tempo, time signature, tonic, and mode before writing events.

Interpret the time signature:

- simple meter: each beat divides into two;
- compound meter: each beat divides into three;
- `6/8` normally has two dotted-quarter beats, not six equal tactus beats;
- irregular meter needs an explicit grouping stated in the intent.

Choose the tactus a listener should tap and the smallest governing division. Use tuplets or finer subdivisions only when their relation to the tactus is audible.

## 2. Design phrase and harmonic rhythm

Mark phrase spans, weak and strong endings, the harmonic goal, and the amount of release before voicing chords. Distinguish a rest in one role from a shared release in the pitched texture. A conventional eight-bar starting point may be a period (antecedent with weaker closure, consequent with stronger closure) or a sentence (presentation followed by continuation), but do not force an archetype when the brief needs another form.

Declare each important span with `section.phrase(...)`. State its attention
owner, boundary strength, maximum continuous activity, tension path, and
goal. A phrase boundary is graded and multi-cue: combine temporal space or
handoff with one or more of note lengthening, thinning, contour closure,
harmonic arrival, register change, or dynamics. Do not schedule the same
one-beat gap every four bars and call it phrasing.

Unless irregularity is requested, declare `grouping="regular"` with equal
whole-bar `subphrase_bars`, such as `[2, 2]`. This is an authored hypermetric
plan, not a genre template. Use `grouping="irregular"` only for a deliberate
extension, compression, elision, or asymmetric design. A rest belongs inside
the counted phrase; do not repeatedly obtain variety by removing one tactus
from an otherwise regular frame.

When a prominent line must change pressure inside the phrase, declare
non-overlapping `section.phrase_stage(...)` spans before filling notes. Give
each stage a formal job, an attack budget, and at most one phrase-wide focus
cue. Mark its exit as continuation, breath, or arrival. Stage lengths and
budgets should express this phrase's trajectory without requiring unequal
metrical spans. Mark stages that own subphrase boundaries as
`metric_role="structural"`; place them on a tactus or bar downbeat. See
[internal-phrase-shape.md](internal-phrase-shape.md) and
[melodic-continuation.md](melodic-continuation.md).

For each important phrase, declare one primary completion point with
`section.arrival(...)` before filling its terminal gesture. A phrase may end
after that point because a tone rings, the ensemble breathes, or a short
echo or link follows. Keep these stages separate: a clean boundary cannot
repair an arrival that happened too early, never became audible, or was
followed by purposeless extra notes.

Write the harmonic spans and their rate of change. Distinguish:

- harmonic change: when the governing chord changes;
- performed harmony attack: when an instrument voices or re-attacks it.

Establish important harmonic changes on a perceptible beat before adding syncopated re-attacks. An off-beat chord attack is meaningful when it prepares, delays, suspends, or answers an established metric event.

## 3. Write the rhythmic skeleton

Create a small beat map for every section:

- bar and phrase downbeats;
- primary and secondary beats;
- stable time-reference role;
- bass arrival points;
- harmony attacks and sustained spans;
- intended role rests;
- intended shared releases.

Use `song.at()` for meter-aware positions and `song.tactus()` or `song.bars()`
for durations. In `6/8`, do not treat integer quarter-note offsets as if they
were dotted-quarter beats.

Declare required empty windows with `section.silence(...)`. Render this skeleton before adding foreground. The listener should be able to count the meter from at least one stable role, and the planned releases must remain audible before decoration begins. Silence is one boundary cue, not the entire phrase model.

Inspect the skeleton bar by bar. Record pitched attacks per bar, the longest shared pitched silence, and onset overlap between roles. A density jump should mark a planned formal event, not an accidental join between generated blocks.

Do not reuse one multiset of bar rhythms in every section and call rotations development. Preserve an identifying rhythm when useful, but alter density, rests, harmonic rhythm, or role between statement, departure, climax, and release.

## 4. Add bass and voice leading

Write bass against harmonic spans and phrase direction. Let it support important arrivals, approach selected changes, and move independently between them. Voice harmony for smoothness, register, and top-line purpose after its rhythm is settled.

## 5. Add foreground

Write a rhythmic idea before its pitch sequence. Audition its attacks and
durations on one neutral pitch: the grouping and forward motion should already
make sense. Place the internal focus, phrase anchors, and cadential tones
first; prefer chord tones at structural beats. Satisfy the planned stage
contrast without filling every available subdivision or inserting a rest at
every stage change. Add passing tones, neighbors, suspensions, anticipations,
and appoggiaturas only with an audible preparation or resolution.

Check melody against the complete accompaniment, not against chord symbols alone. Leave rests and handoffs. When the brief requires independent roles, declare their expected onset overlap with `interaction()` and revise before adding ornament if the result falls outside the range.

## 6. Decorate last

Only after the quantized skeleton works:

- add secondary attacks, fills, pickup notes, counterlines, and articulations;
- compare each optional single-note track against a muted version;
- keep onset humanization disabled unless the user explicitly requests a separate timing experiment.

## Sources

This workflow adapts general principles from the Open Music Theory undergraduate text: [simple meter](https://viva.pressbooks.pub/openmusictheory/chapter/simple-meter-and-time-signatures/), [compound meter](https://viva.pressbooks.pub/openmusictheory/chapter/compound-meters-and-time-signatures/), [phrase hierarchy](https://viva.pressbooks.pub/openmusictheory/chapter/foundational-concepts/), [phrase archetypes](https://viva.pressbooks.pub/openmusictheorycopy/chapter/phrase-archetypes-unique-forms/), and [harmonic phrase function](https://viva.pressbooks.pub/openmusictheory/chapter/intro-to-harmony/).

See [research-foundations.md](research-foundations.md) for the perceptual
boundary, melodic-memory, expectation, tension, and hierarchy sources behind
the phrase workflow. See [arrival-and-closure.md](arrival-and-closure.md) for
the completion workflow and its specific sources.
