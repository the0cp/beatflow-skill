# Foreground and pulse

Use this guidance when a brief needs a prominent melody, thematic development, a designed chord top voice, or a timing experiment.

## Choose the attention owner

Treat `foreground` as optional. Name the one layer that should lead attention in each section. A bass hook, chord top line, rhythmic figure, or changing texture can lead without a separate melody track.

A chord sequence with frequent `top_target` events already contains a designed upper line. Add another foreground only when it has a clear call, answer, interruption, or handoff. Simultaneous attacks compete more strongly than alternating attacks, so inspect their actual onset overlap instead of deleting a whole instrument by role name. Write a lead-free or ornament-free candidate whenever removing a track may improve the arrangement.

## Build phrases, not rotating bars

Do not fill a section by cycling one-bar pitch arrays. Before writing events, state:

- the phrase span and destination;
- two related cells with different jobs;
- the rhythmic or interval feature that identifies each cell;
- where the phrase breathes;
- which harmony changes alter the meaning of a note.

Map these statements onto section time before choosing every pitch. Use declared silence windows for required breaths, and inspect the combined texture: alternating individual rests do not create a shared release when another part fills every gap.

For a prominent line, turn this map into a few non-overlapping
`section.phrase_stage(...)` declarations. Use unequal spans or attack budgets
only when their functions require it; regular spans with
contrasting density, contour, register, harmony, or texture are often the
stronger scaffold. Identify at most one focus through salience, density, or
duration. This prevents a phrase with varied note values from remaining
evenly filled at every smaller timescale. See
[internal-phrase-shape.md](internal-phrase-shape.md).

Do not make the whole phrase one continuous medium-density sentence. Contrast
locally complete short and long gestures, and decide whether each sparse span
is singable or each dense span is instrumentally directional. A
polyphony-capable foreground may use selected dyads or chordal stops as
punctuation without becoming block harmony. See
[gesture-and-foreground-texture.md](gesture-and-foreground-texture.md).

Declare the phrase itself with `section.phrase(...)`. Use a high boundary
strength only when several cues support it. Set `max_continuous` to the
longest gesture the listener should hear without a tactus-sized release.
Shape phrase endings before the last beat: reduce attacks, lengthen an
important tone, close or suspend the contour, clarify the harmonic goal, and
then leave the intended amount of space. A gap added after an already
exhausting stream is too late.

Declare the intended completion point with `section.arrival(...)` before
writing the terminal cell. Then use a stop test: compare the earliest
plausible completion, the next plausible completion, and at most one
explicitly named echo or link. Reject an early cut that leaves a tendency
active and a late cut whose extra attacks no longer change direction,
closure, or formal function. See
[arrival-and-closure.md](arrival-and-closure.md).

For a theme, write a complete multi-bar subject before producing variants. A useful subject contains more than an ascending or descending scale fragment: give it a characteristic interval, rhythm, interruption, or unresolved tendency.

For quality-sensitive thematic work, first render at least three short
subjects or 8-16 bar sketches with genuinely different rhythmic identities.
Reject weak material before long-form development. The first return should
make identity audible through exact or near-exact rhythm and contour; later
entries can fragment, invert, augment, diminish, recombine, or change
function.

For each variation, preserve at least two identity-bearing relationships and change at least two other dimensions. Transform the relationship between cells through omission, recombination, register exchange, counterpoint, harmonic reinterpretation, or changed phrase destination. Arithmetic inversion, uniform transposition, or changing one scale degree is insufficient by itself.

## Keep time legible

The default is exact quantization. Start phrase entries, structural accents, and cadential arrivals on positions whose relationship to the beat is easy to hear. In drumless writing, bass, accompaniment, or harmonic rhythm must make the meter countable before the foreground becomes syncopated.

Quantization alone does not create ensemble time. Check whether important
foreground entries, longer events, leaps, peaks, and resolutions articulate
or audibly cross the same bar and tactus anchors as the accompaniment. A line
whose every group begins as a pickup and whose displaced notes repeatedly
bridge the following beat may imply a competing accent hierarchy even when
every onset is mathematically exact. Use the metric fields on
`phrase_stage()` for quality-sensitive stages and see
[temporal-coordination.md](temporal-coordination.md).

Do not add onset drift, random jitter, or blanket humanization. If the user explicitly asks for a timing experiment:

- preserve a fully quantized baseline;
- move one role or one class of attack;
- keep the deviation smaller than the governing subdivision;
- leave the reference pulse unchanged;
- compare both candidates by listening.

Human timing is a relationship to a grid, not the absence of a grid.

For explicitly independent lines, use `interaction()` to bound shared attacks and inspect both directional overlap. Independence still permits coordinated arrivals; it should not make every onset unrelated to the meter or harmony.

## Listening decision

Render an anchor-clear baseline before the decorated version. Mute optional single-note tracks one at a time so the blamed instrument is identified by evidence. If a decorated candidate does not add a memorable identity, meaningful answer, or necessary tension, omit it.
