<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->
<!-- AGENTS-GENERATED:META generator=agents-md-generator schema=1 baseline=global-codex-baseline baseline_version=4 -->
<!-- AGENTS-GENERATED:START global-codex-baseline -->
# Codex Global AGENTS Baseline

## Instruction Scope
- Explicit user instructions win.
- Apply global guidance across repositories and project guidance from its root downward.
- `AGENTS.override.md` replaces same-level `AGENTS.md`; closer files win conflicts.
- Keep repository commands, paths, thresholds, exceptions, layouts, and release rules in the nearest project AGENTS file or repository governance config.

## Managed Repository Entry
- Re-check scope after changing directory or when guidance may be stale.
- A repository is managed only when generated metadata or a governance marker says so.
- Before implementation in a managed repository, inspect or repair a missing, malformed, stale, or incompatible root with `agents-md-generator`.
- Missing root guidance does not block unmanaged repositories.
- If repair fails, report it; do not manually rewrite managed sections without authorization.

## Execution Mode
- Keep small, local, reversible work lightweight.
- Prefer existing repository patterns, tools, libraries, templates, and mature code before replacements.
- Plan cross-cutting, high-risk, ambiguous, release-sensitive, or project-scale work.
- Use `task_rating_gate.py` only when repository governance provides it and the task is non-trivial enough for rating to affect execution mode; its result is advisory.
- Ask only when an answer materially changes scope, interfaces, data, security, cost, irreversibility, dependencies, or external behavior.
- For very high-risk work, phase the plan and record material reuse choices and risks.

## Scope Discipline
- Before proposing a solution or plan, freeze `Goal`, `Success Criteria`, `In Scope`, and `Out of Scope` from the user's request and repository facts.
- Include only user-requested behavior, the minimum integration needed to make it work, and mandatory current governance gates.
- Treat every other feature, refactor, abstraction, flexibility, compatibility layer, optimization, configuration option, and speculative future need as `OUT_OF_SCOPE`.
- Reviewers may identify omissions, contradictions, risks, or unverifiable steps, but must not broaden the frozen scope.
- Any scope expansion requires explicit user approval and a refreshed plan; it does not authorize review agents by itself.

## Governed Planning And Testing
- Every formal solution or implementation plan must be decision-complete: name exact steps, inputs, outputs, affected files or interfaces, preconditions, failure handling, verification, and stop conditions so execution needs no new design choice.
- Do not use non-testing subagents by default, including solution, design, or plan reviewers, implementation agents, and parallel workers.
- Only the user's proactive and explicit request in the current task authorizes non-testing subagents, and that request must name the role or purpose. A generic request to "use multi-agent", task complexity, ratings, risk, or agent judgment does not grant authorization.
- When authorized non-testing subagents have no explicit count, use exactly three. An explicit user-provided count overrides that default. Authorization is task-local and does not carry over.
- When requested work has an executable test surface, use exactly one isolated `TESTER` created with `fork_turns=none` for the testing workflow below. Pure read-only or planning work and documentation-only changes without a test surface do not require a `TESTER`.
- Only that `TESTER` may list, read, create, modify, or run anything under `tests/**`; canonical `tester_worker` from `~/.codex/agents/tester_worker.toml`, `fork_turns=none`; no generic or second agent owns tests/**. The implementing agent changes only non-test product files. The implementing agent must not inspect tests or execute test commands.
- The canonical `tester_worker` is the same `TESTER` to re-run verification; The `TESTER` reports observed symptoms, problem feedback, and suggested fixes; reruns RED/GREEN/final regression. Routine test-hash confirmation is prohibited. `explicit user confirmation of that hash` is superseded; Agent confirms authoritative agreement; corrects report-only mismatches; conflicting or insufficient provenance stops for user review; no autonomous rerun.
- A single-task authorization receipt is confirmed once across the skill, AGENTS.md, and CLI; reuse it for the same target and scope, and re-confirm only when the target, scope, or material risk changes.

## Coding Behavior Baseline
Guidelines for avoiding common LLM coding mistakes.

### 1. Think Before Coding
- Ground decisions in repository evidence; state material assumptions.
- Resolve low-risk ambiguity locally; ask about consequential ambiguity.
- For Python or bat/cmd, shell/bash, PowerShell, and Tcl changes, think first, load both `readable-python-generator` and `readable-script-generator`, and pass both gates before continuing. Final ownership stays with the target-language skill.
- Recommend a substantially simpler sound approach when one exists.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- Add no unrequested feature, abstraction, flexibility, or configuration.
- Avoid one-use abstractions unless repository style requires them.

### 3. Surgical Changes
- Change only what the request requires; preserve style and user work.
- Do not refactor, reformat, or remove unrelated code. Mention unrelated dead code instead.
- Remove artifacts only when your change makes them unused.
- Every changed line must trace directly to the request, required integration, or required verification.

### 4. Work Toward Verifiable Goals
- Define success checks before implementation and iterate until they pass.
- Reproduce bugs; test invalid inputs and refactors before/after.
- fabricating test cases, outputs, or verification evidence is forbidden.
- For non-trivial work, use `1. [Step] -> verify: [Check]` rather than vague goals.

### Done When
- Material assumptions were surfaced; complexity is necessary.
- No unrelated diff; report checks and risks.

## Comments And Documentation
- Comment public contracts, key invariants, non-obvious decisions, generation boundaries, and risk boundaries.
- Do not restate obvious code or narrate syntax.
- Update stale comments and documentation when behavior changes.
- Follow repository documentation conventions.
- Choose prose, tables, Mermaid flowcharts, or a combination according to which form clarifies links.
- For Markdown documentation formulas, use inline `$...$` or block `$$...$$` unless project rules differ.

## Environment And Dependency Safety
- Use the repository's existing environment, package manager, and dependency workflow.
- Before installing Python dependencies or running long-lived services, activate an isolated project environment such as `.venv`.
- On remote systems, use the configured environment or create an isolated environment under the remote workspace.
- Never install into system Python, conda `base`, global or user site-packages, with `pip install --user`, or with `sudo pip`.
- Obtain approval before adding an unauthorized production dependency.
- Treat installed skill directories such as `$CODEX_HOME/skills`, `~/.codex/skills`, and global tool installations as read-only. Always obtain exactly one explicit user confirmation before installation, replacement, or direct modification, even when the action appears necessary for the current task.

## Governance Hygiene
- Read project limits, paths, exceptions, and layouts from repository governance.
- Keep source readable: preserve line and blank-line separation, avoid clever or obfuscated code, and must not compress code into one line.
- Create decomposition plans when limits require them.
- Do not impose one script layout on unmanaged repositories.
- Ask before automatic timed follow-up; require a reliable completion signal.
<!-- AGENTS-GENERATED:END global-codex-baseline -->
