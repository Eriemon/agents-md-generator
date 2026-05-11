<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->
<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->
<!-- Last updated: {{TIMESTAMP}} | Last verified: {{VERIFIED_TIMESTAMP}} -->

# AGENTS.md

**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.

<!-- AGENTS-GENERATED:START project-overview -->
## Project Overview
{{PROJECT_OVERVIEW}}
<!-- AGENTS-GENERATED:END project-overview -->

<!-- AGENTS-GENERATED:START control-profile -->
## Control Profile
{{CONTROL_PROFILE}}
<!-- AGENTS-GENERATED:END control-profile -->

<!-- AGENTS-GENERATED:START directory-contract -->
## Directory Contract
{{DIRECTORY_CONTRACT}}
<!-- AGENTS-GENERATED:END directory-contract -->

<!-- AGENTS-GENERATED:START release-contract -->
## Release Contract
{{RELEASE_CONTRACT}}
<!-- AGENTS-GENERATED:END release-contract -->

<!-- AGENTS-GENERATED:START engineering-rule-contract -->
## Engineering Rule Contract
{{ENGINEERING_RULE_CONTRACT}}
<!-- AGENTS-GENERATED:END engineering-rule-contract -->

<!-- AGENTS-GENERATED:START skill-design-contract -->
## Skill Design Contract
{{SKILL_DESIGN_CONTRACT}}
<!-- AGENTS-GENERATED:END skill-design-contract -->

<!-- AGENTS-GENERATED:START commands -->
## Commands ({{VERIFICATION_STATUS}})
> Source: {{COMMAND_SOURCE}} - verify before relying on these commands.

| Task | Command | ~Time | Source |
|------|---------|-------|--------|
{{COMMAND_ROWS}}
<!-- AGENTS-GENERATED:END commands -->

## Agent Work Loop
1. Read the nearest `AGENTS.md` before editing files.
2. Inspect existing patterns and generated facts before adding code.
3. Run the smallest relevant check after each change.
4. Run final verification and show command output before claiming completion.
5. Complete the full assigned development task in the current conversation whenever feasible; if blocked, report blockers, completed work, and exact next steps.
6. Before changing folder structure, follow `docs/dir_manager/` and run `manage_dirs.py review` when directory governance is configured.
7. If the user force-confirms a blocked folder change, archive old dir manager content under `docs/dir_manager/history_dir_manager/` before applying it.

<!-- AGENTS-GENERATED:START conversation-completion-contract -->
## Conversation Completion Contract
{{CONVERSATION_COMPLETION_CONTRACT}}
<!-- AGENTS-GENERATED:END conversation-completion-contract -->

<!-- AGENTS-GENERATED:START documentation-governance-contract -->
## Documentation Governance Contract
{{DOCUMENTATION_GOVERNANCE_CONTRACT}}
<!-- AGENTS-GENERATED:END documentation-governance-contract -->

<!-- AGENTS-GENERATED:START file-map -->
## File Map
{{FILE_MAP}}
<!-- AGENTS-GENERATED:END file-map -->

<!-- AGENTS-GENERATED:START golden-samples -->
## Golden Samples
| For | Reference | Key patterns |
|-----|-----------|--------------|
{{GOLDEN_SAMPLE_ROWS}}
<!-- AGENTS-GENERATED:END golden-samples -->

<!-- AGENTS-GENERATED:START utilities -->
## Utilities
| Need | Use | Location |
|------|-----|----------|
{{UTILITY_ROWS}}
<!-- AGENTS-GENERATED:END utilities -->

<!-- AGENTS-GENERATED:START heuristics -->
## Heuristics
| When | Do |
|------|----|
{{HEURISTIC_ROWS}}
<!-- AGENTS-GENERATED:END heuristics -->

<!-- AGENTS-GENERATED:START repository-settings -->
## Repository Settings
{{REPOSITORY_SETTINGS}}
<!-- AGENTS-GENERATED:END repository-settings -->

<!-- AGENTS-GENERATED:START hook-policy -->
## Hook Policy
{{HOOK_POLICY}}
<!-- AGENTS-GENERATED:END hook-policy -->

<!-- AGENTS-GENERATED:START ci-rules -->
## CI Rules
{{CI_RULES}}
<!-- AGENTS-GENERATED:END ci-rules -->

<!-- AGENTS-GENERATED:START github-settings -->
## GitHub Settings
{{GITHUB_SETTINGS}}
<!-- AGENTS-GENERATED:END github-settings -->

<!-- AGENTS-GENERATED:START directory-coverage -->
## Directory Coverage
{{DIRECTORY_COVERAGE}}
<!-- AGENTS-GENERATED:END directory-coverage -->

<!-- AGENTS-GENERATED:START key-decisions -->
## Key Decisions
{{KEY_DECISIONS}}
<!-- AGENTS-GENERATED:END key-decisions -->

## Boundaries

### Always Do
{{ALWAYS_RULES}}

### Ask First
{{ASK_FIRST_RULES}}

### Never Do
{{NEVER_RULES}}

<!-- AGENTS-GENERATED:START codebase-state -->
## Codebase State
{{CODEBASE_STATE}}
<!-- AGENTS-GENERATED:END codebase-state -->

<!-- AGENTS-GENERATED:START terminology -->
## Terminology
| Term | Means |
|------|-------|
{{TERMINOLOGY_ROWS}}
<!-- AGENTS-GENERATED:END terminology -->

<!-- AGENTS-GENERATED:START scope-index -->
## Scoped AGENTS.md
{{SCOPE_INDEX}}
<!-- AGENTS-GENERATED:END scope-index -->

## When Instructions Conflict
Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.
