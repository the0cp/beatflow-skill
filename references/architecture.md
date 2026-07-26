# Architecture

BeatFlow has five small layers:

1. `SKILL.md` gives Codex a composition and revision workflow.
2. The Python DSL makes exact musical plans readable and programmable.
3. strict Composition 1.1 JSON is the style-neutral interchange model.
4. the compiler realizes functional pitches, voicings, and occurrence-level arrangement treatments into an internal Project.
5. validators, advisory diagnostics, the MIDI renderer, and inspector verify and export the result.

Codex owns aesthetic and style decisions. Python owns deterministic structure and rendering. This separation lets the same system write jazz, blues, classical, electronic, or other music without encoding each genre in the engine.

Composition 1.1 is the stable boundary for a future frontend, DAW extension, importer, alternate realizer, or MCP server. It remains able to read Composition 1.0 artifacts. Such clients should reuse the model and checks instead of duplicating musical semantics.

Sections store reusable material. Timeline occurrences store formal intent, energy, active alternatives, and deterministic register/dynamics/gate treatments. This keeps complete-song form compact without hiding musical content in genre templates.

`scripts/run.py` creates a pinned cached Python environment. The skill contains no model API client, sample library, notation corpus, audio synthesizer, mix engine, credentials, or frontend.

The object-graph approach is inspired by Qi He, Gus Xia, and Ziyu Wang's [TOMI paper](https://arxiv.org/abs/2506.23094) and its GPLv3 implementation. BeatFlow does not copy TOMI's retrieval corpus, prompt engine, REAPER integration, or source modules.
