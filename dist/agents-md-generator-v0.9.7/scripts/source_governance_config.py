from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def skill_source_governance_path(root: Path | None = None) -> Path:
    return (root or skill_root()) / "config" / "source-governance.json"


def default_source_governance() -> dict[str, Any]:
    data = read_json(skill_source_governance_path())
    return data if isinstance(data, dict) else {}


def load_skill_source_governance(root: Path | None = None) -> dict[str, Any]:
    path = skill_source_governance_path(root)
    data = read_json(path) if path.is_file() else {}
    if not isinstance(data, dict):
        data = {}
    errors = validate_source_governance_data(data)
    if not path.is_file():
        errors.insert(0, f"missing source governance config: {path.as_posix()}")
    return {"path": path, "exists": path.is_file(), "data": data, "errors": errors}


def default_implementation_constraints() -> dict[str, Any]:
    source = default_source_governance()
    return {
        "source_file_max_lines": int(source.get("max_lines", 0)),
        "line_limit_extensions": list(source.get("hard_fail_extensions", [])),
        "line_limit_scope": "handwritten-source-and-tool-scripts",
        "line_limit_exclude_roots": list(source.get("excluded_roots", [])),
        "script_layout": {
            "required_root": "scripts",
            "families": {"python": ".py", "shell": ".sh", "bat": ".bat", "powershell": ".ps1"},
            "required_pattern": "scripts/<family>/<function>/<name>.<ext>",
            "require_full_triad": True,
            "gui_exception_mode": "explicit-manifest",
        },
    }


def default_global_rule_overrides() -> dict[str, Any]:
    constraints = default_implementation_constraints()
    script_layout = constraints["script_layout"]
    source = default_source_governance()
    return {
        "code_comment_policy": {
            "language": "中文",
            "default_policy": "只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释；禁止复述代码；禁止未经明确要求的批量 AI 注释；行为变化时必须更新旧注释。",
            "formatting": "生成代码必须保留回车/空行分隔，不能把语句、注释、函数粘连到一起。",
            "python": "公共函数/类使用规范 docstring；普通说明注释放在代码上方；禁止右侧尾注释。",
            "c_cpp": "函数、模块核心功能、变量定义和特定功能说明放在代码上方；所有权/生命周期、ABI、并发、内存和未定义行为风险必须优先说明；`#define` 宏注释放在右侧。",
            "verilog_systemverilog": "信号声明、参数定义、assign 和 always 块内寄存器赋值使用右侧注释；声明类型包括 input/output/inout/parameter/localparam/integer/logic/wire/reg/real；module/task/function/generate/always 说明放在语句上方。",
            "positions": {
                "python.public_api": "docstring",
                "python.inline": "above",
                "python.trailing": "forbidden",
                "c_cpp.function": "above",
                "c_cpp.module": "above",
                "c_cpp.variable": "above",
                "c_cpp.specific_behavior": "above",
                "c_cpp.macro_define": "right_side",
                "verilog_systemverilog.module": "above",
                "verilog_systemverilog.declaration": "right_side",
                "verilog_systemverilog.assign": "right_side",
                "verilog_systemverilog.task_function_generate_always": "above",
                "verilog_systemverilog.always_register_assignment": "right_side",
            },
        },
        "long_python_tasks": {
            "enabled": True,
            "prompt_before_automation": True,
            "automation_kind": "heartbeat",
            "default_interval_minutes": 10,
            "long_running_threshold_minutes": 10,
            "completion_check_strategy": {
                "require_reliable_signal": True,
                "allow_process_polling": True,
                "allow_expected_artifact_check": True,
                "allow_output_marker": True,
                "on_unreliable_signal": "deny-automation",
                "on_completion": "continue-then-delete-heartbeat",
                "on_incomplete": "wait-for-next-heartbeat",
            },
        },
        "source_governance": source,
        "source_file_limits": {
            "max_lines": constraints["source_file_max_lines"],
            "included_extensions": list(source.get("hard_fail_extensions", [])),
            "excluded_roots": list(source.get("excluded_roots", [])),
            "decomposition_plan_root": "docs/development/decomposition-plans",
            "required_plan_sections": ["Current Size", "Split Boundaries", "Target Files", "Exit Criteria"],
        },
        "tool_script_layout": {
            "required_root": script_layout["required_root"],
            "families": dict(script_layout["families"]),
            "required_pattern": script_layout["required_pattern"],
            "require_full_triad": bool(script_layout["require_full_triad"]),
            "gui_exception_manifest": ".agents/script-governance-exceptions.json",
        },
    }


