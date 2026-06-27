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

# 导入 技能安装 所需的依赖模块。
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

# 分隔当前密集代码块，保留原有执行顺序。
import subprocess
import sys
from typing import Any
from datetime import datetime

# 提取 模块入口 使用的 dont write bytecode 安装校验值。
sys.dont_write_bytecode = True  # 技能安装校验复制输入值
from agents_common import emit_json, global_codex_agents_status, resolve_project
from agents_decisions import decision_request
from release_content_policy import (
    POLICY_VERSION,
    analyze_release_content_root,
    validate_recorded_release_content_policy,
)
from version_policy import version_policy_error

# 提取 模块入口 使用的 ACTIVE SESSION PATH 安装校验值。
ACTIVE_SESSION_PATH = ".agents/active-session.json"  # 技能安装校验复制输入值


# 定义 fail_json 的技能安装处理入口。
def fail_json(message: str) -> None:

    # 调用 emit_json 处理 fail_json。
    emit_json({"errors": [message]})

    # 抛出 fail_json 已确认的阻断原因。
    raise SystemExit(1)


# 定义 parse_skill_name 的技能安装处理入口。
def parse_skill_name(skill_dir: Path) -> str:

    # 提取 parse_skill_name 使用的 text 安装校验值。
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="ignore")  # 技能安装校验复制输入值

    # 提取 parse_skill_name 使用的 match 安装校验值。
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)  # 技能安装校验复制输入值

    # 校验 parse_skill_name 的安装安全分支。
    if not match:

        # 抛出 parse_skill_name 已确认的阻断原因。
        raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter is required"]}, indent=2))

    # 逐项检查 parse_skill_name 候选项。
    for line in match.group(1).splitlines():

        # 校验 parse_skill_name 的安装安全分支。
        if line.strip().startswith("name:"):

            # 返回 parse_skill_name 的安装流程载荷。
            return line.split(":", 1)[1].strip().strip("\"'")

    # 抛出 parse_skill_name 已确认的阻断原因。
    raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter must include name"]}, indent=2))


# 定义 parse_release_dir 的技能安装处理入口。
def parse_release_dir(release_dir: Path) -> tuple[str, str]:

    # 提取 parse_release_dir 使用的 match 安装校验值。
    match = re.fullmatch(r"(.+)-(v\d+\.\d+\.\d+)", release_dir.name)  # 技能安装校验复制输入值

    # 校验 parse_release_dir 的安装安全分支。
    if not match:

        # 调用 fail_json 处理 parse_release_dir。
        fail_json(f"release directory must be a versioned release directory like <name>-vX.Y.Z: {release_dir}")

    # release 目录名本身必须满足当前版本策略，避免安装历史误发版本。
    str_version_error = version_policy_error(match.group(2))  # 技能安装版本策略诊断

    # 校验 parse_release_dir 的安装安全分支。
    if str_version_error:

        # 调用 fail_json 处理 parse_release_dir。
        fail_json(str_version_error)

    # 返回 parse_release_dir 的安装流程载荷。
    return match.group(1), match.group(2)


# 定义 default_codex_home 的技能安装处理入口。
def default_codex_home(raw: str | None) -> Path:

    # 校验 default_codex_home 的安装安全分支。
    if raw:

        # 返回 default_codex_home 的安装流程载荷。
        return Path(raw).expanduser().resolve()

    # 提取 default_codex_home 使用的 env home 安装校验值。
    env_home = os.environ.get("CODEX_HOME")  # 技能安装校验复制输入值

    # 校验 default_codex_home 的安装安全分支。
    if env_home:

        # 返回 default_codex_home 的安装流程载荷。
        return Path(env_home).expanduser().resolve()

    # 返回 default_codex_home 的安装流程载荷。
    return (Path.home() / ".codex").resolve()


# 定义 install_options 的技能安装处理入口。
def install_options() -> list[dict[str, Any]]:

    # 返回 install_options 的安装流程载荷。
    return [
        {
            "label": "否，跳过安装",
            "value": "skip",
            "description": "默认选项；不复制发布包到任何 skills 目录。",
            "recommended": True,
        },
        {
            "label": "安装到 Codex",
            "value": "codex",
            "description": "复制到 $CODEX_HOME/skills/<skill-name> 或 ~/.codex/skills/<skill-name>。",
            "recommended": False,
        },
        {
            "label": "自定义 skills 目录",
            "value": "custom",
            "description": "复制到用户提供的 skills 根目录下的 <skill-name>。",
            "recommended": False,
        },
    ]


# 定义 sha256_file 的技能安装处理入口。
def sha256_file(path: Path) -> str:

    # 提取 sha256_file 使用的 digest 安装校验值。
    digest = hashlib.sha256()  # 技能安装校验复制输入值

    # 限定 sha256_file 的文件或资源访问范围。
    with path.open("rb") as handle:

        # 逐项检查 sha256_file 候选项。
        for chunk in iter(lambda: handle.read(65536), b""):

            # 调用 update 处理 sha256_file。
            digest.update(chunk)

    # 返回 sha256_file 的安装流程载荷。
    return digest.hexdigest()


# 定义 read_receipt 的技能安装处理入口。
def read_receipt(release_dir: Path) -> tuple[Path, dict[str, Any]]:

    # 定位 receipt path 的文件边界，供 read_receipt 后续读写校验使用。
    receipt_path = release_dir / "RELEASE_RECEIPT.json"  # 技能安装校验复制输入值

    # 校验 read_receipt 的安装安全分支。
    if not receipt_path.is_file():

        # 调用 fail_json 处理 read_receipt。
        fail_json(f"missing RELEASE_RECEIPT.json: {receipt_path}")

    # 保护 read_receipt 中允许失败的外部访问。
    try:

        # 提取 read_receipt 使用的 data 安装校验值。
        dict_data = json.loads(receipt_path.read_text(encoding="utf-8"))  # 技能安装校验复制输入值
    except Exception:

        # 调用 fail_json 处理 read_receipt。
        fail_json(f"invalid RELEASE_RECEIPT.json: {receipt_path}")

    # 校验 read_receipt 的安装安全分支。
    if not isinstance(dict_data, dict):

        # 调用 fail_json 处理 read_receipt。
        fail_json(f"invalid RELEASE_RECEIPT.json: {receipt_path}")

    # 返回 read_receipt 的安装流程载荷。
    return receipt_path, dict_data


# 定义 is_probably_text_bytes 的技能安装处理入口。
def is_probably_text_bytes(data: bytes) -> bool:

    # 校验 is_probably_text_bytes 的安装安全分支。
    if b"\x00" in data:

        # 返回 is_probably_text_bytes 的安装流程载荷。
        return False

    # 保护 is_probably_text_bytes 中允许失败的外部访问。
    try:

        # 调用 decode 处理 is_probably_text_bytes。
        data.decode("utf-8")
    except UnicodeDecodeError:

        # 返回 is_probably_text_bytes 的安装流程载荷。
        return False

    # 返回 is_probably_text_bytes 的安装流程载荷。
    return True


