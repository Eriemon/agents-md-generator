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
  <img alt="Version" src="https://img.shields.io/badge/version-v0.4.0-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent-skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  A Codex-ready agent skill for generating and verifying AGENTS.md files for coding agents.
</p>

AGENTS.md Generator turns an AI coding agent into a more careful repository-onboarding assistant. It provides trigger metadata, operational instructions, templates, deterministic discovery scripts, design-profile prompts, and validation gates for moving from repository facts to verified `AGENTS.md` guidance.

This repository is primarily an **agent skill package**. The Python scripts are the deterministic execution layer, but the main interface is the skill surface an agent can load and follow.

## Why It Exists

Agent instruction files decay quickly when they are written from memory. AGENTS.md Generator makes the agent inspect the repository first, ask only for missing human policy, render a focused root or scoped `AGENTS.md`, and verify references before claiming the draft is ready.

Use it when an agent needs to work on:

- Root or scoped `AGENTS.md` files for Codex and other coding agents.
- Repository onboarding rules, command discovery, and local policy capture.
- Strong-control profiles for skill or engineering projects.
- CLAUDE.md and GEMINI.md compatibility shims when requested.
- Freshness checks, command verification, and review of stale agent docs.

## Skill Architecture

<p align="center">
  <img src="docs/assets/architecture.svg" alt="AGENTS.md Generator skill architecture" width="100%">
</p>

## Workflow

<p align="center">
  <img src="docs/assets/workflow.svg" alt="AGENTS.md Generator workflow" width="100%">
</p>

## Repository Map

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Agent-facing routing, workflow, constraints, and verification rules. |
| `agents/openai.yaml` | UI metadata for skill lists and invocation chips. |
| `scripts/` | Deterministic project inspection, profile collection, rendering, verification, audit, and shim helpers. |
| `assets/templates/` | Root and scoped `AGENTS.md` templates used by the renderer. |
| `references/` | Script guide, review checklist, question bank, coverage notes, and AGENTS.md guidance. |

## Quick Start

Place this repository in a Codex skill search path to use it as an agent skill. For local checks and repository analysis:

```powershell
python scripts/inspect_project.py <project>
python scripts/detect_scopes.py <project>
python scripts/collect_design_profile.py <project>
python scripts/extract_commands.py <project>
python scripts/extract_context.py <project>
python scripts/render_agents.py <project>
python scripts/verify_agents.py <project>
python scripts/audit_skill.py .
```

Strong-control generation uses a design profile. Start with the design interview, save answers to JSON, then render with the generated profile:

```powershell
python scripts/collect_design_profile.py <project> --kind skill
python scripts/collect_design_profile.py <project> --answers answers.json --write
python scripts/render_agents.py <project> --profile <project>/.agents/agents-control.json
python scripts/verify_agents.py <project>
```

Compatibility shims are opt-in:

```powershell
python scripts/create_agent_shims.py <project>
```

## Scope

AGENTS.md Generator is intentionally narrow:

- It creates and reviews AI coding-agent context files, not general project documentation.
- It treats commands discovered from files as candidates until they are actually run.
- It preserves hand-written content outside managed generated blocks.
- It does not fabricate repository policies, owners, CI behavior, branch names, or security rules.
- Local secrets, private infrastructure, generated caches, and machine-specific paths should stay out of generated guidance.

## Contact

For questions, collaboration, or academic use, contact: [erie@seu.edu.cn](mailto:erie@seu.edu.cn).

## Citation

If this skill helps your research, teaching, or engineering workflow, please cite it. The canonical citation metadata is maintained in [CITATION.cff](CITATION.cff).

```bibtex
@software{liu_2026_agents_md_generator,
  author       = {Jiyuan Liu},
  title        = {{AGENTS.md Generator}: An Agent Skill for Coding-Agent Context Files},
  year         = {2026},
  version      = {0.4.0},
  date         = {2026-05-11},
  url          = {https://github.com/Eriemon/agents-md-generator},
  license      = {Apache-2.0},
  note         = {Agent skill package for generating and verifying AGENTS.md files}
}
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
