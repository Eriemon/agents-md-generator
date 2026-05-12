from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "ref",
}


def resolve_project(raw: str | Path) -> Path:
    project = Path(raw).resolve()
    if not project.exists() or not project.is_dir():
        raise SystemExit(f"Project directory does not exist: {project}")
    return project


def emit_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def list_files(root: Path, max_depth: int = 3) -> list[str]:
    out: list[str] = []
    for path in root.rglob("*"):
        parts = set(path.relative_to(root).parts)
        if parts & SKIP_DIRS:
            continue
        if len(path.relative_to(root).parts) > max_depth:
            continue
        if path.is_file():
            out.append(rel(path, root))
    return sorted(out)


def list_dirs(root: Path, max_depth: int = 2) -> list[str]:
    out: list[str] = []
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        relative = path.relative_to(root)
        if set(relative.parts) & SKIP_DIRS:
            continue
        if len(relative.parts) <= max_depth:
            out.append(relative.as_posix())
    return sorted(out)


def has_any(root: Path, names: list[str]) -> bool:
    return any((root / name).exists() for name in names)


def existing_paths(root: Path, names: list[str]) -> list[str]:
    return [name for name in names if (root / name).exists()]


def package_manager(root: Path) -> str:
    package_json = read_json(root / "package.json")
    field = package_json.get("packageManager", "")
    if isinstance(field, str) and "@" in field:
        return field.split("@", 1)[0]
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        return "bun"
    if (root / "package-lock.json").exists() or (root / "package.json").exists():
        return "npm"
    if (root / "composer.json").exists():
        return "composer"
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "go.mod").exists():
        return "go"
    return "unknown"


def pm_run(pm: str) -> str:
    return {"pnpm": "pnpm", "yarn": "yarn", "bun": "bun run"}.get(pm, "npm run")


def pm_dlx(pm: str) -> str:
    return {"pnpm": "pnpm dlx", "yarn": "yarn dlx", "bun": "bunx"}.get(pm, "npx")


def inspect_project(root: Path) -> dict[str, Any]:
    config_files = [name for name in [
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "composer.json",
        "go.mod",
        "Makefile",
        "justfile",
    ] if (root / name).exists()]

    languages: list[str] = []
    framework = "none"
    project_type = "unknown"

    package_json = read_json(root / "package.json")
    if package_json:
        languages.append("typescript")
        deps = {}
        for key in ("dependencies", "devDependencies"):
            value = package_json.get(key, {})
            if isinstance(value, dict):
                deps.update(value)
        if "next" in deps:
            framework = "next.js"
            project_type = "typescript-nextjs"
        elif "react" in deps:
            framework = "react"
            project_type = "typescript-react"
        elif "vue" in deps:
            framework = "vue"
            project_type = "typescript-vue"
        elif "express" in deps:
            framework = "express"
            project_type = "typescript-node"
        else:
            project_type = "typescript"

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        languages.append("python")
        text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
        if "django" in text:
            framework = "django"
        elif "fastapi" in text:
            framework = "fastapi"
        elif "flask" in text:
            framework = "flask"
        project_type = "python"

    composer = read_json(root / "composer.json")
    if composer:
        languages.append("php")
        require = composer.get("require", {}) if isinstance(composer.get("require"), dict) else {}
        composer_type = composer.get("type", "")
        if (root / "ext_emconf.php").exists() or "typo3/cms-core" in require:
            framework = "typo3"
            project_type = "php-typo3-extension" if composer_type == "typo3-cms-extension" else "php-typo3"
        elif "laravel/framework" in require:
            framework = "laravel"
            project_type = "php-laravel"
        elif "symfony/framework-bundle" in require:
            framework = "symfony"
            project_type = "php-symfony"
        else:
            project_type = "php"

    if (root / "go.mod").exists():
        languages.append("go")
        project_type = "go-cli" if (root / "cmd").exists() else "go"
        framework = "go"

    skill_files = sorted(path for path in root.glob("*/SKILL.md") if path.is_file())
    skill_files.extend(sorted(path for path in root.glob("skills/*/SKILL.md") if path.is_file()))
    if (root / "SKILL.md").exists() or skill_files:
        if "skill" not in languages:
            languages.append("skill")
        project_type = "skill-repo"
        if framework == "none":
            framework = "codex-skill"

    ci: list[str] = []
    if (root / ".github" / "workflows").exists():
        ci.append("github_actions")
    if (root / ".gitlab-ci.yml").exists():
        ci.append("gitlab_ci")

    ai_configs = [name for name in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursor",
        ".claude",
        ".windsurf",
    ] if (root / name).exists()]

    return {
        "project_root": str(root),
        "root_agents_md_exists": (root / "AGENTS.md").is_file(),
        "primary_language": languages[0] if languages else "unknown",
        "languages": sorted(set(languages)),
        "package_manager": package_manager(root),
        "framework": framework,
        "project_type": project_type,
        "ci": ci,
        "ai_configs": ai_configs,
        "config_files": config_files,
        "directories": list_dirs(root),
        "files": list_files(root),
    }