# 定义 normalize_line_endings 的技能安装处理入口。
def normalize_line_endings(text: str) -> str:

    # 返回 normalize_line_endings 的安装流程载荷。
    return text.replace("\r\n", "\n")


# 提取 模块入口 使用的 SANITIZED PLACEHOLDERS 安装校验值。
SANITIZED_PLACEHOLDERS = {  # 技能安装校验复制输入值
    "api_key": "<REDACTED_API_KEY>",  # 技能安装校验复制输入值
    "password": "<REDACTED_PASSWORD>",  # 技能安装校验复制输入值
    "email": "<REDACTED_EMAIL>",  # 技能安装校验复制输入值
    "local_path": "<REDACTED_LOCAL_PATH>",  # 技能安装校验复制输入值
}

# 提取 模块入口 使用的 SANITIZED ASSIGNMENT RULES 安装校验值。
SANITIZED_ASSIGNMENT_RULES = [  # 技能安装校验复制输入值
    (  # 技能安装校验复制输入值
        "api_key",  # 技能安装校验复制输入值
        re.compile(r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET)(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"),  # 技能安装校验复制输入值
    ),  # 技能安装校验复制输入值
    (  # 技能安装校验复制输入值
        "password",  # 技能安装校验复制输入值
        re.compile(r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),  # 技能安装校验复制输入值
    ),  # 技能安装校验复制输入值
]

# 提取 模块入口 使用的 LOCAL PRIVATE PATH RE 安装校验值。
LOCAL_PRIVATE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[^\s\"'`<>\),\]}]+")  # 技能安装校验复制输入值

# 提取 模块入口 使用的 SANITIZED INLINE RULES 安装校验值。
SANITIZED_INLINE_RULES = [  # 技能安装校验复制输入值
    ("email", re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)),  # 技能安装校验复制输入值
    ("local_path", LOCAL_PRIVATE_PATH_RE),  # 技能安装校验复制输入值
]

# 提取 模块入口 使用的 SANITIZED BINARY PATTERNS 安装校验值。
SANITIZED_BINARY_PATTERNS = [  # 技能安装校验复制输入值
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),  # 技能安装校验复制输入值
    ("password", re.compile(br"password", flags=re.IGNORECASE)),  # 技能安装校验复制输入值
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),  # 技能安装校验复制输入值
]

# 提取 模块入口 使用的 RELEASE REQUIRED REFERENCE PREFIXES 安装校验值。
RELEASE_REQUIRED_REFERENCE_PREFIXES = ("runtime/", "integration/", "config/", "scripts/", "references/", "agents/", "assets/")  # 技能安装校验复制输入值


# 定义 should_skip_sanitized_assignment_value 的技能安装处理入口。
def should_skip_sanitized_assignment_value(value: str) -> bool:

    # 返回 should_skip_sanitized_assignment_value 的安装流程载荷。
    return value.strip().startswith("re.compile(")


# 定义 sanitize_release_text 的技能安装处理入口。
def sanitize_release_text(text: str) -> tuple[str, list[dict[str, str]]]:

    # 提取 sanitize_release_text 使用的 redacted 安装校验值。
    redacted = text  # 技能安装校验复制输入值

    # 汇总 matches ，作为技能安装校验和复制候选清单。
    list_matches: list[dict[str, str]] = []  # 技能安装校验复制输入值

    # 逐项检查 sanitize_release_text 候选项。
    for rule_name, pattern in SANITIZED_ASSIGNMENT_RULES:

        # 提取 sanitize_release_text 使用的 placeholder 安装校验值。
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]  # 技能安装校验复制输入值

        # 提取 sanitize_release_text 使用的 hit 安装校验值。
        bool_hit = False  # 技能安装校验复制输入值

        # 定义 replace_assignment 的技能安装处理入口。
        def replace_assignment(match: re.Match[str]) -> str:
            nonlocal bool_hit

            # 校验 replace_assignment 的安装安全分支。
            if should_skip_sanitized_assignment_value(match.group(2)):

                # 返回 replace_assignment 的安装流程载荷。
                return match.group(0)

            # 提取 replace_assignment 使用的 hit 安装校验值。
            bool_hit = True  # 技能安装校验复制输入值

            # 返回 replace_assignment 的安装流程载荷。
            return f"{match.group(1)}{placeholder}"

        # 提取 sanitize_release_text 使用的 updated 安装校验值。
        updated = pattern.sub(replace_assignment, redacted)  # 技能安装校验复制输入值

        # 校验 sanitize_release_text 的安装安全分支。
        if bool_hit:

            # 追加 sanitize_release_text 诊断。
            list_matches.append({"rule": rule_name, "placeholder": placeholder})

            # 提取 sanitize_release_text 使用的 redacted 安装校验值。
            redacted = updated  # 技能安装校验复制输入值

    # 逐项检查 sanitize_release_text 候选项。
    for rule_name, pattern in SANITIZED_INLINE_RULES:

        # 提取 sanitize_release_text 使用的 placeholder 安装校验值。
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]  # 技能安装校验复制输入值

        # 提取 sanitize_release_text 使用的 updated、count 安装校验值。
        updated, count = pattern.subn(placeholder, redacted)  # 技能安装校验复制输入值

        # 校验 sanitize_release_text 的安装安全分支。
        if count:

            # 追加 sanitize_release_text 诊断。
            list_matches.append({"rule": rule_name, "placeholder": placeholder})

            # 提取 sanitize_release_text 使用的 redacted 安装校验值。
            redacted = updated  # 技能安装校验复制输入值

    # 返回 sanitize_release_text 的安装流程载荷。
    return redacted, list_matches

# 定义 detect_binary_sensitive_matches 的技能安装处理入口。
def detect_binary_sensitive_matches(data: bytes) -> list[str]:

    # 汇总 hits ，作为技能安装校验和复制候选清单。
    list_hits: list[str] = []  # 技能安装校验复制输入值

    # 逐项检查 detect_binary_sensitive_matches 候选项。
    for rule_name, pattern in SANITIZED_BINARY_PATTERNS:

        # 校验 detect_binary_sensitive_matches 的安装安全分支。
        if pattern.search(data):

            # 追加 detect_binary_sensitive_matches 诊断。
            list_hits.append(rule_name)

    # 返回 detect_binary_sensitive_matches 的安装流程载荷。
    return sorted(set(list_hits))


