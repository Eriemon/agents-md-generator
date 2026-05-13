# AGENTS.md Question Bank

Ask only when repository inspection cannot answer the question.

## Mandatory Design Interview

Run `python scripts/collect_design_profile.py <project>` first and ask question 1. After the user confirms the branch, rerun with `--kind skill` or `--kind engineering`, ask every returned question in order using the returned selectable `options`, then show `review_summary` and ask the yes/no `confirmation_question`. If the user says no, collect corrections and repeat the summary. Validate answers with `collect_design_profile.py --answers <answers.json>` first; use `--write` only after setting `alignment_confirmed=true`.

| ID | Branch | Ask |
|----|--------|-----|
| 1 | all | Confirm whether this is skill development or engineering development. Skill development goes to 2; engineering development goes to 11. |
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
| 11 | engineering | What does this project do? |
| 12 | engineering | Why build this project? |
| 13 | engineering | What are the expected outcome and goals? |
| 14 | engineering | Is development on a remote server, WSL, or local machine? |
| 15 | engineering | Is there experience or precedent to borrow? |
| 16 | engineering | What is the project name? |
| 17 | engineering | Should this project use local git management without remote submission? |
| 18 | engineering | Is the project folder the `master` branch and `dist/` the release branch area? |
| 19 | engineering | Should release folders be named `<project-name>-vx.x.x` under `dist/` and zipped? |
| 20 | all | Does the current working folder already contain a project or skill? |
| 21 | all | If yes, confirm the AGENTS.md is generated from current content and the local, remote, and feature-addition directory structures are fixed. |

## Trigger And Docs Layout Questions

| Need | Ask |
|------|-----|
| Root AGENTS.md missing | This work folder has no root `AGENTS.md`; should I enter AGENTS.md design or restructuring for this project now? |
| Root AGENTS.md version abnormal | The current work folder root `AGENTS.md` is missing `agents_version` or `generator_version`, or the version does not match the installed `agents-md-generator`; should I enter the AGENTS.md design or restructuring flow now? |
| User says 计划/规划/准备 | Because this is a current workspace/current repository/current work folder planning request, should I first inspect the root `AGENTS.md`, report pass-only when it is healthy, and ask before entering AGENTS design or restructuring when it is abnormal? |
| Branch governance abnormal | The current work folder branch state does not match the configured branch model; should I enter branch cleanup or release governance before normal generation continues? |
| Existing docs layout ambiguous | Existing `docs/` content may conflict with AGENTS.md governance. Is it acceptable to add governance subdirectories under the existing `docs/` folder? |

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
