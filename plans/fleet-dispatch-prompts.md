# Fleet Dispatch Prompts

3 waves, each managed by an Opus 4.6 orchestrator dispatching parallel agents.

Wave 2 requires Wave 1 complete. Wave 3 requires Wave 2 functional.

---

## Wave 1 — imas-standard-names

```
Implement Features 01, 03, and 04 for the imas-standard-names project 
at /home/ITER/mcintos/Code/imas-standard-names using parallel agents.

Read all plans in plans/features/ before starting. Use `uv run` for 
all Python commands. 100% test coverage required on new code.

Agent A: Feature 01 (Grammar API Exports) then Feature 04 (JSON Schema Contract)
  - Plan: plans/features/01-grammar-api-exports.md
  - Plan: plans/features/04-json-schema-contract.md

Agent B: Feature 03 (Grammar Extensions)
  - Plan: plans/features/03-grammar-extensions.md
  - Context: plans/research/05-maarten-feedback-gaps.md
  - Use rubber-duck review before implementing binary operators (Phase 2)

Launch both agents simultaneously. They have no dependencies on each other.
After both complete: uv run ruff check --fix && uv run ruff format && uv run pytest --cov
```

---

## Wave 2 — imas-codex (SN Build Pipeline)

```
Implement Feature 05 (SN Build Pipeline) in the imas-codex project 
at /home/ITER/mcintos/Code/imas-codex using parallel agents.

Read plans/features/standard-names/05-sn-build-pipeline.md and 
plans/features/standard-names/00-implementation-order.md before starting.
Study the existing dd_workers.py pipeline as the architectural pattern to follow.
Use `uv run` for all Python commands.

Prerequisite — verify Wave 1 outputs:
  uv run python -c "from imas_standard_names.grammar import compose_standard_name; print('OK')"

Agent A: Pipeline core — sn/pipeline.py, sn/workers.py, sn/state.py, sn/graph_ops.py
Agent B: Source plugins + prompts — sn/sources/, llm/prompts/sn/
Agent C: CLI + progress display — cli/sn.py, sn/progress.py, schemas/facility.yaml updates

Launch all three simultaneously. Resolve import conflicts in integration pass.
After all complete: uv run pytest --cov
Integration test: uv run imas-codex sn build --source dd --ids equilibrium --dry-run
```

---

## Wave 3 — imas-codex (Review, Benchmark, Publish)

```
Implement Features 06, 07, and 08 in the imas-codex project 
at /home/ITER/mcintos/Code/imas-codex using parallel agents.

Read plans in plans/features/standard-names/ for each feature before starting.
Use `uv run` for all Python commands.

Prerequisite — verify Wave 2 pipeline:
  uv run imas-codex sn build --source dd --ids equilibrium --dry-run

Agent A: Feature 06 (Cross-Model Review) — plans/features/standard-names/06-cross-model-review.md
Agent B: Feature 07 (Benchmarking) — plans/features/standard-names/07-benchmarking.md
Agent C: Feature 08 (Publish YAML + PR) — plans/features/standard-names/08-publish.md

Launch all three simultaneously. Agents A and C both modify sn/workers.py — 
resolve conflicts after completion.
After all complete: uv run pytest --cov
End-to-end: uv run imas-codex sn build --source dd --ids equilibrium --dry-run
```