def command_entry(task: str, command: str, source: str, notes: str = "", seconds: str = "") -> dict[str, str]:
    return {
        "task": task,
        "command": command,
        "source": source,
        "notes": notes,
        "time": seconds or "~30s",
        "verified": "false",
    }


def extract_commands(root: Path) -> dict[str, Any]:
    commands: list[dict[str, str]] = []

    makefile = root / "Makefile"
    if makefile.exists():
        text = makefile.read_text(encoding="utf-8", errors="ignore")
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))
        mapping = {
            "Setup": ["setup", "install"],
            "Run": ["dev", "serve", "run"],
            "Format": ["format", "fmt"],
            "Lint": ["lint", "check"],
            "Test (all)": ["test", "tests"],
            "Build": ["build"],
            "Typecheck": ["typecheck", "types"],
        }
        for task, candidates in mapping.items():
            for target in candidates:
                if target in targets:
                    commands.append(command_entry(task, f"make {target}", "Makefile"))
                    break

    package_json = read_json(root / "package.json")
    if package_json:
        scripts = package_json.get("scripts", {})
        scripts = scripts if isinstance(scripts, dict) else {}
        pm = package_manager(root)
        run = pm_run(pm)
        dlx = pm_dlx(pm)
        if scripts:
            commands.append(command_entry("Setup", f"{pm} install", "lockfile/package.json", "~install dependencies"))
        script_map = {
            "Run": ["dev", "start"],
            "Format": ["format", "fmt"],
            "Lint": ["lint"],
            "Test (all)": ["test"],
            "Build": ["build"],
            "Typecheck": ["typecheck", "type-check", "types"],
        }
        for task, names in script_map.items():
            for name in names:
                if name in scripts:
                    cmd = f"{pm} test" if task == "Test (all)" and pm in {"npm", "pnpm"} else f"{run} {name}"
                    commands.append(command_entry(task, cmd, "package.json"))
                    break
        deps_text = json.dumps(package_json)
        if "vitest" in deps_text:
            commands.append(command_entry("Test (single)", f"{dlx} vitest run", "package.json", "~single test file", "~2s"))
        elif "jest" in deps_text:
            commands.append(command_entry("Test (single)", f"{dlx} jest", "package.json", "~single test file", "~2s"))

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "[tool.ruff" in text:
            commands.append(command_entry("Lint", "ruff check .", "pyproject.toml", "", "~10s"))
            commands.append(command_entry("Format", "ruff format .", "pyproject.toml", "", "~5s"))
        if "mypy" in text:
            commands.append(command_entry("Typecheck", "mypy .", "pyproject.toml", "", "~15s"))
        if "pytest" in text or (root / "tests").exists():
            commands.append(command_entry("Test (all)", "pytest", "pyproject.toml/tests", "", "~30s"))

    composer = read_json(root / "composer.json")
    if composer:
        scripts = composer.get("scripts", {}) if isinstance(composer.get("scripts"), dict) else {}
        for task, names in {
            "Lint": ["lint", "cs:check"],
            "Format": ["format", "cs:fix"],
            "Test (all)": ["test"],
            "Typecheck": ["phpstan", "stan"],
        }.items():
            for name in names:
                if name in scripts:
                    commands.append(command_entry(task, f"composer run {name}", "composer.json"))
                    break

    if (root / "go.mod").exists():
        commands.extend([
            command_entry("Format", "gofmt -w .", "go.mod", "", "~5s"),
            command_entry("Test (all)", "go test ./...", "go.mod", "", "~30s"),
            command_entry("Build", "go build ./...", "go.mod", "", "~30s"),
        ])

    workflow_dir = root / ".github" / "workflows"
    if workflow_dir.exists():
        for workflow in sorted(workflow_dir.glob("*.y*ml")):
            text = workflow.read_text(encoding="utf-8", errors="ignore")
            for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):
                command = (raw[0] or raw[1]).strip().strip("'\"")
                if not command or command.startswith(("|", ">")):
                    continue
                first_line = command.splitlines()[0].strip()
                if not first_line:
                    continue
                lowered = first_line.lower()
                if any(token in lowered for token in ("lint", "eslint", "ruff", "phpstan")):
                    task = "CI Lint"
                elif any(token in lowered for token in ("test", "pytest", "vitest", "jest", "go test")):
                    task = "CI Test"
                elif any(token in lowered for token in ("build", "compile")):
                    task = "CI Build"
                elif any(token in lowered for token in ("typecheck", "type-check", "tsc", "mypy")):
                    task = "CI Typecheck"
                else:
                    task = "CI Command"
                commands.append(command_entry(task, first_line, rel(workflow, root)))

    seen: set[tuple[str, str]] = set()
    unique = []
    for item in commands:
        key = (item["task"], item["command"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return {"commands": unique}


def workflow_runs(root: Path) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        return rules
    for workflow in sorted(workflow_dir.glob("*.y*ml")):
        text = workflow.read_text(encoding="utf-8", errors="ignore")
        for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):
            command = (raw[0] or raw[1]).strip().strip("'\"")
            if not command or command.startswith(("|", ">")):
                continue
            first_line = command.splitlines()[0].strip()
            if first_line:
                rules.append({"workflow": rel(workflow, root), "command": first_line})
    return rules


def extract_context(root: Path) -> dict[str, Any]:
    documentation_names = {"README.md", "CONTRIBUTING.md", "SECURITY.md", "ARCHITECTURE.md"}
    documentation = [name for name in sorted(documentation_names) if (root / name).exists()]
    for docs_dir in ("docs", "Documentation"):
        base = root / docs_dir
        if base.exists():
            documentation.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    adr_dirs = ["adr", "adrs", "docs/adr", "docs/adrs", "docs/decisions", "architecture/decisions"]
    adrs: list[str] = []
    for adr_dir in adr_dirs:
        base = root / adr_dir
        if base.exists():
            adrs.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    utilities: list[str] = []
    for name in ("Makefile", "justfile"):
        if (root / name).exists():
            utilities.append(name)
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        utilities.extend(rel(path, root) for path in sorted(scripts_dir.iterdir()) if path.is_file())

    quality_names = [
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "ruff.toml",
        ".ruff.toml",
        "mypy.ini",
        "pytest.ini",
        "tsconfig.json",
        "eslint.config.js",
        "eslint.config.mjs",
        ".eslintrc",
        ".eslintrc.json",
        ".prettierrc",
        ".prettierrc.json",
        "phpstan.neon",
    ]
    quality_configs = existing_paths(root, quality_names)

    platform_names = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        ".devcontainer/devcontainer.json",
        ".tool-versions",
        ".python-version",
        ".nvmrc",
        "mise.toml",
        ".mise.toml",
        "flake.nix",
        "shell.nix",
        "Taskfile.yml",
        "Taskfile.yaml",
    ]
    platform_files = existing_paths(root, platform_names)

    ide_names = [
        ".editorconfig",
        ".vscode/settings.json",
        ".vscode/extensions.json",
        ".idea/codeStyles/Project.xml",
        ".idea/inspectionProfiles/Project_Default.xml",
    ]
    ide_settings = existing_paths(root, ide_names)

    architecture_names = [
        "CODEOWNERS",
        ".github/CODEOWNERS",
        "ARCHITECTURE.md",
        "docs/architecture.md",
        "docs/ARCHITECTURE.md",
        "docs/adr/index.md",
    ]
    architecture_files = existing_paths(root, architecture_names)

    dependency_names = [
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
        "renovate.json",
        ".renovaterc",
        ".renovaterc.json",
        "dependabot.yml",
        "dependabot.yaml",
    ]
    dependency_configs = existing_paths(root, dependency_names)

    hook_names = [
        "lefthook.yml",
        ".lefthook.yml",
        "captainhook.json",
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "Build/hooks/pre-push",
        ".githooks/pre-commit",
        ".githooks/pre-push",
    ]
    hook_configs = existing_paths(root, hook_names)
    if (root / ".husky").is_dir():
        hook_configs.append(".husky/")

    github_names = [
        ".github/CODEOWNERS",
        ".github/copilot-instructions.md",
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
        ".github/renovate.json",
    ]
    github_settings = existing_paths(root, github_names)
    rulesets_dir = root / ".github" / "rulesets"
    if rulesets_dir.exists():
        github_settings.extend(rel(path, root) for path in sorted(rulesets_dir.glob("*.json"))[:12])

    coverage_names = [
        "src",
        "app",
        "lib",
        "tests",
        "test",
        "docs",
        "Documentation",
        "scripts",
        "tools",
        "cmd",
        "internal",
        "pkg",
        ".github/workflows",
    ]
    directory_coverage_candidates = [
        name for name in coverage_names
        if (root / name).is_dir() and not (root / name / "AGENTS.md").exists()
    ]

    reference_projects: list[str] = []
    for base_name in ("reference-projects", "references/projects", "examples/reference-projects"):
        base = root / base_name
        if base.exists() and base.is_dir():
            for child in sorted(base.iterdir()):
                if child.is_dir():
                    reference_projects.append(rel(child, root))

    agent_config_names = [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursorrules",
        ".aider.conf.yml",
        ".aider.conf.yaml",
    ]
    agent_configs = [name for name in agent_config_names if (root / name).exists()]

    golden_samples: list[str] = []
    sample_patterns = [
        "tests/test_*.*",
        "tests/*_test.*",
        "src/*.*",
        "app/*.*",
        "lib/*.*",
        "examples/*.*",
        "samples/*.*",
    ]
    for pattern in sample_patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and len(golden_samples) < 8:
                golden_samples.append(rel(path, root))

    return {
        "documentation": sorted(dict.fromkeys(documentation)),
        "adrs": sorted(dict.fromkeys(adrs)),
        "utilities": sorted(dict.fromkeys(utilities)),
        "quality_configs": sorted(dict.fromkeys(quality_configs)),
        "platform_files": sorted(dict.fromkeys(platform_files)),
        "ide_settings": sorted(dict.fromkeys(ide_settings)),
        "architecture_files": sorted(dict.fromkeys(architecture_files)),
        "dependency_configs": sorted(dict.fromkeys(dependency_configs)),
        "hook_configs": sorted(dict.fromkeys(hook_configs)),
        "github_settings": sorted(dict.fromkeys(github_settings)),
        "directory_coverage_candidates": sorted(dict.fromkeys(directory_coverage_candidates)),
        "reference_projects": sorted(dict.fromkeys(reference_projects)),
        "agent_configs": sorted(dict.fromkeys(agent_configs)),
        "golden_samples": sorted(dict.fromkeys(golden_samples)),
        "ci_rules": workflow_runs(root),
    }


def detect_scopes(root: Path) -> dict[str, Any]:
    candidates = {
        "src": "source code patterns",
        "tests": "test conventions and fixtures",
        "test": "test conventions and fixtures",
        "docs": "documentation standards",
        "frontend": "frontend stack and UI conventions",
        "web": "frontend stack and UI conventions",
        "backend": "backend stack and service conventions",
        "internal": "internal module boundaries",
        "cmd": "CLI entry points and flags",
        "scripts": "automation script conventions",
        ".github/workflows": "CI workflow rules",
    }
    scopes = []
    for path, purpose in candidates.items():
        full = root / path
        if full.exists() and full.is_dir():
            scopes.append({"path": path, "purpose": purpose, "agents_file": f"{path}/AGENTS.md"})

    packages = root / "packages"
    if packages.exists():
        for child in sorted(packages.iterdir()):
            if child.is_dir():
                path = child.relative_to(root).as_posix()
                scopes.append({"path": path, "purpose": "workspace package-specific rules", "agents_file": f"{path}/AGENTS.md"})
    return {"scopes": scopes}


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def today() -> str:
    return date.today().isoformat()


def parse_args(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("project", nargs="?", default=".", help="Target project directory")
    return parser