# 定义 file_manifest 的技能安装处理入口。
def file_manifest(release_dir: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:

    # 提取 file_manifest 使用的 excluded 安装校验值。
    excluded = exclude or set()  # 技能安装校验复制输入值

    # 提取 file_manifest 使用的 manifest 安装校验值。
    list_manifest: list[dict[str, str]] = []  # 技能安装校验复制输入值

    # 逐项检查 file_manifest 候选项。
    for path in sorted(release_dir.rglob("*")):

        # 校验 file_manifest 的安装安全分支。
        if not path.is_file():

            # 分隔 file_manifest 的控制流边界。
            continue

        # 提取 file_manifest 使用的 relative 安装校验值。
        relative = path.relative_to(release_dir).as_posix()  # 技能安装校验复制输入值

        # 校验 file_manifest 的安装安全分支。
        if relative in excluded:

            # 分隔 file_manifest 的控制流边界。
            continue

        # 追加 file_manifest 诊断。
        list_manifest.append({"path": relative, "sha256": sha256_file(path)})

    # 返回 file_manifest 的安装流程载荷。
    return list_manifest


# 定义 referenced_release_paths 的技能安装处理入口。
def referenced_release_paths(skill_text: str) -> set[str]:

    # 汇总 paths ，作为技能安装校验和复制候选清单。
    set_paths: set[str] = set()  # 技能安装校验复制输入值

    # 逐项检查 referenced_release_paths 候选项。
    for raw in re.findall(r"`([^`]+)`", skill_text):

        # 提取 referenced_release_paths 使用的 value 安装校验值。
        raw_value = raw.strip()  # 技能安装校验复制输入值

        # 校验 referenced_release_paths 的安装安全分支。
        if "<" in raw_value or ">" in raw_value:

            # 分隔 referenced_release_paths 的控制流边界。
            continue

        # 校验 referenced_release_paths 的安装安全分支。
        if not raw_value.startswith(RELEASE_REQUIRED_REFERENCE_PREFIXES):

            # 分隔 referenced_release_paths 的控制流边界。
            continue

        # 调用 add 处理 referenced_release_paths。
        set_paths.add(raw_value.rstrip("/"))

    # 返回 referenced_release_paths 的安装流程载荷。
    return set_paths


# 定义 validate_release_completeness 的技能安装处理入口。
def validate_release_completeness(release_dir: Path, receipt: dict[str, Any]) -> list[str]:

    # 汇总 errors ，作为技能安装校验和复制候选清单。
    list_errors: list[str] = []  # 技能安装校验复制输入值

    # 定位 skill path 的文件边界，供 validate_release_completeness 后续读写校验使用。
    skill_path = release_dir / "SKILL.md"  # 技能安装校验复制输入值

    # 校验 validate_release_completeness 的安装安全分支。
    if not skill_path.is_file():

        # 返回 validate_release_completeness 的安装流程载荷。
        return ["release directory is missing SKILL.md"]

    # 提取 validate_release_completeness 使用的 actual manifest 安装校验值。
    actual_manifest = {  # 技能安装校验复制输入值
        item["path"]  # 技能安装校验复制输入值
        for item in file_manifest(release_dir, exclude={"RELEASE_RECEIPT.json"})  # 技能安装校验复制输入值
        if isinstance(item, dict) and str(item.get("path", "")).strip()  # 技能安装校验复制输入值
    }

    # 提取 validate_release_completeness 使用的 skill text 安装校验值。
    skill_text = skill_path.read_text(encoding="utf-8", errors="ignore")  # 技能安装校验复制输入值

    # 逐项检查 validate_release_completeness 候选项。
    for reference in sorted(referenced_release_paths(skill_text)):

        # 校验 validate_release_completeness 的安装安全分支。
        if reference in actual_manifest:

            # 分隔 validate_release_completeness 的控制流边界。
            continue

        # 校验 validate_release_completeness 的安装安全分支。
        if (release_dir / reference).exists():

            # 分隔 validate_release_completeness 的控制流边界。
            continue

        # 校验 validate_release_completeness 的安装安全分支。
        if any(path.startswith(reference + "/") for path in actual_manifest):

            # 分隔 validate_release_completeness 的控制流边界。
            continue

        # 追加 validate_release_completeness 诊断。
        list_errors.append(f"release directory is missing SKILL.md referenced path: {reference}")

    # 汇总 recorded files ，作为技能安装校验和复制候选清单。
    recorded_files = receipt.get("files")  # 技能安装校验复制输入值

    # 校验 validate_release_completeness 的安装安全分支。
    if isinstance(recorded_files, list):

        # 提取 validate_release_completeness 使用的 recorded manifest 安装校验值。
        recorded_manifest = {str(item.get("path", "")).strip() for item in recorded_files if isinstance(item, dict)}  # 技能安装校验复制输入值

        # 逐项检查 validate_release_completeness 候选项。
        for required_name in ("SKILL.md",):

            # 校验 validate_release_completeness 的安装安全分支。
            if required_name not in recorded_manifest:

                # 追加 validate_release_completeness 诊断。
                list_errors.append(f"release receipt is missing required file entry: {required_name}")

    # 返回 validate_release_completeness 的安装流程载荷。
    return list_errors


# 定义 normalize_branch_list_line 的技能安装处理入口。
def normalize_branch_list_line(line: str) -> str:

    # 返回 normalize_branch_list_line 的安装流程载荷。
    return line.strip().lstrip("*+ ").strip()


# 定义 parse_status_paths 的技能安装处理入口。
def parse_status_paths(line: str) -> list[str]:

    # 提取 parse_status_paths 使用的 body 安装校验值。
    body = line[3:].strip() if len(line) >= 4 else line.strip()  # 技能安装校验复制输入值

    # 校验 parse_status_paths 的安装安全分支。
    if " -> " in body:

        # 定位 old path、new path 的文件边界，供 parse_status_paths 后续读写校验使用。
        old_path, new_path = body.split(" -> ", 1)  # 技能安装校验复制输入值

        # 返回 parse_status_paths 的安装流程载荷。
        return [old_path.strip().replace("\\", "/"), new_path.strip().replace("\\", "/")]

    # 返回 parse_status_paths 的安装流程载荷。
    return [body.replace("\\", "/")]


# 定义 filter_runtime_status_lines 的技能安装处理入口。
def filter_runtime_status_lines(lines: list[str]) -> list[str]:

    # 提取 filter_runtime_status_lines 使用的 ignored 安装校验值。
    set_ignored = {ACTIVE_SESSION_PATH.replace("\\", "/")}  # 技能安装校验复制输入值

    # 提取 filter_runtime_status_lines 使用的 filtered 安装校验值。
    list_filtered: list[str] = []  # 技能安装校验复制输入值

    # 逐项检查 filter_runtime_status_lines 候选项。
    for line in lines:

        # 校验 filter_runtime_status_lines 的安装安全分支。
        if not line.strip():

            # 分隔 filter_runtime_status_lines 的控制流边界。
            continue

        # 汇总 paths ，作为技能安装校验和复制候选清单。
        paths = [path for path in parse_status_paths(line) if path and path not in set_ignored]  # 技能安装校验复制输入值

        # 校验 filter_runtime_status_lines 的安装安全分支。
        if paths:

            # 追加 filter_runtime_status_lines 诊断。
            list_filtered.append(line)

    # 返回 filter_runtime_status_lines 的安装流程载荷。
    return list_filtered


# 定义 infer_repo_root 的技能安装处理入口。
def infer_repo_root(release_dir: Path) -> Path | None:

    # 校验 infer_repo_root 的安装安全分支。
    if release_dir.parent.name != "dist":

        # 返回 infer_repo_root 的安装流程载荷。
        return None

    # 提取 infer_repo_root 使用的 root 安装校验值。
    root = release_dir.parent.parent  # 技能安装校验复制输入值

    # 校验 infer_repo_root 的安装安全分支。
    if not root.exists():

        # 返回 infer_repo_root 的安装流程载荷。
        return None

    # 提取 infer_repo_root 使用的 result 安装校验值。
    command_result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True, capture_output=True, check=False)  # 技能安装校验复制输入值

    # 校验 infer_repo_root 的安装安全分支。
    if command_result.returncode != 0:

        # 返回 infer_repo_root 的安装流程载荷。
        return None

    # 保护 infer_repo_root 中允许失败的外部访问。
    try:

        # 提取 infer_repo_root 使用的 repo root 安装校验值。
        repo_root = Path(command_result.stdout.strip()).resolve()  # 技能安装校验复制输入值
    except Exception:

        # 返回 infer_repo_root 的安装流程载荷。
        return None

    # 返回 infer_repo_root 的安装流程载荷。
    return repo_root if repo_root == root.resolve() else None


