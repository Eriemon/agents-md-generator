<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md">中文</a>
</p>

<p align="center">
  <img src="assets/readme/hero.png" alt="AGENTS.md Generator" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v2.1.1-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent--skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  A Codex-ready skill for turning repository reality into clear, scoped coding-agent guidance.
</p>

<p align="center">
  Latest release: <strong>v2.1.1</strong> · Released on <strong>2026-08-11</strong>
</p>

AGENTS.md Generator helps maintainers shape the rules that coding agents actually need: what exists, what matters, where a rule applies, and how work continues after a handoff. It combines repository discovery, grouped design conversations, deterministic renderers, directory governance, and release tooling in one skill package.

## Why maintainers use it

- Turn an unfamiliar repository into a short, navigable context layer.
- Keep root and scoped rules aligned with the directories they govern.
- Carry the same intent through local development, validation, packaging, and installation.
- Give a new agent a clear way to resume without reopening every design decision.

## 01 — Start from repository facts

The skill begins with the tree that is really present. It identifies project shape, languages, command surfaces, ownership boundaries, and existing guidance before asking for decisions. That keeps the first draft grounded in the repository instead of an imagined template.

![Project facts: repository tree, knowledge graph, language mix, command surface, and scope candidates](assets/readme/project-facts.png)

## 02 — Align policy before writing

Grouped design prompts turn ambiguous preferences into explicit choices about scope, inheritance, naming, remote routes, and release boundaries. Once the profile is aligned, managed blocks can stay compact while human notes remain yours.

![Design profile: policy answers, key questions, scope boundary, and decision matrix](assets/readme/design-profile.png)

## 03 — Carry the workflow through release

Render only the blocks owned by the generator, preserve the rest of each file, and use the same package contract for a local skill checkout, a versioned dist directory, and an existing GitHub mirror. The result is a workflow that can be resumed, reviewed, installed, and maintained without changing its meaning at every step.

![Rule rendering: inherited and scoped AGENTS.md files with managed blocks and focused diffs](assets/readme/rule-rendering.png)

## Get started

Run the design and validation flow from the repository while developing the skill:

```powershell
python skills/agents-md-generator/scripts/python/design/collect_design_profile.py --project .
python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator
python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator
```

Install only from a versioned package directory:

```powershell
python skills/agents-md-generator/scripts/python/release/install_skill.py `
  dist/agents-md-generator-v2.1.1 --target skip
```

## Develop locally, mirror deliberately

The source skill directory is the only place where README and workflow changes are authored. A release package is created from that source, and an existing `github/` checkout receives only the completed package. Local development, installation, and remote publication stay separate decisions.

```powershell
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  status --project . --skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  check --project . --skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  mirror --project . --skill-dir skills/agents-md-generator `
  --release-dir dist/agents-md-generator-v2.1.1
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  verify --project . --skill-dir skills/agents-md-generator `
  --release-dir dist/agents-md-generator-v2.1.1
```

The mirror keeps `.git`, replaces the checkout content with the selected dist package, compares the resulting files, and never creates a remote repository or runs `commit`, `push`, `tag`, or GitHub Release actions for you.

## What ships in the skill

| Capability | Maintainer outcome |
| --- | --- |
| Repository discovery | A compact map of project shape and ownership boundaries |
| Design alignment | Scoped rules that match the way directories are actually used |
| Deterministic rendering | Managed blocks that can be regenerated without erasing human notes |
| Directory governance | Clear gates for roots, nested scopes, and handoff state |
| Release lifecycle | A versioned package that can be installed or mirrored consistently |

## Authors and citation

Jiyuan Liu and He Li are with the School of Electronic Science and Engineering, Southeast University (东南大学). The work is developed with the Heterogeneous Intelligence and Quantum Computing Laboratory (HIQC).

If you build on this skill, cite the package through [CITATION.cff](CITATION.cff):

```bibtex
@software{liu_2026_agents_md_generator,
  author = {Jiyuan Liu and He Li},
  title = {{AGENTS.md Generator}: An Agent Skill for Coding-Agent Context Files},
  year = {2026},
  version = {2.1.1},
  date = {2026-08-11},
  url = {https://github.com/Eriemon/agents-md-generator},
  license = {Apache-2.0}
}
```

Released under the Apache License 2.0. See [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CITATION.cff](CITATION.cff).
