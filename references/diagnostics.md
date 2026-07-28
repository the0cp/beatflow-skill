# Diagnostics and revision

Diagnostics expose measurable evidence. They do not accept or reject musical
taste.

## What BeatFlow observes

BeatFlow groups advisory observations into six areas:

- **form**: target duration, energy path, layer changes, repeated arrangement
  states, and development labels without audible change;
- **time**: meter and tactus alignment, phrase grouping, pulse phases, shared
  releases, density discontinuities, and declared silence;
- **phrasing**: boundary evidence, continuous activity, gesture spans, stage
  entry and exit behavior, focus, arrival, and post-arrival activity;
- **roles**: onset overlap, handoff or independence contracts, masking,
  competing foregrounds, and duplicated rhythms;
- **pitch and harmony**: realized range, directional runs, structural
  non-chord tones, chord support, designed top lines, and voice-leading
  evidence;
- **repetition and texture**: duration vocabulary, attack density, repeated
  bar shapes, fixed chord blocks, and polyphonic-attack budgets.

The report includes the measurements behind each observation, such as attack
counts, onset overlap, tactus activity, boundary gaps, sounding-run lengths,
arrival holds, event-pattern similarity, and pitch-motion ratios.

## Interpret observations in context

Many reported patterns can be intentional. Continuous motor rhythm, ostinato,
drone, unison, elided cadence, dense counterpoint, syncopation, or fixed block
texture may be exactly what the brief requires.

Phrase-boundary evidence combines temporal gap, final-note lengthening, and
terminal density reduction. It cannot directly measure every cue supplied by
harmony, contour, dynamics, timbre, performance, or cultural convention.

Treat each observation as a listening question:

1. Does it contradict the written intent?
2. Is the responsible cause form, timing, role interaction, phrase design,
   harmony, pitch motion, or only playback timbre?
3. Does the revision improve the isolated layer and the full arrangement?

## Candidate comparison

`compare` measures pairwise Jaccard similarity over event type, musical
function, section position, onset, duration, chord size, percussion lane, and
occurrence arrangement state. Use it to reject cosmetic variants before a
listening round.

Similarity is not a plagiarism detector, harmonic analysis, or quality score.

## Revision order

1. Repair hard validation errors.
2. Check the meter and shared clock.
3. Check role ownership and instrument contracts.
4. Check phrase grouping, gesture continuity, and arrival.
5. Check harmony, bass support, structural tones, and voicing.
6. Check articulation, balance, MIDI program, and destination instrument.
7. Rerender and listen.

Revise the highest causal layer that explains the problem. Do not add a new
threshold or genre rule for one weak passage.