# 定义 source_skill_dir_from_receipt 的技能安装处理入口。
def source_skill_dir_from_receipt(repo_root: Path, receipt: dict[str, Any]) -> Path | None:

    # 定位 source path 的文件边界，供 source_skill_dir_from_receipt 后续读写校验使用。
    source_path = str(receipt.get("source_path", "")).strip()  # 技能安装校验复制输入值

    # 校验 source_skill_dir_from_receipt 的安装安全分支。
    if not source_path:

        # 返回 source_skill_dir_from_receipt 的安装流程载荷。
        return None

    # 提取 source_skill_dir_from_receipt 使用的 candidate 安装校验值。
    candidate = (repo_root / source_path).resolve()  # 技能安装校验复制输入值

    # 校验 source_skill_dir_from_receipt 的安装安全分支。
    if not candidate.exists():

        # 返回 source_skill_dir_from_receipt 的安装流程载荷。
        return None

    # 保护 source_skill_dir_from_receipt 中允许失败的外部访问。
    try:

        # 调用 relative_to 处理 source_skill_dir_from_receipt。
        candidate.relative_to(repo_root.resolve())
    except ValueError:

        # 返回 source_skill_dir_from_receipt 的安装流程载荷。
        return None

    # 返回 source_skill_dir_from_receipt 的安装流程载荷。
    return candidate


# 定义 verify_repo_release_state 的技能安装处理入口。
def verify_repo_release_state(repo_root: Path) -> list[str]:

    # 汇总 errors ，作为技能安装校验和复制候选清单。
    list_errors: list[str] = []  # 技能安装校验复制输入值

    # 提取 verify_repo_release_state 使用的 branch 安装校验值。
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=repo_root, text=True, capture_output=True, check=False)  # 技能安装校验复制输入值

    # 汇总 branches ，作为技能安装校验和复制候选清单。
    branches = subprocess.run(["git", "branch", "--list"], cwd=repo_root, text=True, capture_output=True, check=False)  # 技能安装校验复制输入值

    # 汇总 status ，作为技能安装校验和复制候选清单。
    status = subprocess.run(["git", "status", "--short"], cwd=repo_root, text=True, capture_output=True, check=False)  # 技能安装校验复制输入值

    # 校验 verify_repo_release_state 的安装安全分支。
    if any(item.returncode != 0 for item in [branch, branches, status]):

        # 返回 verify_repo_release_state 的安装流程载荷。
        return ["unable to inspect repository git state for strong release install validation"]

    # 提取 verify_repo_release_state 使用的 current branch 安装校验值。
    current_branch = branch.stdout.strip()  # 技能安装校验复制输入值

    # 汇总 local branches ，作为技能安装校验和复制候选清单。
    local_branches = sorted(normalize_branch_list_line(line) for line in branches.stdout.splitlines() if line.strip())  # 技能安装校验复制输入值

    # 汇总 status lines ，作为技能安装校验和复制候选清单。
    list_status_lines = filter_runtime_status_lines(status.stdout.splitlines())  # 技能安装校验复制输入值

    # 校验 verify_repo_release_state 的安装安全分支。
    if current_branch != "master":

        # 追加 verify_repo_release_state 诊断。
        list_errors.append("strong install validation requires current branch master")

    # 校验 verify_repo_release_state 的安装安全分支。
    if local_branches != ["master", "release"]:

        # 追加 verify_repo_release_state 诊断。
        list_errors.append("strong install validation requires only local branches master and release")

    # 校验 verify_repo_release_state 的安装安全分支。
    if list_status_lines:

        # 追加 verify_repo_release_state 诊断。
        list_errors.append("strong install validation requires a clean committed worktree")

    # 返回 verify_repo_release_state 的安装流程载荷。
    return list_errors


