<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->
<!-- AGENTS-GENERATED:META generator=agents-md-generator schema=1 baseline=global-codex-baseline baseline_version=6 -->
<!-- AGENTS-GENERATED:START global-codex-baseline -->
# Global Codex AGENTS Baseline

## Instruction Scope
- Explicit user instructions win
- Apply global guidance across repositories
- `AGENTS.override.md` replaces same-level `AGENTS.md`; closer files win conflicts.
- Keep commands/release governance

## Managed Repository Entry
- A repository is managed only when metadata or a governance marker says so.
- Before implementation, inspect/repair roots.
- Global baseline source: read `$CODEX_HOME/AGENTS.md` before relying on user-level rules.

## Execution Mode
- Prefer existing repository patterns, tools, libraries, templates; phase the plan and record material reuse choices and risks.
- Use `task_rating_gate.py` only when governance provides it and the task is non-trivial enough for rating to affect execution mode; result is advisory.
- Ask only when an answer materially changes scope, security, cost, or external behavior.

## Scope Discipline
- Before proposing a solution or plan, freeze `Goal`, `Success Criteria`, `In Scope`, and `Out of Scope` from the request and repository facts.
- Treat every other feature, refactor, abstraction, flexibility, compatibility layer, optimization, option, and speculation as `OUT_OF_SCOPE`.
- Reviewers may identify omissions, contradictions, risks, or unverifiable steps; must not broaden the frozen scope.
- Scope expansion needs explicit approval and a refreshed plan; it does not authorize reviewers.

## Governed Planning And Testing
- ### Plan consistency review
  Before first output or complete replacement of `<proposed_plan>` in Plan Mode, the main Agent must review the plan for internal contradictions and confirm alignment with the approved requirements and applicable rules.
  Resolve directly actionable contradictions first; ask about decisions that require the user, and do not output the plan until they are resolved.
  This review stays with the main Agent and is independent of runtime session state.
- Formal plans must be decision-complete: steps, inputs, outputs, interfaces, preconditions, failures, verification, stop conditions; execution needs no new design choice.
- Do not use non-testing subagents by default, including solution, design, or plan reviewers, implementation agents, and parallel workers.
- A proactive and explicit request in the current task authorizes non-testing subagents; the request must name the role or purpose.
- A generic request to "use multi-agent" does not grant arbitrary-subagent authorization.
- If you have no explicit count, use exactly three; An explicit user-provided count overrides that default.
- Arbitrary solution/design/implementation/research subagents require role-specific authorization; task complexity, ratings, risk, or agent judgment does not grant authorization.
- explicit user confirmation of that hash.
- Reuse one target per canonical role; an unconfigured state blocks the role.
- New tests use `<work-folder>/tests/<feature>/test_<behavior>.<ext>` under one root `tests/`; existing violations block completion.
- Runtime role state is stored in project configuration; generated instruction files contain only explicitly enabled role contracts.
- Authorization is task-local and does not carry over; one receipt covers skill, AGENTS.md, CLI until target, scope, or risk changes.
- Routine test-hash confirmation is prohibited. An authoritative current tests result may confirm only when it agrees with the current tests tree or receipt. Conflicting or insufficient provenance stops for user review without an autonomous rerun.

## Remote Upload Boundary
- Never upload the whole work folder or a workspace bundle; `.git/`, `git/`, `github/`, `dist/`, `ref/`, and archives are forbidden. Upload only listed files or narrow directories.

## Coding Behavior Baseline
Guidelines for avoiding common LLM coding mistakes.

### 1. Think Before Coding
- Ground decisions in repository evidence; state material assumptions.
- Resolve low-risk ambiguity locally; ask about consequential ambiguity.
- For difficult implementation problems, check library documentation and reuse supported APIs before replacement code; avoid custom substitutes that add debugging cost.
- For Python, bat/cmd, shell/bash, PowerShell, and Tcl changes, plus Node-only JavaScript (`.js`/`.mjs`) and static Dockerfile changes, load both `readable-python-generator` and `readable-script-generator`; keep final ownership by language.
- Managed roots render `shared`, `python`, and `script` once; Python uses `readable-python-generator`, and scripts use `readable-script-generator`.
- Human-readable Python/script output uses `> INFO: [kind]`, `> WARNING: [kind]`, `> ERR: [kind]`; machine-readable output stays unprefixed.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- Add no unrequested feature, abstraction, flexibility, or configuration.

### 3. Surgical Changes
- Change only what the request requires; preserve style and user work.
- Do not refactor, reformat, or remove unrelated code. Mention unrelated dead code instead.
- Remove artifacts only when your change makes them unused.
- Every changed line must trace directly to the request, integration, or verification.

### 4. Work Toward Verifiable Goals
- Define success checks before implementation and iterate until they pass.
- Reproduce bugs; test invalid inputs and refactors before/after.
- fabricating test cases, outputs, or verification evidence is forbidden.
- For non-trivial work, use `1. [Step] -> verify: [Check]` rather than vague goals.

### Done When

## Comments And Documentation
- Comment public contracts, key invariants, non-obvious decisions, generation boundaries, and risk boundaries; do not restate obvious code or narrate syntax.
- Choose prose, tables, Mermaid flowcharts, or a combination according to which form clarifies links.
- Update stale comments and documentation when behavior changes.
- For Markdown documentation formulas, use inline `$...$` or block `$$...$$` unless project rules differ.

## Environment And Dependency Safety
- Use the repository's existing environment, package manager, and dependency workflow.
- Before dependencies or long-lived services, use an isolated project environment such as `.venv`.
- On remote systems, use the configured environment or create an isolated environment under the remote workspace.
- Never install into system Python, conda `base`, global/user site-packages, `pip install --user`, or `sudo pip`.
- Obtain approval before adding an unauthorized production dependency.
- Treat installed skill directories `$CODEX_HOME/skills` and global `$CODEX_HOME/AGENTS.md` as read-only; Always obtain exactly one explicit user confirmation before install, replace, or direct changes.

## Governance Hygiene
- Read project limits, paths, exceptions, layouts from repository governance.
- Keep source readable: preserve line/blank-line separation, avoid clever or obfuscated code, and must not compress code into one line.
- Create decomposition plans when needed.
- Ask before timed follow-up; require completion
<!-- AGENTS-GENERATED:END global-codex-baseline -->
