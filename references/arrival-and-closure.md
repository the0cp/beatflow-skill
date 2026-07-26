# Arrival and closure

A phrase boundary answers “where does this span end?” An arrival answers
“where does its musical work become complete?” They may be separated by a
held tone, silence, echo, link, or afterglow. Do not treat trailing silence as
proof that the preceding notes formed a convincing ending.

## Plan the arrival before filling the phrase

For each important phrase:

1. state the phrase's musical function in plain language;
2. choose one primary arrival onset inside the phrase;
3. decide whether it is `open`, `partial`, `closed`, or deliberately `elided`;
4. name the roles responsible for making it audible;
5. decide whether harmony must be merely `supported`, fully `resolved`, or
   left `free`;
6. reserve enough time for the arrival to stand and for its declared
   post-action;
7. only then write the approach and foreground detail.

Use `section.arrival(...)` to make that plan executable:

```python
section.arrival(
    "arr_answer",
    "phr_answer",
    beat(14),
    functions=["foreground", "low"],
    closure="closed",
    strength=0.85,
    min_hold=beat(2),
    harmonic_stability="resolved",
    post_action="stop",
    max_post_attacks=0,
    goal="Complete the answer on the local tonic and let it stand.",
)
```

The schema does not define a cadence vocabulary. A tonal cadence, modal
repose, rhythmic cutoff, textural convergence, registral landing, or another
style-appropriate event can serve as the arrival. The declared fields only
make the intended timing and evidence inspectable.

## Use a stop test

When a phrase sounds as if it says too little or too much, do not immediately
add or delete its last note. Render two or three terminal variants from the
same setup:

- stop at the earliest plausible completion;
- stop at the next plausible completion;
- keep one short, explicitly named echo or link.

Listen without seeing the piano roll. Reject a cut that leaves an active
tendency unanswered. Reject a continuation whose new attacks no longer
change closure, direction, or formal function. Keep the shortest ending that
completes the intended job without making the phrase sound amputated.

This comparison is more reliable than a universal note-count rule. Different
meters, tempi, textures, and musical languages support different terminal
lengths.

## Diagnose distinct failure modes

- `arrival_missing`: the music stops before the declared completion point;
- `arrival_not_articulated`: a non-elided arrival is crossed only by an old
  sustain, with no selected role marking the point;
- `arrival_hold_too_short`: the structural landing disappears before its
  declared minimum duration;
- `post_arrival_overrun`: extra attacks exceed the declared echo, link, or
  afterglow budget;
- `arrival_harmonic_support_missed`: observable arrival pitches contradict
  the requested harmonic stability;
- `arrival_harmony_not_fully_observable`: functional or relative targets
  prevent the authored plan from proving the requested stability.

These observations do not prove that an ending is good. They separate common
causes so revision can target timing, pitch support, or surplus continuation
instead of applying one generic “more breath” fix.

## Research basis and limits

Temporal placement and tonal content interact in perceived melodic
completion; a tonally plausible ending can lose resolution when its timing is
misaligned. Melodic continuation judgments also depend on local intervallic
implication, while phrase-level expectancy depends on both pitch and rhythmic
structure. Formal-function theory further distinguishes grouping boundaries
from the musical function of ending and from material that occurs
after-the-end.

These findings motivate explicit arrival intent and comparative listening.
They do not provide a universal cadence detector, and much of the formal
theory describes Western tonal repertoires.

Sources:

- Boltz, M. (1989). Rhythm and “good endings”: Effects of temporal structure
  on tonality judgments. *Perception & Psychophysics, 46*(1), 9-17.
  [DOI](https://doi.org/10.3758/BF03208069)
- Thompson, W. F., Cuddy, L. L., & Plaus, C. (1997). Expectancies generated
  by melodic intervals: Evaluation of principles of melodic implication in a
  melody-completion task. *Perception & Psychophysics, 59*(7), 1069-1076.
  [DOI](https://doi.org/10.3758/BF03205521)
- Schellenberg, E. G. (1996). Expectancy in melody: Tests of the
  implication-realization model. *Cognition, 58*(1), 75-125.
  [DOI](https://doi.org/10.1016/0010-0277(95)00665-6)
- Prince, J. B., & Loo, L.-M. (2017). Surface and structural effects of pitch
  and time on global melodic expectancies. *Psychological Research, 81*(1),
  255-270. [DOI](https://doi.org/10.1007/s00426-015-0737-y)
- Caplin, W. E. (2009). What are formal functions?
  [Author PDF](https://williamcaplin.com/download/what-are-formal-functions.pdf)

