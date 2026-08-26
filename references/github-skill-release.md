# GitHub-Linked Skill Release Contract

This contract treats the skill source, the versioned `dist/` release, and the `github/` checkout in the user work folder as three verifiable copies. It applies to this skill and to any later skill; a developer only needs to register one mapping in `.agents/agents-control.json`.

## Binding Rules

| Item | Contract |
| --- | --- |
| Repository policy | `existing-only`: connect only to an existing remote repository; stop instead of creating one |
| Checkout | `github/<skill-name>/`, inside the current work folder, retaining `.git/` |
| Source | Complete the normal versioned `dist/<skill>-vX.Y.Z/` release and receipt before mirroring |
| Content | The mirrored checkout manifest must match the dist manifest file by file with SHA-256; README files come only from the source directory |
| Remote actions | Tools do not commit, tag, push, create a GitHub release, or create a remote repository |
| Confirmation | Installation confirmation and remote-publication confirmation are independent checkpoints |

## Standard Flow

1. `status`: confirm checkout, `origin`, branch, and worktree state.
2. `check`: confirm the source and dist public-file contract, version, and content allowlist.
3. Complete the ordinary release/install flow; accept only a versioned dist directory containing `RELEASE_RECEIPT.json`.
4. `mirror`: when the checkout is clean and the mapping matches, remove old non-`.git` content and copy the complete dist content; do not edit README files separately in the mirror.
5. `plan`: write `docs/git_manager/github-publish-<skill>-vX.Y.Z.json` with differences, manifests, and manual actions.
6. After an independent remote-publication confirmation, the maintainer performs the Git/GitHub write actions manually.
7. `verify`: recheck the local manifest; this cannot be interpreted as proof of remote publication.

## Stop On Failure

- The mapping is missing, the URL or branch does not match, or the checkout is dirty.
- dist is missing a public file, version metadata has drifted, or a README functional illustration uses a remote image or SVG (header shields are not functional illustrations).
- Any symlink, path escape, manifest difference, or receipt mismatch is present.

When another skill developer needs a GitHub link, they must add a mapping and use this same flow instead of embedding a second implicit publication workflow in skill scripts.