# 定义 validate_release_sanitization 的技能安装处理入口。
def validate_release_sanitization(
    release_dir: Path,
    tuple_receipt_path: Path,
    tuple_receipt: dict[str, Any],
    repo_root: Path | None,
    list_errors: list[str],
) -> None:
    """校验 release receipt 中记录的 sanitization 证据。

    数组契约:
        shape/维度: 本函数处理 release 文件树和 receipt 映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 Path、dict 和 list 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 RELEASE_RECEIPT.json schema。
    """

    # 提取 validate_release_sanitization 使用的 sanitization 安装校验值。
    sanitization = tuple_receipt.get("sanitization")  # 技能安装校验复制输入值

    # 校验 validate_release_sanitization 的安装安全分支。
    if not isinstance(sanitization, dict):

        # 追加 validate_release_sanitization 诊断。
        list_errors.append("release receipt sanitization block is missing")
    else:

        # 校验 validate_release_sanitization 的安装安全分支。
        if bool(sanitization.get("enabled")) is not True:

            # 追加 validate_release_sanitization 诊断。
            list_errors.append("release receipt sanitization enabled flag is missing or false")

        # 校验 validate_release_sanitization 的安装安全分支。
        if str(sanitization.get("scope", "")).strip() != "broad":

            # 追加 validate_release_sanitization 诊断。
            list_errors.append("release receipt sanitization scope is missing or invalid")

        # 校验 validate_release_sanitization 的安装安全分支。
        if str(sanitization.get("mode", "")).strip() != "auto-redact-dist-copy":

            # 追加 validate_release_sanitization 诊断。
            list_errors.append("release receipt sanitization mode is missing or invalid")

        # 校验 validate_release_sanitization 的安装安全分支。
        if bool(sanitization.get("receipt_required")) is not True:

            # 追加 validate_release_sanitization 诊断。
            list_errors.append("release receipt sanitization receipt_required flag is missing or false")

        # 汇总 files ，作为技能安装校验和复制候选清单。
        files = sanitization.get("files")  # 技能安装校验复制输入值

        # 校验 validate_release_sanitization 的安装安全分支。
        if not isinstance(files, list):

            # 追加 validate_release_sanitization 诊断。
            list_errors.append("release receipt sanitization files list is missing")
        else:

            # 提取 validate_release_sanitization 使用的 declared 安装校验值。
            dict_declared: dict[str, dict[str, Any]] = {}  # 技能安装校验复制输入值

            # 逐项检查 validate_release_sanitization 候选项。
            for item in files:

                # 校验 validate_release_sanitization 的安装安全分支。
                if not isinstance(item, dict):

                    # 追加 validate_release_sanitization 诊断。
                    list_errors.append("release receipt sanitization files list contains invalid entries")

                    # 分隔 validate_release_sanitization 的控制流边界。
                    continue

                # 定位 rel path 的文件边界，供 validate_release_sanitization 后续读写校验使用。
                rel_path = str(item.get("path", "")).strip()  # 技能安装校验复制输入值

                # 校验 validate_release_sanitization 的安装安全分支。
                if not rel_path:

                    # 追加 validate_release_sanitization 诊断。
                    list_errors.append("release receipt sanitization file entry is missing path")

                    # 分隔 validate_release_sanitization 的控制流边界。
                    continue

                # 汇总 rules ，作为技能安装校验和复制候选清单。
                rules = item.get("rules")  # 技能安装校验复制输入值

                # 校验 validate_release_sanitization 的安装安全分支。
                if not isinstance(rules, list) or not all(str(value).strip() for value in rules):

                    # 追加 validate_release_sanitization 诊断。
                    list_errors.append(f"release receipt sanitization rules are missing for {rel_path}")

                # 汇总 placeholders ，作为技能安装校验和复制候选清单。
                placeholders = item.get("placeholders")  # 技能安装校验复制输入值

                # 校验 validate_release_sanitization 的安装安全分支。
                if not isinstance(placeholders, list) or not all(str(value).strip() for value in placeholders):

                    # 追加 validate_release_sanitization 诊断。
                    list_errors.append(f"release receipt sanitization placeholders are missing for {rel_path}")

                # 提取 validate_release_sanitization 使用的 中间载荷 安装校验值。
                dict_declared[rel_path] = item  # 技能安装校验复制输入值

            # 提取 validate_release_sanitization 使用的 expected declared 安装校验值。
            set_expected_declared: set[str] = set()  # 技能安装校验复制输入值

            # 提取 validate_release_sanitization 使用的 source skill dir 安装校验值。
            source_skill_dir = source_skill_dir_from_receipt(repo_root, tuple_receipt) if repo_root is not None else None  # 技能安装校验复制输入值

            # 校验 validate_release_sanitization 的安装安全分支。
            if source_skill_dir is not None:

                # 逐项检查 validate_release_sanitization 候选项。
                for source_path in sorted(source_skill_dir.rglob("*")):

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if not source_path.is_file():

                        # 分隔 validate_release_sanitization 的控制流边界。
                        continue

                    # 提取 validate_release_sanitization 使用的 relative 安装校验值。
                    relative = source_path.relative_to(source_skill_dir).as_posix()  # 技能安装校验复制输入值

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if relative == tuple_receipt_path.name:

                        # 分隔 validate_release_sanitization 的控制流边界。
                        continue

                    # 定位 release path 的文件边界，供 validate_release_sanitization 后续读写校验使用。
                    release_path = release_dir / relative  # 技能安装校验复制输入值

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if not release_path.is_file():

                        # 分隔 validate_release_sanitization 的控制流边界。
                        continue

                    # 汇总 source bytes ，作为技能安装校验和复制候选清单。
                    source_bytes = source_path.read_bytes()  # 技能安装校验复制输入值

                    # 汇总 release bytes ，作为技能安装校验和复制候选清单。
                    release_bytes = release_path.read_bytes()  # 技能安装校验复制输入值

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if is_probably_text_bytes(source_bytes):

                        # 提取 validate_release_sanitization 使用的 source text 安装校验值。
                        source_text = source_bytes.decode("utf-8")  # 技能安装校验复制输入值

                        # 汇总 expected text、matches ，作为技能安装校验和复制候选清单。
                        tuple_expected_text, tuple_matches = sanitize_release_text(source_text)  # 技能安装校验复制输入值

                        # 校验 validate_release_sanitization 的安装安全分支。
                        if tuple_matches:

                            # 调用 add 处理 validate_release_sanitization。
                            set_expected_declared.add(relative)

                            # 提取 validate_release_sanitization 使用的 row 安装校验值。
                            row = dict_declared.get(relative)  # 技能安装校验复制输入值

                            # 校验 validate_release_sanitization 的安装安全分支。
                            if row is None:

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"release receipt is missing sanitization record for {relative}")

                            # 校验 validate_release_sanitization 的安装安全分支。
                            elif str(row.get("sha256", "")).strip() != sha256_file(release_path):

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"release receipt sanitization hash mismatch for {relative}")

                            # 校验 validate_release_sanitization 的安装安全分支。
                            if not is_probably_text_bytes(release_bytes):

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"sanitized release file is not valid UTF-8 text: {relative}")

                                # 分隔 validate_release_sanitization 的控制流边界。
                                continue

                            # 提取 validate_release_sanitization 使用的 actual text 安装校验值。
                            actual_text = release_bytes.decode("utf-8")  # 技能安装校验复制输入值

                            # 校验 validate_release_sanitization 的安装安全分支。
                            if normalize_line_endings(actual_text) != normalize_line_endings(tuple_expected_text):

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"sanitized release content mismatch for {relative}")

                        # 校验 validate_release_sanitization 的安装安全分支。
                        elif release_bytes != source_bytes:

                            # 追加 validate_release_sanitization 诊断。
                            list_errors.append(f"undeclared release diff outside sanitization receipt: {relative}")
                    else:

                        # 汇总 hits ，作为技能安装校验和复制候选清单。
                        list_hits = detect_binary_sensitive_matches(source_bytes)  # 技能安装校验复制输入值

                        # 校验 validate_release_sanitization 的安装安全分支。
                        if list_hits:

                            # 追加 validate_release_sanitization 诊断。
                            list_errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {relative}")

                        # 校验 validate_release_sanitization 的安装安全分支。
                        elif release_bytes != source_bytes:

                            # 追加 validate_release_sanitization 诊断。
                            list_errors.append(f"undeclared binary release diff outside sanitization receipt: {relative}")

                # 提取 validate_release_sanitization 使用的 unexpected 安装校验值。
                unexpected = sorted(set(dict_declared) - set_expected_declared)  # 技能安装校验复制输入值

                # 逐项检查 validate_release_sanitization 候选项。
                for relative in unexpected:

                    # 追加 validate_release_sanitization 诊断。
                    list_errors.append(f"release receipt declares unexpected sanitized file: {relative}")
            else:

                # 逐项检查 validate_release_sanitization 候选项。
                for path in sorted(release_dir.rglob("*")):

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if not path.is_file() or path.name == tuple_receipt_path.name:

                        # 分隔 validate_release_sanitization 的控制流边界。
                        continue

                    # 提取 validate_release_sanitization 使用的 relative 安装校验值。
                    relative = path.relative_to(release_dir).as_posix()  # 技能安装校验复制输入值

                    # 提取 validate_release_sanitization 使用的 data 安装校验值。
                    dict_data = path.read_bytes()  # 技能安装校验复制输入值

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if is_probably_text_bytes(dict_data):

                        # 提取 validate_release_sanitization 使用的 text 安装校验值。
                        text = dict_data.decode("utf-8")  # 技能安装校验复制输入值

                        # 汇总 sanitized text、matches ，作为技能安装校验和复制候选清单。
                        tuple_sanitized_text, tuple_matches = sanitize_release_text(text)  # 技能安装校验复制输入值

                        # 校验 validate_release_sanitization 的安装安全分支。
                        if tuple_matches:

                            # 调用 add 处理 validate_release_sanitization。
                            set_expected_declared.add(relative)

                            # 提取 validate_release_sanitization 使用的 row 安装校验值。
                            row = dict_declared.get(relative)  # 技能安装校验复制输入值

                            # 校验 validate_release_sanitization 的安装安全分支。
                            if row is None:

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"release receipt is missing sanitization record for {relative}")

                            # 校验 validate_release_sanitization 的安装安全分支。
                            elif str(row.get("sha256", "")).strip() != sha256_file(path):

                                # 追加 validate_release_sanitization 诊断。
                                list_errors.append(f"release receipt sanitization hash mismatch for {relative}")

                        # 校验 validate_release_sanitization 的安装安全分支。
                        if normalize_line_endings(text) != normalize_line_endings(tuple_sanitized_text):

                            # 追加 validate_release_sanitization 诊断。
                            list_errors.append(f"release directory still contains unsanitized sensitive content: {relative}")
                    else:

                        # 汇总 hits ，作为技能安装校验和复制候选清单。
                        list_hits = detect_binary_sensitive_matches(dict_data)  # 技能安装校验复制输入值

                        # 校验 validate_release_sanitization 的安装安全分支。
                        if list_hits:

                            # 追加 validate_release_sanitization 诊断。
                            list_errors.append(f"release directory contains sensitive binary content: {relative}")

                # 逐项检查 validate_release_sanitization 候选项。
                for relative, row in dict_declared.items():

                    # 定位 release path 的文件边界，供 validate_release_sanitization 后续读写校验使用。
                    release_path = release_dir / relative  # 技能安装校验复制输入值

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if not release_path.is_file():

                        # 追加 validate_release_sanitization 诊断。
                        list_errors.append(f"release receipt sanitization file entry points to a missing file: {relative}")

                        # 分隔 validate_release_sanitization 的控制流边界。
                        continue

                    # 校验 validate_release_sanitization 的安装安全分支。
                    if str(row.get("sha256", "")).strip() != sha256_file(release_path):

                        # 追加 validate_release_sanitization 诊断。
                        list_errors.append(f"release receipt sanitization hash mismatch for {relative}")



