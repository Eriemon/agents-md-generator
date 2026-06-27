<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->
<!-- AGENTS-GENERATED:META generator=agents-md-generator schema=1 baseline=global-codex-baseline baseline_version=3 -->
<!-- AGENTS-GENERATED:START global-codex-baseline -->
# Codex Global AGENTS Baseline

## Instruction Scope
- Follow explicit user instructions first.
- Codex normally loads applicable AGENTS guidance automatically at session start.
- Global guidance applies across repositories; project guidance applies from the project root down to the current working directory.
- At each directory level, `AGENTS.override.md` replaces `AGENTS.md` when present.
- Files closer to the current working directory override broader guidance on conflict.
- Keep repository-specific commands, paths, thresholds, exceptions, directory layouts, and release rules in the nearest project AGENTS file or governance config.

## Managed Repository Entry
- Re-check instruction scope when the working directory changes, loaded guidance is uncertain, or repository governance appears stale.
- Treat a repository as `agents-md-generator` managed only when generated AGENTS metadata or a repository governance marker indicates that status.
- In a managed repository, if the root `AGENTS.md` is missing, malformed, stale, or version-incompatible, run `agents-md-generator` inspection or repair before ordinary implementation.
- In an unmanaged repository, a missing root `AGENTS.md` is not itself a blocker.
- If automated repair is unavailable or fails, report the blocker and do not manually rewrite generated managed sections unless the user explicitly requests it.

## Execution Mode
- Keep small, local, reversible tasks lightweight.
- Prefer existing repository patterns, tools, libraries, templates, and mature open-source code before building from scratch.
- Use a written plan for cross-cutting, high-risk, materially ambiguous, release-sensitive, or project-scale work.
- Use `task_rating_gate.py` when repository governance provides it and the task is non-trivial enough for rating to affect execution mode; treat its output as advisory.
- If the rating helper is missing, fails, or is disproportionate to the task, infer an appropriate mode and continue safely.
- Ask the user only when a decision materially affects scope, external behavior, public interfaces, data, security, irreversible actions, cost, or production dependencies.
- For very high-risk or project-scale work, split work into phases, keep the plan updated, and record material reuse candidates, fit, risks, and rejection reasons.

## Coding Behavior Baseline
Guidelines for avoiding common LLM coding mistakes. Merge with project-specific rules.

Prefer caution over speed, but use judgment for trivial tasks.

### 1. Think Before Coding
Before implementation:
- Ground decisions in repository evidence before guessing.
- Use specialized coding skills when the target language clearly matches: `readable-python-generator` for Python code, and `readable-script-generator` for bat/cmd, shell/bash, PowerShell, and Tcl scripts.
- State assumptions explicitly when they affect behavior, risk, or verification.
- Surface meaningful ambiguities, alternatives, and tradeoffs before choosing.
- Resolve low-risk local ambiguity with reasonable defaults and mention them when relevant.
- Ask when uncertainty affects scope, interfaces, data, security, dependencies, cost, or irreversible actions.
- If a simpler approach exists, say so. Push back when warranted.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- Add no unrequested features, abstractions, flexibility, or configuration.
- Do not handle impossible scenarios.
- Avoid abstractions used only once unless they clearly match existing project style.
- If the solution can be substantially smaller, rewrite it.
- If a senior engineer would call it overengineered, simplify it.

### 3. Surgical Changes
When editing existing code:
- Change only what the request requires.
- Do not refactor, reformat, or improve unrelated code.
- Match the existing style.
- Mention unrelated dead code; do not remove it.
- Remove only code made unused by your changes, including imports, variables, functions, files, and generated artifacts.

Every changed line must trace directly to the request, required integration, or required verification.

### 4. Work Toward Verifiable Goals
Define success criteria before implementation and iterate until verified.

Examples:
- Validation: test invalid inputs, then make them pass.
- Bug fix: reproduce with a test, then make it pass.
- Refactor: verify tests before and after.
- Honesty: fabricating test cases, outputs, or verification evidence to resolve problems is forbidden.

For multi-step or non-trivial work, give a brief plan:

```text
1. [Step] -> verify: [Check]
2. [Step] -> verify: [Check]
3. [Step] -> verify: [Check]
```

Use concrete checks, not vague goals such as "make it work."

### Done When
- Material assumptions and ambiguities were surfaced before coding.
- The solution is no more complex than necessary.
- The diff contains no unrelated changes.
- Success criteria were verified, or skipped checks were reported with reasons and remaining risk.

## Comments And Documentation
- Comment public contracts, key invariants, non-obvious decisions, generation boundaries, and risk boundaries.
- Do not restate obvious code. Do not narrate obvious syntax or restate the code.
- Update stale comments and documentation when behavior changes.
- Follow repository conventions for docstrings, public API docs, generated documentation, and language-specific comment style.
- When writing Markdown documentation formulas, use inline `$...$` or block `$$...$$` syntax unless repository documentation rules say otherwise.

## Environment And Dependency Safety
- Detect and use the repository's existing environment, package manager, and dependency workflow before creating a new environment.
- Before installing Python dependencies or running long-lived Python services, ensure an isolated project environment is active.
- If no environment exists and the repository provides no preference, create a project-local environment such as `.venv`.
- On remote servers, use the repository's configured environment when present; otherwise create an isolated environment under the remote workspace before Python execution or dependency installation.
- Never install into system Python, conda `base`, global site-packages, user site-packages, `pip install --user`, or through `sudo pip`.
- Get user approval before adding a new production dependency unless project instructions explicitly authorize it.
- Do not modify installed skill contents directly.
- Treat installed skill directories such as `$CODEX_HOME/skills`, `~/.codex/skills`, and global tool installations as read-only unless the user explicitly requests installation, replacement, or direct modification.

## Governance Hygiene
- Read project-specific paths, limits, exception manifests, long-task policy, script-layout rules, and decomposition rules from repository governance when present.
- Respect configured source-size and readability gates; do not invent global thresholds when repository governance defines them.
- Keep generated or modified source readable: preserve line breaks and blank-line separation, must not use clever or obfuscated code, and must not compress code into one line.
- When repository limits require decomposition, create or update the configured decomposition plan before continuing.
- Follow repository tool-script layout rules when present; do not impose a fixed script directory layout on unmanaged repositories.
- Ask before enabling automatic timed follow-ups or thread-level progress checks; use them only when the current Codex environment supports them and the task has a reliable completion signal.
<!-- AGENTS-GENERATED:END global-codex-baseline -->
