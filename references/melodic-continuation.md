# Melodic rhythm and continuation

Use this guide when a melody contains legal pitches and explicit rests but
sounds as if the performer forgot the next note, resumed mid-thought, or added
one note too many.

## Diagnose rhythm before pitch

Export or audition the foreground on one neutral pitch. Preserve its exact
onsets and durations. If the line still hesitates or rambles, changing scale
degrees will not repair it.

For the first one or two bars, write an attack-and-duration prototype before
choosing all pitches. It should establish:

- a recognizable subdivision or grouping;
- one metric relationship that can be remembered;
- a clear local continuation or stopping point;
- enough empty space to articulate the idea without implying an accidental
  boundary.

Treat note connection and group separation as different variables. Inside one
gesture, let most note durations reach the following onset. Between gestures,
use a deliberate separation whose position is more important than repeating
one small gap after every note. A line with legal onsets can still sound
word-by-word when nearly every gate is shortened by the same amount.

An attack pattern such as `xx,xxxx` is not universally better than
`xx,xxx0x`. The latter can make effective syncopation or interruption. It
fails when an established slot disappears once, the surrounding meter and
harmony do not explain the omission, and the same line resumes as if nothing
happened.

## Establish, confirm, then transform

For identity-bearing melody, use this general sequence:

1. **Establish** a short rhythmic cell and contour.
2. **Confirm** it with an exact or near-exact rhythmic restatement while
   preserving the recognizable attack positions.
3. **Transform** one structural relationship: compression, expansion,
   fragmentation, displacement, contour, register, harmonic function, or
   phrase placement.
4. **Consequences** must be audible. A displacement should land somewhere; a
   fragmentation should increase or redirect motion; an interruption should
   produce a response, breath, handoff, or arrival.

Do not transform several dimensions before the listener can identify the
source idea. Do not call one unexplained missing attack a variation.

## Separate job changes from boundaries

An internal stage may move from initiation to development without stopping.
For each `phrase_stage`, declare:

- `min_connected_ratio` when the stage should contain an audibly joined
  gesture;
- `exit_behavior="continue"` when momentum should cross the stage boundary;
- `exit_behavior="breathe"` only after a locally complete gesture;
- `exit_behavior="arrive"` at the primary completion;
- `exit_behavior="free"` when another role or deliberate ambiguity governs
  the grouping.

After a true breath, restart with a recognizable entry, pickup, answer, or new
idea. Do not resume halfway through the previous cell.

`min_connected_ratio` is an authored expectation, not a genre default. Legato,
portato, detached, and mixed articulation are all valid. Use it only when
cohesion inside a specific gesture matters.

## Optional phrase scaffolds

These are compositional scaffolds, not engine templates and not requirements:

- **Sentence:** state a basic idea, confirm or restate it, then create
  continuation through smaller units, sequence, increased activity, harmonic
  acceleration, or another audible destabilization toward an arrival.
- **Period:** make an antecedent with a weaker completion, then return to
  recognizable opening material and answer it with a stronger completion.
- **Through-composed phrase:** when neither archetype fits, still declare how
  identity is established, where expectation changes, and how the phrase
  completes.

The sentence's continuation normally gains momentum through functional change;
it does not require a rest between every unit. The period's second phrase must
sound related before its stronger answer becomes meaningful.

## Revision test

Before expanding the composition:

1. Listen to the rhythmic skeleton on one pitch.
2. Listen to the melody alone.
3. Listen with only the time-reference and harmonic skeleton.
4. Mark every silence as articulation, breath, handoff, arrival, or deliberate
   syncopation.
5. Inspect connected-pair ratio and median duration/inter-onset ratio for each
   important stage. Repair uniform micro-gaps, any continuation that waits a
   full tactus unintentionally, and any post-arrival attack with no declared
   job.
6. Preserve one early rhythmic confirmation before substantial variation.

This test constrains causal relationships, not note count. It allows sparse,
dense, syncopated, additive, motoric, and non-tonal writing when those choices
are explicit.

## Research basis and limits

Boltz found that temporal expectancy depends jointly on periodic accent and
melodic phrase relations. Jones, Boltz, and Klein showed that phrase context
changes when listeners expect a sequence to end, including when preterminal
notes are omitted. Drake and Palmer found that rhythmic grouping, melodic
accent, and metric accent are distinct structures in performance. Caplin's
formal-function work distinguishes presentation, continuation, and cadential
jobs; immediate repetition can establish unit size, while fragmentation can
support continuation. Carr, Olsen, and Thompson found that otherwise matched
legato melodies were perceived as more cohesive than staccato melodies.

These studies explain why an isolated hole may sound like a broken group and
why recognizable confirmation helps later transformation. They do not imply a
universal four-note cell, fixed bar length, or Western tonal melody template.

Sources:

- Boltz, M. G. (1993). The generation of temporal and melodic expectancies
  during musical listening. *Perception & Psychophysics, 53*(6), 585-600.
  [DOI](https://doi.org/10.3758/BF03211736)
- Jones, M. R., Boltz, M. G., & Klein, J. M. (1993). Expected endings and
  judged duration. *Memory & Cognition, 21*(5), 646-665.
  [DOI](https://doi.org/10.3758/BF03197196)
- Drake, C., & Palmer, C. (1993). Accent structures in music performance.
  *Music Perception, 10*(3), 343-378.
  [DOI](https://doi.org/10.2307/40285574)
- Caplin, W. E. (1987). The expanded cadential progression: A category for
  the analysis of classical form. *Journal of Musicological Research, 7*,
  215-257.
  [Author PDF](https://williamcaplin.com/download/caplin-ecp.pdf)
- Carr, N. R., Olsen, K. N., & Thompson, W. F. (2023). The perceptual and
  emotional consequences of articulation in music. *Music Perception, 40*(3),
  202-219. [DOI](https://doi.org/10.1525/MP.2023.40.3.202)
