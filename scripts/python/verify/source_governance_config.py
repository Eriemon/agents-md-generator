"""加载、合并并校验源码治理、注释策略和脚本输出策略配置。"""

# 导入 脚本治理 所需的依赖模块。
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

# 导入 脚本治理 所需的依赖模块。
import json
from pathlib import Path
from typing import Any

# 定义 read_json 的脚本治理处理入口。
def read_json(path: Path) -> dict[str, Any]:

    # 保护 read_json 中允许失败的外部访问。
    try:

        # 返回 read_json 已整理完成的调用载荷。
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:

        # 返回 read_json 已整理完成的调用载荷。
        return {}

# 定义 skill_root 的脚本治理处理入口。
def skill_root() -> Path:

    # 返回 skill_root 已整理完成的调用载荷。
    return Path(__file__).resolve().parents[3]

# 定义 skill_source_governance_path 的脚本治理处理入口。
def skill_source_governance_path(root: Path | None = None) -> Path:

    # 返回 skill_source_governance_path 已整理完成的调用载荷。
    return (root or skill_root()) / "config" / "source-governance.json"

# 定义 skill_script_output_policy_path 的脚本治理处理入口。
def skill_script_output_policy_path(root: Path | None = None) -> Path:

    # 返回 skill_script_output_policy_path 已整理完成的调用载荷。
    return (root or skill_root()) / "config" / "script-output-policy-default.json"

# 定义 default_source_governance 的脚本治理处理入口。
def default_source_governance() -> dict[str, Any]:

    # 保留 data 中间值，支撑 default_source_governance 的当前计算步骤。
    dict_data = read_json(skill_source_governance_path())  # data 用于本步治理判断

    # 返回 default_source_governance 已整理完成的调用载荷。
    return dict_data if isinstance(dict_data, dict) else {}

# 定义 default_script_output_policy 的脚本治理处理入口。
def default_script_output_policy() -> dict[str, Any]:

    # 保留 data 中间值，支撑 default_script_output_policy 的当前计算步骤。
    dict_data = read_json(skill_script_output_policy_path())  # data 用于本步治理判断

    # 返回 default_script_output_policy 已整理完成的调用载荷。
    return dict_data if isinstance(dict_data, dict) else {}

# 定义 load_skill_source_governance 的脚本治理处理入口。
def load_skill_source_governance(root: Path | None = None) -> dict[str, Any]:

    # 保留 path 中间值，支撑 load_skill_source_governance 的当前计算步骤。
    path_path = skill_source_governance_path(root)  # path 用于本步治理判断

    # 保留 data 中间值，支撑 load_skill_source_governance 的当前计算步骤。
    dict_data = read_json(path_path) if path_path.is_file() else {}  # data 用于本步治理判断

    # 检查 load_skill_source_governance 的当前条件是否需要进入专门分支。
    if not isinstance(dict_data, dict):

        # 保留 data 中间值，支撑 load_skill_source_governance 的当前计算步骤。
        dict_data = {}  # data 用于本步治理判断

    # 收集 errors 条目，保持 load_skill_source_governance 的处理顺序稳定。
    list_errors = validate_source_governance_data(dict_data)  # errors 用于本步治理判断

    # 检查 load_skill_source_governance 的当前条件是否需要进入专门分支。
    if not path_path.is_file():

        # 调用 insert 完成 load_skill_source_governance 的当前动作。
        list_errors.insert(0, f"missing source governance config: {path_path.as_posix()}")

    # 返回 load_skill_source_governance 已整理完成的调用载荷。
    return {"path": path_path, "exists": path_path.is_file(), "data": dict_data, "errors": list_errors}

# 定义 default_implementation_constraints 的脚本治理处理入口。
def default_implementation_constraints() -> dict[str, Any]:

    # 保留 source 中间值，支撑 default_implementation_constraints 的当前计算步骤。
    dict_source = default_source_governance()  # source 用于本步治理判断

    # 返回 default_implementation_constraints 已整理完成的调用载荷。
    return {
        "source_file_max_bytes": int(dict_source.get("max_bytes", 0)),
        "size_limit_extensions": list(dict_source.get("hard_fail_extensions", [])),
        "size_limit_scope": "handwritten-source-and-tool-scripts",
        "size_limit_exclude_roots": list(dict_source.get("excluded_roots", [])),
        "script_layout": {
            "required_root": "scripts",
            "families": {"python": ".py", "shell": ".sh", "bat": ".bat", "powershell": ".ps1"},
            "required_pattern": "scripts/<family>/<function>/<name>.<ext>",
            "require_full_triad": True,
            "gui_exception_mode": "explicit-manifest",
        },
    }

