<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md">中文</a>
</p>

<p align="center">
  <img src="docs/assets/hero.svg" alt="AGENTS.md Generator" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v2.0.8-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent-skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  A Codex-ready skill for generating, repairing, and verifying AGENTS.md governance from repository facts.
</p>

<p align="center">
  Latest release: <strong>v2.0.8</strong> · Released on <strong>2026-08-09</strong>
</p>

AGENTS.md Generator helps coding agents produce instruction files that stay grounded in the real repository instead of drifting into guessed policy. It combines trigger metadata, grouped design interviews, deterministic Python scripts, docs-governance helpers, directory-governance gates, and verification checks so an agent can move from repository facts to trustworthy `AGENTS.md` output.

This repository is primarily an **agent skill package**. The Python scripts are the deterministic execution layer; the main product is the skill workflow an agent can load and follow.

## What It Solves

Handwritten agent rule files become stale quickly. Commands stop matching the repo, path references drift, and local operating rules get duplicated in inconsistent places. AGENTS.md Generator gives the agent a stricter path:

- inspect the repository first
- ask only for missing human policy
- keep root and scoped `AGENTS.md` files small and focused
- route docs governance, directory governance, and release governance through scripts
- verify that metadata, paths, contracts, and reply-language rules are actually consistent

## Core Capabilities

- Root and scoped `AGENTS.md` generation for Codex-style coding agents.
- Grouped design interviews with resumable state and explicit confirmation gates.
- Controlled takeover flow for older workspaces with version-mismatched root `AGENTS.md`.
- Repository fact extraction for commands, docs, CI hints, scopes, and governance signals.
- Strong-control profiles for skill and engineering projects.
- Docs governance for handoff, memory, development, install, and git-manager records.
- Progressive-disclosure command registry with JSON sources, a SQLite FTS index, and a read-only query CLI.
- Directory-governance review and structure gates through `scripts/python/dirs/manage_dirs.py`.
- Compatibility shim generation for `CLAUDE.md` and `GEMINI.md` when requested.
- Verification, audit, automated review governance, skill-effectiveness evals, and aggregate confidence checks for release readiness.

## What's New In v2.0.8

v2.0.8 synchronizes the public skill payload with the latest governed runtime. It keeps the existing public entrypoints, but makes the global instruction baseline, test-agent boundary, remote work-folder contract, and release evidence more explicit and fail-closed.

### Global v4 governance baseline

- Updates the generated global baseline to v4: every plan now freezes the goal, success criteria, in-scope and out-of-scope boundaries, and formal plans must name inputs, outputs, affected files or interfaces, preconditions, failure handling, verification, and stop conditions.
- Removes the assumption that read-only, design, write, or governance-high-risk modes authorize extra agents. Non-testing agents require a proactive user request that names their purpose; executable test surfaces use exactly one isolated `tester_worker` that owns `tests/**`.
- Adds the single-task authorization receipt contract so the skill, root `AGENTS.md`, and CLI reuse one authorization for the same target and scope, while changes to target, scope, or material risk require renewed confirmation.

### Workspace and remote-operation boundaries

- Generated roots now carry a state-aware, fail-closed remote work-folder contract. It resolves the configured route and verified workspace before allowing remote work and keeps deployment, runtime, backup, and archive lifecycle details in the planned structure record.
- Official codebase-memory indexing, refresh, rebuild, recovery, and the configured cache/root artifact are treated as part of the governed project boundary; other external writes remain prohibited until the exact action is explicitly requested and confirmed.
- The Python source-name rule now exempts `__main__.py` alongside `__init__.py`, preserving executable module entrypoints without weakening the no-digit functional-name rule for other modules.

### New evidence and rendering helpers

- Adds `scripts/python/common/codebase_memory_health.py` for live-versus-disk codebase-memory health checks and `scripts/python/common/tester_worker_profile.py` for the canonical tester contract.
- Adds `scripts/python/render/render_contract_templates.py` and `scripts/python/verify/test_evidence.py`, plus decomposition-plan references for the new responsibility boundaries. These helpers make contract rendering and test-evidence provenance inspectable instead of relying on prose-only claims.
- The managed payload comparison against v2.0.3 contains 13 added files, 57 changed files, 84 unchanged files, and no removals in the synchronized public payload directories. The public repository shell is preserved and the final release ZIP includes both bilingual READMEs and `docs/`.