def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return ".agents/global-rule-overrides.json"
    inline = profile.get("global_rule_overrides", {})
    if isinstance(inline, dict):
        candidate = str(inline.get("path", "")).strip()
        if candidate:
            return candidate
    legacy = str(profile.get("global_rule_overrides_config", "")).strip()
    return legacy or ".agents/global-rule-overrides.json"


def global_rule_overrides_path(root: Path, profile: dict[str, Any] | None = None) -> Path:
    candidate = Path(global_rule_overrides_reference(profile))
    return candidate if candidate.is_absolute() else (root / candidate)


def merge_object(base: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in raw.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_object(merged[key], value)
        else:
            merged[key] = value
    return merged


def legacy_global_rule_overrides(profile: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_global_rule_overrides()
    if not isinstance(profile, dict):
        return defaults
    constraints = profile.get("implementation_constraints", {})
    if not isinstance(constraints, dict) or not constraints:
        return defaults
    layout = constraints.get("script_layout", {}) if isinstance(constraints.get("script_layout", {}), dict) else {}
    return merge_object(
        defaults,
        {
            "source_file_limits": {
                "max_lines": constraints.get("source_file_max_lines", defaults["source_file_limits"]["max_lines"]),
                "included_extensions": constraints.get("line_limit_extensions", defaults["source_file_limits"]["included_extensions"]),
                "excluded_roots": constraints.get("line_limit_exclude_roots", defaults["source_file_limits"]["excluded_roots"]),
            },
            "tool_script_layout": {
                "required_root": layout.get("required_root", defaults["tool_script_layout"]["required_root"]),
                "families": layout.get("families", defaults["tool_script_layout"]["families"]),
                "required_pattern": layout.get("required_pattern", defaults["tool_script_layout"]["required_pattern"]),
                "require_full_triad": layout.get("require_full_triad", defaults["tool_script_layout"]["require_full_triad"]),
            },
        },
    )


def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    errors: list[str] = []
    if not comment_policy:
        return ["code_comment_policy must be a non-empty object"]
    required_text_fields = ("language", "default_policy", "formatting", "python", "c_cpp", "verilog_systemverilog")
    for key in required_text_fields:
        if require_explicit and key not in comment_policy:
            errors.append(f"code_comment_policy.{key} must be explicitly set")
        if not str(comment_policy.get(key, "")).strip():
            errors.append(f"code_comment_policy.{key} must be set")
    required_snippets = {
        "default_policy": ["非显然意图", "不变量", "风险", "生成边界", "公共 API 行为", "禁止复述代码", "禁止未经明确要求的批量 AI 注释", "行为变化时必须更新旧注释"],
        "formatting": ["回车/空行分隔", "不能把语句、注释、函数粘连到一起"],
        "python": ["docstring", "代码上方", "禁止右侧尾注释"],
        "c_cpp": ["函数", "模块核心功能", "变量定义", "#define", "右侧", "所有权/生命周期"],
        "verilog_systemverilog": ["module", "input/output/inout/parameter/localparam/integer/logic/wire/reg/real", "assign", "always", "右侧", "上方"],
    }
    for key, snippets in required_snippets.items():
        value = str(comment_policy.get(key, ""))
        for snippet in snippets:
            if snippet not in value:
                errors.append(f"code_comment_policy.{key} missing required rule `{snippet}`")
    positions = comment_policy.get("positions")
    required_positions = {
        "python.public_api": "docstring",
        "python.inline": "above",
        "python.trailing": "forbidden",
        "c_cpp.function": "above",
        "c_cpp.module": "above",
        "c_cpp.variable": "above",
        "c_cpp.specific_behavior": "above",
        "c_cpp.macro_define": "right_side",
        "verilog_systemverilog.module": "above",
        "verilog_systemverilog.declaration": "right_side",
        "verilog_systemverilog.assign": "right_side",
        "verilog_systemverilog.task_function_generate_always": "above",
        "verilog_systemverilog.always_register_assignment": "right_side",
    }
    if require_explicit and "positions" not in comment_policy:
        errors.append("code_comment_policy.positions must be explicitly set")
    if not isinstance(positions, dict):
        return errors + ["code_comment_policy.positions must be an object"]
    allowed_positions = {"above", "right_side", "docstring", "forbidden"}
    for key, expected in required_positions.items():
        if require_explicit and key not in positions:
            errors.append(f"code_comment_policy.positions.{key} must be explicitly set")
        if positions.get(key) != expected:
            errors.append(f"code_comment_policy.positions.{key} must be {expected}")
    for key, value in positions.items():
        if value not in allowed_positions:
            errors.append(f"code_comment_policy.positions.{key} has invalid value {value}")
    return errors


def validate_source_governance_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not data:
        return ["source_governance must be a non-empty object"]
    max_lines = data.get("max_lines")
    if not isinstance(max_lines, int) or max_lines <= 0:
        errors.append("source_governance.max_lines must be a positive integer")
    extensions = data.get("hard_fail_extensions")
    if not isinstance(extensions, list) or not extensions or not all(str(item).startswith(".") for item in extensions):
        errors.append("source_governance.hard_fail_extensions must be a non-empty extension list")
    excluded_roots = data.get("excluded_roots")
    if not isinstance(excluded_roots, list):
        errors.append("source_governance.excluded_roots must be a list")
    test_only = data.get("test_only_patterns")
    if not isinstance(test_only, dict) or not isinstance(test_only.get("path_globs"), list) or not test_only.get("path_globs"):
        errors.append("source_governance.test_only_patterns.path_globs must be a non-empty list")
    comment_gate = data.get("comment_policy_gate")
    if not isinstance(comment_gate, dict):
        errors.append("source_governance.comment_policy_gate must be an object")
    else:
        if not isinstance(comment_gate.get("enabled"), bool):
            errors.append("source_governance.comment_policy_gate.enabled must be boolean")
        if not isinstance(comment_gate.get("forbid_ai_comment_markers"), list):
            errors.append("source_governance.comment_policy_gate.forbid_ai_comment_markers must be a list")
        if not isinstance(comment_gate.get("python"), dict):
            errors.append("source_governance.comment_policy_gate.python must be an object")
        if not isinstance(comment_gate.get("c_cpp"), dict):
            errors.append("source_governance.comment_policy_gate.c_cpp must be an object")
    return errors


def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    comment_policy = data.get("code_comment_policy", {}) if isinstance(data.get("code_comment_policy", {}), dict) else {}
    long_tasks = data.get("long_python_tasks", {}) if isinstance(data.get("long_python_tasks", {}), dict) else {}
    source_governance = data.get("source_governance", {}) if isinstance(data.get("source_governance", {}), dict) else {}
    source_limits = data.get("source_file_limits", {}) if isinstance(data.get("source_file_limits", {}), dict) else {}
    script_layout = data.get("tool_script_layout", {}) if isinstance(data.get("tool_script_layout", {}), dict) else {}
    errors.extend(validate_code_comment_policy_data(comment_policy))
    errors.extend(validate_source_governance_data(source_governance))
    if long_tasks.get("automation_kind") != "heartbeat":
        errors.append("long_python_tasks.automation_kind must be heartbeat")
    for key in ("default_interval_minutes", "long_running_threshold_minutes"):
        value = long_tasks.get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"long_python_tasks.{key} must be a positive integer")
    if not isinstance(long_tasks.get("completion_check_strategy"), dict) or not long_tasks.get("completion_check_strategy"):
        errors.append("long_python_tasks.completion_check_strategy must be a non-empty object")
    if not isinstance(source_limits.get("max_lines"), int) or source_limits.get("max_lines", 0) <= 0:
        errors.append("source_file_limits.max_lines must be a positive integer")
    if not isinstance(source_limits.get("included_extensions"), list):
        errors.append("source_file_limits.included_extensions must be a list of extensions")
    if not isinstance(source_limits.get("excluded_roots"), list):
        errors.append("source_file_limits.excluded_roots must be a list")
    if not str(source_limits.get("decomposition_plan_root", "")).strip():
        errors.append("source_file_limits.decomposition_plan_root must be set")
    if not isinstance(source_limits.get("required_plan_sections"), list) or not source_limits.get("required_plan_sections"):
        errors.append("source_file_limits.required_plan_sections must be a non-empty list")
    families = script_layout.get("families")
    if not str(script_layout.get("required_root", "")).strip():
        errors.append("tool_script_layout.required_root must be set")
    if not isinstance(families, dict) or not families:
        errors.append("tool_script_layout.families must be a non-empty object")
    elif not all(str(ext).startswith(".") for ext in families.values()):
        errors.append("tool_script_layout.families values must be extensions")
    if not str(script_layout.get("required_pattern", "")).strip():
        errors.append("tool_script_layout.required_pattern must be set")
    if not isinstance(script_layout.get("require_full_triad"), bool):
        errors.append("tool_script_layout.require_full_triad must be boolean")
    if not str(script_layout.get("gui_exception_manifest", "")).strip():
        errors.append("tool_script_layout.gui_exception_manifest must be set")
    return errors


def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = legacy_global_rule_overrides(profile)
    path = global_rule_overrides_path(root, profile)
    raw = read_json(path) if path.exists() else {}
    merged = merge_object(defaults, raw) if isinstance(raw, dict) else defaults
    errors = validate_global_rule_overrides_data(merged)
    if path.exists():
        if not isinstance(raw, dict):
            errors.append("local governance config must be a JSON object")
        elif "code_comment_policy" not in raw:
            errors.append("code_comment_policy must be present in local governance config")
        else:
            raw_policy = raw.get("code_comment_policy")
            if not isinstance(raw_policy, dict):
                errors.append("code_comment_policy must be a non-empty object")
            else:
                errors.extend(validate_code_comment_policy_data(raw_policy, require_explicit=True))
        if "source_governance" not in raw:
            errors.append("source_governance must be present in local governance config")
        elif not isinstance(raw.get("source_governance"), dict):
            errors.append("source_governance must be a non-empty object")
        else:
            errors.extend(validate_source_governance_data(raw["source_governance"]))
    return {"path": path, "exists": path.is_file(), "data": merged, "errors": errors}


def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded = load_global_rule_overrides(root, profile)
    path = loaded["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(loaded["data"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        loaded = load_global_rule_overrides(root, profile)
    manifest_path = root / str(loaded["data"]["tool_script_layout"].get("gui_exception_manifest", ".agents/script-governance-exceptions.json")).strip()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        manifest_path.write_text('{\n  "gui_startup": []\n}\n', encoding="utf-8")
    return loaded


def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    defaults = default_implementation_constraints()
    if root is not None:
        overrides = load_global_rule_overrides(root, profile)["data"]
        source_governance = overrides.get("source_governance", {})
        script_layout = overrides["tool_script_layout"]
        return {
            "source_file_max_lines": int(source_governance.get("max_lines", defaults["source_file_max_lines"])),
            "line_limit_extensions": list(source_governance.get("hard_fail_extensions", defaults["line_limit_extensions"])),
            "line_limit_scope": defaults["line_limit_scope"],
            "line_limit_exclude_roots": list(source_governance.get("excluded_roots", defaults["line_limit_exclude_roots"])),
            "script_layout": {
                "required_root": str(script_layout.get("required_root", defaults["script_layout"]["required_root"])),
                "families": dict(script_layout.get("families", defaults["script_layout"]["families"])),
                "required_pattern": str(script_layout.get("required_pattern", defaults["script_layout"]["required_pattern"])),
                "require_full_triad": bool(script_layout.get("require_full_triad", defaults["script_layout"]["require_full_triad"])),
                "gui_exception_mode": "explicit-manifest",
                "gui_exception_manifest": str(script_layout.get("gui_exception_manifest", ".agents/script-governance-exceptions.json")),
            },
        }
    if not isinstance(profile, dict):
        return defaults
    raw = profile.get("implementation_constraints", {})
    if not isinstance(raw, dict):
        return defaults
    merged = dict(defaults)
    merged.update({key: value for key, value in raw.items() if key != "script_layout"})
    merged["script_layout"] = dict(defaults["script_layout"])
    script_layout = raw.get("script_layout", {})
    if isinstance(script_layout, dict):
        merged["script_layout"].update(script_layout)
    return merged
