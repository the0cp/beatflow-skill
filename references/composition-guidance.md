# Composition guidance

BeatFlow provides a language and a verification pipeline, not a style recipe. Codex must make the musical decisions.

## Begin with causality

Write a one-paragraph intent before events. Identify what creates motion, what anchors it, what leads attention, what creates contrast, and where the listener should feel arrival. Then design meter and phrase, harmonic rhythm, role interaction, and finally notes.

A useful role plan answers:

- Which role owns the main time reference?
- Which attacks are shared ensemble statements?
- Which parts answer, leave space, or pull against that reference?
- Where does foreground density rise and fall?
- Which harmony changes demand melodic or bass preparation?

Independence is not randomness. Parts can share meter and harmonic time while using different attack sets.

Turn the plan into executable intent. Declare phrase scope and perceptual
goals with `section.phrase(...)`, declare the primary point of completion
with `section.arrival(...)`, and use `section.phrase_stage(...)` when a
prominent line needs an executable internal density and focus plan. Then
reserve structurally necessary empty windows
with `section.silence(...)`. When independence, call-and-response,
interlocking, or handoff is central to the brief, declare the expected onset
relationship with `interaction()` instead of relying on prose alone. See
[arrival-and-closure.md](arrival-and-closure.md) before writing a prominent
terminal gesture.

Before pitch generation, make a shared-clock pass. Mark bar downbeats, tactus
anchors, harmony changes, bass arrivals, phrase entries, and planned
displacements. A quantized pickup is not coordinated merely because its
fraction is exact. Important foreground attacks and durations must preserve
the same recoverable accent hierarchy as the accompaniment. See
[temporal-coordination.md](temporal-coordination.md).

## Protect the instrument contract

Classify the planned instrumentation before writing events:

- `essential`: explicitly requested or responsible for the intended ensemble identity;
- `substitutable`: its musical function must survive, but another instrument may carry it;
- `optional`: decorative, alternate, or developmental material that may be removed after comparison.

Record the classification in the composition intent, priorities, or exclusions. A genre label informs the decision but does not automatically make every conventional instrument essential.

Classify prominence separately as primary, co-primary, support, or background.
An essential instrument may still be support. After rendering, inspect each
track's realized note count and average velocity, then audition primary/support
pairs. These values do not predict synthesizer loudness, but a support part
that is both denser and materially stronger is a concrete masking risk.

When a part fails, distinguish among a weak role, weak writing, weak balance,
and weak playback timbre. Muting is useful for diagnosis, but it does not
cancel an essential part. Rewrite its rhythm, register, voicing, density,
velocity, volume, or relationship first; change its preview program or
destination sound when timbre is the problem. Change the contract only after
explaining the tradeoff and obtaining user approval.

## Hear hierarchy, not only grid

Quantization only says that an attack is measurable. It does not say that its metric role is legible. Choose the tactus and its simple or compound division, establish phrase and bar downbeats, then decide which weak positions create syncopation against them.

Distinguish the harmony span from a performed chord attack. When every voicing waits for an unrelated subdivision position, the listener hears floating harmony even though the data is perfectly quantized.

## Phrase before pitch list

For each foreground phrase, decide:

- rhythmic identity;
- contrasting short and long gesture spans;
- whether each sparse passage is singable or each dense passage is
  instrumentally directional;
- where a polyphony-capable foreground uses single notes, dyads, or chordal
  punctuation;
- starting state and destination;
- one or two recognizable transformations;
- contour and register;
- tension and release;
- breath or handoff.

Map those decisions to a few metrically grounded stages before writing a
pitch list. Give stages different formal jobs or attack budgets, and mark at
most one focus through salience, density, or duration. Decide whether each
stage should continue without a perceptual break, end in a breath, or reach an
arrival. When a stage should sound like one word or gesture, declare
`min_connected_ratio` and let most internal durations reach the next onset.
When a stage contains several utterances, declare `max_gesture`; when a piano
or ensemble line changes foreground texture, declare a small
polyphonic-attack budget.
When shared time is essential, optionally declare its `entry_anchor`,
`min_tactus_attack_ratio`, and `max_off_tactus_bridge_ratio`. Do not set these
from a genre preset; choose them from the phrase's actual metric job.
A structural stage must begin at the phrase start or a declared subphrase
boundary. Keep regular stage lengths when content contrast already supplies
the needed shape.
A new formal job does not require a rest, while a connected phrase does not
require every note to be legato. Do not impose the same stage sequence on
every phrase. See
[internal-phrase-shape.md](internal-phrase-shape.md) and
[melodic-continuation.md](melodic-continuation.md).

Then choose functional targets. Stable tones, chromatic approaches, chord extensions, leaps, and repetitions are all valid when they serve the phrase. Do not assume that pitch-class correctness creates a convincing line.

When the theme carries the work, do not move straight from a prose brief to
a complete long form. Write at least three short candidates that differ in
rhythm, contour, interruption, or phrase placement. Include an exact or
near-exact restatement before heavy transformation, render the candidates,
and select by listening. Development cannot rescue a subject that has no
recognizable identity.

## Express time directly

Every event has an exact section-local onset and duration in quarter-note beats. Use rational values such as `beat(1, 3)` for tuplets. A swung or asymmetric feel is a pattern of authored onsets and durations, not a global renderer switch.

The PPQ must represent every rational time exactly. The default 960 supports common halves, thirds, quarters, fifths, sixths, eighths, tenths, twelfths, and sixteenths.

## Arrange with space

Treat silence, register, note length, and role handoff as compositional material. A harmony role need not re-attack continuously, but a changed harmony must become perceptible through bass, voicing, sustain, or another role. A foreground need not occupy the whole section. Bass and pulse may coincide selectively while retaining independent motion.

A token half-beat gap repeated inside otherwise continuous writing is not automatically a phrase boundary. Inspect both each role's rests and the full pitched texture's shared releases. At important endings, combine more than one cue: space or handoff, lengthening, thinning, contour closure, harmonic arrival, register, or dynamics. Preserve continuous motor writing when it is intentional; otherwise make selected boundaries structurally audible and vary their strength.

Use different chord sizes and registers when the texture calls for it. The compiler minimizes voicing motion, but it cannot decide where the arrangement needs silence or a fuller attack.

## Candidate diversity

When generating alternatives, change at least one causal layer:

- phrase rhythm and rest placement;
- role relationship;
- harmonic path or harmonic rhythm;
- formal contrast;
- register and density trajectory.

Do not call transposition, a new random seed, or minor velocity edits a new candidate.

## Listening loop

Inspect and diagnose first, but select by listening. If timing feels wrong, revise rhythm and role relationships. If the line lacks direction, revise phrase design. If MIDI timbre is distracting, audition a clearer program or a better sound library before rewriting valid musical structure.

See [research-foundations.md](research-foundations.md) for the evidence and
limitations behind boundary, memory, expectation, tension, and hierarchy
guidance, including why grouping boundaries and musical completion are
modeled separately.
