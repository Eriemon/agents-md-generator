# 导入 项目事实 所需的依赖模块。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 项目事实 所需的依赖模块。
import json
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# 导入 项目事实 所需的依赖模块。
from agents_common import (
    SKIP_DIRS,
    codex_sessions_root,
    display_path,
    global_codex_agents_status,
    managed_scripts_root,
    normalize_path_key,

    # 分隔当前密集代码块，保留原有执行顺序。
    package_manager,
    parse_agents_metadata,
    pm_dlx,
    pm_run,
    project_profile,
    read_installed_skill_version,

    # 再次分隔当前长代码块，降低连续语句密度。
    read_json,
    read_skill_version,
    rel,
    root_agents_sync_command,
    workspace_has_existing_content,
)

# 分隔导入清单的后续成员，避免超长连续导入块。
from source_governance import source_governance_report
import source_governance_config
from source_governance_config import (
    default_global_rule_overrides,
    default_implementation_constraints,

    # 分隔导入清单末段，保证分组阅读边界清楚。
    global_rule_overrides_path,
    global_rule_overrides_reference,
    implementation_constraints_from_profile,
    load_global_rule_overrides,
    validate_code_comment_policy_data,
    validate_global_rule_overrides_data,
)
from workspace_settings_policy import discover_workspace_settings

# 解析 模块入口 需要的 EPHEMERAL ROOT INPUT FILE RE 项目事实。
EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(  # 项目事实扫描渲染输入值
    (
        r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|"  # 临时输入前缀集合
        r"blocked-change|blocked-remote-change|blocked-remote-source-change)"  # 阻断场景输入前缀集合
        r"(?:-[a-z0-9._-]+)?\.json$"  # 临时输入可选后缀
    ),  # 项目事实扫描临时输入文件模式
    flags=re.IGNORECASE,  # 项目事实扫描渲染输入值
)

# 解析 模块入口 需要的 ALLOWED ROOT FILE PATTERNS 项目事实。
ALLOWED_ROOT_FILE_PATTERNS = (  # 项目事实扫描渲染输入值
    "answers.json",  # 项目事实扫描渲染输入值
    "*-answers.json",  # 项目事实扫描渲染输入值
    "change.json",  # 项目事实扫描渲染输入值
    "*-change.json",  # 项目事实扫描渲染输入值
    "session.json",  # 项目事实扫描渲染输入值
    "recovery.json",  # 项目事实扫描渲染输入值
    "handoff.json",  # 项目事实扫描渲染输入值
    "stage.json",  # 项目事实扫描渲染输入值
    "changelog.json",  # 项目事实扫描渲染输入值
)

# 定义 parse_session_meta 的项目事实处理入口。
def parse_session_meta(path: Path) -> dict[str, Any]:

    # 保护 parse_session_meta 中允许失败的外部访问。
    try:

        # 限定 parse_session_meta 的文件或资源访问范围。
        with path.open("r", encoding="utf-8", errors="ignore") as handle:

            # 逐项检查 parse_session_meta 候选项。
            for raw in handle:

                # 解析 parse_session_meta 需要的 data 项目事实。
                dict_data = json.loads(raw)  # 项目事实扫描渲染输入值

                # 校验 parse_session_meta 分支条件。
                if dict_data.get("type") != "session_meta":

                    # 分隔 parse_session_meta 的控制流边界。
                    continue

                # 解析 parse_session_meta 需要的 payload 项目事实。
                payload = dict_data.get("payload", {})  # 项目事实扫描渲染输入值

                # 校验 parse_session_meta 分支条件。
                if isinstance(payload, dict):

                    # 返回 parse_session_meta 调用载荷。
                    return payload
    except Exception:

        # 返回 parse_session_meta 调用载荷。
        return {}

    # 返回 parse_session_meta 调用载荷。
    return {}

# 定义 matched_codex_sessions 的项目事实处理入口。
def matched_codex_sessions(root: Path) -> list[dict[str, str]]:

    # 解析 matched_codex_sessions 需要的 sessions root 项目事实。
    sessions_root = codex_sessions_root()  # 项目事实扫描渲染输入值

    # 校验 matched_codex_sessions 分支条件。
    if not sessions_root.is_dir():

        # 返回 matched_codex_sessions 调用载荷。
        return []

    # 解析 matched_codex_sessions 需要的 key 项目事实。
    key = normalize_path_key(root)  # 项目事实扫描渲染输入值

    # 汇总 matches ，作为 AGENTS 渲染的项目事实候选清单。
    list_matches: list[dict[str, str]] = []  # 项目事实扫描渲染输入值

    # 逐项检查 matched_codex_sessions 候选项。
    for path in sorted(sessions_root.rglob("*.jsonl")):

        # 保存 payload 映射，维持 matched_codex_sessions 的字段关系。
        dict_payload = parse_session_meta(path)  # 项目事实扫描渲染输入值

        # 校验 matched_codex_sessions 分支条件。
        if not dict_payload:

            # 分隔 matched_codex_sessions 的控制流边界。
            continue

        # 解析 matched_codex_sessions 需要的 cwd key 项目事实。
        cwd_key = normalize_path_key(dict_payload.get("cwd", ""))  # 项目事实扫描渲染输入值

        # 校验 matched_codex_sessions 分支条件。
        if not cwd_key or cwd_key != key:

            # 分隔 matched_codex_sessions 的控制流边界。
            continue

        # 追加 matched_codex_sessions 诊断。
        list_matches.append(
            {
                "id": str(dict_payload.get("id", "")).strip(),
                "cwd": str(dict_payload.get("cwd", "")).strip(),
                "timestamp": str(dict_payload.get("timestamp", "")).strip(),
                "path": path.resolve().as_posix(),
            }
        )

    # 返回 matched_codex_sessions 调用载荷。
    return list_matches