# 定义 default_global_rule_overrides 的脚本治理处理入口。
def default_global_rule_overrides() -> dict[str, Any]:

    # 收集 constraints 条目，保持 default_global_rule_overrides 的处理顺序稳定。
    dict_constraints = default_implementation_constraints()  # constraints 用于本步治理判断

    # 保留 script layout 中间值，支撑 default_global_rule_overrides 的当前计算步骤。
    script_layout = dict_constraints["script_layout"]  # script layout 用于本步治理判断

    # 保留 source 中间值，支撑 default_global_rule_overrides 的当前计算步骤。
    dict_source = default_source_governance()  # source 用于本步治理判断

    # 返回 default_global_rule_overrides 已整理完成的调用载荷。
    return {
        "coding_behavior": {
            "comment_quality": "只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释；禁止复述代码；禁止未经明确要求的批量 AI 注释；行为变化时必须更新旧注释。",
            "formatting": "生成代码必须保留回车/空行分隔，不能把语句、注释、函数粘连到一起；严禁把代码压缩到一行，严禁生成人看不懂的炫技代码。",
            "language_skill_routing": {
                "python": "进行 Python 代码生成、修改、注释、规范化时优先使用 `readable-python-generator`，并遵循其任务分类、注释质量、变量命名和质量门禁。",
                "script": "进行 bat/cmd、shell/bash、PowerShell、Tcl 脚本生成、审查、重构、修复、解释、添加/规范中文语义注释时优先使用 `readable-script-generator`；目标必须是这些脚本语言。Python 目标继续使用 `readable-python-generator`；脚本包装器调用 Python 外部命令时仍按脚本目标处理。",
            },
        },
        "script_output_policy": default_script_output_policy(),
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
        "source_governance": dict_source,
        "source_file_limits": {
            "max_bytes": dict_constraints["source_file_max_bytes"],
            "included_extensions": list(dict_source.get("hard_fail_extensions", [])),
            "excluded_roots": list(dict_source.get("excluded_roots", [])),
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

# 定义 global_rule_overrides_reference 的脚本治理处理入口。
def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:

    # 检查 global_rule_overrides_reference 的当前条件是否需要进入专门分支。
    if not isinstance(profile, dict):

        # 返回 global_rule_overrides_reference 已整理完成的调用载荷。
        return ".agents/global-rule-overrides.json"

    # 保留 inline 中间值，支撑 global_rule_overrides_reference 的当前计算步骤。
    inline = profile.get("global_rule_overrides", {})  # inline 用于本步治理判断

    # 检查 global_rule_overrides_reference 的当前条件是否需要进入专门分支。
    if isinstance(inline, dict):

        # 保留 candidate 中间值，支撑 global_rule_overrides_reference 的当前计算步骤。
        candidate = str(inline.get("path", "")).strip()  # candidate 用于本步治理判断

        # 检查 global_rule_overrides_reference 的当前条件是否需要进入专门分支。
        if candidate:

            # 返回 global_rule_overrides_reference 已整理完成的调用载荷。
            return candidate

    # 保留 legacy 中间值，支撑 global_rule_overrides_reference 的当前计算步骤。
    legacy = str(profile.get("global_rule_overrides_config", "")).strip()  # legacy 用于本步治理判断

    # 返回 global_rule_overrides_reference 已整理完成的调用载荷。
    return legacy or ".agents/global-rule-overrides.json"

# 定义 global_rule_overrides_path 的脚本治理处理入口。
def global_rule_overrides_path(root: Path, profile: dict[str, Any] | None = None) -> Path:

    # 保留 candidate 中间值，支撑 global_rule_overrides_path 的当前计算步骤。
    path_candidate = Path(global_rule_overrides_reference(profile))  # candidate 用于本步治理判断

    # 返回 global_rule_overrides_path 已整理完成的调用载荷。
    return path_candidate if path_candidate.is_absolute() else (root / path_candidate)

# 定义 merge_object 的脚本治理处理入口。
def merge_object(base: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:

    # 保留 merged 中间值，支撑 merge_object 的当前计算步骤。
    dict_merged = dict(base)  # merged 用于本步治理判断

    # 逐项推进 merge_object 的候选项检查。
    for key, raw_value in raw.items():

        # 检查 merge_object 的当前条件是否需要进入专门分支。
        if isinstance(raw_value, dict) and isinstance(dict_merged.get(key), dict):

            # 保留 中间载荷 中间值，支撑 merge_object 的当前计算步骤。
            dict_merged[key] = merge_object(dict_merged[key], raw_value)  # 中间载荷 用于本步治理判断
        else:

            # 保留 中间载荷 中间值，支撑 merge_object 的当前计算步骤。
            dict_merged[key] = raw_value  # 中间载荷 用于本步治理判断

    # 返回 merge_object 已整理完成的调用载荷。
    return dict_merged

# 定义 legacy_global_rule_overrides 的脚本治理处理入口。
def legacy_global_rule_overrides(profile: dict[str, Any] | None) -> dict[str, Any]:

    # 收集 defaults 条目，保持 legacy_global_rule_overrides 的处理顺序稳定。
    dict_defaults = default_global_rule_overrides()  # defaults 用于本步治理判断

    # 检查 legacy_global_rule_overrides 的当前条件是否需要进入专门分支。
    if not isinstance(profile, dict):

        # 返回 legacy_global_rule_overrides 已整理完成的调用载荷。
        return dict_defaults

    # 收集 constraints 条目，保持 legacy_global_rule_overrides 的处理顺序稳定。
    constraints = profile.get("implementation_constraints", {})  # constraints 用于本步治理判断

    # 检查 legacy_global_rule_overrides 的当前条件是否需要进入专门分支。
    if not isinstance(constraints, dict) or not constraints:

        # 返回 legacy_global_rule_overrides 已整理完成的调用载荷。
        return dict_defaults

    # 保留 layout 中间值，支撑 legacy_global_rule_overrides 的当前计算步骤。
    layout = constraints.get("script_layout", {}) if isinstance(constraints.get("script_layout", {}), dict) else {}  # layout 用于本步治理判断

    # 返回 legacy_global_rule_overrides 已整理完成的调用载荷。
    return merge_object(
        dict_defaults,
        {
            "source_file_limits": {
                "max_bytes": constraints.get("source_file_max_bytes", dict_defaults["source_file_limits"]["max_bytes"]),
                "included_extensions": constraints.get("size_limit_extensions", dict_defaults["source_file_limits"]["included_extensions"]),
                "excluded_roots": constraints.get("size_limit_exclude_roots", dict_defaults["source_file_limits"]["excluded_roots"]),
            },
            "tool_script_layout": {
                "required_root": layout.get("required_root", dict_defaults["tool_script_layout"]["required_root"]),
                "families": layout.get("families", dict_defaults["tool_script_layout"]["families"]),
                "required_pattern": layout.get("required_pattern", dict_defaults["tool_script_layout"]["required_pattern"]),
                "require_full_triad": layout.get("require_full_triad", dict_defaults["tool_script_layout"]["require_full_triad"]),
            },
        },
    )

# 定义 validate_code_comment_policy_data 的脚本治理处理入口。
def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:

    # 收集 errors 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
    if not comment_policy:

        # 返回 validate_code_comment_policy_data 已整理完成的调用载荷。
        return ["code_comment_policy must be a non-empty object"]

    # 收集 required text fields 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    tuple_required_text_fields = ("language", "default_policy", "formatting", "python", "c_cpp", "verilog_systemverilog")  # required text fields 用于本步治理判断

    # 逐项推进 validate_code_comment_policy_data 的候选项检查。
    for key in tuple_required_text_fields:

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if require_explicit and key not in comment_policy:

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append(f"code_comment_policy.{key} must be explicitly set")

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if not str(comment_policy.get(key, "")).strip():

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append(f"code_comment_policy.{key} must be set")

    # 收集 required snippets 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    dict_required_snippets = {  # required snippets 用于本步治理判断
        "default_policy": ["非显然意图", "不变量", "风险", "生成边界", "公共 API 行为", "禁止复述代码", "禁止未经明确要求的批量 AI 注释", "行为变化时必须更新旧注释"],  # required snippets 用于本步治理判断
        "formatting": ["回车/空行分隔", "不能把语句、注释、函数粘连到一起", "严禁把代码压缩到一行", "炫技代码"],  # required snippets 用于本步治理判断
        "python": ["docstring", "代码上方", "strict readable 规则允许右侧中文用途注释", "禁止模板化"],  # required snippets 用于本步治理判断
        "c_cpp": ["函数", "模块核心功能", "变量定义", "#define", "右侧", "所有权/生命周期"],  # C/C++ 注释策略必备片段
        "verilog_systemverilog": ["module", "input/output/inout/parameter/localparam/integer/logic/wire/reg/real", "assign", "always", "右侧", "上方"],  # required snippets 用于本步治理判断
    }

    # 逐项推进 validate_code_comment_policy_data 的候选项检查。
    for key, snippets in dict_required_snippets.items():

        # 保留 value 中间值，支撑 validate_code_comment_policy_data 的当前计算步骤。
        str_value = str(comment_policy.get(key, ""))  # value 用于本步治理判断

        # 逐项推进 validate_code_comment_policy_data 的候选项检查。
        for snippet in snippets:

            # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
            if snippet not in str_value:

                # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
                list_errors.append(f"code_comment_policy.{key} missing required rule `{snippet}`")

    # 收集 positions 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    positions = comment_policy.get("positions")  # positions 用于本步治理判断

    # 收集 required positions 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    dict_required_positions = {  # required positions 用于本步治理判断
        "python.public_api": "docstring",  # required positions 用于本步治理判断
        "python.inline": "above",  # required positions 用于本步治理判断
        "python.trailing": "strict-readable-assignment-purpose",  # required positions 用于本步治理判断
        "c_cpp.function": "above",  # required positions 用于本步治理判断
        "c_cpp.module": "above",  # required positions 用于本步治理判断
        "c_cpp.variable": "above",  # required positions 用于本步治理判断
        "c_cpp.specific_behavior": "above",  # required positions 用于本步治理判断
        "c_cpp.macro_define": "right_side",  # required positions 用于本步治理判断
        "verilog_systemverilog.module": "above",  # required positions 用于本步治理判断
        "verilog_systemverilog.declaration": "right_side",  # required positions 用于本步治理判断
        "verilog_systemverilog.assign": "right_side",  # required positions 用于本步治理判断
        "verilog_systemverilog.task_function_generate_always": "above",  # required positions 用于本步治理判断
        "verilog_systemverilog.always_register_assignment": "right_side",  # required positions 用于本步治理判断
    }

    # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "positions" not in comment_policy:

        # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
        list_errors.append("code_comment_policy.positions must be explicitly set")

    # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
    if not isinstance(positions, dict):

        # 返回 validate_code_comment_policy_data 已整理完成的调用载荷。
        return list_errors + ["code_comment_policy.positions must be an object"]

    # 收集 allowed positions 条目，保持 validate_code_comment_policy_data 的处理顺序稳定。
    set_allowed_positions = {"above", "right_side", "docstring", "forbidden", "strict-readable-assignment-purpose"}  # allowed positions 用于本步治理判断

    # 逐项推进 validate_code_comment_policy_data 的候选项检查。
    for key, expected in dict_required_positions.items():

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if require_explicit and key not in positions:

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append(f"code_comment_policy.positions.{key} must be explicitly set")

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if positions.get(key) != expected:

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append(f"code_comment_policy.positions.{key} must be {expected}")

    # 逐项推进 validate_code_comment_policy_data 的候选项检查。
    for key, str_value in positions.items():

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if str_value not in set_allowed_positions:

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append(f"code_comment_policy.positions.{key} has invalid value {str_value}")

    # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
    if positions.get("python.assignment") not in (None, "right_side"):

        # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
        list_errors.append("code_comment_policy.positions.python.assignment must be right_side when set")

    # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
    if positions.get("python.assignment") == "right_side":

        # 保留 python policy 中间值，支撑 validate_code_comment_policy_data 的当前计算步骤。
        str_python_policy = str(comment_policy.get("python", ""))  # python policy 用于本步治理判断

        # 检查 validate_code_comment_policy_data 的当前条件是否需要进入专门分支。
        if "右侧中文用途注释" not in str_python_policy:

            # 调用 append 完成 validate_code_comment_policy_data 的当前动作。
            list_errors.append("code_comment_policy.python missing required assignment exception `右侧中文用途注释`")

    # 返回 validate_code_comment_policy_data 已整理完成的调用载荷。
    return list_errors

# 定义 migrate_code_comment_policy_to_coding_behavior 的脚本治理处理入口。
def migrate_code_comment_policy_to_coding_behavior(raw: dict[str, Any]) -> dict[str, Any]:

    # 复制输入配置，避免调用方原始字典被兼容迁移路径污染。
    dict_migrated = dict(raw)  # 迁移后的治理配置

    # 只在新键缺失时消费旧键；新键存在时以新治理概念为准。
    if "coding_behavior" not in dict_migrated and isinstance(dict_migrated.get("code_comment_policy"), dict):
        legacy_policy = dict_migrated["code_comment_policy"]  # 旧注释策略兼容输入
        default_coding_behavior = default_global_rule_overrides()["coding_behavior"]  # 新编码行为默认值

        # 旧配置中的格式规则仍然有价值，迁移到 Coding Behavior Baseline。
        formatting = str(legacy_policy.get("formatting", default_coding_behavior["formatting"])).strip()

        # 旧 Python 策略只作为兼容输入；路由关键词缺失时使用新默认，避免弱化技能选择。
        python_route = str(legacy_policy.get("python", "")).strip()
        if "readable-python-generator" not in python_route:
            python_route = default_coding_behavior["language_skill_routing"]["python"]

        # 写入新键结构，脚本路由总是从新默认补齐。
        dict_migrated["coding_behavior"] = {
            "comment_quality": str(legacy_policy.get("default_policy", default_coding_behavior["comment_quality"])).strip(),
            "formatting": formatting or default_coding_behavior["formatting"],
            "language_skill_routing": {
                "python": python_route,
                "script": default_coding_behavior["language_skill_routing"]["script"],
            },
        }

    # 旧键只作为输入兼容，不再保留到新渲染和重写输出。
    dict_migrated.pop("code_comment_policy", None)

    # 返回迁移后的治理配置。
    return dict_migrated

# 定义 validate_coding_behavior_data 的脚本治理处理入口。
def validate_coding_behavior_data(coding_behavior: dict[str, Any], *, require_explicit: bool = False) -> list[str]:

    # 收集 errors 条目，保持 validate_coding_behavior_data 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 validate_coding_behavior_data 的当前条件是否需要进入专门分支。
    if not coding_behavior:

        # 返回 validate_coding_behavior_data 已整理完成的调用载荷。
        return ["coding_behavior must be a non-empty object"]

    # 显式配置必须保留 language_skill_routing 键，避免回退到旧概念。
    if require_explicit and "language_skill_routing" not in coding_behavior:
        list_errors.append("coding_behavior.language_skill_routing must be explicitly set")

    # 读取路由结构，供后续逐项检查。
    routing = coding_behavior.get("language_skill_routing", {})  # 语言技能路由配置
    if not isinstance(routing, dict) or not routing:
        return list_errors + ["coding_behavior.language_skill_routing must be a non-empty object"]

    # 新配置必须同时覆盖 Python 和脚本目标。
    for key in ("python", "script"):
        if require_explicit and key not in routing:
            list_errors.append(f"coding_behavior.language_skill_routing.{key} must be explicitly set")
        if not str(routing.get(key, "")).strip():
            list_errors.append(f"coding_behavior.language_skill_routing.{key} must be set")

    # Python 路由必须明确使用 Python 专用技能，不能被脚本技能接管。
    python_route = str(routing.get("python", ""))  # Python 技能路由文本
    if "readable-python-generator" not in python_route:
        list_errors.append("coding_behavior.language_skill_routing.python missing `readable-python-generator`")
    if "readable-script-generator" in python_route:
        list_errors.append("coding_behavior.language_skill_routing.python must not route Python targets to `readable-script-generator`")

    # 脚本路由必须覆盖目标语言和脚本技能，同时保留 Python 边界。
    script_route = str(routing.get("script", ""))  # 脚本技能路由文本
    for snippet in (
        "readable-script-generator",
        "bat/cmd",
        "shell/bash",
        "PowerShell",
        "Tcl",
        "Python 目标继续使用 `readable-python-generator`",
        "脚本包装器调用 Python",
    ):
        if snippet not in script_route:
            list_errors.append(f"coding_behavior.language_skill_routing.script missing required rule `{snippet}`")

    # 格式规则仍属于编码行为基线，用于防止代码被压缩成不可读输出。
    formatting = str(coding_behavior.get("formatting", ""))  # 编码格式约束文本
    for snippet in ("回车/空行分隔", "不能把语句、注释、函数粘连到一起", "严禁把代码压缩到一行", "炫技代码"):
        if snippet not in formatting:
            list_errors.append(f"coding_behavior.formatting missing required rule `{snippet}`")

    # 返回 validate_coding_behavior_data 已整理完成的调用载荷。
    return list_errors

# 定义 validate_script_output_policy_data 的脚本治理处理入口。
def validate_script_output_policy_data(policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:

    # 收集 errors 条目，保持 validate_script_output_policy_data 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if not policy:

        # 返回 validate_script_output_policy_data 已整理完成的调用载荷。
        return ["script_output_policy must be a non-empty object"]

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "enabled" not in policy:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.enabled must be explicitly set")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if not isinstance(policy.get("enabled"), bool):

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.enabled must be boolean")

    # 收集 formats 条目，保持 validate_script_output_policy_data 的处理顺序稳定。
    formats = policy.get("format")  # formats 用于本步治理判断

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "format" not in policy:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.format must be explicitly set")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if not isinstance(formats, dict):

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.format must be an object")
    else:

        # 收集 required formats 条目，保持 validate_script_output_policy_data 的处理顺序稳定。
        dict_required_formats = {  # required formats 用于本步治理判断
            "info": "> INFO: [{kind}]",  # required formats 用于本步治理判断
            "warning": "> WARNING: [{kind}]",  # required formats 用于本步治理判断
            "error": "> ERR: [{kind}]",  # required formats 用于本步治理判断
        }

        # 逐项推进 validate_script_output_policy_data 的候选项检查。
        for key, expected in dict_required_formats.items():

            # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
            if require_explicit and key not in formats:

                # 调用 append 完成 validate_script_output_policy_data 的当前动作。
                list_errors.append(f"script_output_policy.format.{key} must be explicitly set")

            # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
            if formats.get(key) != expected:

                # 调用 append 完成 validate_script_output_policy_data 的当前动作。
                list_errors.append(f"script_output_policy.format.{key} must be `{expected}`")

    # 收集 kinds 条目，保持 validate_script_output_policy_data 的处理顺序稳定。
    kinds = policy.get("kinds")  # kinds 用于本步治理判断

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "kinds" not in policy:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.kinds must be explicitly set")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if not isinstance(kinds, list) or not kinds:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.kinds must be a non-empty list")
    else:

        # 保留 normalized 中间值，支撑 validate_script_output_policy_data 的当前计算步骤。
        normalized = [str(item).strip() for item in kinds]  # normalized 用于本步治理判断

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if any(not item for item in normalized):

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.kinds must not contain empty values")

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if len(set(normalized)) != len(normalized):

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.kinds must not contain duplicates after trimming")

    # 保留 python policy 中间值，支撑 validate_script_output_policy_data 的当前计算步骤。
    python_policy = policy.get("python")  # python policy 用于本步治理判断

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "python" not in policy:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.python must be explicitly set")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if not isinstance(python_policy, dict):

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.python must be an object")
    else:

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if require_explicit and "info_default" not in python_policy:

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.python.info_default must be explicitly set")

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if python_policy.get("info_default") != "on":

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.python.info_default must be on")

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if require_explicit and "quiet_flag" not in python_policy:

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.python.quiet_flag must be explicitly set")

        # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
        if python_policy.get("quiet_flag") != "--quiet":

            # 调用 append 完成 validate_script_output_policy_data 的当前动作。
            list_errors.append("script_output_policy.python.quiet_flag must be --quiet")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if require_explicit and "machine_readable_exemption" not in policy:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.machine_readable_exemption must be explicitly set")

    # 检查 validate_script_output_policy_data 的当前条件是否需要进入专门分支。
    if policy.get("machine_readable_exemption") is not True:

        # 调用 append 完成 validate_script_output_policy_data 的当前动作。
        list_errors.append("script_output_policy.machine_readable_exemption must be true")

    # 返回 validate_script_output_policy_data 已整理完成的调用载荷。
    return list_errors

# 定义 validate_source_governance_data 的脚本治理处理入口。
def validate_source_governance_data(data: dict[str, Any]) -> list[str]:

    # 收集 errors 条目，保持 validate_source_governance_data 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(data, dict) or not data:

        # 返回 validate_source_governance_data 已整理完成的调用载荷。
        return ["source_governance must be a non-empty object"]

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if "max_lines" in data:

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.max_lines is retired; use source_governance.max_bytes")

    # 收集 max bytes 条目，保持 validate_source_governance_data 的处理顺序稳定。
    max_bytes = data.get("max_bytes")  # max bytes 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(max_bytes, int) or max_bytes <= 0:

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.max_bytes must be a positive integer")

    # 收集 extensions 条目，保持 validate_source_governance_data 的处理顺序稳定。
    extensions = data.get("hard_fail_extensions")  # extensions 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(extensions, list) or not extensions or not all(str(item).startswith(".") for item in extensions):

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.hard_fail_extensions must be a non-empty extension list")

    # 收集 excluded roots 条目，保持 validate_source_governance_data 的处理顺序稳定。
    excluded_roots = data.get("excluded_roots")  # excluded roots 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(excluded_roots, list):

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.excluded_roots must be a list")

    # 保留 test only 中间值，支撑 validate_source_governance_data 的当前计算步骤。
    test_only = data.get("test_only_patterns")  # test only 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(test_only, dict) or not isinstance(test_only.get("path_globs"), list) or not test_only.get("path_globs"):

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.test_only_patterns.path_globs must be a non-empty list")

    # 保留 comment gate 中间值，支撑 validate_source_governance_data 的当前计算步骤。
    comment_gate = data.get("comment_policy_gate")  # comment gate 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(comment_gate, dict):

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.comment_policy_gate must be an object")
    else:

        # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
        if not isinstance(comment_gate.get("enabled"), bool):

            # 调用 append 完成 validate_source_governance_data 的当前动作。
            list_errors.append("source_governance.comment_policy_gate.enabled must be boolean")

        # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
        if not isinstance(comment_gate.get("forbid_ai_comment_markers"), list):

            # 调用 append 完成 validate_source_governance_data 的当前动作。
            list_errors.append("source_governance.comment_policy_gate.forbid_ai_comment_markers must be a list")

        # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
        if not isinstance(comment_gate.get("python"), dict):

            # 调用 append 完成 validate_source_governance_data 的当前动作。
            list_errors.append("source_governance.comment_policy_gate.python must be an object")
        else:

            # 保留 python gate 中间值，支撑 validate_source_governance_data 的当前计算步骤。
            python_gate = comment_gate.get("python", {})  # python gate 用于本步治理判断

            # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
            if "allow_assignment_trailing_comment" in python_gate and not isinstance(
                python_gate.get("allow_assignment_trailing_comment"),
                bool,
            ):

                # 调用 append 完成 validate_source_governance_data 的当前动作。
                list_errors.append("source_governance.comment_policy_gate.python.allow_assignment_trailing_comment must be boolean")

        # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
        if not isinstance(comment_gate.get("c_cpp"), dict):

            # 调用 append 完成 validate_source_governance_data 的当前动作。
            list_errors.append("source_governance.comment_policy_gate.c_cpp must be an object")

    # 保留 readability gate 中间值，支撑 validate_source_governance_data 的当前计算步骤。
    readability_gate = data.get("readability_gate")  # readability gate 用于本步治理判断

    # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
    if not isinstance(readability_gate, dict):

        # 调用 append 完成 validate_source_governance_data 的当前动作。
        list_errors.append("source_governance.readability_gate must be an object")
    else:

        # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
        if not isinstance(readability_gate.get("enabled"), bool):

            # 调用 append 完成 validate_source_governance_data 的当前动作。
            list_errors.append("source_governance.readability_gate.enabled must be boolean")

        # 逐项推进 validate_source_governance_data 的候选项检查。
        for key in ("max_physical_line_bytes", "single_line_min_bytes", "minified_line_min_bytes"):

            # 保留 value 中间值，支撑 validate_source_governance_data 的当前计算步骤。
            raw_value = readability_gate.get(key)  # value 用于本步治理判断

            # 检查 validate_source_governance_data 的当前条件是否需要进入专门分支。
            if not isinstance(raw_value, int) or raw_value <= 0:

                # 调用 append 完成 validate_source_governance_data 的当前动作。
                list_errors.append(f"source_governance.readability_gate.{key} must be a positive integer")

    # 返回 validate_source_governance_data 已整理完成的调用载荷。
    return list_errors

# 定义 validate_global_rule_overrides_data 的脚本治理处理入口。
def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:

    # 收集 errors 条目，保持 validate_global_rule_overrides_data 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 coding behavior 中间值，支撑 validate_global_rule_overrides_data 的当前计算步骤。
    coding_behavior = data.get("coding_behavior", {}) if isinstance(data.get("coding_behavior", {}), dict) else {}  # coding behavior 用于本步治理判断

    # 保留 script output policy 中间值，支撑 validate_global_rule_overrides_data 的当前计算步骤。
    script_output_policy = data.get("script_output_policy", {}) if isinstance(data.get("script_output_policy", {}), dict) else {}  # script output policy 用于本步治理判断

    # 收集 long tasks 条目，保持 validate_global_rule_overrides_data 的处理顺序稳定。
    long_tasks = data.get("long_python_tasks", {}) if isinstance(data.get("long_python_tasks", {}), dict) else {}  # long tasks 用于本步治理判断

    # 保留 source governance 中间值，支撑 validate_global_rule_overrides_data 的当前计算步骤。
    source_governance = data.get("source_governance", {}) if isinstance(data.get("source_governance", {}), dict) else {}  # source governance 用于本步治理判断

    # 收集 source limits 条目，保持 validate_global_rule_overrides_data 的处理顺序稳定。
    source_limits = data.get("source_file_limits", {}) if isinstance(data.get("source_file_limits", {}), dict) else {}  # source limits 用于本步治理判断

    # 保留 script layout 中间值，支撑 validate_global_rule_overrides_data 的当前计算步骤。
    script_layout = data.get("tool_script_layout", {}) if isinstance(data.get("tool_script_layout", {}), dict) else {}  # script layout 用于本步治理判断

    # 调用 extend 完成 validate_global_rule_overrides_data 的当前动作。
    list_errors.extend(validate_coding_behavior_data(coding_behavior))

    # 调用 extend 完成 validate_global_rule_overrides_data 的当前动作。
    list_errors.extend(validate_script_output_policy_data(script_output_policy))

    # 调用 extend 完成 validate_global_rule_overrides_data 的当前动作。
    list_errors.extend(validate_source_governance_data(source_governance))

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if long_tasks.get("automation_kind") != "heartbeat":

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("long_python_tasks.automation_kind must be heartbeat")

    # 逐项推进 validate_global_rule_overrides_data 的候选项检查。
    for key in ("default_interval_minutes", "long_running_threshold_minutes"):

        # 保留 value 中间值，支撑 validate_global_rule_overrides_data 的当前计算步骤。
        raw_value = long_tasks.get(key)  # value 用于本步治理判断

        # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
        if not isinstance(raw_value, int) or raw_value <= 0:

            # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
            list_errors.append(f"long_python_tasks.{key} must be a positive integer")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(long_tasks.get("completion_check_strategy"), dict) or not long_tasks.get("completion_check_strategy"):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("long_python_tasks.completion_check_strategy must be a non-empty object")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if "max_lines" in source_limits:

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.max_lines is retired; use source_file_limits.max_bytes")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(source_limits.get("max_bytes"), int) or source_limits.get("max_bytes", 0) <= 0:

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.max_bytes must be a positive integer")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(source_limits.get("included_extensions"), list):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.included_extensions must be a list of extensions")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(source_limits.get("excluded_roots"), list):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.excluded_roots must be a list")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not str(source_limits.get("decomposition_plan_root", "")).strip():

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.decomposition_plan_root must be set")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(source_limits.get("required_plan_sections"), list) or not source_limits.get("required_plan_sections"):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("source_file_limits.required_plan_sections must be a non-empty list")

    # 收集 families 条目，保持 validate_global_rule_overrides_data 的处理顺序稳定。
    families = script_layout.get("families")  # families 用于本步治理判断

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not str(script_layout.get("required_root", "")).strip():

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.required_root must be set")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(families, dict) or not families:

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.families must be a non-empty object")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    elif not all(str(ext).startswith(".") for ext in families.values()):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.families values must be extensions")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not str(script_layout.get("required_pattern", "")).strip():

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.required_pattern must be set")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not isinstance(script_layout.get("require_full_triad"), bool):

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.require_full_triad must be boolean")

    # 检查 validate_global_rule_overrides_data 的当前条件是否需要进入专门分支。
    if not str(script_layout.get("gui_exception_manifest", "")).strip():

        # 调用 append 完成 validate_global_rule_overrides_data 的当前动作。
        list_errors.append("tool_script_layout.gui_exception_manifest must be set")

    # 返回 validate_global_rule_overrides_data 已整理完成的调用载荷。
    return list_errors

