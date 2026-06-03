# AGENTS.md Question Bank

Ask only when repository inspection cannot answer the question.

## Table of Contents

- [Mandatory Design Interview](#mandatory-design-interview)
- [Trigger And Docs Layout Questions](#trigger-and-docs-layout-questions)
- [Human Policy](#human-policy)
- [Engineering Rule Policy](#engineering-rule-policy)
- [Verification Policy](#verification-policy)
- [Workflow Policy](#workflow-policy)
- [Domain Context](#domain-context)

## Mandatory Design Interview

Start grouped interviews with `python scripts/collect_design_profile.py <project> --start`. Resume unfinished chains with `--resume`, answer only the current group with `--answer-file partial.json`, and never silently skip an unfinished `.agents/design-interview-state.json` chain. After each group, show `review_summary` and ask the yes/no `confirmation_question`. If the user says no, keep the interview on that same group until it is re-confirmed. Save the final aligned answers to JSON only after the last `alignment_confirmed=true`, then use `collect_design_profile.py --answers <answers.json> --write`.

| ID | Branch | Ask |
|----|--------|-----|
| 1 | all | Confirm whether this is skill development or engineering development. Skill development goes to 2; engineering development goes to 11. |
| 32 | all | What is the default conversation language that must be written into the control profile and enforced in the root `AGENTS.md`? |
| 45 | all | Should this work folder enable remote servers? If yes, complete install/configure/route-mapping/check/workspace-check gates, build one or more task routes with `task_name`, `primary_server_id`, and optional `fallback_server_ids`, and if a route omits explicit tasks, fall back to the selected primary server `functions`. |
| 2 | skill | What does this skill do? |
| 3 | skill | Why develop this skill? |
| 4 | skill | Are there reference materials? They are temporary inputs and must be manually deleted after development. |
| 5 | skill | Who is the target audience: research, commercial, personal, or other? |
| 6 | skill | What is the skill name? |
| 7 | skill | Are there design cautions or prior experience to preserve? |
| 8 | skill | Should this skill use local git management without remote submission? |
| 9 | skill | Is the skill folder the `master` branch and `dist/` the release branch area? |
| 10 | skill | Should release folders be named `<skill-name>-vx.x.x` under `dist/` and zipped? |
| 22 | skill | What user requests, file types, project states, or tasks should trigger this skill? |
| 23 | skill | Which Skill design patterns does it use: Tool Wrapper, Generator, Reviewer, Inversion, Pipeline, or another pattern? |
| 24 | skill | What belongs in `SKILL.md`, `references/`, `scripts/`, `assets/`, and `agents/openai.yaml`? |
| 25 | skill | How will the skill enforce progressive disclosure and keep `SKILL.md` concise? |
| 26 | skill | Which validation gates are mandatory before claiming the skill is ready? |
| 27 | skill | When is forward-testing required, and how should it be performed? |
| 28 | skill | What are the detailed development requirements? |
| 29 | skill | What is the expected result after development is complete? |
| 30 | skill | How should the completed skill be validated? |
| 31 | skill | What validation granularity is required before final acceptance? |
| 42 | all | What is the governed local directory structure for source, tests, dist, docs, and supporting files? |
| 43 | all | What is the governed remote directory structure or the explicit statement that no remote structure is configured? |
| 44 | all | What are the fixed rules for where new features, scripts, docs, tests, and release artifacts must go? |
| 46 | all | If the remote workspace needs a conda prefix environment, where must it live? Recommended: `.conda/<env-name>/`. If remote is not configured, store `disabled`. |
| 47 | all | If the remote workspace produces runtime artifacts, what is the active run directory template? Recommended: `runs/<run-id>/`. If remote is not configured, store `disabled`. |
| 48 | all | If the remote workspace archives verified runtime artifacts, what is the backup directory template? Recommended: `backups/runs/<run-id>/`. If remote is not configured, store `disabled`. |
| 49 | all | When must remote runtime artifacts leave the active run directory and move into backups? Recommended: `after required verification passes`. If remote is not configured, store `disabled`. |
| 11 | engineering | What does this project do? |
| 12 | engineering | Why build this project? |
| 13 | engineering | What are the expected outcome and goals? |
| 14 | engineering | Is development on a remote server, WSL, or local machine? |
| 15 | engineering | Is there experience or precedent to borrow? |
| 16 | engineering | What is the project name? |
| 17 | engineering | Should this project use local git management without remote submission? |
| 18 | engineering | Is the project folder the `master` branch and `dist/` the release branch area? |
| 19 | engineering | Should release folders be named `<project-name>-vx.x.x` under `dist/` and zipped? |
| 33 | engineering | What are the detailed engineering development requirements? |
| 34 | engineering | What are the engineering resource boundaries for source, scripts, tests, docs, deployment, and release artifacts? |
| 35 | engineering | How should the completed engineering project be validated? |
| 36 | engineering | What validation granularity is required before final acceptance? |
| 37 | engineering | When is forward-testing required, and how should it be performed? |
| 38 | engineering | Which one primary engineering rule set should shape this project, or should no book-derived rule set be active? |
| 39 | engineering | Should the engineering rule set use `none`, `mini`, or `nano` mode? |
| 40 | engineering | Should the engineering rule set be `project-baseline`, `scoped`, or `on-demand`? |
| 41 | engineering | What local engineering-rule notes or tradeoffs should be preserved? |
| 20 | all | Does the current working folder already contain a project or skill? |
| 21 | all | Confirm that the local, remote, and feature-addition directory rules are fixed strongly enough to become the directory contract. |

## Trigger And Docs Layout Questions

| Need | Ask |
|------|-----|
| Root AGENTS.md missing | If this work folder already has landed content, do not launch the full design interview. Enter takeover mode, confirm the minimal identity fields first, then complete the full structured directory contract before forced local directory takeover and governance scaffolding. |
| Root AGENTS.md version abnormal | If the current work folder root `AGENTS.md` is version-abnormal and the folder already has landed content, do not enter the full design interview. Enter takeover mode, keep identity questions minimal, but still require the full structured directory contract before continuing. |
| Existing content but no AGENTS | This work folder already has landed content but no root `AGENTS.md`; should I first read the exact-cwd Codex sessions, generate history experience, and then write the latest current experience files before normal AGENTS generation continues? |
| User says 计划/规划/准备 | Because this is a current workspace/current repository/current work folder planning request, should I first inspect the root `AGENTS.md`, report pass-only when it is healthy, and ask before entering AGENTS design or restructuring when it is abnormal? |
| Branch governance abnormal | The current work folder branch state does not match the configured branch model; should I enter branch cleanup or release governance before normal generation continues? |
| Existing docs layout ambiguous | Existing `docs/` content may conflict with AGENTS.md governance. Is it acceptable to add governance subdirectories under the existing `docs/` folder? |
| Structure governance abnormal | Normal design flow asks whether to normalize the structure first. Takeover mode does not ask again; it should proceed with forced local takeover using `manage_dirs.py takeover-fix`. |

## Human Policy

| Need | Ask |
|------|-----|
| Risk areas unknown | Which directories or operations should agents treat as high risk? |
| Approval boundaries unknown | Which changes require explicit approval before editing? |
| Dependency policy absent | Should agents ask before adding or upgrading dependencies? |
| Generated files unclear | Which generated, vendor, or build artifacts must agents avoid editing? |

## Engineering Rule Policy

Ask these when the user wants book-derived engineering guidance in generated AGENTS.md. Record answers in `engineering_rule_primary`, `engineering_rule_mode`, `engineering_rule_scope`, and `engineering_rule_notes`.

| Need | Ask |
|------|-----|
| Primary rule set unknown | Which one primary engineering rule set should shape the project: refactoring, legacy-code, reliability, architecture, domain modeling, data-intensive systems, or another supported option? |
| Compression level unknown | Should the rule set use `mini` for normal focused guidance or `nano` for tiny always-on guidance? |
| Scope unknown | Should this guidance be project-baseline, scoped to selected directories, or on-demand for matching tasks? |
| Notes unknown | Which local lessons or tradeoffs should be preserved without copying full reference material? |

## Verification Policy

| Need | Ask |
|------|-----|
| Multiple checks exist | Which command is the required final verification before claiming completion? |
| Expensive checks exist | Which checks are safe locally, and which require approval? |
| No runnable checks found | What manual verification should agents perform when no tests exist? |

## Workflow Policy

| Need | Ask |
|------|-----|
| Commit policy absent | Are agents expected to commit changes, and what format should commits use? |
| Branch/PR policy absent | Are agents allowed to push branches or open PRs? |
| Review expectations unknown | What review evidence should agents provide after changes? |
| Git management preference unknown | Should this skill enable git management? Offer `是（默认）`, `否`, or `其他` and record the exact user intent. |

## Domain Context

| Need | Ask |
|------|-----|
| Purpose unclear | What should an AI agent know about this repository in one sentence? |
| Terminology missing | Which domain terms are easy for agents to misunderstand? |
| Golden samples unclear | Which files best demonstrate the patterns agents should follow? |