# 定义 validate_release_dir 的技能安装处理入口。
def validate_release_dir(release_dir: Path) -> dict[str, Any]:

    # 提取 validate_release_dir 使用的 skill name、version 安装校验值。
    tuple_skill_name, tuple_version = parse_release_dir(release_dir)  # 技能安装校验复制输入值

    # 定位 receipt path、receipt 的文件边界，供 validate_release_dir 后续读写校验使用。
    tuple_receipt_path, tuple_receipt = read_receipt(release_dir)  # 技能安装校验复制输入值

    # 汇总 errors ，作为技能安装校验和复制候选清单。
    list_errors: list[str] = []  # 技能安装校验复制输入值

    # 提取 validate_release_dir 使用的 release content 安装校验值。
    release_content = analyze_release_content_root(release_dir)  # 技能安装校验复制输入值

    # 校验 validate_release_dir 的安装安全分支。
    if str(tuple_receipt.get("skill_name", "")).strip() != tuple_skill_name:

        # 追加 validate_release_dir 诊断。
        list_errors.append("release receipt skill_name does not match release directory name")

    # 校验 validate_release_dir 的安装安全分支。
    if str(tuple_receipt.get("version", "")).strip() != tuple_version:

        # 追加 validate_release_dir 诊断。
        list_errors.append("release receipt version does not match release directory version")

    # 汇总 expected files ，作为技能安装校验和复制候选清单。
    list_expected_files = file_manifest(release_dir, exclude={tuple_receipt_path.name})  # 技能安装校验复制输入值

    # 汇总 actual files ，作为技能安装校验和复制候选清单。
    actual_files = tuple_receipt.get("files")  # 技能安装校验复制输入值

    # 校验 validate_release_dir 的安装安全分支。
    if not isinstance(actual_files, list):

        # 追加 validate_release_dir 诊断。
        list_errors.append("release receipt files list is missing")
    else:

        # 提取 validate_release_dir 使用的 normalized 安装校验值。
        list_normalized = []  # 技能安装校验复制输入值

        # 逐项检查 validate_release_dir 候选项。
        for item in actual_files:

            # 校验 validate_release_dir 的安装安全分支。
            if not isinstance(item, dict):

                # 追加 validate_release_dir 诊断。
                list_errors.append("release receipt files list contains invalid entries")

                # 分隔 validate_release_dir 的控制流边界。
                continue

            # 追加 validate_release_dir 诊断。
            list_normalized.append({"path": str(item.get("path", "")).strip(), "sha256": str(item.get("sha256", "")).strip()})

        # 校验 validate_release_dir 的安装安全分支。
        if list_normalized != list_expected_files:

            # 追加 validate_release_dir 诊断。
            list_errors.append("release receipt file manifest does not match release directory contents")

    # 提取 validate_release_dir 使用的 repo root 安装校验值。
    repo_root = infer_repo_root(release_dir)  # 技能安装校验复制输入值

    # 提取 validate_release_dir 使用的 validation level 安装校验值。
    validation_level = "strong" if repo_root is not None else "reduced_assurance"  # 技能安装校验复制输入值

    # 提取 validate_release_dir 使用的 provenance mode 安装校验值。
    provenance_mode = "repository-dist" if repo_root is not None else "external-copy"  # 技能安装校验复制输入值

    # 提取 validate_release_dir 使用的 expected validation 安装校验值。
    expected_validation = "strong" if repo_root is not None else "reduced_assurance"  # 技能安装校验复制输入值

    # 校验 validate_release_dir 的安装安全分支。
    if str(tuple_receipt.get("validation_level", "")).strip() != expected_validation:

        # 追加 validate_release_dir 诊断。
        list_errors.append("release receipt validation_level does not match the installation source")

    # 校验 release receipt 中记录的 sanitization 证据。
    validate_release_sanitization(
        release_dir,
        tuple_receipt_path,
        tuple_receipt,
        repo_root,
        list_errors,
    )

    # 校验 validate_release_dir 的安装安全分支。
    if repo_root is not None:

        # 调用 extend 处理 validate_release_dir。
        list_errors.extend(verify_repo_release_state(repo_root))

    # 提取 validate_release_dir 使用的 source skill dir 安装校验值。
    source_skill_dir = source_skill_dir_from_receipt(repo_root, tuple_receipt) if repo_root is not None else None  # 技能安装校验复制输入值

    # 汇总 source forbidden paths ，作为技能安装校验和复制候选清单。
    list_source_forbidden_paths: list[str] = []  # 技能安装校验复制输入值

    # 校验 validate_release_dir 的安装安全分支。
    if source_skill_dir is not None:

        # 汇总 source forbidden paths ，作为技能安装校验和复制候选清单。
        list_source_forbidden_paths = analyze_release_content_root(  # 技能安装校验复制输入值
            source_skill_dir,  # 技能安装校验复制输入值
            allow_source_only_repo_local=True,  # 技能安装校验复制输入值
        )["forbidden_paths"]  # 技能安装校验复制输入值

    # 汇总 policy errors ，作为技能安装校验和复制候选清单。
    policy_errors = validate_recorded_release_content_policy(  # 技能安装校验复制输入值
        tuple_receipt.get("release_content_policy"),  # 技能安装校验复制输入值
        release_content,  # 技能安装校验复制输入值
        forbidden_source_paths=list_source_forbidden_paths,  # 技能安装校验复制输入值
        require_source_paths=source_skill_dir is not None,  # 技能安装校验复制输入值
    )

    # 校验 validate_release_dir 的安装安全分支。
    if release_content["unexpected_top_level_entries"]:

        # 追加 validate_release_dir 诊断。
        policy_errors.append("release content policy rejected unexpected top-level release entries")

    # 校验 validate_release_dir 的安装安全分支。
    if release_content["forbidden_paths"]:

        # 追加 validate_release_dir 诊断。
        policy_errors.append("release content policy rejected forbidden development content in release")

    # 调用 extend 处理 validate_release_dir。
    list_errors.extend(policy_errors)

    # 调用 extend 处理 validate_release_dir。
    list_errors.extend(validate_release_completeness(release_dir, tuple_receipt))

    # 返回 validate_release_dir 的安装流程载荷。
    return {
        "skill_name": tuple_skill_name,
        "version": tuple_version,
        "receipt_path": str(tuple_receipt_path),
        "repo_root": str(repo_root) if repo_root else "",
        "validation_level": validation_level,
        "provenance_mode": provenance_mode,
        "policy_version": POLICY_VERSION,
        "forbidden_source_paths": list_source_forbidden_paths,
        "forbidden_release_paths": release_content["forbidden_paths"],
        "release_content_policy_ok": not policy_errors,
        "errors": list_errors,
    }