# 定义 load_global_rule_overrides 的脚本治理处理入口。
def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 收集 defaults 条目，保持 load_global_rule_overrides 的处理顺序稳定。
    dict_defaults = legacy_global_rule_overrides(profile)  # defaults 用于本步治理判断

    # 保留 path 中间值，支撑 load_global_rule_overrides 的当前计算步骤。
    path_path = global_rule_overrides_path(root, profile)  # path 用于本步治理判断

    # 保留 raw 中间值，支撑 load_global_rule_overrides 的当前计算步骤。
    raw = read_json(path_path) if path_path.exists() else {}  # raw 用于本步治理判断

    # 迁移旧 code_comment_policy 输入，后续逻辑只处理 coding_behavior。
    migrated_raw = migrate_code_comment_policy_to_coding_behavior(raw) if isinstance(raw, dict) else raw  # 迁移后的原始配置

    # 保留 merged 中间值，支撑 load_global_rule_overrides 的当前计算步骤。
    merged = merge_object(dict_defaults, migrated_raw) if isinstance(migrated_raw, dict) else dict_defaults  # merged 用于本步治理判断

    # 收集 errors 条目，保持 load_global_rule_overrides 的处理顺序稳定。
    list_errors = validate_global_rule_overrides_data(merged)  # errors 用于本步治理判断

    # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
    if path_path.exists():

        # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
        if not isinstance(raw, dict):

            # 调用 append 完成 load_global_rule_overrides 的当前动作。
            list_errors.append("local governance config must be a JSON object")

        # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
        elif "coding_behavior" not in migrated_raw:

            # 调用 append 完成 load_global_rule_overrides 的当前动作。
            list_errors.append("coding_behavior.language_skill_routing must be present in local governance config")
        else:

            # 保留 raw coding behavior 中间值，支撑 load_global_rule_overrides 的当前计算步骤。
            raw_coding_behavior = migrated_raw.get("coding_behavior")  # raw coding behavior 用于本步治理判断

            # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
            if not isinstance(raw_coding_behavior, dict):

                # 调用 append 完成 load_global_rule_overrides 的当前动作。
                list_errors.append("coding_behavior must be a non-empty object")
            else:

                # 调用 extend 完成 load_global_rule_overrides 的当前动作。
                list_errors.extend(validate_coding_behavior_data(raw_coding_behavior, require_explicit=True))

        # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
        if "script_output_policy" not in raw:

            # 调用 append 完成 load_global_rule_overrides 的当前动作。
            list_errors.append("script_output_policy must be present in local governance config")
        else:

            # 保留 raw script output policy 中间值，支撑 load_global_rule_overrides 的当前计算步骤。
            raw_script_output_policy = raw.get("script_output_policy")  # raw script output policy 用于本步治理判断

            # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
            if not isinstance(raw_script_output_policy, dict):

                # 调用 append 完成 load_global_rule_overrides 的当前动作。
                list_errors.append("script_output_policy must be a non-empty object")
            else:

                # 调用 extend 完成 load_global_rule_overrides 的当前动作。
                list_errors.extend(validate_script_output_policy_data(raw_script_output_policy, require_explicit=True))

        # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
        if "source_governance" not in raw:

            # 调用 append 完成 load_global_rule_overrides 的当前动作。
            list_errors.append("source_governance must be present in local governance config")

        # 检查 load_global_rule_overrides 的当前条件是否需要进入专门分支。
        elif not isinstance(raw.get("source_governance"), dict):

            # 调用 append 完成 load_global_rule_overrides 的当前动作。
            list_errors.append("source_governance must be a non-empty object")
        else:

            # 调用 extend 完成 load_global_rule_overrides 的当前动作。
            list_errors.extend(validate_source_governance_data(raw["source_governance"]))

    # 返回 load_global_rule_overrides 已整理完成的调用载荷。
    return {"path": path_path, "exists": path_path.is_file(), "data": merged, "errors": list_errors}

