# Architecture

BeatFlow separates musical judgment from deterministic execution:

1. `SKILL.md` gives Codex the composition and revision workflow.
2. The Python DSL makes exact plans readable and programmable.
3. strict Composition 1.1 JSON stores authored musical intent.
4. the compiler realizes pitches, voicings, and occurrence treatments into an
   internal Project.
5. validators, advisory diagnostics, the MIDI renderer, and the inspector
   verify and export the result.

Codex owns style, form, harmony, rhythm, instrumentation, and phrasing. The
engine owns representation, validation, deterministic realization, and MIDI
serialization. Keep that boundary instead of adding one engine path per
genre.

Sections store reusable material. Timeline occurrences store formal intent,
energy, active alternatives, and deterministic register, dynamics, and gate
treatments. This keeps complete-song form compact while leaving the musical
content explicit.

Composition 1.1 is the public interchange boundary for future editors,
importers, DAW extensions, alternate realizers, or MCP tools. Reuse its models
and checks rather than duplicating musical semantics.

`scripts/run.py` creates a pinned cached Python environment and delegates to
the same CLI used by development installations.