# 定义 session_message_rows 的项目事实处理入口。
def session_message_rows(path: Path, limit: int = 48) -> list[dict[str, str]]:

    # 汇总 rows ，作为 AGENTS 渲染的项目事实候选清单。
    list_rows: list[dict[str, str]] = []  # 项目事实扫描渲染输入值

    # 保护 session_message_rows 中允许失败的外部访问。
    try:

        # 限定 session_message_rows 的文件或资源访问范围。
        with path.open("r", encoding="utf-8", errors="ignore") as handle:

            # 逐项检查 session_message_rows 候选项。
            for raw in handle:

                # 保护 session_message_rows 中允许失败的外部访问。
                try:

                    # 解析 session_message_rows 需要的 data 项目事实。
                    dict_data = json.loads(raw)  # 项目事实扫描渲染输入值
                except Exception:

                    # 分隔 session_message_rows 的控制流边界。
                    continue

                # 校验 session_message_rows 分支条件。
                if dict_data.get("type") != "event_msg":

                    # 分隔 session_message_rows 的控制流边界。
                    continue

                # 解析 session_message_rows 需要的 payload 项目事实。
                payload = dict_data.get("payload", {})  # 项目事实扫描渲染输入值

                # 校验 session_message_rows 分支条件。
                if not isinstance(payload, dict):

                    # 分隔 session_message_rows 的控制流边界。
                    continue

                # 解析 session_message_rows 需要的 message type 项目事实。
                message_type = str(payload.get("type", "")).strip()  # 项目事实扫描渲染输入值

                # 解析 session_message_rows 需要的 role 项目事实。
                role = "user" if message_type == "user_message" else "assistant" if message_type == "agent_message" else ""  # 项目事实扫描渲染输入值

                # 解析 session_message_rows 需要的 message 项目事实。
                message = str(payload.get("message", "")).strip()  # 项目事实扫描渲染输入值

                # 校验 session_message_rows 分支条件。
                if not role or not message:

                    # 分隔 session_message_rows 的控制流边界。
                    continue

                # 追加 session_message_rows 诊断。
                list_rows.append({"role": role, "message": message})

                # 校验 session_message_rows 分支条件。
                if len(list_rows) >= limit:

                    # 分隔 session_message_rows 的控制流边界。
                    break
    except Exception:

        # 返回 session_message_rows 调用载荷。
        return []

    # 返回 session_message_rows 调用载荷。
    return list_rows

# 定义 list_files 的项目事实处理入口。
def list_files(root: Path, max_depth: int = 3) -> list[str]:

    # 汇总 out ，作为 AGENTS 渲染的项目事实候选清单。
    list_out: list[str] = []  # 项目事实扫描渲染输入值

    # 逐项检查 list_files 候选项。
    for path in root.rglob("*"):

        # 汇总 parts ，作为 AGENTS 渲染的项目事实候选清单。
        set_parts = set(path.relative_to(root).parts)  # 项目事实扫描渲染输入值

        # 校验 list_files 分支条件。
        if set_parts & SKIP_DIRS:

            # 分隔 list_files 的控制流边界。
            continue

        # 校验 list_files 分支条件。
        if len(path.relative_to(root).parts) > max_depth:

            # 分隔 list_files 的控制流边界。
            continue

        # 校验 list_files 分支条件。
        if path.is_file():

            # 追加 list_files 诊断。
            list_out.append(rel(path, root))

    # 返回 list_files 调用载荷。
    return sorted(list_out)

# 定义 list_dirs 的项目事实处理入口。
def list_dirs(root: Path, max_depth: int = 2) -> list[str]:

    # 汇总 out ，作为 AGENTS 渲染的项目事实候选清单。
    list_out: list[str] = []  # 项目事实扫描渲染输入值

    # 逐项检查 list_dirs 候选项。
    for path in root.rglob("*"):

        # 校验 list_dirs 分支条件。
        if not path.is_dir():

            # 分隔 list_dirs 的控制流边界。
            continue

        # 解析 list_dirs 需要的 relative 项目事实。
        relative = path.relative_to(root)  # 项目事实扫描渲染输入值

        # 校验 list_dirs 分支条件。
        if set(relative.parts) & SKIP_DIRS:

            # 分隔 list_dirs 的控制流边界。
            continue

        # 校验 list_dirs 分支条件。
        if len(relative.parts) <= max_depth:

            # 追加 list_dirs 诊断。
            list_out.append(relative.as_posix())

    # 返回 list_dirs 调用载荷。
    return sorted(list_out)

# 定义 has_any 的项目事实处理入口。
def has_any(root: Path, names: list[str]) -> bool:

    # 返回 has_any 调用载荷。
    return any((root / name).exists() for name in names)


# 定义 existing_paths 的项目事实处理入口。
def existing_paths(root: Path, names: list[str]) -> list[str]:

    # 返回 existing_paths 调用载荷。
    return [name for name in names if (root / name).exists()]