# 定义 ensure_global_rule_overrides_file 的脚本治理处理入口。
def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 保留 loaded 中间值，支撑 ensure_global_rule_overrides_file 的当前计算步骤。
    dict_loaded = load_global_rule_overrides(root, profile)  # loaded 用于本步治理判断

    # 保留 path 中间值，支撑 ensure_global_rule_overrides_file 的当前计算步骤。
    path = dict_loaded["path"]  # path 用于本步治理判断

    # 调用 mkdir 完成 ensure_global_rule_overrides_file 的当前动作。
    path.parent.mkdir(parents=True, exist_ok=True)

    # 检查 ensure_global_rule_overrides_file 的当前条件是否需要进入专门分支。
    if not path.exists():

        # 调用 write_text 完成 ensure_global_rule_overrides_file 的当前动作。
        path.write_text(json.dumps(dict_loaded["data"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        # 保留 loaded 中间值，支撑 ensure_global_rule_overrides_file 的当前计算步骤。
        dict_loaded = load_global_rule_overrides(root, profile)  # loaded 用于本步治理判断
    else:

        # 读取现有 JSON，判断是否需要把旧 code_comment_policy 迁移为新键。
        raw_existing = read_json(path)  # 现有本地治理配置
        if isinstance(raw_existing, dict) and ("code_comment_policy" in raw_existing or "coding_behavior" not in raw_existing):

            # 调用 write_text 完成 ensure_global_rule_overrides_file 的迁移写回。
            path.write_text(json.dumps(dict_loaded["data"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            # 保留 loaded 中间值，支撑 ensure_global_rule_overrides_file 的当前计算步骤。
            dict_loaded = load_global_rule_overrides(root, profile)  # loaded 用于本步治理判断

    # 定位 manifest path 的文件边界，供 ensure_global_rule_overrides_file 后续读写校验使用。
    manifest_path = root / str(dict_loaded["data"]["tool_script_layout"].get("gui_exception_manifest", ".agents/script-governance-exceptions.json")).strip()  # manifest path 用于本步治理判断

    # 调用 mkdir 完成 ensure_global_rule_overrides_file 的当前动作。
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # 检查 ensure_global_rule_overrides_file 的当前条件是否需要进入专门分支。
    if not manifest_path.exists():

        # 调用 write_text 完成 ensure_global_rule_overrides_file 的当前动作。
        manifest_path.write_text('{\n  "gui_startup": []\n}\n', encoding="utf-8")

    # 返回 ensure_global_rule_overrides_file 已整理完成的调用载荷。
    return dict_loaded

# 定义 implementation_constraints_from_profile 的脚本治理处理入口。
def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:

    # 收集 defaults 条目，保持 implementation_constraints_from_profile 的处理顺序稳定。
    dict_defaults = default_implementation_constraints()  # defaults 用于本步治理判断

    # 检查 implementation_constraints_from_profile 的当前条件是否需要进入专门分支。
    if root is not None:

        # 收集 overrides 条目，保持 implementation_constraints_from_profile 的处理顺序稳定。
        overrides = load_global_rule_overrides(root, profile)["data"]  # overrides 用于本步治理判断

        # 保留 source governance 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
        source_governance = overrides.get("source_governance", {})  # source governance 用于本步治理判断

        # 保留 script layout 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
        script_layout = overrides["tool_script_layout"]  # script layout 用于本步治理判断

        # 返回 implementation_constraints_from_profile 已整理完成的调用载荷。
        return {
            "source_file_max_bytes": int(source_governance.get("max_bytes", dict_defaults["source_file_max_bytes"])),
            "size_limit_extensions": list(source_governance.get("hard_fail_extensions", dict_defaults["size_limit_extensions"])),
            "size_limit_scope": dict_defaults["size_limit_scope"],
            "size_limit_exclude_roots": list(source_governance.get("excluded_roots", dict_defaults["size_limit_exclude_roots"])),
            "script_layout": {
                "required_root": str(script_layout.get("required_root", dict_defaults["script_layout"]["required_root"])),
                "families": dict(script_layout.get("families", dict_defaults["script_layout"]["families"])),
                "required_pattern": str(script_layout.get("required_pattern", dict_defaults["script_layout"]["required_pattern"])),
                "require_full_triad": bool(script_layout.get("require_full_triad", dict_defaults["script_layout"]["require_full_triad"])),
                "gui_exception_mode": "explicit-manifest",
                "gui_exception_manifest": str(script_layout.get("gui_exception_manifest", ".agents/script-governance-exceptions.json")),
            },
        }

    # 检查 implementation_constraints_from_profile 的当前条件是否需要进入专门分支。
    if not isinstance(profile, dict):

        # 返回 implementation_constraints_from_profile 已整理完成的调用载荷。
        return dict_defaults

    # 保留 raw 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
    raw = profile.get("implementation_constraints", {})  # raw 用于本步治理判断

    # 检查 implementation_constraints_from_profile 的当前条件是否需要进入专门分支。
    if not isinstance(raw, dict):

        # 返回 implementation_constraints_from_profile 已整理完成的调用载荷。
        return dict_defaults

    # 保留 merged 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
    dict_merged = dict(dict_defaults)  # merged 用于本步治理判断

    # 调用 update 完成 implementation_constraints_from_profile 的当前动作。
    dict_merged.update({key: value for key, value in raw.items() if key != "script_layout"})

    # 保留 中间载荷 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
    dict_merged["script_layout"] = dict(dict_defaults["script_layout"])  # 中间载荷 用于本步治理判断

    # 保留 script layout 中间值，支撑 implementation_constraints_from_profile 的当前计算步骤。
    script_layout = raw.get("script_layout", {})  # script layout 用于本步治理判断

    # 检查 implementation_constraints_from_profile 的当前条件是否需要进入专门分支。
    if isinstance(script_layout, dict):

        # 调用 update 完成 implementation_constraints_from_profile 的当前动作。
        dict_merged["script_layout"].update(script_layout)

    # 返回 implementation_constraints_from_profile 已整理完成的调用载荷。
    return dict_merged