### Compatibility, migration, validation, and limits

- Existing public CLI entrypoints remain supported. Existing generated roots should be refreshed with v2.0.8 when they need the v4 baseline, the explicit tester contract, or the state-aware remote work-folder rules; internal helper paths remain implementation details.
- The v2.0.8 archive receipt declares strong pre/post release validation and 153 included skill files. This public checkout continues to exclude repo-local tests, smoke runs, reports, caches, authentication material, credentials, private keys, and machine-specific absolute paths from public release assets.
- This release does not claim a real remote-server or installed-skill run. Consumers who need those boundaries must run the documented opt-in remote or installation checks in their own environment.

## What's New In v2.0.3

v2.0.3 tightens three boundaries that were still coupled in the first public v2 release: installed-skill identity versus runtime capability, editable registry sources versus their generated index, and the current workspace versus external filesystem targets. The release keeps the existing public CLI surface while making failures more precise and generated governance harder to weaken accidentally.

### RemoteSSH Capability Discovery

- Treats an installed `erie-remote-ssh` skill as present when its directory and root `SKILL.md` exist. CLI and settings discovery are reported as separate capabilities instead of changing the installation result.
- Prefers the current `scripts/python/runtime/remote_ssh.py` entry point and keeps `scripts/remote_ssh.py` as a compatibility fallback for older installed releases.
- Reports an installed skill with no supported CLI as a runtime-capability error with exit code 127, rather than incorrectly directing the user to reinstall it.

### Self-Describing Registry Layout

- Moves registry metadata, governance configuration, and JSON Schemas into `metadata/`, `governance/`, and `schemas/`. The `config/registry/` root now contains only the generated `registry.sqlite3` file plus responsibility-specific subdirectories.
- Discovers exactly one valid manifest below the registry root and rejects missing, duplicate, root-level, or boundary-escaping declarations instead of relying on a hard-coded `manifest.json` path.
- Uses manifest-defined document roles and schema paths for optional document-governance initialization. Document registration remains opt-in and no registry state is created merely because the infrastructure is available.

### Managed Workspace Boundary

- Every generated managed root now contains exactly one `Workspace boundary` rule. Normal modifications stay inside the current work folder or a verified remote-server work folder.
- External reads must be necessary and side-effect free. External modifications require the normalized target, action, scope, risks, alternatives, and recovery limits to be disclosed, followed by two separate confirmations: one for the exception in principle and one for the exact action.
- Verification rejects missing, duplicated, weakened, blanket-approved, urgent, or first-confirmation-only variants. A changed target or scope invalidates both confirmations.

### Compatibility, Migration, And Validation

- Existing public command entry points remain supported. Integrations that read the old flat registry JSON paths must switch to the manifest and role-based layout or use the registry helpers.
- Managed roots produced before v2.0.3 should be refreshed with the installed v2.0.3 generator so the new workspace boundary is rendered and verified.
- The public mirror validates the final package with quick skill validation, cache-free Python AST parsing, registry consistency checks, focused RemoteSSH/registry/workspace-boundary scenarios, release-content policy checks, and a sanitized package inspection. Canonical source-repository unit tests are not stored or rerun in this public mirror, and their upstream receipt is not presented as a local test run.
- The downloadable asset excludes tests, smoke runs, reports, caches, nested `dist/`, local authentication material, credentials, private keys, and machine-specific absolute paths. Approved attribution stays visible in the repository, while contact email values in the downloadable asset are replaced with `<REDACTED_EMAIL>`.

## What's New In v2.0.1

