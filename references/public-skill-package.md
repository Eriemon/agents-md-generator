# Public Skill Package Contract

Every managed skill source directory and versioned release directory must contain these root files:

`VERSION`, `LICENSE`, `README.md`, `README-CN.md`, `SECURITY.md`, `pyproject.toml`, `CONTRIBUTING.md`, `CITATION.cff`, and the runtime entry point `SKILL.md`.

## README Illustration Rules

- Both README files must contain local PNG illustrations that explain real functionality.
- Each illustration must be at least 1600x900 so repository hosts and documentation mirrors can display it clearly.
- Functional illustrations must not use SVG, Mermaid, remote images, or broken relative paths; existing header shields.io badges may remain as version, license, and target metadata.
- Illustrations must explain how user input passes through inspection, design, rendering, review, and a verifiable installable release rather than presenting a step-by-step activity log.
- If an Image2-generated PNG carries SVG or remote metadata, losslessly re-encode it as a clean PNG before adding it to the source directory or dist.

## Functional Figure Composition

- The hero figure is a horizontal 16:9 overview that lets a reader see the skill input, core processing chain, and verifiable output at a glance.
- Detail figures split the major capabilities, such as fact collection, design profiling, rule generation, evidence verification, or release boundaries; each figure needs its own information focus and must not be a crop of the hero.
- Panels, tables, relationship maps, code fragments, state cards, and short labels are allowed when they clarify the function. Text must serve the functional explanation rather than replace it with generic decoration.
- English and Chinese figures must express the same functional relationships. Layout and color may vary slightly, but semantics may not change.
- When a later skill developer explicitly asks to generate figures or README illustrations, this contract applies automatically: inspect and reuse existing assets first, and use Image2/ImageGen only when a suitable local asset is missing; SVG, Mermaid, remote functional figures, and purely decorative posters are forbidden.

| Figure class | Required question | Recommended information | Unacceptable substitute |
| --- | --- | --- | --- |
| Hero | Where does the user enter, what does the skill do, and what is delivered? | Input card, core processing chain, outputs, gates or boundaries | A poster containing only a title and branding |
| Project facts/capabilities | Which real facts does the skill use? | Directory tree, fact graph, command/dependency/language signals, scope candidates | Fabricated statistics or unrelated stock imagery |
| Design profile | Which questions and policies determine the result? | Question cards, policy sliders, scope table, decision matrix, locked state | A semantically empty dashboard decoration |
| Rule rendering | How do rules inherit, override, and preserve the human boundary? | Root rules, directory rules, inheritance arrows, managed blocks, human blocks, minimal diff | Putting everything into one unmaintainable document |
| Evidence gate | Why may the result be handed off, or why must it be blocked? | Input evidence, gate cards, pass/warning/block, receipts, fail-closed path | Showing only green success with no failure conditions |

Every figure label must be supported by the corresponding skill behavior, configuration, command, or deliverable. If a generation model introduces uncontrolled numbers, versions, paths, or states, replace them with conceptual labels or remove them during cleanup; never treat model guesses as project facts.

The source README is the only authoritative bilingual product page. `dist/` and `github/` accept only its complete copy. The `release_content_policy.validate_public_skill_files` function enforces this contract and is reused by audit, packaging, and GitHub-publish CLIs. Missing or non-compliant content fails closed.
