# Diagnostics and revision

Diagnostics expose evidence; they do not accept or reject taste.

For long-form work, diagnostics also compare actual and target duration, occurrence energy, active layers, repeated arrangement signatures, and whether a declared development changes anything audible.

## Current observations

`diagnose` can report:

- nearly identical onset sets between roles;
- foreground that covers almost an entire long section;
- too little duration vocabulary in a sizable segment;
- a long pitched stream without a phrase-sized gap;
- repeated fixed-size chord blocks;
- one exact bar pattern dominating a long segment;
- a foreground bar shape repeated under transposition;
- a separate foreground competing with an already designed chord top line;
- a dense foreground using fine off-grid subdivisions without a percussion anchor;
- harmony attacks that rarely establish a primary beat or bar downbeat;
- the same role rhythm reused across most formal sections;
- unresolved non-chord tones repeatedly placed on structural beats;
- percussion spread across too many unrelated within-beat phases;
- an interaction outside its declared overlap range;
- a declared phrase containing no selected pitched attacks;
- a declared phrase whose measured boundary evidence is too weak;
- a grouped phrase whose duration does not match its declared subphrase bars;
- a structural stage outside a declared subphrase boundary;
- a regular phrase that restarts after a full-tactus rest away from a
  subphrase boundary;
- multiple regular phrases that repeat the same one-tactus subtraction
  pattern;
- phrase activity that exceeds its declared continuous-motion limit;
- a declared tension release not reflected in density or boundary cues;
- a phrase stage that misses its declared attack budget;
- a phrase stage whose sounding run exceeds its declared gesture-span limit;
- a phrase stage that misses its declared polyphonic-attack budget;
- a phrase stage that misses its declared internal connected-pair ratio;
- a phrase stage whose first attack misses its declared metric entry anchor;
- a phrase stage that misses its declared tactus-alignment minimum;
- a phrase stage that exceeds its declared displaced-hold maximum;
- a declared phrase-stage continuation interrupted by a tactus-sized gap;
- a declared phrase-stage breath without a tactus-sized gap;
- a long phrase whose continuous gestures are all similarly long;
- a phrase focus that is not distinguished through its selected observable
  cue;
- a declared arrival with no sounding event or no new articulation;
- a declared arrival that does not hold for its intended duration;
- attacks that overrun a declared arrival's post-action budget;
- observable arrival pitches that miss declared harmonic support;
- a declared silence occupied by an attack or sustain;
- a dense pitched texture with no tactus-sized shared release;
- an abrupt bar-to-bar change in pitched attack density;
- unusually long directional pitch runs after realization.
- a dense foreground that rarely articulates bar downbeats while repeatedly
  carrying off-tactus attacks across the following tactus.

Metrics include meter kind, tactus and division, phrase duration in bars and
tactus, grouping and subphrase boundaries, tactus activity and attack-count
patterns, active tactus runs and full-tactus rest positions, metric-position counts,
tactus alignment, bar-downbeat coverage, role onset counts, section activity,
pitched-texture silence and longest shared release, pitched attacks per bar,
phrase attack density in thirds, boundary gap, final-note lengthening,
terminal density change, boundary evidence, longest and individual continuous
phrase spans, phrase-stage attack density, duration vocabulary, maximum
duration, gesture count and spans, single-note and polyphonic attack counts,
polyphonic-attack ratio, salience,
phrase-stage transition pairs, connected-pair ratio, micro-gap count, median
gate ratio, metric entry, tactus-attack ratio, off-tactus bridge ratio, exit
behavior, and exit gap,
arrival articulation, hold, post-arrival attack count, observable harmonic
support, declared-silence occupancy, attention-line attacks and shared attack ratio,
structural chord-tone behavior, within-tactus pulse phases, directional
overlap, duration entropy, rest gaps, exact and transposition-equivalent
bar-pattern diversity, chord-size vocabulary, pitch range, step ratio, leap
ratio, and direction-change ratio.

Boundary evidence is a weighted observation of temporal gap, final-note
lengthening, and terminal attack-density reduction. It does not measure every
possible cue, such as harmony, contour, dynamics, performance, or cultural
convention. Each signal is contextual. A continuous motor rhythm, ostinato,
drone, unison passage, elided cadence, or fixed block texture can be correct.
Keep it when the intent explains it.

## Candidate comparison

`compare` computes pairwise Jaccard similarity over per-function event type, section position, onset, duration, chord size, percussion lane, and occurrence arrangement state. It flags extremely similar candidates so that cosmetic variants do not consume the listening round.

Similarity is not a plagiarism detector, harmonic comparison, or quality score.

## Revision order

1. Repair validation errors.
2. Check whether diagnostics contradict the written intent.
3. Revise the highest causal layer responsible: form, role interaction, phrase rhythm, harmony, pitch motion, then articulation.
4. Rerender and listen.
5. Keep diagnostics that describe intentional musical identity.