# 定义 is_allowed_root_file 的项目事实处理入口。
def is_allowed_root_file(name: str, allowed_root_files: set[str]) -> bool:

    # 解析 is_allowed_root_file 需要的 normalized 项目事实。
    normalized = str(name).strip()  # 项目事实扫描渲染输入值

    # 校验 is_allowed_root_file 分支条件。
    if normalized in allowed_root_files:

        # 返回 is_allowed_root_file 调用载荷。
        return True

    # 校验 is_allowed_root_file 分支条件。
    if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(normalized):

        # 返回 is_allowed_root_file 调用载荷。
        return True

    # 返回 is_allowed_root_file 调用载荷。
    return any(fnmatch(normalized, pattern) for pattern in ALLOWED_ROOT_FILE_PATTERNS)

# 定义 inspect_project 的项目事实处理入口。
def inspect_project(root: Path) -> dict[str, Any]:

    # 汇总 config files ，作为 AGENTS 渲染的项目事实候选清单。
    config_files = [name for name in [  # 项目事实扫描渲染输入值
        "package.json",  # 项目事实扫描渲染输入值
        "pnpm-lock.yaml",  # 项目事实扫描渲染输入值
        "package-lock.json",  # 项目事实扫描渲染输入值
        "yarn.lock",  # 项目事实扫描渲染输入值
        "bun.lock",  # 项目事实扫描渲染输入值
        "bun.lockb",  # 项目事实扫描渲染输入值
        "pyproject.toml",  # 项目事实扫描渲染输入值
        "uv.lock",  # 项目事实扫描渲染输入值
        "poetry.lock",  # 项目事实扫描渲染输入值
        "composer.json",  # 项目事实扫描渲染输入值
        "go.mod",  # 项目事实扫描渲染输入值
        "Makefile",  # 项目事实扫描渲染输入值
        "justfile",  # 项目事实扫描渲染输入值
    ] if (root / name).exists()]  # 项目事实扫描渲染输入值

    # 调用 extend 处理 inspect_project。
    config_files.extend(discover_workspace_settings(root))

    # 汇总 languages ，作为 AGENTS 渲染的项目事实候选清单。
    list_languages: list[str] = []  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 framework 项目事实。
    str_framework = "none"  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 project type 项目事实。
    str_project_type = "unknown"  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 package json 项目事实。
    package_json = read_json(root / "package.json")  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if package_json:

        # 追加 inspect_project 诊断。
        list_languages.append("typescript")

        # 汇总 deps ，作为 AGENTS 渲染的项目事实候选清单。
        dict_deps = {}  # 项目事实扫描渲染输入值

        # 逐项检查 inspect_project 候选项。
        for key in ("dependencies", "devDependencies"):

            # 解析 inspect_project 需要的 value 项目事实。
            raw_value = package_json.get(key, {})  # 项目事实扫描渲染输入值

            # 校验 inspect_project 分支条件。
            if isinstance(raw_value, dict):

                # 调用 update 处理 inspect_project。
                dict_deps.update(raw_value)

        # 校验 inspect_project 分支条件。
        if "next" in dict_deps:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "next.js"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "typescript-nextjs"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "react" in dict_deps:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "react"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "typescript-react"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "vue" in dict_deps:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "vue"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "typescript-vue"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "express" in dict_deps:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "express"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "typescript-node"  # 项目事实扫描渲染输入值
        else:

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "typescript"  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 pyproject 项目事实。
    pyproject = root / "pyproject.toml"  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if pyproject.exists():

        # 追加 inspect_project 诊断。
        list_languages.append("python")

        # 解析 inspect_project 需要的 text 项目事实。
        text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        if "django" in text:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "django"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "fastapi" in text:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "fastapi"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "flask" in text:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "flask"  # 项目事实扫描渲染输入值

        # 解析 inspect_project 需要的 project type 项目事实。
        str_project_type = "python"  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 composer 项目事实。
    composer = read_json(root / "composer.json")  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if composer:

        # 追加 inspect_project 诊断。
        list_languages.append("php")

        # 解析 inspect_project 需要的 require 项目事实。
        require = composer.get("require", {}) if isinstance(composer.get("require"), dict) else {}  # 项目事实扫描渲染输入值

        # 解析 inspect_project 需要的 composer type 项目事实。
        composer_type = composer.get("type", "")  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        if (root / "ext_emconf.php").exists() or "typo3/cms-core" in require:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "typo3"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "php-typo3-extension" if composer_type == "typo3-cms-extension" else "php-typo3"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "laravel/framework" in require:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "laravel"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "php-laravel"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        elif "symfony/framework-bundle" in require:

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "symfony"  # 项目事实扫描渲染输入值

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "php-symfony"  # 项目事实扫描渲染输入值
        else:

            # 解析 inspect_project 需要的 project type 项目事实。
            str_project_type = "php"  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if (root / "go.mod").exists():

        # 追加 inspect_project 诊断。
        list_languages.append("go")

        # 解析 inspect_project 需要的 project type 项目事实。
        str_project_type = "go-cli" if (root / "cmd").exists() else "go"  # 项目事实扫描渲染输入值

        # 解析 inspect_project 需要的 framework 项目事实。
        str_framework = "go"  # 项目事实扫描渲染输入值

    # 汇总 skill files ，作为 AGENTS 渲染的项目事实候选清单。
    skill_files = sorted(path for path in root.glob("*/SKILL.md") if path.is_file())  # 项目事实扫描渲染输入值

    # 调用 extend 处理 inspect_project。
    skill_files.extend(sorted(path for path in root.glob("skills/*/SKILL.md") if path.is_file()))

    # 校验 inspect_project 分支条件。
    if (root / "SKILL.md").exists() or skill_files:

        # 校验 inspect_project 分支条件。
        if "skill" not in list_languages:

            # 追加 inspect_project 诊断。
            list_languages.append("skill")

        # 解析 inspect_project 需要的 project type 项目事实。
        str_project_type = "skill-repo"  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        if str_framework == "none":

            # 解析 inspect_project 需要的 framework 项目事实。
            str_framework = "codex-skill"  # 项目事实扫描渲染输入值

    # 汇总 ci ，作为 AGENTS 渲染的项目事实候选清单。
    list_ci: list[str] = []  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if (root / ".github" / "workflows").exists():

        # 追加 inspect_project 诊断。
        list_ci.append("github_actions")

    # 校验 inspect_project 分支条件。
    if (root / ".gitlab-ci.yml").exists():

        # 追加 inspect_project 诊断。
        list_ci.append("gitlab_ci")

    # 汇总 ai configs ，作为 AGENTS 渲染的项目事实候选清单。
    ai_configs = [name for name in [  # 项目事实扫描渲染输入值
        "AGENTS.md",  # 项目事实扫描渲染输入值
        "CLAUDE.md",  # 项目事实扫描渲染输入值
        "GEMINI.md",  # 项目事实扫描渲染输入值
        ".github/copilot-instructions.md",  # 项目事实扫描渲染输入值
        ".cursor",  # 项目事实扫描渲染输入值
        ".claude",  # 项目事实扫描渲染输入值
        ".windsurf",  # 项目事实扫描渲染输入值
    ] if (root / name).exists()]  # 项目事实扫描渲染输入值

    # 定位 root agents path 的文件边界，供 inspect_project 后续读写校验使用。
    root_agents_path = root / "AGENTS.md"  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 root agents text 项目事实。
    root_agents_text = root_agents_path.read_text(encoding="utf-8", errors="ignore") if root_agents_path.is_file() else ""  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 agents metadata 项目事实。
    agents_metadata = parse_agents_metadata(root_agents_text)  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 profile 项目事实。
    profile = read_json(root / ".agents" / "agents-control.json")  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 installed version 项目事实。
    installed_version = read_installed_skill_version()  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 runtime version 项目事实。
    runtime_version = read_skill_version()  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 project skill version 项目事实。
    project_skill_version = read_skill_version(root / "skills" / "agents-md-generator")  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 expected agents version 项目事实。
    expected_agents_version = project_skill_version or installed_version  # 项目事实扫描渲染输入值

    # 汇总 trigger reasons ，作为 AGENTS 渲染的项目事实候选清单。
    list_trigger_reasons: list[str] = []  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if not root_agents_path.is_file():

        # 追加 inspect_project 诊断。
        list_trigger_reasons.append("missing_root_agents_md")
    else:

        # 解析 inspect_project 需要的 agents version 项目事实。
        agents_version = agents_metadata.get("agents_version", "")  # 项目事实扫描渲染输入值

        # 解析 inspect_project 需要的 generator version 项目事实。
        generator_version = agents_metadata.get("generator_version", "")  # 项目事实扫描渲染输入值

        # 校验 inspect_project 分支条件。
        if not agents_version:

            # 追加 inspect_project 诊断。
            list_trigger_reasons.append("missing_agents_version")

        # 校验 inspect_project 分支条件。
        if not generator_version:

            # 追加 inspect_project 诊断。
            list_trigger_reasons.append("missing_generator_version")

        # 校验 inspect_project 分支条件。
        if not expected_agents_version:

            # 追加 inspect_project 诊断。
            list_trigger_reasons.append("installed_skill_version_unavailable")
        else:

            # 校验 inspect_project 分支条件。
            if agents_version and agents_version != expected_agents_version:

                # 追加 inspect_project 诊断。
                list_trigger_reasons.append("agents_version_mismatch")

            # 校验 inspect_project 分支条件。
            if generator_version and generator_version != expected_agents_version:

                # 追加 inspect_project 诊断。
                list_trigger_reasons.append("generator_version_mismatch")

    # 汇总 repair reasons ，作为 AGENTS 渲染的项目事实候选清单。
    set_repair_reasons = {  # 项目事实扫描渲染输入值
        "missing_agents_version",  # 项目事实扫描渲染输入值
        "missing_generator_version",  # 项目事实扫描渲染输入值
        "agents_version_mismatch",  # 项目事实扫描渲染输入值
        "generator_version_mismatch",  # 项目事实扫描渲染输入值
    }

    # 解析 inspect_project 需要的 repair command 项目事实。
    repair_command = root_agents_sync_command(root, profile) if any(reason in set_repair_reasons for reason in list_trigger_reasons) else ""  # 项目事实扫描渲染输入值

    # 汇总 matched sessions ，作为 AGENTS 渲染的项目事实候选清单。
    list_matched_sessions = matched_codex_sessions(root)  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 session bootstrap required 项目事实。
    session_bootstrap_required = (not root_agents_path.is_file()) and workspace_has_existing_content(root)  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 global codex 项目事实。
    global_codex = global_codex_agents_status(project_root=root, profile=profile)  # 项目事实扫描渲染输入值

    # 标记 structure fix confirmation required 判断，控制 inspect_project 的分支走向。
    bool_structure_fix_confirmation_required = False  # 项目事实扫描渲染输入值

    # 汇总 structure fix reasons ，作为 AGENTS 渲染的项目事实候选清单。
    list_structure_fix_reasons: list[str] = []  # 项目事实扫描渲染输入值

    # 校验 inspect_project 分支条件。
    if isinstance(profile, dict):

        # 解析 inspect_project 需要的 contract 项目事实。
        contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}  # 项目事实扫描渲染输入值

        # 解析 inspect_project 需要的 primary root 项目事实。
        primary_root = str(contract.get("primary_project_root", "")).strip().strip("/")  # 项目事实扫描渲染输入值

        # 汇总 allowed root files ，作为 AGENTS 渲染的项目事实候选清单。
        allowed_root_files = {  # 项目事实扫描渲染输入值
            str(item).strip()  # 项目事实扫描渲染输入值
            for item in contract.get("allowed_root_files", ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".gitignore", ".gitattributes", ".editorconfig"])  # 项目事实扫描渲染输入值
            if str(item).strip()  # 项目事实扫描渲染输入值
        }

        # 校验 inspect_project 分支条件。
        if primary_root and not (root / primary_root).exists():

            # 标记 structure fix confirmation required 判断，控制 inspect_project 的分支走向。
            bool_structure_fix_confirmation_required = True  # 项目事实扫描渲染输入值

            # 追加 inspect_project 诊断。
            list_structure_fix_reasons.append(f"missing primary project root `{primary_root}/`")

        # 汇总 allowed roots ，作为 AGENTS 渲染的项目事实候选清单。
        allowed_roots = {  # 项目事实扫描渲染输入值
            str(item).strip().strip("/").split("/", 1)[0]  # 项目事实扫描渲染输入值
            for item in contract.get("allowed_new_paths", [])  # 项目事实扫描渲染输入值
            if str(item).strip()  # 项目事实扫描渲染输入值
        }

        # 校验 inspect_project 分支条件。
        if allowed_roots:

            # 逐项检查 inspect_project 候选项。
            for child in root.iterdir():

                # 校验 inspect_project 分支条件。
                if child.is_file():

                    # 校验 inspect_project 分支条件。
                    if not is_allowed_root_file(child.name, allowed_root_files):

                        # 标记 structure fix confirmation required 判断，控制 inspect_project 的分支走向。
                        bool_structure_fix_confirmation_required = True  # 项目事实扫描渲染输入值

                        # 追加 inspect_project 诊断。
                        list_structure_fix_reasons.append(f"root-level file requires review: `{child.name}`")

                    # 分隔 inspect_project 的控制流边界。
                    continue

                # 校验 inspect_project 分支条件。
                if child.name in SKIP_DIRS or child.name in {".agents", "AGENTS.md"}:

                    # 分隔 inspect_project 的控制流边界。
                    continue

                # 校验 inspect_project 分支条件。
                if child.name not in allowed_roots:

                    # 标记 structure fix confirmation required 判断，控制 inspect_project 的分支走向。
                    bool_structure_fix_confirmation_required = True  # 项目事实扫描渲染输入值

                    # 追加 inspect_project 诊断。
                    list_structure_fix_reasons.append(f"top-level path requires review: `{child.name}`")

        # 逐项检查 inspect_project 候选项。
        for legacy in [root / "HANDOFF.md", root / "DEVELOPMENT.md", root / "experience", root / "docs" / "HANDOFF.md", root / "docs" / "DEVELOPMENT.md"]:

            # 校验 inspect_project 分支条件。
            if legacy.exists():

                # 标记 structure fix confirmation required 判断，控制 inspect_project 的分支走向。
                bool_structure_fix_confirmation_required = True  # 项目事实扫描渲染输入值

                # 追加 inspect_project 诊断。
                list_structure_fix_reasons.append(f"legacy docs path requires migration: `{display_path(legacy, root)}`")

    # 汇总 constraints ，作为 AGENTS 渲染的项目事实候选清单。
    dict_constraints = implementation_constraints_from_profile(profile, root)  # 项目事实扫描渲染输入值

    # 解析 inspect_project 需要的 source governance 项目事实。
    source_governance = source_governance_report(root, profile)  # 项目事实扫描渲染输入值

    # 保存 script layout 映射，维持 inspect_project 的字段关系。
    dict_script_layout = script_layout_facts(root, profile)  # 项目事实扫描渲染输入值

    # 汇总 overrides ，作为 AGENTS 渲染的项目事实候选清单。
    dict_overrides = load_global_rule_overrides(root, profile)  # 项目事实扫描渲染输入值

    # 从源码后缀补充语言事实，覆盖无 pyproject/package 配置的小项目。
    set_source_suffix_languages = {  # 源码后缀到语言名映射
        ".py": "python",
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".v": "verilog",
        ".sv": "systemverilog",
        ".bat": "script",
        ".cmd": "script",
        ".sh": "script",
        ".ps1": "script",
        ".psm1": "script",
        ".tcl": "script",
    }
    for path_source in root.rglob("*"):
        if not path_source.is_file() or any(part in SKIP_DIRS for part in path_source.relative_to(root).parts):
            continue
        str_language = set_source_suffix_languages.get(path_source.suffix.lower())
        if str_language and str_language not in list_languages:
            list_languages.append(str_language)

    # 返回 inspect_project 调用载荷。
    return {
        "project_root": str(root),
        "root_agents_md_exists": root_agents_path.is_file(),
        "root_agents_md_metadata": agents_metadata,
        "root_agents_md_version": agents_metadata.get("agents_version", ""),
        "root_agents_md_generator_version": agents_metadata.get("generator_version", ""),
        "root_agents_md_default_language": agents_metadata.get("default_language", ""),
        "current_skill_version": runtime_version,
        "installed_skill_version": installed_version,
        "root_agents_md_trigger_required": bool(list_trigger_reasons),
        "root_agents_md_trigger_reasons": list_trigger_reasons,
        "root_agents_md_rebuild_required": bool(list_trigger_reasons),
        "root_agents_md_rebuild_reasons": list_trigger_reasons,
        "root_agents_md_repair_command": repair_command,
        "global_codex_agents_exists": global_codex["exists"],
        "global_codex_agents_empty": global_codex["empty"],
        "global_codex_agents_managed": global_codex["managed"],
        "global_codex_agents_baseline_ok": global_codex["baseline_ok"],
        "global_codex_agents_repair_required": global_codex["repair_required"],
        "global_codex_agents_repair_reasons": global_codex["repair_reasons"],
        "global_codex_agents_repair_command": global_codex["repair_command"],
        "global_codex_agents_requires_user_confirmation": global_codex["requires_user_confirmation"],
        "session_history_bootstrap_required": session_bootstrap_required,
        "session_history_match_scope": "exact-cwd",
        "matched_session_count": len(list_matched_sessions),
        "matched_session_ids": [item["id"] for item in list_matched_sessions if item["id"]],
        "matched_session_paths": [item["path"] for item in list_matched_sessions],
        "structure_fix_confirmation_required": bool_structure_fix_confirmation_required,
        "structure_fix_default": "yes",
        "structure_fix_reasons": list_structure_fix_reasons,
        "implementation_constraints": dict_constraints,
        "global_rule_overrides_path": dict_overrides["path"].relative_to(root).as_posix(),
        "global_rule_overrides_exists": dict_overrides["exists"],
        "global_rule_overrides_valid": not dict_overrides["errors"],
        "global_rule_overrides_errors": list(dict_overrides["errors"]),
        "global_rule_overrides": dict_overrides["data"],
        "source_governance": source_governance,
        "oversized_source_files": source_governance["oversized_source_files"],
        "test_code_boundary_violations": source_governance["test_code_boundary_violations"],
        "comment_policy_violations": source_governance["comment_policy_violations"],
        "tool_script_layout_violations": dict_script_layout["tool_script_layout_violations"],
        "script_triad_gaps": dict_script_layout["script_triad_gaps"],
        "gui_script_exemptions": dict_script_layout["gui_script_exemptions"],
        "primary_language": list_languages[0] if list_languages else "unknown",
        "languages": sorted(set(list_languages)),
        "package_manager": package_manager(root),
        "framework": str_framework,
        "project_type": str_project_type,
        "ci": list_ci,
        "ai_configs": ai_configs,
        "config_files": config_files,
        "directories": list_dirs(root),
        "files": list_files(root),
    }

