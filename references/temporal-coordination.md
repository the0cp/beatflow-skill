# Temporal coordination

Use this guidance when a melody sounds quantized but still feels detached from
the accompaniment, as if the parts imply different tempos.

## Quantization is not a shared clock

An exact onset can still have the wrong structural role. A foreground may use
legal eighths and sixteenths while its entries, longer notes, contour peaks,
and resolutions repeatedly avoid the tactus and bar frame established by the
other parts. The result is not necessarily an isolated wrong note. It is a
conflict between accent hierarchies.

Before writing pitches, make a small anchor map:

- bar downbeats and phrase entries;
- tactus positions that carry structural attacks;
- harmony changes and bass arrivals;
- one intended pickup, suspension, or anticipation at a time;
- the point where each displaced event returns to the shared meter.

The foreground does not need to attack every anchor. It may sustain through an
anchor, leave space, or syncopate against it. However, its important attacks
and durations must make the same tactus and phrase frame recoverable.

## A diagnostic comparison

BeatFlow compared the top attacked note of the upper track with the lower
track in four public-domain MIDI realizations. The comparison is descriptive,
not a style model:

| Realization | Bar-downbeat attack coverage | Tactus-aligned attacks | Off-tactus attacks held across the next tactus |
| --- | ---: | ---: | ---: |
| Bach, Minuet BWV Anh. 116 | 100% | 67% | 0% |
| Beethoven, Für Elise | 97% | 26% | 4% |
| Rameau, Tambourin | 98% | 65% | 2% |
| Joplin, Maple Leaf Rag | 47% | 25% | 13% |
| Rejected BeatFlow foreground | 7% | 22% | 63% |

The useful difference is not that professional music puts every attack on a
beat. Für Elise has many weak-position attacks, and Maple Leaf Rag uses
persistent pickups and syncopation. Even the rag articulates substantially
more bar frames and carries far fewer displaced attacks across the following
tactus than the rejected foreground. The rejected line's syncopation became
the permanent phase instead of a departure and return.

Method limitations:

- the top note at each upper-track onset is only a practical melody proxy;
- ornamentation and pickups can lower tactus alignment without weakening the
  bar frame;
- the sample is too small for genre inference or automatic composition;
- the MIDI files are analysis references, not templates or source material,
  and are not bundled with BeatFlow.

The sources were the
[Mutopia Project](https://www.mutopiaproject.org/legal.html) public-domain
editions of
[Minuet BWV Anh. 116](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=77)
and
[Für Elise](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=931),
the Mutopia public-domain edition of
[Maple Leaf Rag](https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=23),
plus the public-domain Wikimedia Commons realization of
[Rameau's Tambourin](https://commons.wikimedia.org/wiki/File:RAMEAU_Tambourin.mid).

## Authoring contract

For an important `phrase_stage()`, optionally declare:

- `metric_role`: `structural`, `pickup`, `extension`, `elision`, or `free`;
- `entry_anchor`: `free`, `division`, `tactus`, or `bar_downbeat`;
- `min_tactus_attack_ratio`: the minimum share of unique stage attacks that
  should articulate the tactus;
- `max_off_tactus_bridge_ratio`: the maximum share of off-tactus events that
  may continue across the following tactus.

For example:

```python
section.phrase_stage(
    "stg_answer",
    "phr_hook",
    beat(4),
    beat(4),
    functions=["foreground"],
    role="develop",
    min_attacks=4,
    max_attacks=7,
    entry_anchor="bar_downbeat",
    min_tactus_attack_ratio=0.25,
    max_off_tactus_bridge_ratio=0.35,
    exit_behavior="continue",
    goal="Answer on the new harmony, then use one audible anticipation.",
)
```

These values are authored expectations, not genre defaults. Leave them unset
for free rhythm, rubato, cadenzas, drones, or deliberate metric ambiguity.
Choose them before writing events. A structural stage must begin at the phrase
start or a declared subphrase boundary; do not use `division` as a
post-hoc description of an accidental displaced start.

## Revision pass

1. Render only pulse, bass, and harmony. Confirm one perceptual clock.
2. Render the foreground rhythm on one pitch. Ignore pitch quality.
3. Mark phrase-stage entries, long notes, leaps, peaks, and arrivals.
4. Move structural accents to selected bar, tactus, harmony, or bass anchors.
5. Keep only displacements that have a named function and audible return.
6. Restore contour and pitch targets without changing the accepted rhythm.
7. Listen to accompaniment, rhythm-only foreground, and the complete version.

Do not solve the problem by forcing every note onto a quarter note. A stable
clock supports rhythmic variety; it does not replace it.
