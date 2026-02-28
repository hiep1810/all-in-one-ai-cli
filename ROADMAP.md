# Roadmap

## P0 (Build Next)

1. Agent loop v2
- Implement iterative `plan -> act -> observe -> replan`.
- Add `max_steps`, stop conditions, and failure exit reasons.
- Persist step state in structured JSON.

2. TUI productivity
- Add `\\history`, `\\clear`, `\\save`, `\\copylast`.
- Add command autocomplete after typing `\\`.
- Add streaming AI output in chat mode.

3. Safety layer
- Add approval prompts for risky tools in TUI/CLI.
- Add policy levels per tool class (`read`, `write`, `shell`, `network`).
- Add allowed path sandbox config.

4. Tool contracts
- Define tool argument schemas and validation errors.
- Add timeout/retry settings per tool.
- Standardize tool result format.

## P1 (After P0 Stabilizes)

1. Provider expansion
- Add OpenAI/Anthropic adapters under unified interface.
- Add fallback routing and health checks.

2. Workflow engine v2
- Add variables, conditionals, and step outputs in YAML workflows.
- Add `workflow inspect` and dry run.

3. Memory improvements
- Add rolling session summary.
- Add project memory index and retrieval.

4. Observability
- Add run IDs, metrics, and summarized audit report command.

## P2 (Scale + Collaboration)

1. Multi-agent mode
- Planner, executor, reviewer role handoff.

2. GitHub integration
- Generate issue/PR summaries and patch suggestions.

3. Packaging and releases
- `pipx` install path, semantic versioning, changelog flow.

4. Quality gates
- Unit + integration tests and CI pipeline.