# 定义 target_path 的技能安装处理入口。
def target_path(skill_name: str, target: str, codex_home: str | None, custom_root: str | None) -> Path | None:

    # 校验 target_path 的安装安全分支。
    if target == "skip":

        # 返回 target_path 的安装流程载荷。
        return None

    # 校验 target_path 的安装安全分支。
    if target == "codex":

        # 返回 target_path 的安装流程载荷。
        return default_codex_home(codex_home) / "skills" / skill_name

    # 校验 target_path 的安装安全分支。
    if target == "custom":

        # 校验 target_path 的安装安全分支。
        if not custom_root:

            # 抛出 target_path 已确认的阻断原因。
            raise SystemExit(json.dumps({"errors": ["--custom-root is required when --target custom"]}, indent=2))

        # 返回 target_path 的安装流程载荷。
        return Path(custom_root).expanduser().resolve() / skill_name

    # 抛出 target_path 已确认的阻断原因。
    raise SystemExit(json.dumps({"errors": ["--target must be skip, codex, or custom"]}, indent=2))


# 定义 stamp 的技能安装处理入口。
def stamp() -> str:

    # 返回 stamp 的安装流程载荷。
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# 定义 backup_root_for 的技能安装处理入口。
def backup_root_for(destination: Path) -> Path:

    # 返回 backup_root_for 的安装流程载荷。
    return destination.parent.parent / "skill_backups"


# 定义 unique_backup_path 的技能安装处理入口。
def unique_backup_path(destination: Path) -> Path:

    # 提取 unique_backup_path 使用的 root 安装校验值。
    path_root = backup_root_for(destination)  # 技能安装校验复制输入值

    # 提取 unique_backup_path 使用的 base 安装校验值。
    base = path_root / f"{destination.name}-{stamp()}"  # 技能安装校验复制输入值

    # 提取 unique_backup_path 使用的 candidate 安装校验值。
    path_candidate = base  # 技能安装校验复制输入值

    # 提取 unique_backup_path 使用的 index 安装校验值。
    int_index = 2  # 技能安装校验复制输入值

    # 逐项检查 unique_backup_path 候选项。
    while path_candidate.exists():

        # 提取 unique_backup_path 使用的 candidate 安装校验值。
        path_candidate = Path(f"{base}-{index}")  # 技能安装校验复制输入值

        # 提取 unique_backup_path 使用的 index 安装校验值。
        int_index += 1  # 技能安装校验复制输入值

    # 返回 unique_backup_path 的安装流程载荷。
    return path_candidate


