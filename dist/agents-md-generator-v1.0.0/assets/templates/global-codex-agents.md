<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->
<!-- AGENTS-GENERATED:START global-codex-baseline -->
# Codex Global AGENTS Baseline

## Work Start
- Before starting any work in a repository or work folder, read the current work folder root `AGENTS.md`.
- If the current work folder has no root `AGENTS.md`, or the root file is missing required version metadata, stop normal implementation flow and run `agents-md-generator` inspection or repair first.

## Precedence
- Apply instructions in this order: explicit user instruction, nearest current work folder `AGENTS.md`, parent scoped `AGENTS.md`, this global `.codex/AGENTS.md`, then generic defaults.

## Repair
- When the current work folder needs AGENTS repair, use `agents-md-generator` to inspect the workspace and rebuild or update the root `AGENTS.md` before ordinary development continues.

## Shared Governance
- When a Python task is expected to run for a long time, ask the user before enabling automatic timed follow-up. If the user agrees, use thread-level timed check-ins, continue the workflow after the task completes, and remove the timed follow-up after completion.
- Handwritten source files should stay within 1000 lines. If a file must exceed that limit, create and follow a decomposition plan before continuing.
- Non-GUI project tool scripts should live under the fixed runtime quartet: `scripts/python/<function>/<name>.py`, `scripts/shell/<function>/<name>.sh`, `scripts/bat/<function>/<name>.bat`, and `scripts/powershell/<function>/<name>.ps1`.
- Repository-specific thresholds, exception manifests, decomposition-plan locations, and long-task progress-check details must come from the current work folder's local JSON governance configuration and the scripts that read it; do not invent or duplicate those details in the global file.
<!-- AGENTS-GENERATED:END global-codex-baseline -->
