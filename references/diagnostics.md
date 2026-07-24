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
- unusually long directional pitch runs after realization.

Metrics include meter kind, tactus and division, metric-position counts, tactus alignment, bar-downbeat coverage, role onset counts, section activity, attention-line attacks and shared attack ratio, structural chord-tone behavior, within-tactus pulse phases, directional overlap, duration entropy, rest gaps, exact and transposition-equivalent bar-pattern diversity, chord-size vocabulary, pitch range, step ratio, leap ratio, and direction-change ratio.

Each signal is contextual. A continuous motor rhythm, ostinato, drone, unison passage, or fixed block texture can be correct. Keep it when the intent explains it.

## Candidate comparison

`compare` computes pairwise Jaccard similarity over per-function event type, section position, onset, duration, chord size, percussion lane, and occurrence arrangement state. It flags extremely similar candidates so that cosmetic variants do not consume the listening round.

Similarity is not a plagiarism detector, harmonic comparison, or quality score.

## Revision order

1. Repair validation errors.
2. Check whether diagnostics contradict the written intent.
3. Revise the highest causal layer responsible: form, role interaction, phrase rhythm, harmony, pitch motion, then articulation.
4. Rerender and listen.
5. Keep diagnostics that describe intentional musical identity.