# 定义 copy_skill 的技能安装处理入口。
def copy_skill(skill_dir: Path, destination: Path, replace: bool) -> dict[str, Any]:

    # 定位 backup path 的文件边界，供 copy_skill 后续读写校验使用。
    path_backup_path: Path | None = None  # 技能安装校验复制输入值

    # 校验 copy_skill 的安装安全分支。
    if destination.exists():

        # 校验 copy_skill 的安装安全分支。
        if not replace:

            # 抛出 copy_skill 已确认的阻断原因。
            raise FileExistsError(f"target already exists: {destination}")

        # 定位 backup path 的文件边界，供 copy_skill 后续读写校验使用。
        path_backup_path = unique_backup_path(destination)  # 技能安装校验复制输入值

        # 调用 mkdir 处理 copy_skill。
        path_backup_path.parent.mkdir(parents=True, exist_ok=True)

        # 调用 move 处理 copy_skill。
        shutil.move(str(destination), str(path_backup_path))

    # 调用 mkdir 处理 copy_skill。
    destination.parent.mkdir(parents=True, exist_ok=True)

    # 提取 copy_skill 使用的 ignore 安装校验值。
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")  # 技能安装校验复制输入值

    # 调用 copytree 处理 copy_skill。
    shutil.copytree(skill_dir, destination, ignore=ignore)

    # 提取 copy_skill 使用的 legacy evolution 安装校验值。
    legacy_evolution = destination / "assets" / "templates" / "evolution"  # 技能安装校验复制输入值

    # 校验 copy_skill 的安装安全分支。
    if legacy_evolution.exists():

        # 调用 rmtree 处理 copy_skill。
        shutil.rmtree(legacy_evolution, ignore_errors=True)

    # 返回 copy_skill 的安装流程载荷。
    return {
        "backup_path": str(path_backup_path) if path_backup_path else "",
    }


# 定义 main 的技能安装处理入口。
def main() -> None:

    # 提取 main 使用的 parser 安装校验值。
    parser = argparse.ArgumentParser(description="Install a verified Codex skill after explicit user confirmation.")  # 技能安装校验复制输入值

    # 调用 add_argument 处理 main。
    parser.add_argument("release_dir")

    # 调用 add_argument 处理 main。
    parser.add_argument("--target", choices=["skip", "codex", "custom"], default="skip")

    # 调用 add_argument 处理 main。
    parser.add_argument("--codex-home", default=None)

    # 调用 add_argument 处理 main。
    parser.add_argument("--custom-root", default=None)

    # 调用 add_argument 处理 main。
    parser.add_argument("--write", action="store_true", help="Actually copy the skill. Default is dry-run.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--replace", action="store_true", help="Replace an existing installed skill after user confirmation.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--install-intent", choices=["unspecified", "requested"], default="unspecified")

    # 汇总 args ，作为技能安装校验和复制候选清单。
    args = parser.parse_args()  # 技能安装校验复制输入值

    # 提取 main 使用的 release dir 安装校验值。
    release_dir = resolve_project(args.release_dir)  # 技能安装校验复制输入值

    # 提取 main 使用的 validation 安装校验值。
    dict_validation = validate_release_dir(release_dir)  # 技能安装校验复制输入值

    # 校验 main 的安装安全分支。
    if dict_validation["errors"]:

        # 调用 emit_json 处理 main。
        emit_json(dict_validation)

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 提取 main 使用的 skill name 安装校验值。
    skill_name = dict_validation["skill_name"]  # 技能安装校验复制输入值

    # 提取 main 使用的 destination 安装校验值。
    destination = target_path(skill_name, args.target, args.codex_home, args.custom_root)  # 技能安装校验复制输入值

    # 提取 main 使用的 result 安装校验值。
    dict_result: dict[str, Any] = {  # 技能安装校验复制输入值
        "release_dir": str(release_dir),  # 技能安装校验复制输入值
        "skill_name": skill_name,  # 技能安装校验复制输入值
        "version": dict_validation["version"],  # 技能安装校验复制输入值
        "target": args.target,  # 技能安装校验复制输入值
        "install_intent": args.install_intent,  # 技能安装校验复制输入值
        "destination": str(destination) if destination else "",  # 技能安装校验复制输入值
        "installed": False,  # 技能安装校验复制输入值
        "skipped": args.target == "skip" or not args.write,  # 技能安装校验复制输入值
        "backup_path": "",  # 技能安装校验复制输入值
        "receipt_path": dict_validation["receipt_path"],  # 技能安装校验复制输入值
        "provenance_mode": dict_validation["provenance_mode"],  # 技能安装校验复制输入值
        "validation_level": dict_validation["validation_level"],  # 技能安装校验复制输入值
        "policy_version": dict_validation["policy_version"],  # 技能安装校验复制输入值
        "forbidden_source_paths": dict_validation["forbidden_source_paths"],  # 技能安装校验复制输入值
        "forbidden_release_paths": dict_validation["forbidden_release_paths"],  # 技能安装校验复制输入值
        "release_content_policy_ok": dict_validation["release_content_policy_ok"],  # 技能安装校验复制输入值
        "global_codex_agents_status": global_codex_agents_status(args.codex_home),  # 技能安装校验复制输入值
    }

    # 检查 main 的安装意图是否需要补充用户确认载荷。
    if args.install_intent == "unspecified" and (args.target == "skip" or not args.write):

        # 提取 main 使用的 中间载荷 安装校验值。
        dict_result["confirmation_question"] = "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。"  # 技能安装校验复制输入值

        # 提取 main 使用的 中间载荷 安装校验值。
        dict_result["options"] = install_options()  # 技能安装校验复制输入值

        # 提取 main 使用的 中间载荷 安装校验值。
        dict_result["decision_request"] = decision_request(  # 技能安装校验复制输入值
            "install_confirmation",  # 技能安装校验复制输入值
            question=dict_result["confirmation_question"],  # 技能安装校验复制输入值
            options=dict_result["options"],  # 技能安装校验复制输入值
            default="skip",  # 技能安装校验复制输入值
            risk="medium",  # 技能安装校验复制输入值
            next_action="rerun install_skill.py with --write and the selected target when installation is confirmed",  # 技能安装校验复制输入值
            context={"release_dir": str(release_dir), "target": args.target},  # 技能安装校验复制输入值
        )

    # 校验 main 的安装安全分支。
    if args.target == "skip" or not args.write:

        # 调用 emit_json 处理 main。
        emit_json(dict_result)

        # 返回 main 的安装流程载荷。
        return

    # 说明该控制语句在脚本治理流程中的分支职责。
    assert destination is not None

    # 保护 main 中允许失败的外部访问。
    try:

        # 汇总 install details ，作为技能安装校验和复制候选清单。
        dict_install_details = copy_skill(release_dir, destination, args.replace)  # 技能安装校验复制输入值
    except SystemExit:

        # 抛出 main 已确认的阻断原因。
        raise
    except Exception as exc:

        # 调用 emit_json 处理 main。
        emit_json({"errors": [str(exc)], **dict_result})

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 调用 update 处理 main。
    dict_result.update(dict_install_details)

    # 提取 main 使用的 中间载荷 安装校验值。
    dict_result["installed"] = True  # 技能安装校验复制输入值

    # 提取 main 使用的 中间载荷 安装校验值。
    dict_result["skipped"] = False  # 技能安装校验复制输入值

    # 调用 emit_json 处理 main。
    emit_json(dict_result)


# 校验 模块入口 的安装安全分支。
if __name__ == "__main__":

    # 调用 main 处理 模块入口。
    main()


