<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md">Chinese</a>
</p>

<p align="center">
  <img src="assets/readme/hero.png" alt="AGENTS.md Generator user journey" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v3.1.0-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent--skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  A multi-harness skill that turns a real repository into clear, scoped instructions for an AI coding assistant.
</p>

<p align="center">
  Release date: 2026-08-24
</p>

## What it does

Use this skill when an AI assistant needs to understand a repository before changing it. It discovers the folders, languages, tools, and existing guidance, then helps you shape concise root and folder-level `AGENTS.md` instructions. The result is a repository context layer that is easier for an AI assistant to follow and for a human to review.

![Project facts: the assistant maps folders, languages, tools, and scope](assets/readme/project-facts.png)

## Install

Ask your AI assistant to install the skill from https://github.com/Eriemon/agents-md-generator.

The assistant should show the source it found, the files it will add, and the target skill name before writing anything. You can stop before installation if the preview does not match your intent.

For manual installation commands, see the Skill-development bundle section below.

## Before you start

- Open the repository you want the assistant to understand.
- Make sure the assistant can read the repository and its existing guidance files.
- Decide which folders should have shared instructions and which folders need their own rules.
- Keep any private credentials or generated build output outside the material you ask the assistant to inspect.

## Skill-development bundle

The package includes `assets/installer/install.ps1`, `install.sh`, and `install.bat`. It supports the Codex, Claude, Gemini, and DeepSeek harnesses. From the root of an extracted versioned release package, you can run an installer manually:

```powershell
.\assets\installer\install.ps1
```

```bat
cmd /c call .\assets\installer\install.bat
```

```bash
./assets/installer/install.sh
```

Append `-DryRun` (PowerShell/BAT) or `--dry-run` (shell) to preview the installation without writing files. The entrypoints consume a hash-bound projection generated from `config/agent-platforms.json`, guide the user in English, and validate project kind, destination paths, containment, catalog/projection hashes, and replacement confirmation before writing. The bundle is Skill-development-only; Engineering projects are rejected before any write, and BAT is only a PowerShell forwarding entrypoint.

```powershell
.\assets\installer\install.ps1 -DryRun
```

```bash
./assets/installer/install.sh --dry-run
```

## How to use

After installation, ask your AI assistant to use `AGENTS.md Generator` for the repository in front of it. A useful request is: “Inspect this repository, summarize the facts you found, then propose scoped `AGENTS.md` guidance for my review.”

![Design profile: the assistant turns your answers into scoped choices](assets/readme/design-profile.png)

## Preview and confirm

Review the proposed folders, rule scope, inheritance, and wording. Ask for changes while the proposal is still a preview. Confirm only after the instructions describe the repository you actually want to maintain.

![Rule rendering: approved guidance appears at the right repository scopes](assets/readme/rule-rendering.png)

## What you get

- A concise root `AGENTS.md` for shared repository instructions.
- Optional folder-level `AGENTS.md` files for narrower rules.
- Managed sections that an AI assistant can refresh without erasing your own notes.
- A readable summary of the decisions and files the assistant changed.

![Delivery view: the assistant presents the final files for handoff](assets/readme/evidence-guard.png)

## Authors and citation

Jiyuan Liu and He Li are with the School of Electronic Science and Engineering, Southeast University. The work is developed with the Heterogeneous Intelligence and Quantum Computing Laboratory (HIQC).

If you build on this skill, cite the package through [CITATION.cff](CITATION.cff):

```bibtex
@software{liu_2026_agents_md_generator,
  author = {Jiyuan Liu and He Li},
  title = {{AGENTS.md Generator}: An Agent Skill for Coding-Agent Context Files},
  year = {2026},
  version = {3.0.1},
  date = {2026-08-24},
  url = {https://github.com/Eriemon/agents-md-generator},
  license = {Apache-2.0}
}
```

Released under the Apache License 2.0. See [LICENSE](LICENSE), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CITATION.cff](CITATION.cff).
