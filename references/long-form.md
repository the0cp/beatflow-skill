# Long-form arrangement

Use this workflow for complete songs or briefs longer than 90 seconds.

## Duration and form

Set `target_duration_seconds` before writing events. Estimate the required bars from tempo and meter, then design a timeline whose actual duration falls within ten percent of the target.

Prefer a small set of meaningful reusable sections over one giant section or dozens of nearly identical copies. Write genuinely new harmony or phrase material when the form needs contrast.

## Material versus occurrence

A section owns reusable musical material. A timeline occurrence owns how that material is presented.

Declare each occurrence as one of:

- `statement`: first clear presentation;
- `repeat`: intentionally similar return;
- `develop`: recognizable material with changed arrangement;
- `contrast`: a different formal state;
- `climax`: maximum structural or registral intensity;
- `release`: withdrawal, cadence, or coda.

Use `arrange()` for audible occurrence-level changes:

- remove or restore layers;
- enable a `default_enabled=False` counterline, fill, or alternate ending;
- move suitable pitched layers by octave;
- change velocity or gate;
- transpose only when the harmonic context supports it.

Do not label a return `develop` or `climax` while leaving its arrangement state unchanged.

## Alternative material

Partition optional material into complete segments. For example, keep a base foreground segment enabled by default and a final-chorus counterline disabled by default. On the climax occurrence, disable the base segment or keep it as appropriate, then enable the alternative.

Avoid random note thinning as a substitute for arrangement. Choose which musical layer appears.

## Long-form checks

Review:

- actual versus target duration;
- energy range and climax placement;
- active segments and tracks per occurrence;
- foreground sounding activity;
- repeated sections with identical arrangement signatures;
- developmental labels that make no audible structural change.

These checks verify form intent, not musical quality. Listen for transition preparation, accumulated expectation, payoff, and whether the ending feels earned.