# 定义 command_entry 的项目事实处理入口。
def command_entry(task: str, command: str, source: str, notes: str = "", seconds: str = "") -> dict[str, str]:

    # 返回 command_entry 调用载荷。
    return {
        "task": task,
        "command": command,
        "source": source,
        "notes": notes,
        "time": seconds or "~30s",
        "verified": "false",
    }

# 定义 extract_commands 的项目事实处理入口。
def extract_commands(root: Path) -> dict[str, Any]:

    # 汇总 commands ，作为 AGENTS 渲染的项目事实候选清单。
    list_commands: list[dict[str, str]] = []  # 项目事实扫描渲染输入值

    # 解析 extract_commands 需要的 makefile 项目事实。
    makefile = root / "Makefile"  # 项目事实扫描渲染输入值

    # 校验 extract_commands 分支条件。
    if makefile.exists():

        # 解析 extract_commands 需要的 text 项目事实。
        text = makefile.read_text(encoding="utf-8", errors="ignore")  # 项目事实扫描渲染输入值

        # 汇总 targets ，作为 AGENTS 渲染的项目事实候选清单。
        set_targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))  # 项目事实扫描渲染输入值

        # 保存 mapping 映射，维持 extract_commands 的字段关系。
        dict_mapping = {  # 项目事实扫描渲染输入值
            "Setup": ["setup", "install"],  # 项目事实扫描渲染输入值
            "Run": ["dev", "serve", "run"],  # 项目事实扫描渲染输入值
            "Format": ["format", "fmt"],  # 项目事实扫描渲染输入值
            "Lint": ["lint", "check"],  # 项目事实扫描渲染输入值
            "Test (all)": ["test", "tests"],  # 项目事实扫描渲染输入值
            "Build": ["build"],  # 项目事实扫描渲染输入值
            "Typecheck": ["typecheck", "types"],  # 项目事实扫描渲染输入值
        }

        # 逐项检查 extract_commands 候选项。
        for str_task, candidates in dict_mapping.items():

            # 逐项检查 extract_commands 候选项。
            for target in candidates:

                # 校验 extract_commands 分支条件。
                if target in set_targets:

                    # 追加 extract_commands 诊断。
                    list_commands.append(command_entry(str_task, f"make {target}", "Makefile"))

                    # 分隔 extract_commands 的控制流边界。
                    break

    # 解析 extract_commands 需要的 package json 项目事实。
    package_json = read_json(root / "package.json")  # 项目事实扫描渲染输入值

    # 校验 extract_commands 分支条件。
    if package_json:

        # 汇总 scripts ，作为 AGENTS 渲染的项目事实候选清单。
        scripts = package_json.get("scripts", {})  # 项目事实扫描渲染输入值

        # 汇总 scripts ，作为 AGENTS 渲染的项目事实候选清单。
        scripts = scripts if isinstance(scripts, dict) else {}  # 项目事实扫描渲染输入值

        # 解析 extract_commands 需要的 pm 项目事实。
        pm = package_manager(root)  # 项目事实扫描渲染输入值

        # 解析 extract_commands 需要的 run 项目事实。
        run = pm_run(pm)  # 项目事实扫描渲染输入值

        # 解析 extract_commands 需要的 dlx 项目事实。
        dlx = pm_dlx(pm)  # 项目事实扫描渲染输入值

        # 校验 extract_commands 分支条件。
        if scripts:

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Setup", f"{pm} install", "lockfile/package.json", "~install dependencies"))

        # 保存 script map 映射，维持 extract_commands 的字段关系。
        dict_script_map = {  # 项目事实扫描渲染输入值
            "Run": ["dev", "start"],  # 项目事实扫描渲染输入值
            "Format": ["format", "fmt"],  # 项目事实扫描渲染输入值
            "Lint": ["lint"],  # 项目事实扫描渲染输入值
            "Test (all)": ["test"],  # 项目事实扫描渲染输入值
            "Build": ["build"],  # 项目事实扫描渲染输入值
            "Typecheck": ["typecheck", "type-check", "types"],  # 项目事实扫描渲染输入值
        }

        # 逐项检查 extract_commands 候选项。
        for str_task, names in dict_script_map.items():

            # 逐项检查 extract_commands 候选项。
            for name in names:

                # 校验 extract_commands 分支条件。
                if name in scripts:

                    # 解析 extract_commands 需要的 cmd 项目事实。
                    cmd = f"{pm} test" if str_task == "Test (all)" and pm in {"npm", "pnpm"} else f"{run} {name}"  # 项目事实扫描渲染输入值

                    # 追加 extract_commands 诊断。
                    list_commands.append(command_entry(str_task, cmd, "package.json"))

                    # 分隔 extract_commands 的控制流边界。
                    break

        # 解析 extract_commands 需要的 deps text 项目事实。
        deps_text = json.dumps(package_json)  # 项目事实扫描渲染输入值

        # 校验 extract_commands 分支条件。
        if "vitest" in deps_text:

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Test (single)", f"{dlx} vitest run", "package.json", "~single test file", "~2s"))

        # 校验 extract_commands 分支条件。
        elif "jest" in deps_text:

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Test (single)", f"{dlx} jest", "package.json", "~single test file", "~2s"))

    # 解析 extract_commands 需要的 pyproject 项目事实。
    pyproject = root / "pyproject.toml"  # 项目事实扫描渲染输入值

    # 校验 extract_commands 分支条件。
    if pyproject.exists():

        # 解析 extract_commands 需要的 text 项目事实。
        text = pyproject.read_text(encoding="utf-8", errors="ignore")  # 项目事实扫描渲染输入值

        # 校验 extract_commands 分支条件。
        if "[tool.ruff" in text:

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Lint", "ruff check .", "pyproject.toml", "", "~10s"))

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Format", "ruff format .", "pyproject.toml", "", "~5s"))

        # 校验 extract_commands 分支条件。
        if "mypy" in text:

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Typecheck", "mypy .", "pyproject.toml", "", "~15s"))

        # 校验 extract_commands 分支条件。
        if "pytest" in text or (root / "tests").exists():

            # 追加 extract_commands 诊断。
            list_commands.append(command_entry("Test (all)", "pytest", "pyproject.toml/tests", "", "~30s"))

    # 解析 extract_commands 需要的 composer 项目事实。
    composer = read_json(root / "composer.json")  # 项目事实扫描渲染输入值

    # 校验 extract_commands 分支条件。
    if composer:

        # 汇总 scripts ，作为 AGENTS 渲染的项目事实候选清单。
        scripts = composer.get("scripts", {}) if isinstance(composer.get("scripts"), dict) else {}  # 项目事实扫描渲染输入值

        # 逐项检查 extract_commands 候选项。
        for str_task, names in {
            "Lint": ["lint", "cs:check"],
            "Format": ["format", "cs:fix"],
            "Test (all)": ["test"],
            "Typecheck": ["phpstan", "stan"],
        }.items():

            # 逐项检查 extract_commands 候选项。
            for name in names:

                # 校验 extract_commands 分支条件。
                if name in scripts:

                    # 追加 extract_commands 诊断。
                    list_commands.append(command_entry(str_task, f"composer run {name}", "composer.json"))

                    # 分隔 extract_commands 的控制流边界。
                    break

    # 校验 extract_commands 分支条件。
    if (root / "go.mod").exists():

        # 调用 extend 处理 extract_commands。
        list_commands.extend([
            command_entry("Format", "gofmt -w .", "go.mod", "", "~5s"),
            command_entry("Test (all)", "go test ./...", "go.mod", "", "~30s"),
            command_entry("Build", "go build ./...", "go.mod", "", "~30s"),
        ])

    # 解析 extract_commands 需要的 workflow dir 项目事实。
    workflow_dir = root / ".github" / "workflows"  # 项目事实扫描渲染输入值

    # 校验 extract_commands 分支条件。
    if workflow_dir.exists():

        # 逐项检查 extract_commands 候选项。
        for workflow in sorted(workflow_dir.glob("*.y*ml")):

            # 解析 extract_commands 需要的 text 项目事实。
            text = workflow.read_text(encoding="utf-8", errors="ignore")  # 项目事实扫描渲染输入值

            # 逐项检查 extract_commands 候选项。
            for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):

                # 解析 extract_commands 需要的 command 项目事实。
                command = (raw[0] or raw[1]).strip().strip("'\"")  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                if not command or command.startswith(("|", ">")):

                    # 分隔 extract_commands 的控制流边界。
                    continue

                # 解析 extract_commands 需要的 first line 项目事实。
                first_line = command.splitlines()[0].strip()  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                if not first_line:

                    # 分隔 extract_commands 的控制流边界。
                    continue

                # 解析 extract_commands 需要的 lowered 项目事实。
                lowered = first_line.lower()  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                if any(token in lowered for token in ("lint", "eslint", "ruff", "phpstan")):

                    # 解析 extract_commands 需要的 task 项目事实。
                    str_task = "CI Lint"  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                elif any(token in lowered for token in ("test", "pytest", "vitest", "jest", "go test")):

                    # 解析 extract_commands 需要的 task 项目事实。
                    str_task = "CI Test"  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                elif any(token in lowered for token in ("build", "compile")):

                    # 解析 extract_commands 需要的 task 项目事实。
                    str_task = "CI Build"  # 项目事实扫描渲染输入值

                # 校验 extract_commands 分支条件。
                elif any(token in lowered for token in ("typecheck", "type-check", "tsc", "mypy")):

                    # 解析 extract_commands 需要的 task 项目事实。
                    str_task = "CI Typecheck"  # 项目事实扫描渲染输入值
                else:

                    # 解析 extract_commands 需要的 task 项目事实。
                    str_task = "CI Command"  # 项目事实扫描渲染输入值

                # 追加 extract_commands 诊断。
                list_commands.append(command_entry(str_task, first_line, rel(workflow, root)))

    # 解析 extract_commands 需要的 seen 项目事实。
    set_seen: set[tuple[str, str]] = set()  # 项目事实扫描渲染输入值

    # 汇总 unique ，作为 AGENTS 渲染的项目事实候选清单。
    list_unique = []  # 项目事实扫描渲染输入值

    # 逐项检查 extract_commands 候选项。
    for item in list_commands:

        # 解析 extract_commands 需要的 key 项目事实。
        tuple_key = (item["task"], item["command"])  # 项目事实扫描渲染输入值

        # 校验 extract_commands 分支条件。
        if tuple_key not in set_seen:

            # 调用 add 处理 extract_commands。
            set_seen.add(tuple_key)

            # 追加 extract_commands 诊断。
            list_unique.append(item)

    # 返回 extract_commands 调用载荷。
    return {"commands": list_unique}

