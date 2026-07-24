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

## Protect the instrument contract

Classify the planned instrumentation before writing events:

- `essential`: explicitly requested or responsible for the intended ensemble identity;
- `substitutable`: its musical function must survive, but another instrument may carry it;
- `optional`: decorative, alternate, or developmental material that may be removed after comparison.

Record the classification in the composition intent, priorities, or exclusions. A genre label informs the decision but does not automatically make every conventional instrument essential.

When a part fails, distinguish among a weak role, weak writing, and weak playback timbre. Muting is useful for diagnosis, but it does not cancel an essential part. Rewrite its rhythm, register, voicing, density, or relationship first; change its preview program or destination sound when timbre is the problem. Change the contract only after explaining the tradeoff and obtaining user approval.

## Hear hierarchy, not only grid

Quantization only says that an attack is measurable. It does not say that its metric role is legible. Choose the tactus and its simple or compound division, establish phrase and bar downbeats, then decide which weak positions create syncopation against them.

Distinguish the harmony span from a performed chord attack. When every voicing waits for an unrelated subdivision position, the listener hears floating harmony even though the data is perfectly quantized.

## Phrase before pitch list

For each foreground phrase, decide:

- rhythmic identity;
- starting state and destination;
- one or two recognizable transformations;
- contour and register;
- tension and release;
- breath or handoff.

Then choose functional targets. Stable tones, chromatic approaches, chord extensions, leaps, and repetitions are all valid when they serve the phrase. Do not assume that pitch-class correctness creates a convincing line.

## Express time directly

Every event has an exact section-local onset and duration in quarter-note beats. Use rational values such as `beat(1, 3)` for tuplets. A swung or asymmetric feel is a pattern of authored onsets and durations, not a global renderer switch.

The PPQ must represent every rational time exactly. The default 960 supports common halves, thirds, quarters, fifths, sixths, eighths, tenths, twelfths, and sixteenths.

## Arrange with space

Treat silence, register, note length, and role handoff as compositional material. A harmony role need not re-attack continuously, but a changed harmony must become perceptible through bass, voicing, sustain, or another role. A foreground need not occupy the whole section. Bass and pulse may coincide selectively while retaining independent motion.

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