v2.0.1 is the first public v2 release. It is tuned for using this skill with [GPT-5.6 Sol in Codex](https://developers.openai.com/api/docs/models/gpt-5.6-sol): keep the always-loaded instruction surface compact, move detailed operational knowledge behind deterministic lookups, and make execution evidence easier to verify. These are architecture-level efficiency improvements; the project does not claim an unmeasured wall-clock or token-cost percentage.

### Smaller Agent Context, Richer On-Demand Runtime

- Compresses `SKILL.md` from 44,796 bytes and 202 lines to 12,683 bytes and 119 lines, a 71.7% byte reduction in the primary agent-facing instruction file.
- Moves detailed command syntax into `config/registry/`, backed by versioned JSON sources, schemas, a manifest, and a SQLite FTS index. `query_registry.py ask` retrieves only the instructions needed for the current task and never executes returned commands.
- Keeps the reduction honest: deterministic Python modules grow from 89 to 99 files because implementation and validation detail moved out of the prompt-facing document instead of being discarded.

### Runtime And Governance Architecture

- Replaces 26 legacy underscore-prefixed internal modules and decomposition notes with public, responsibility-focused modules for project discovery, profile assembly, persistent memory, release policy, rendering, routing contracts, and eval policy/release cases.
- Adds first-class codebase-memory integration with explicit full-index, architecture-analysis, persistence, and live-versus-disk parity checks before governed writes.
- Adds persistent memory storage and bounded retrieval views, while keeping handoff and long-term memory contracts explicit and continuing to reject raw machine-local paths.
- Adds optional document registration with catalog, knowledge, interface, duplicate-review, and migration records. It remains opt-in: no registry state is created unless the user explicitly requests document registration or migration.
- Strengthens source governance, content-density checks, semantic review evidence, release packaging, sanitization, provenance receipts, and command/root/routing contract evaluation.

### Compatibility And Migration

- Existing public CLI entry points remain the supported interface; internal module paths are not a compatibility contract. Compatibility wrappers route old public entry points to the new focused modules where applicable.
- Replace `source_file_limits.max_lines` and `source_governance.max_lines` with byte-based `max_bytes` policies; v2 rejects the retired line-count fields.
- Replace deprecated confidence-gate switches `--skip-missing-eval-runner` and `--require-eval-runner` with `--eval-runner-policy optional` and `--eval-runner-policy required`.
- Evolution and experience subsystems remain retired. Compatibility shims for `CLAUDE.md` and `GEMINI.md` remain explicit opt-in operations.

### Release Safety

- The v1.4.6-to-v2.0.1 managed payload comparison contains 50 new files, 52 changed files, 26 retired paths, and 38 unchanged files before the public release receipt is regenerated.
- Installable assets continue to exclude repo-local tests, smoke runs, reports, caches, nested `dist/`, local authentication files, credentials, private keys, and machine-specific absolute paths.
- Explicitly approved author/contact email remains public for attribution; unapproved contact data and other sensitive material are still blocked or redacted.

## Skill Architecture

<p align="center">
  <img src="docs/assets/architecture.svg" alt="AGENTS.md Generator skill architecture" width="100%">
</p>

## Workflow

<p align="center">
  <img src="docs/assets/workflow.svg" alt="AGENTS.md Generator workflow" width="100%">
</p>

## Typical Paths

1. Healthy workspace root:
   Run `inspect_project.py`, confirm the root `AGENTS.md` is healthy, and report pass status for workspace-trigger phrases related to planning or preparation.
2. Explicit AGENTS update:
   Start the grouped interview, collect the missing policy, render root/scoped files, then verify.
3. Version-mismatched old workspace:
   Enter takeover mode, keep identity questions minimal, still complete the structured directory contract, then repair governance.
4. Strong-control release flow:
   Run `quick_validate.py`, `audit_skill.py`, `verify_agents.py`, `evaluate_skill.py`, and the review/eval gates before packaging or installation.

## Repository Map

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Agent-facing routing, workflow, constraints, and verification rules. |
| `agents/openai.yaml` | Skill metadata used by the host UI. |
| `scripts/python/` | Deterministic inspection, interview, rendering, docs-governance, directory-governance, release-installation, verification, audit, and evaluation helpers. |
| `config/registry/` | Responsibility-specific JSON sources and schemas under subdirectories, plus the generated SQLite FTS index at the registry root. |
| `assets/templates/` | Bundled root and scoped `AGENTS.md` templates used by the current release flow. |
| `evals/` | Repo-local skill-effectiveness cases and release-safe evaluation data used by the governance tooling. |
| `references/` | Script guide, review checklist, question bank, capability notes, and AGENTS guidance. |
| `docs/assets/` | Hero, workflow, and architecture diagrams used in this README pair. |

## Install

Tell your AI assistant: install https://github.com/Eriemon/agents-md-generator

Manual setup:

```powershell
git clone https://github.com/Eriemon/agents-md-generator.git
cd .\agents-md-generator
python -m pip install -e .
```

If you use Codex or another skill-aware host, place this repository in the host's skill search path and restart the host after installation.

## Quick Start

Read-only inspection and scoping:

```powershell
python scripts/python/detect/inspect_project.py <project>
python scripts/python/detect/detect_scopes.py <project>
python scripts/python/detect/extract_commands.py <project>
python scripts/python/detect/extract_context.py <project>
```

Grouped design interview and profile write:

```powershell
python scripts/python/design/collect_design_profile.py <project> --start
python scripts/python/design/collect_design_profile.py <project> --answer-file partial.json
python scripts/python/design/collect_design_profile.py <project> --answers answers.json --write
```

Render and verify:

```powershell
python scripts/python/render/render_agents.py <project> --profile <project>/.agents/agents-control.json
python scripts/python/verify/verify_agents.py <project>
python scripts/python/docs/manage_docs.py verify <project>
```

Query detailed operational guidance on demand:

```powershell
python scripts/python/registry/query_registry.py ask "verify" --limit 3 --json
```

Use a compact command or policy keyword for FTS queries; add `--category` or `--kind` to narrow results instead of combining many unrelated terms.

Codex token usage review:

```powershell
python scripts/python/detect/codex_token_usage_review.py --hours 48
python scripts/python/detect/codex_token_usage_review.py --hours 48 --json
python scripts/python/detect/codex_token_usage_review.py --hours 48 --verbose
```

Skill-release validation:

```powershell
python scripts/python/verify/quick_validate.py .
python scripts/python/verify/run_skill_evals.py evals/evals.json
python scripts/python/verify/evaluate_skill.py . <project>
```

The self-audit contract applies to the installable runtime before public repository documents are composed, because the canonical runtime intentionally keeps `SKILL.md` as its only root explanation:

```powershell
python scripts/python/verify/audit_skill.py <runtime-stage>
```

After `README.md`, `README-CN.md`, `LICENSE`, and `CITATION.cff` are added, validate the final ZIP with the release-package inspection and release gates rather than auditing the public mirror as the canonical runtime.

Source-repository note:

- This repository no longer keeps repo-local `tests/` under version control.
- Installable release policy rejects `tests/`, `smoke*`, `reports/`, and cache artifacts from packaged outputs.

Advanced governance-sensitive release checks:

```powershell
python scripts/python/verify/review_governance.py <project> --base <sha> --head HEAD --skill-dir . --mode all
python scripts/python/verify/run_confidence_gate.py <project> --review-base <sha> --external-skill-dir <healthy-skill-dir>
```

Compatibility shims stay opt-in:

```powershell
python scripts/python/render/create_agent_shims.py <project>
```

## Scope

AGENTS.md Generator is intentionally narrow:

- It creates and reviews agent-governance files, not general project documentation.
- It treats discovered commands as candidates until they are actually executed.
- It preserves handwritten content outside managed generated blocks.
- It keeps maintainability and script-governance detail in config-backed policy instead of repeating it everywhere in prose.
- External projects should call the installed runtime, for example `python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py ...`, rather than copying this skill's scripts into project-local tool folders.
- It should not emit secrets, private infrastructure details, generated caches, or machine-specific absolute paths.

## Affiliation

Jiyuan Liu and He Li are with the School of Electronic Science and Engineering, Southeast University.
They are affiliated with the Heterogeneous Intelligence and Quantum Computing Laboratory (HIQC), which works on heterogeneous intelligence, quantum computing, and related computing systems research.

## Contact

For questions, collaboration, or academic use, contact: `<REDACTED_EMAIL>`.

## Citation

If this skill helps your research, teaching, or engineering workflow, please cite it. The canonical citation metadata is maintained in [CITATION.cff](CITATION.cff).

```bibtex
@software{liu_2026_agents_md_generator,
  author       = {Jiyuan Liu and He Li},
  title        = {{AGENTS.md Generator}: An Agent Skill for Coding-Agent Context Files},
  year         = {2026},
  version      = {2.0.8},
  date         = {2026-08-09},
  url          = {https://github.com/Eriemon/agents-md-generator},
  license      = {Apache-2.0},
  note         = {Agent skill package for generating and verifying AGENTS.md files}
}
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