# 定义 workflow_runs 的项目事实处理入口。
def workflow_runs(root: Path) -> list[dict[str, str]]:

    # 汇总 rules ，作为 AGENTS 渲染的项目事实候选清单。
    list_rules: list[dict[str, str]] = []  # 项目事实扫描渲染输入值

    # 解析 workflow_runs 需要的 workflow dir 项目事实。
    workflow_dir = root / ".github" / "workflows"  # 项目事实扫描渲染输入值

    # 校验 workflow_runs 分支条件。
    if not workflow_dir.exists():

        # 返回 workflow_runs 调用载荷。
        return list_rules

    # 逐项检查 workflow_runs 候选项。
    for workflow in sorted(workflow_dir.glob("*.y*ml")):

        # 解析 workflow_runs 需要的 text 项目事实。
        text = workflow.read_text(encoding="utf-8", errors="ignore")  # 项目事实扫描渲染输入值

        # 逐项检查 workflow_runs 候选项。
        for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):

            # 解析 workflow_runs 需要的 command 项目事实。
            command = (raw[0] or raw[1]).strip().strip("'\"")  # 项目事实扫描渲染输入值

            # 校验 workflow_runs 分支条件。
            if not command or command.startswith(("|", ">")):

                # 分隔 workflow_runs 的控制流边界。
                continue

            # 解析 workflow_runs 需要的 first line 项目事实。
            first_line = command.splitlines()[0].strip()  # 项目事实扫描渲染输入值

            # 校验 workflow_runs 分支条件。
            if first_line:

                # 追加 workflow_runs 诊断。
                list_rules.append({"workflow": rel(workflow, root), "command": first_line})

    # 返回 workflow_runs 调用载荷。
    return list_rules

# 定义 default_global_rule_overrides 的项目事实处理入口。
def default_global_rule_overrides() -> dict[str, Any]:

    # 返回 default_global_rule_overrides 调用载荷。
    return source_governance_config.default_global_rule_overrides()


# 定义 default_implementation_constraints 的项目事实处理入口。
def default_implementation_constraints() -> dict[str, Any]:

    # 返回 default_implementation_constraints 调用载荷。
    return source_governance_config.default_implementation_constraints()


# 定义 global_rule_overrides_reference 的项目事实处理入口。
def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:

    # 返回 global_rule_overrides_reference 调用载荷。
    return source_governance_config.global_rule_overrides_reference(profile)


# 定义 global_rule_overrides_path 的项目事实处理入口。
def global_rule_overrides_path(root: Path, profile: dict[str, Any] | None = None) -> Path:

    # 返回 global_rule_overrides_path 调用载荷。
    return source_governance_config.global_rule_overrides_path(root, profile)
