"""加载、合并并校验源码治理、注释策略和脚本输出策略配置。"""

# 导入脚本治理所需的标准库模块。
from __future__ import annotations

# 解析 JSON 配置时只依赖标准库，避免治理入口额外引入运行时包。
import json
from pathlib import Path
from typing import Any

# 本地治理路径由 Path 组合得到，避免在业务文案中重复猜测。
DEFAULT_GLOBAL_OVERRIDES_PATH = (Path(".agents") / "global-rule-overrides.json").as_posix()  # 本地覆盖配置路径

# GUI 例外清单路径同样由治理目录和文件名组合得到。
DEFAULT_GUI_EXCEPTION_MANIFEST = (Path(".agents") / "script-governance-exceptions.json").as_posix()  # GUI 例外清单路径

# 复用语言技能路由默认文案与强制短语，保持渲染和校验一致。
from routing_contract import (
    DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON,
    DEFAULT_LANGUAGE_SKILL_ROUTING_SHARED,
    DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT,
    PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,
    SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,
    SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,

    # 禁用短语根据当前实际安装状态阻止路由虚构技能可用性。
    PYTHON_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS,
    SCRIPT_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS,
    managed_language_skill_route_defaults,
    missing_language_skill_route_snippets,
    _load_structured_route_defaults,
)

# 读取 JSON 文件，失败时回退为空映射。
def read_json(path_target: Path) -> dict[str, Any]:
    """读取 JSON 文件并在失败时返回空映射。

    参数:
        path_target: 待读取的 JSON 文件路径。

    返回:
        解析后的 JSON 对象；读取失败或 JSON 非法时返回空映射。
    """

    # 尝试读取并解析目标 JSON，兼容治理命令面对缺文件或脏文件的情况。
    try:

        # 返回解析成功后的 JSON 对象，供调用方继续做结构收口。
        return json.loads(path_target.read_text(encoding="utf-8"))

    # 读取失败时统一回退为空映射，避免调用方重复处理文件异常。
    except Exception:

        # 返回空映射，让上游继续输出结构化诊断。
        return {}

# 定位当前 skill 的根目录，供多个默认配置入口复用。
def skill_root() -> Path:
    """返回当前 skill 根目录。

    参数:
        无显式业务参数，目录来自当前文件的相对位置。

    返回:
        当前 agents-md-generator skill 的根目录路径。
    """

    # 返回从当前文件回溯得到的 skill 根目录。
    return Path(__file__).resolve().parents[3]

# 解析源码治理默认配置文件的固定位置。
def skill_source_governance_path(root: Path | None = None) -> Path:
    """返回源码治理默认配置文件路径。

    参数:
        root: 可选的 skill 根目录覆盖值；未提供时自动推导当前 skill 根目录。

    返回:
        `source-governance.json` 在 skill 内的绝对路径。
    """

    # 返回源码治理默认配置文件的绝对路径。
    return (root or skill_root()) / "config" / "source-governance.json"

# 解析脚本输出策略默认配置文件的固定位置。
def skill_script_output_policy_path(root: Path | None = None) -> Path:
    """返回脚本输出策略默认配置文件路径。

    参数:
        root: 可选的 skill 根目录覆盖值；未提供时自动推导当前 skill 根目录。

    返回:
        `script-output-policy-default.json` 在 skill 内的绝对路径。
    """

    # 返回脚本输出策略默认配置文件的绝对路径。
    return (root or skill_root()) / "config" / "script-output-policy-default.json"

# 读取源码治理默认配置，并把非对象结果压回空映射。
def default_source_governance() -> dict[str, Any]:
    """加载源码治理默认配置。

    参数:
        无显式业务参数，配置来源固定为 skill 内置默认文件。

    返回:
        源码治理默认配置；若读取结果不是对象则返回空映射。
    """

    # 读取 skill 自带的源码治理默认配置，供后续默认值拼装复用。
    dict_source_governance = read_json(skill_source_governance_path())  # skill 自带的源码治理默认配置

    # 返回结构正确的默认配置；非对象结果直接改回空映射。
    return dict_source_governance if isinstance(dict_source_governance, dict) else {}

# 读取脚本输出策略默认配置，并把非对象结果压回空映射。
def default_script_output_policy() -> dict[str, Any]:
    """加载脚本输出策略默认配置。

    参数:
        无显式业务参数，配置来源固定为 skill 内置默认文件。

    返回:
        脚本输出策略默认配置；若读取结果不是对象则返回空映射。
    """

    # 读取 skill 自带的脚本输出策略模板，供根 AGENTS 和 verifier 复用。
    dict_script_output_policy = read_json(skill_script_output_policy_path())  # skill 自带的脚本输出策略模板

    # 返回结构正确的输出策略默认值；非对象结果直接回退为空映射。
    return dict_script_output_policy if isinstance(dict_script_output_policy, dict) else {}

# 读取源码治理配置文件，并把存在性和结构错误一起打包返回。
def load_skill_source_governance(root: Path | None = None) -> dict[str, Any]:
    """加载源码治理配置并附带结构化诊断。

    参数:
        root: 可选的 skill 根目录覆盖值；未提供时自动推导当前 skill 根目录。

    返回:
        包含配置路径、存在性、配置正文和校验错误列表的结构化结果。
    """

    # 记录配置文件路径，后续既要尝试读取也要在错误里回显该位置。
    path_source_governance = skill_source_governance_path(root)  # 源码治理配置文件路径

    # 只有配置文件真实存在时才尝试读取，避免额外的文件系统异常。
    dict_source_governance = read_json(path_source_governance) if path_source_governance.is_file() else {}  # 当前读取到的源码治理配置

    # 非对象 JSON 对治理入口没有意义，这里统一改回空映射。
    if not isinstance(dict_source_governance, dict):

        # 把非法结构压回空映射，让后续校验走统一的字段错误路径。
        dict_source_governance = {}  # 非法 JSON 结构改写后的空配置

    # 先跑字段级校验，统一收集源码治理配置的结构错误。
    list_errors = validate_source_governance_data(dict_source_governance)  # 源码治理配置的结构化错误

    # 缺少默认文件时把路径诊断放到最前面，方便用户先看到根因。
    if not path_source_governance.is_file():

        # 把缺文件错误压到首位，避免被后续字段错误淹没。
        list_errors.insert(
            0,
            f"missing source governance config: {path_source_governance.as_posix()}",
        )

    # 返回源码治理配置的完整读取结果与诊断列表。
    return {
        "path": path_source_governance,
        "exists": path_source_governance.is_file(),
        "data": dict_source_governance,
        "errors": list_errors,
    }

# 组合旧实现仍依赖的默认实现约束视图。
def default_implementation_constraints() -> dict[str, Any]:
    """生成兼容旧字段结构的默认实现约束。

    参数:
        无显式业务参数，默认值全部来自当前 skill 的源码治理配置。

    返回:
        旧实现约束视图，供兼容层和历史 profile 继续复用。
    """

    # 读取源码治理默认值，供兼容视图回填原始块并拆出可复用的限制字段。
    dict_source_governance = default_source_governance()  # 默认源码治理配置

    # 返回兼容旧字段命名的默认实现约束视图。
    return {
        "source_file_max_bytes": int(dict_source_governance.get("max_bytes", 0)),
        "size_limit_extensions": list(dict_source_governance.get("hard_fail_extensions", [])),
        "size_limit_scope": "handwritten-source-and-tool-scripts",
        "size_limit_exclude_roots": list(dict_source_governance.get("excluded_roots", [])),
        "script_layout": {
            "required_root": "scripts",
            "families": {
                "python": ".py",
                "shell": ".sh",
                "bat": ".bat",
                "powershell": ".ps1",
            },
            "required_pattern": (Path("<script-root>") / "<family>" / "<function>" / "<name>.<extension>").as_posix(),
            "require_full_triad": True,
            "gui_exception_mode": "explicit-manifest",
        },
    }

# 生成根 AGENTS 渲染和 verifier 共用的本地治理默认配置。
def default_global_rule_overrides() -> dict[str, Any]:
    """构造本地治理配置的默认值。

    参数:
        无显式业务参数，默认值来自当前 skill 内置配置与固定契约短语。

    返回:
        供渲染器、校验器和兼容迁移逻辑共用的默认治理配置对象。
    """

    # 先组装兼容旧实现约束的默认值，后续多个子结构都会复用它。
    dict_constraints = default_implementation_constraints()  # 默认实现约束视图

    # 提取脚本布局默认值，避免在返回字典里重复索引多次。
    dict_script_layout = dict_constraints["script_layout"]  # 默认脚本布局约束

    # 这份默认树既要回填 source_governance 主块，也要借出扩展名和排除目录给兼容字段复刻。
    dict_source_governance_defaults = default_source_governance()  # 源码治理默认树

    # 结构化 route records 作为渲染、compact、audit 和 evaluation 的共享事实源。
    dict_structured_routes = _load_structured_route_defaults().get("routes", {})  # 结构化语言路由

    # 提取三条 full_text，避免默认配置字典中的长表达式挤在单行。
    str_default_shared_route = str(  # 共同门禁默认文案
        dict_structured_routes.get("shared", {}).get("full_text", DEFAULT_LANGUAGE_SKILL_ROUTING_SHARED)  # 共享路由全文来源
    )

    # Python 路由默认全文沿用 structured record 的 full_text。
    str_default_python_route = str(  # Python 默认文案
        dict_structured_routes.get("python", {}).get("full_text", DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON)  # Python 路由全文来源
    )

    # 脚本路由默认全文沿用 structured record 的 full_text。
    str_default_script_route = str(  # 脚本默认文案
        dict_structured_routes.get("script", {}).get("full_text", DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT)  # 脚本路由全文来源
    )

    # 默认注释规则同时保留渲染器和审计器要求的兼容短语。
    str_comment_quality = (
        "Comments must explain non-obvious intent, invariants, risk boundaries, "
        "generation boundaries, or public API behavior; do not restate code or "
        "perform bulk AI commenting without explicit request; update stale "
        "comments when behavior changes."
    )

    # 格式规则拆成可读片段，供根配置和 verifier 共用。
    str_formatting = (
        "Generated code must preserve line and blank-line separation; "
        "do not glue statements, comments, and functions together, "
        "compress code into one line, or use clever obfuscation."
    )  # 代码格式治理文案

    # 把前面准备好的默认片段组装成根 AGENTS 与 verifier 共用的完整治理配置。
    return {
        "coding_behavior": {
            "comment_quality": str_comment_quality,
            "formatting": str_formatting,
            "language_skill_routing": {
                "shared": str_default_shared_route,
                "python": str_default_python_route,
                "script": str_default_script_route,
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
        "source_governance": dict_source_governance_defaults,
        "source_file_limits": {
            "max_bytes": dict_constraints["source_file_max_bytes"],
            "included_extensions": list(dict_source_governance_defaults.get("hard_fail_extensions", [])),
            "excluded_roots": list(dict_source_governance_defaults.get("excluded_roots", [])),
            "decomposition_plan_root": (Path("docs") / "development" / "decomposition-plans").as_posix(),
            "required_plan_sections": [
                "Current Size",
                "Split Boundaries",
                "Target Files",
                "Exit Criteria",
            ],
        },
        "tool_script_layout": {
            "required_root": dict_script_layout["required_root"],
            "families": dict(dict_script_layout["families"]),
            "required_pattern": dict_script_layout["required_pattern"],
            "require_full_triad": bool(dict_script_layout["require_full_triad"]),
            "gui_exception_manifest": DEFAULT_GUI_EXCEPTION_MANIFEST,
        },
    }

# 提取本地治理配置路径，兼容新旧 profile 字段。
def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:
    """返回本地治理配置路径文本。

    参数:
        profile: 当前控制档案；可同时兼容新旧字段结构。

    返回:
        本地治理配置文件的路径文本；缺省时回退到 `.agents/global-rule-overrides.json`。
    """

    # 缺少控制档案时直接回退到默认治理配置路径。
    if not isinstance(profile, dict):

        # 返回默认的本地治理配置路径。
        return DEFAULT_GLOBAL_OVERRIDES_PATH

    # 先读取新结构中的路径覆盖值，优先尊重显式配置。
    dict_inline_overrides = profile.get("global_rule_overrides", {})  # 新结构中的治理配置覆盖块

    # 新结构是映射时，再尝试提取其中的路径字段。
    if isinstance(dict_inline_overrides, dict):

        # 记录新结构里的候选路径文本，便于后续判断是否为空。
        str_candidate_path = str(dict_inline_overrides.get("path", "")).strip()  # 新结构候选路径文本

        # 新结构给出了非空路径时，直接把它作为最终答案返回。
        if str_candidate_path:

            # 返回新结构显式指定的治理配置路径。
            return str_candidate_path

    # 新结构没有路径时，继续兼容旧字段中的路径文本。
    str_legacy_path = str(profile.get("global_rule_overrides_config", "")).strip()  # 旧结构里的治理配置路径

    # 返回旧路径或默认路径，保证调用方总能拿到可解析的目标。
    return str_legacy_path or DEFAULT_GLOBAL_OVERRIDES_PATH

# 把治理配置路径文本解析成绝对路径对象。
def global_rule_overrides_path(
    root: Path,
    profile: dict[str, Any] | None = None,
) -> Path:
    """返回本地治理配置文件的绝对路径。

    参数:
        root: 当前项目根目录。
        profile: 可选的控制档案；用于兼容新旧路径字段。

    返回:
        本地治理配置文件的绝对路径对象。
    """

    # 先解析出路径文本，再统一转换成 Path 对象。
    path_reference = Path(global_rule_overrides_reference(profile))  # 治理配置路径文本对应的 Path 对象

    # 返回绝对路径；相对路径会自动挂到项目根目录下。
    return path_reference if path_reference.is_absolute() else (root / path_reference)

# 深度合并两个对象配置，供默认值与用户覆盖值收口。
def merge_object(base: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    """递归合并两个对象配置。

    参数:
        base: 作为基础值的默认配置对象。
        raw: 需要覆盖到基础值上的用户配置对象。

    返回:
        合并后的新配置对象；输入对象本身不会被原地修改。
    """

    # 先复制基础配置，确保递归合并不会改写调用方原对象。
    dict_merged = dict(base)  # 递归合并过程中持续更新的新对象

    # 逐个处理用户覆盖字段，必要时继续向下递归。
    for str_key, obj_raw_value in raw.items():

        # 两侧都是对象时继续递归，保留深层默认值与覆盖值。
        if isinstance(obj_raw_value, dict) and isinstance(dict_merged.get(str_key), dict):

            # 把子对象合并结果写回当前键，继续保持字典层级完整。
            dict_merged[str_key] = merge_object(dict_merged[str_key], obj_raw_value)  # 当前键对应的递归合并结果

        # 其余类型直接覆盖，保持用户显式值优先生效。
        else:

            # 把非对象覆盖值直接写回结果对象。
            dict_merged[str_key] = obj_raw_value  # 当前键的最终覆盖值

    # 返回递归合并完成后的新配置对象。
    return dict_merged

# 把旧版 implementation_constraints 兼容成新的本地治理配置结构。
def legacy_global_rule_overrides(profile: dict[str, Any] | None) -> dict[str, Any]:
    """从旧版 implementation_constraints 推导兼容治理配置。

    参数:
        profile: 当前控制档案；可能仍包含历史字段结构。

    返回:
        与现代本地治理配置结构对齐的兼容对象。
    """

    # 先取一份现代默认治理配置，兼容路径只在此基础上补旧字段。
    dict_defaults = default_global_rule_overrides()  # 现代治理配置默认值

    # 缺少控制档案时无法读取历史字段，直接返回现代默认配置。
    if not isinstance(profile, dict):

        # 返回不带历史覆盖的现代默认治理配置。
        return dict_defaults

    # 读取旧版实现约束块，后续只从这里抽取仍有价值的历史字段。
    dict_constraints = profile.get("implementation_constraints", {})  # 旧版实现约束块

    # 历史字段缺失或不是对象时，不需要再做兼容迁移。
    if not isinstance(dict_constraints, dict) or not dict_constraints:

        # 返回没有历史覆盖的现代默认治理配置。
        return dict_defaults

    # 先取出旧版脚本布局原始值，后续只在对象场景下继续读取子字段。
    obj_script_layout = dict_constraints.get("script_layout", {})  # 旧版脚本布局原始值

    # 只有对象类型才能作为布局映射继续参与兼容迁移。
    dict_script_layout = obj_script_layout if isinstance(obj_script_layout, dict) else {}  # 旧版脚本布局对象

    # 返回把历史实现约束映射到现代治理结构后的兼容配置。
    return merge_object(
        dict_defaults,
        {
            "source_file_limits": {
                "max_bytes": dict_constraints.get(
                    "source_file_max_bytes",
                    dict_defaults["source_file_limits"]["max_bytes"],
                ),
                "included_extensions": dict_constraints.get(
                    "size_limit_extensions",
                    dict_defaults["source_file_limits"]["included_extensions"],
                ),
                "excluded_roots": dict_constraints.get(
                    "size_limit_exclude_roots",
                    dict_defaults["source_file_limits"]["excluded_roots"],
                ),
            },
            "tool_script_layout": {
                "required_root": dict_script_layout.get(
                    "required_root",
                    dict_defaults["tool_script_layout"]["required_root"],
                ),
                "families": dict_script_layout.get(
                    "families",
                    dict_defaults["tool_script_layout"]["families"],
                ),
                "required_pattern": dict_script_layout.get(
                    "required_pattern",
                    dict_defaults["tool_script_layout"]["required_pattern"],
                ),
                "require_full_triad": dict_script_layout.get(
                    "require_full_triad",
                    dict_defaults["tool_script_layout"]["require_full_triad"],
                ),
            },
        },
    )
 
# 旧版注释位置合同单独校验，避免主策略校验器同时承担枚举和正文职责。
def validate_code_comment_positions(
    comment_policy: dict[str, Any],
    *,
    require_explicit: bool = False,
) -> list[str]:
    """校验旧版注释位置映射及 Python 赋值例外。

    参数:
        comment_policy: 旧版注释策略映射。
        require_explicit: 是否要求所有位置键显式存在。

    返回:
        按检查顺序累积的位置合同错误。
    """

    # 读取注释位置映射，并在显式模式下先确认 positions 键没有被删掉。
    dict_positions = comment_policy.get("positions")  # 注释位置映射

    # 本函数独立累积位置诊断，供主策略校验器统一合并。
    list_errors: list[str] = []  # 注释位置合同诊断

    # 显式模式要求保留 positions 主键，避免位置约束悄悄退回默认值。
    if require_explicit and "positions" not in comment_policy:

        # 追加主键缺失错误，提醒调用方不要丢掉整块位置策略。
        list_errors.append("code_comment_policy.positions must be explicitly set")

    # 非对象的 positions 无法继续按键验证，因此这里直接终止并返回。
    if not isinstance(dict_positions, dict):

        # 把类型错误附加到当前诊断列表后整体返回。
        return list_errors + ["code_comment_policy.positions must be an object"]

    # 固化兼容迁移后各语言注释位置的强制映射。
    dict_required_positions = {  # 各语言必须固定下来的注释位置
        "python.public_api": "docstring",  # Python 公共 API 注释位置
        "python.inline": "above",  # Python 行内解释统一放在上方
        "python.trailing": "strict-readable-assignment-purpose",  # Python 赋值用途注释位置
        "c_cpp.function": "above",  # C/C++ 函数说明写在声明上方
        "c_cpp.module": "above",  # C/C++ 模块注释位置
        "c_cpp.variable": "above",  # C/C++ 变量注释位置
        "c_cpp.specific_behavior": "above",  # C/C++ 特定行为注释位置
        "c_cpp.macro_define": "right_side",  # C/C++ 宏定义注释位置
        "verilog_systemverilog.module": "above",  # Verilog 模块总说明写在模块头上方
        "verilog_systemverilog.declaration": "right_side",  # Verilog 声明注释位置
        "verilog_systemverilog.assign": "right_side",  # Verilog assign 注释位置
        "verilog_systemverilog.task_function_generate_always": "above",  # Verilog 行为块注释位置
        "verilog_systemverilog.always_register_assignment": "right_side",  # Verilog 时序赋值注释位置
    }

    # 限定 positions 允许使用的枚举值，防止兼容层把任意字符串吞进来。
    set_allowed_positions = {  # 允许使用的注释位置枚举
        "above",  # 上方注释位置
        "right_side",  # 右侧注释位置
        "docstring",  # docstring 位置只用于公共 API 说明
        "forbidden",  # 禁止注释位置
        "strict-readable-assignment-purpose",  # 严格可读赋值用途注释位置
    }

    # 逐项比对强制位置，并在显式模式下检查原始键是否完整保留。
    for str_position_key, str_expected_value in dict_required_positions.items():

        # 显式模式下缺键本身就是错误，因为这会掩盖真实治理漂移。
        if require_explicit and str_position_key not in dict_positions:

            # 记录缺少的位置键，方便直接回到配置文件补齐。
            list_errors.append(f"code_comment_policy.positions.{str_position_key} must be explicitly set")

        # 兼容迁移后的值必须与仓库约定完全一致，不能只做到“差不多”。
        if dict_positions.get(str_position_key) != str_expected_value:

            # 报告期望值，减少调用方再次查 schema 的往返成本。
            list_errors.append(f"code_comment_policy.positions.{str_position_key} must be {str_expected_value}")

    # 额外扫描用户自带的 positions，拒绝任何未登记的枚举值。
    for str_position_key, str_position_value in dict_positions.items():

        # 只允许仓库认可的位置值，避免未知字符串进入后续渲染链路。
        if str_position_value not in set_allowed_positions:

            # 把非法枚举值原样回显，帮助调用方快速定位拼写或概念错误。
            list_errors.append(
                f"code_comment_policy.positions.{str_position_key} has invalid value {str_position_value}",
            )

    # Python 普通赋值只允许不设置或明确设为 right_side。
    if dict_positions.get("python.assignment") not in (None, "right_side"):

        # 报告赋值位置越界，防止旧配置引入未约定的注释落点。
        list_errors.append("code_comment_policy.positions.python.assignment must be right_side when set")

    # 当 Python 赋值允许右侧注释时，策略正文里也必须写明该例外。
    if dict_positions.get("python.assignment") == "right_side":

        # 提取 Python 注释策略文本，核对是否同步声明右侧用途注释例外。
        str_python_policy = str(comment_policy.get("python", ""))  # Python 注释策略文本

        # 缺少例外说明会让位置规则与正文策略相互矛盾。
        if "右侧中文用途注释" not in str_python_policy:

            # 明确指出缺失的是赋值例外说明，避免用户误补到别的字段。
            list_errors.append("code_comment_policy.python missing required assignment exception `右侧中文用途注释`")

    # 返回位置合同的完整诊断供主校验器合并。
    return list_errors

# 校验旧版 code_comment_policy 兼容配置是否仍满足仓库注释治理要求。
def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    """校验旧版 `code_comment_policy` 兼容配置是否仍满足仓库注释治理要求。

    参数:
        comment_policy: 旧版注释策略映射，通常来自兼容迁移前的治理配置。
        require_explicit: 为 True 时，要求关键字段必须显式出现在配置中。

    返回:
        按检查顺序累积的错误消息列表。
    """

    # 空配置没有兼容意义，先返回统一根因，避免后续字段错误淹没主问题。
    if not comment_policy:

        # 直接指出旧版注释策略对象缺失，供调用方优先修复入口配置。
        return ["code_comment_policy must be a non-empty object"]

    # 创建诊断容器，后续所有错误都按字段出现顺序稳定追加进去。
    list_errors: list[str] = []  # 按检查顺序累积的诊断

    # 列出旧版注释策略中必须保留的核心文本字段。
    tuple_required_text_fields = (  # 旧版注释策略必须保留的文本字段
        "language",  # 语言约束字段
        "default_policy",  # 默认注释策略字段
        "formatting",  # 格式治理字段
        "python",  # Python 段承载双技能门禁文本
        "c_cpp",  # C/C++ 段承载旧注释规则正文
        "verilog_systemverilog",  # 这一段装的是 HDL 注释规则正文，不承担 Python 或脚本路由职责
    )

    # 先做存在性和非空检查，避免后续短语校验建立在空字符串上。
    for str_field_name in tuple_required_text_fields:

        # 显式模式要求原始键继续存在，不能只依赖渲染器默认值兜底。
        if require_explicit and str_field_name not in comment_policy:

            # 记录缺键错误，提醒调用方不要在兼容迁移时静默删掉约束入口。
            list_errors.append(
                f"code_comment_policy.{str_field_name} must be explicitly set",
            )

        # 即使不是显式模式，空白文本也会让兼容策略失去约束力。
        if not str(comment_policy.get(str_field_name, "")).strip():

            # 追加空值错误，阻止弱化后的空文本通过兼容校验。
            list_errors.append(f"code_comment_policy.{str_field_name} must be set")

    # 为不同语言和策略块定义必须保留的治理短语。
    dict_required_snippets = {  # 各字段必须保留的治理短语
        "default_policy": [  # 默认注释策略的必备短语
            "non-obvious intent",  # 注释必须解释非显然意图
            "invariants",  # 注释必须覆盖不变量
            "risk boundaries",  # 注释必须说明风险点
            "generation boundaries",  # 注释必须声明生成边界
            "public API behavior",  # 注释必须说明公共 API 行为
            "do not restate code",  # 禁止注释简单复述代码
            "without explicit request",  # 禁止未请求的批量 AI 注释
            "update stale comments",  # 行为变化时必须同步更新旧注释
        ],
        "formatting": [  # 格式治理必备短语
            "line and blank-line separation",  # 代码需要保留回车和空行
            "do not glue statements",  # 语句和注释之间必须有分隔
            "compress code into one line",  # 禁止输出单行压缩源码
            "clever obfuscation",  # 禁止可读性差的炫技写法
        ],
        "python": [  # Python 注释策略必备短语
            "docstring",  # Python 公共 API 使用 docstring 说明
            "代码上方",  # Python 注释优先写在代码上方
            "strict readable 规则允许右侧中文用途注释",  # Python 允许赋值用途尾注释例外
            "禁止模板化",  # Python 注释禁止模板化生成
        ],
        "c_cpp": [  # C/C++ 规则强调函数职责、宏语义与资源生命周期
            "函数",  # C/C++ 需要说明函数职责
            "模块核心功能",  # C/C++ 需要交代模块职责
            "变量定义",  # C/C++ 变量定义需要目的说明
            "#define",  # C/C++ 宏定义需要解释含义
            "右侧",  # C/C++ 允许右侧注释时必须说明边界
            "所有权/生命周期",  # C/C++ 需要说明资源所有权与生命周期
        ],
        "verilog_systemverilog": [  # Verilog/SystemVerilog 规则强调端口、时序块与注释落点
            "module",  # Verilog 需要说明模块职责
            "input, output, inout, parameter, localparam, integer, logic, wire, reg, real",  # Verilog 需要覆盖端口与声明语义
            "assign",  # Verilog 需要说明连续赋值职责
            "always",  # Verilog 需要说明时序或组合块行为
            "右侧",  # Verilog 允许右侧注释时要说明边界
            "上方",  # Verilog 默认要求把语义注释放在代码上方
        ],
    }

    # 逐段核对策略正文，确认关键治理短语没有在兼容迁移中被弱化。
    for str_field_name, list_required_snippets in dict_required_snippets.items():

        # 统一把字段正文转成字符串，便于逐项比对必备短语。
        str_policy_text = str(comment_policy.get(str_field_name, ""))  # 当前字段的策略文本

        # 任何一个必备短语缺失，都说明对应语言策略已经偏离仓库约束。
        for str_required_snippet in list_required_snippets:

            # 缺失的治理短语需要逐条报告，方便用户直接补回原文。
            if str_required_snippet not in str_policy_text:

                # 记录具体短语缺失位置，减少手工定位和比对成本。
                list_errors.append(
                    f"code_comment_policy.{str_field_name} missing required rule `{str_required_snippet}`",
                )

    # 位置枚举和 Python 赋值例外由独立校验器追加诊断。
    list_errors.extend(validate_code_comment_positions(comment_policy, require_explicit=require_explicit))

    # 返回 coding_behavior 的完整诊断列表，保持治理校验函数的接口契约。
    return list_errors

# 把旧版 code_comment_policy 兼容迁移到新的 coding_behavior 结构。
def migrate_code_comment_policy_to_coding_behavior(raw: dict[str, Any]) -> dict[str, Any]:
    """把旧版 `code_comment_policy` 兼容迁移到新的 `coding_behavior` 结构。

    参数:
        raw: 原始治理配置映射，可能仍包含旧版注释策略字段。

    返回:
        已完成兼容迁移的新治理配置副本。
    """

    # 先复制输入配置，确保兼容迁移不会污染调用方传入的原始对象。
    dict_migrated = dict(raw)  # 迁移后的治理配置

    # 只有新结构缺失且旧结构存在时，才真正消费 code_comment_policy 输入。
    if "coding_behavior" not in dict_migrated and isinstance(dict_migrated.get("code_comment_policy"), dict):

        # 读取旧版注释策略对象，后续从中抽取仍有价值的兼容字段。
        dict_legacy_policy = dict_migrated["code_comment_policy"]  # 旧注释策略兼容输入

        # 读取新编码行为默认值，供缺项和弱化场景统一回退。
        dict_default_coding_behavior = default_global_rule_overrides()["coding_behavior"]  # 新编码行为默认值

        # 读取旧配置中可能携带的 custom structured route，避免迁移时丢失用户字段形状。
        dict_legacy_route_source = dict_legacy_policy.get("language_skill_routing", {})  # 旧语言路由来源

        # 非映射旧值不能作为结构化路由来源继续传播。
        if not isinstance(dict_legacy_route_source, dict):

            # 兼容旧配置直接把 structured 放在 code_comment_policy 下的写法。
            dict_legacy_route_source = dict_legacy_policy  # 旧配置根对象作为兼容来源

        # 读取用户显式的 structured route，迁移时保持其字段形状。
        dict_custom_structured_routes = dict_legacy_route_source.get("structured")  # 用户自定义 structured 路由记录

        # 旧格式规则仍然有效，优先沿用原值并在空白场景回退到新默认。
        str_formatting = str(dict_legacy_policy.get("formatting", dict_default_coding_behavior["formatting"])).strip()  # 兼容后的格式规则文本

        # 先读取旧版 Python 路由文本，再检查它是否仍满足双技能门禁短语。
        str_python_route = str(dict_legacy_policy.get("python", "")).strip()  # 旧版 Python 路由文本

        # 缺少关键路由短语时，直接回退到新默认，避免兼容迁移弱化技能选择。
        if missing_language_skill_route_snippets(str_python_route, PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS):

            # 用新默认 Python 路由覆盖弱化后的旧文本。
            str_python_route = dict_default_coding_behavior["language_skill_routing"]["python"]  # 回退后的 Python 路由文本

        # 先构造现代路由，再根据 custom structured 是否存在决定是否保留默认平面字段。
        dict_migrated_language_routing = {  # 迁移后的默认语言路由映射
            "shared": dict_default_coding_behavior["language_skill_routing"]["shared"],  # 共同门禁派生文本
            "python": str_python_route,  # Python legacy 派生文本
            "script": dict_default_coding_behavior["language_skill_routing"]["script"],  # 脚本 legacy 派生文本
        }

        # 存在 custom structured 时，才切换到用户明确提供的结构化记录。
        if isinstance(dict_custom_structured_routes, dict):

            # custom structured route 只保留显式 legacy 平面字段和自定义结构化记录。
            dict_migrated_language_routing = {  # custom route 的兼容投影
                str_route_name: dict_legacy_route_source[str_route_name]  # 保留用户显式 legacy 文案
                for str_route_name in ("shared", "python", "script")  # 只复制三个兼容键
                if str_route_name in dict_legacy_route_source  # 忽略未显式提供的键
            }

            # 结构化记录仍是 custom route 的唯一事实源。
            dict_migrated_language_routing["structured"] = dict_custom_structured_routes  # 用户自定义结构化记录

        # 写入新的 coding_behavior 结构，并保留 custom route 的原始形状。
        dict_migrated["coding_behavior"] = {
            "comment_quality": str(  # 兼容后的注释质量文本
                dict_legacy_policy.get("default_policy", dict_default_coding_behavior["comment_quality"]),  # 旧版默认注释策略文本
            ).strip(),
            "formatting": str_formatting or dict_default_coding_behavior["formatting"],  # 兼容后的格式治理文本
            "language_skill_routing": dict_migrated_language_routing,  # 兼容后的语言技能路由映射
        }

    # 旧键只作为兼容输入存在，迁移完成后不再保留到新输出结构。
    dict_migrated.pop("code_comment_policy", None)

    # 返回迁移后的配置副本，供后续渲染和校验统一使用。
    return dict_migrated

# 从对象配置里读取某个子键；只接受字典值，其他情况统一回退为空映射。
def mapping_value_or_empty(data: dict[str, Any], str_key: str) -> dict[str, Any]:
    """读取对象子键，并在值不是映射时回退为空映射。

    参数:
        data: 待读取的父级配置映射。
        str_key: 需要提取的子键名称。

    返回:
        当子键值是 dict 时返回原对象；否则返回空映射。
    """

    # 先取出调用方请求的子键值，后续统一判断它能否继续按映射处理。
    obj_value = data.get(str_key)  # 候选子块值

    # 只有真正的字典才能继续作为治理子块向下传递。
    if isinstance(obj_value, dict):

        # 把原始映射交给下游校验器，保留字段级错误定位能力。
        return obj_value

    # 非映射值全部回退为空对象，避免子校验器收到错误类型后级联崩掉。
    return {}

# 把语言技能路由里缺失的强制短语逐项登记到错误列表。
def append_missing_language_route_snippets(
    str_route_text: str,
    tuple_required_snippets: tuple[str, ...],
    str_route_name: str,
    list_errors: list[str],
) -> None:
    """检查语言路由文本，并登记缺失的强制短语。

    参数:
        str_route_text: 当前目标语言的完整路由文本。
        tuple_required_snippets: 该目标语言必须保留的短语清单。
        str_route_name: 错误消息里使用的目标语言键名。
        list_errors: 用于追加缺失短语错误的共享列表。

    返回:
        无业务返回值；缺失项直接追加到传入错误列表。
    """

    # 逐条核对强制短语，保证语言路由不会被弱化成模糊建议。
    for str_required_snippet in tuple_required_snippets:

        # 缺失任一短语都意味着该目标语言的技能边界已经发生漂移。
        if str_required_snippet not in str_route_text:

            # 把缺失短语和目标语言键一并回显，方便直接回到配置文本修正。
            list_errors.append(
                "coding_behavior.language_skill_routing."
                f"{str_route_name} missing required rule `{str_required_snippet}`",
            )

# 语言技能路由验证器检查必需目标、短语和禁用技能名。
def language_skill_routing_errors(
    dict_routing: dict[str, Any],
    *,
    require_explicit: bool,
) -> list[str]:
    """返回 Python 与脚本语言路由的字段和内容错误。

    参数：dict_routing 为路由映射，require_explicit 控制显式字段要求。
    返回：保持目标语言和短语检查顺序的错误列表。
    """

    # 当前 helper 的错误仅覆盖语言技能路由分区。
    list_errors: list[str] = []  # 语言路由诊断列表

    # structured records 是路由唯一事实源，旧字符串字段只作为派生兼容输出。
    dict_structured_routes = dict_routing.get("structured")  # 当前输入中的结构化路由记录

    # 缺少 structured 时回读 packaged defaults，避免验证阶段误用旧平面字段。
    if dict_structured_routes is None:

        # 公共治理 JSON 只保留三字段，结构化校验回读 packaged route source。
        dict_structured_routes = _load_structured_route_defaults().get("routes", {})  # packaged 结构化路由默认值

    # 显式 structured 非映射时必须保留错误并切换为空映射。
    elif not isinstance(dict_structured_routes, dict):

        # 显式提供但类型错误的 structured 字段仍必须报告。
        list_errors.append("coding_behavior.language_skill_routing.structured must be an object")

        # 空映射让后续三类路由检查继续返回完整诊断。
        dict_structured_routes = {}  # 无效 structured 的安全空值

    # 共同门禁和两个语言目标都必须存在 full/compact 两种结构化文案。
    for str_route_key in ("shared", "python", "script"):

        # 显式模式下缺少子键本身就是治理漂移。
        if require_explicit and str_route_key not in dict_routing:

            # 回显缺少的目标语言键。
            list_errors.append(f"coding_behavior.language_skill_routing.{str_route_key} must be explicitly set")

        # 结构化记录的两种文案都必须非空，避免渲染时回退旧字符串。
        dict_route_record = dict_structured_routes.get(str_route_key, {})  # 当前目标语言的 structured record

        # legacy 字段必须与当前 structured.full_text 一致，防止弱化只改平面投影。
        str_expected_route_text = (
            str(dict_route_record.get("full_text", ""))  # structured source 的当前全文
            if isinstance(dict_route_record, dict)  # 合法记录才提供派生全文
            else ""  # 无效记录使用空文本触发后续错误
        )

        # 读取配置中对应的 legacy 字段，供派生关系比较使用。
        str_legacy_route_text = str(dict_routing.get(str_route_key, "")).strip()  # 当前 legacy 投影文本

        # 显式路由的派生关系一旦断裂，验证器必须报告而不是回退默认文案。
        if require_explicit and str_legacy_route_text != str_expected_route_text:

            # 回显目标字段，定位用户配置与 structured source 的漂移。
            list_errors.append(
                f"coding_behavior.language_skill_routing.{str_route_key} must derive from structured.full_text"
            )

        # 非映射记录不能表达完整路由合同，先报告并跳过本目标的后续字段检查。
        if not isinstance(dict_route_record, dict):

            # 记录结构错误后继续检查其他目标语言，集中返回全部缺口。
            list_errors.append(f"coding_behavior.language_skill_routing.structured.{str_route_key} must be an object")

            # 当前目标没有可继续读取的 full/compact 字段。
            continue

        # full_text 和 compact_text 必须同时存在，避免渲染器回退旧字符串。
        list_route_text_values = [  # 当前语言路由的两种文案值
            str(dict_route_record.get(str_text_key, "")).strip()  # 读取当前文案字段
            for str_text_key in ("full_text", "compact_text")  # 依次检查 full_text 与 compact_text
        ]

        # full_text 与 compact_text 均非空才允许该路由进入必需短语校验。
        bool_route_text_complete = all(list_route_text_values)  # 当前路由文案完整性结果

        # 两种文案任一缺失都必须报告结构化路由合同不完整。
        if not bool_route_text_complete:

            # 空字符串不能代替路由合同。
            list_errors.append(
                f"coding_behavior.language_skill_routing.structured.{str_route_key} "
                "full_text and compact_text must be set"
            )

    # 三类路由分别绑定必需短语与禁用技能名。
    list_route_contracts = [  # 语言目标合同表
        ("shared", SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS, ()),  # 共同门禁合同
        ("python", PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS, PYTHON_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS),  # Python 路由合同
        ("script", SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS, SCRIPT_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS),  # 脚本路由合同
    ]

    # 合同顺序保持共同门禁先于 Python 和脚本。
    for str_route_name, tuple_required, tuple_forbidden in list_route_contracts:

        # full/compact 文案共同接受必需短语与禁用技能名检查。
        dict_route_record = dict_structured_routes.get(str_route_name, {})  # 当前目标的 structured record

        # 仅从合法 structured record 提取 full_text，避免把任意对象转成路由正文。
        str_route_text = str(dict_route_record.get("full_text", "")) if isinstance(dict_route_record, dict) else ""  # 当前目标路由全文

        # 公共 helper 逐项追加必需短语缺口。
        append_missing_language_route_snippets(
            str_route_text, tuple_required, str_route_name, list_errors,
        )

        # 禁用技能名不能残留在安装态路由中。
        for str_forbidden_snippet in tuple_forbidden:

            # 精确诊断回显不可用技能名。
            if str_forbidden_snippet in str_route_text:

                # 当前错误绑定目标路由和具体技能名。
                list_errors.append(
                    f"coding_behavior.language_skill_routing.{str_route_name} mentions unavailable skill "
                    f"`{str_forbidden_snippet}`",
                )

    # 返回完整语言路由诊断。
    return list_errors

# 格式规则验证器检查多行排版和可读性下限。
def formatting_rule_errors(str_formatting: str) -> list[str]:
    """返回编码格式治理文本缺少的强制规则。

    参数：str_formatting 为编码格式约束文本。
    返回：按固定短语顺序排列的格式错误。
    """

    # 必需短语覆盖分隔、粘连、一行压缩和炫技写法。
    tuple_required_snippets = (  # 格式规则必备短语
        "line and blank-line separation",  # 多行分隔要求
        "do not glue statements",  # 结构分隔要求
        "compress code into one line",  # 禁止一行压缩
        "clever obfuscation",  # 禁止晦涩写法
    )

    # 列表推导保持错误顺序与既有循环一致。
    return [
        f"coding_behavior.formatting missing required rule `{str_snippet}`"
        for str_snippet in tuple_required_snippets
        if str_snippet not in str_formatting
    ]

# 校验新的 coding_behavior 结构是否完整保留语言路由和格式治理约束。
def validate_coding_behavior_data(coding_behavior: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    """校验新式 `coding_behavior` 结构是否满足语言技能路由与格式治理要求。

    参数:
        coding_behavior: 新版编码行为配置映射。
        require_explicit: 为 True 时，要求关键字段必须显式保留在输入配置中。

    返回:
        按检查顺序累积的错误消息列表。
    """

    # 空配置说明新版编码行为块整体缺失，先返回统一根因。
    if not coding_behavior:

        # 直接指出编码行为对象为空，避免后续路由错误掩盖入口问题。
        return ["coding_behavior must be a non-empty object"]

    # 创建 coding_behavior 的诊断容器，后续错误按字段检查顺序稳定追加。
    list_errors: list[str] = []  # coding_behavior 诊断列表

    # 显式模式要求 language_skill_routing 主键继续存在，不能只靠默认值兜底。
    if require_explicit and "language_skill_routing" not in coding_behavior:

        # 记录路由主键缺失，提醒调用方不要丢掉整块技能路由约束。
        list_errors.append("coding_behavior.language_skill_routing must be explicitly set")

    # 读取语言技能路由结构，后续所有 Python/脚本检查都依赖这一映射。
    dict_routing = coding_behavior.get("language_skill_routing", {})  # 语言技能路由配置

    # 非对象或空对象都无法继续按目标语言逐项校验。
    if not isinstance(dict_routing, dict) or not dict_routing:

        # 把类型/空值问题作为根因返回，避免继续产生级联噪声。
        return list_errors + ["coding_behavior.language_skill_routing must be a non-empty object"]

    # 语言路由 helper 保持 Python 与脚本诊断顺序。
    list_errors.extend(language_skill_routing_errors(dict_routing, require_explicit=require_explicit))

    # 格式 helper 追加多行排版和可读性规则缺口。
    list_errors.extend(formatting_rule_errors(str(coding_behavior.get("formatting", ""))))

    # 这里直接返回 coding_behavior 错误列表，供上层决定是否阻断渲染。
    return list_errors

# 分段校验 script_output_policy.enabled 的脚本治理处理入口。
def append_script_output_policy_enabled_errors(
    policy: dict[str, Any],
    list_errors: list[str],
    *,
    require_explicit: bool,
) -> None:
    """补充 `script_output_policy.enabled` 的结构化错误。

    参数:
        policy: 脚本输出策略配置映射。
        list_errors: 供当前函数追加错误的列表。
        require_explicit: 为 True 时，要求 enabled 字段显式存在。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 显式模式要求 enabled 主键继续存在，避免默认值掩盖缺字段问题。
    if require_explicit and "enabled" not in policy:

        # 回显 enabled 主键缺失，提醒调用方恢复总开关字段。
        list_errors.append("script_output_policy.enabled must be explicitly set")

    # enabled 必须继续保持布尔值，输出策略不能依赖字符串真假。
    if not isinstance(policy.get("enabled"), bool):

        # 报出 enabled 的布尔契约错误，保持总开关语义稳定。
        list_errors.append("script_output_policy.enabled must be boolean")

# 细化核对 script_output_policy.format 中的固定前缀契约。
def append_script_output_policy_format_errors(
    policy: dict[str, Any],
    list_errors: list[str],
    *,
    require_explicit: bool,
) -> None:
    """补充 `script_output_policy.format` 的结构化错误。

    参数:
        policy: 脚本输出策略配置映射。
        list_errors: 供当前函数追加错误的列表。
        require_explicit: 为 True 时，要求 format 主键与等级键显式存在。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取 format 配置块，后续继续核对三个固定前缀。
    dict_format_policy = policy.get("format")  # 脚本输出前缀映射

    # 显式模式要求 format 主键继续存在，避免前缀治理被整块删掉。
    if require_explicit and "format" not in policy:

        # 回显 format 主键缺失，方便调用方直接补齐配置。
        list_errors.append("script_output_policy.format must be explicitly set")

    # format 必须是对象，否则无法逐级表达 info/warning/error 前缀。
    if not isinstance(dict_format_policy, dict):

        # 把 format 结构错误直接回显给调用方。
        list_errors.append("script_output_policy.format must be an object")

        # 返回 append_script_output_policy_format_errors 调用载荷。
        return

    # 汇总固定等级前缀，保持日志协议和文档口径一致。
    dict_required_format_map = {  # 固定日志等级前缀映射
        "info": "> INFO: [{kind}]",  # 普通过程信息前缀
        "warning": "> WARNING: [{kind}]",  # 警告级前缀
        "error": "> ERR: [{kind}]",  # 错误级前缀
    }

    # 逐级核对固定前缀，防止输出协议被随手改写。
    for str_level, str_expected_prefix in dict_required_format_map.items():

        # 显式模式要求每个等级键继续保留在 format 配置中。
        if require_explicit and str_level not in dict_format_policy:

            # 回显缺失的等级键，便于调用方一次补齐。
            list_errors.append(f"script_output_policy.format.{str_level} must be explicitly set")

        # 即使等级键存在，也必须与仓库约定前缀完全一致。
        if dict_format_policy.get(str_level) != str_expected_prefix:

            # 报出期望前缀文本，减少调用方对照文档的往返。
            list_errors.append(f"script_output_policy.format.{str_level} must be `{str_expected_prefix}`")

# 细化核对 script_output_policy.kinds 中的分类来源约束。
def append_script_output_policy_kind_errors(
    policy: dict[str, Any],
    list_errors: list[str],
    *,
    require_explicit: bool,
) -> None:
    """补充 `script_output_policy.kinds` 的结构化错误。

    参数:
        policy: 脚本输出策略配置映射。
        list_errors: 供当前函数追加错误的列表。
        require_explicit: 为 True 时，要求 kinds 主键显式存在。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取 kinds 列表，后续继续核对非空、空白和去空白后的重复项。
    list_kind_values = policy.get("kinds")  # kind 标记列表

    # 显式模式要求 kinds 主键继续存在，避免输出种类契约失去来源。
    if require_explicit and "kinds" not in policy:

        # 回显 kinds 主键缺失，提醒调用方恢复种类治理。
        list_errors.append("script_output_policy.kinds must be explicitly set")

    # kinds 至少要有一个元素，空列表无法表达任何允许的输出类别。
    if not isinstance(list_kind_values, list) or not list_kind_values:

        # 统一把空列表和错误类型收敛为列表契约错误。
        list_errors.append("script_output_policy.kinds must be a non-empty list")

        # 缺少非空 kinds 列表时，后续空白与重复检查已经失去输入前提。
        return

    # 规范化每个 kind 的前后空白，避免空格差异绕过重复检测。
    list_normalized_kinds = [str(item).strip() for item in list_kind_values]  # 规范化后的 kind 列表

    # 空白元素会让日志类别不可判定，因此需要单独拦截。
    if any(not str_kind for str_kind in list_normalized_kinds):

        # 直接指出存在空值，方便调用方回看原始列表。
        list_errors.append("script_output_policy.kinds must not contain empty values")

    # 去空白后仍然重复说明种类定义存在语义碰撞。
    if len(set(list_normalized_kinds)) != len(list_normalized_kinds):

        # 保持原有错误文案，避免破坏既有调用方与测试预期。
        list_errors.append("script_output_policy.kinds must not contain duplicates after trimming")

# 分段校验 script_output_policy 的 Python quiet 与机器可读豁免治理入口。
def append_script_output_policy_runtime_errors(
    policy: dict[str, Any],
    list_errors: list[str],
    *,
    require_explicit: bool,
) -> None:
    """补充 Python quiet 与机器可读豁免的结构化错误。

    参数:
        policy: 脚本输出策略配置映射。
        list_errors: 供当前函数追加错误的列表。
        require_explicit: 为 True 时，要求 Python 子块和豁免字段显式存在。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取 Python 输出子策略，继续核对默认 INFO 与 quiet 标志契约。
    dict_python_policy = policy.get("python")  # Python 输出子策略

    # 显式模式要求 Python 子块继续存在，不能只保留脚本通用层。
    if require_explicit and "python" not in policy:

        # 回显 Python 子块缺失，提醒调用方恢复 Python 输出规则。
        list_errors.append("script_output_policy.python must be explicitly set")

    # 只有对象子块才能继续读取 info_default 与 quiet_flag。
    if not isinstance(dict_python_policy, dict):

        # 把 Python 子块类型错误直接回显给调用方。
        list_errors.append("script_output_policy.python must be an object")

    # Python 子块结构有效后，再继续核对默认 INFO 与 quiet_flag 契约。
    else:

        # 显式模式要求 info_default 字段继续保留，避免悄悄回退成静默模式。
        if require_explicit and "info_default" not in dict_python_policy:

            # 回显 info_default 缺失，便于调用方直接补字段。
            list_errors.append("script_output_policy.python.info_default must be explicitly set")

        # Python 过程性 INFO 约定默认开启，这是当前仓库的既定契约。
        if dict_python_policy.get("info_default") != "on":

            # 拒绝 off 或布尔替代表达，保持用户可见输出一致性。
            list_errors.append("script_output_policy.python.info_default must be on")

        # 显式模式要求 quiet_flag 继续存在，避免 CLI 静默控制开关被删掉。
        if require_explicit and "quiet_flag" not in dict_python_policy:

            # 回显 quiet_flag 缺失，方便调用方补齐 CLI 约束。
            list_errors.append("script_output_policy.python.quiet_flag must be explicitly set")

        # 当前仓库统一使用 --quiet 关闭 INFO；其他拼写都视为协议漂移。
        if dict_python_policy.get("quiet_flag") != "--quiet":

            # 报出固定 quiet 标志，减少调用方查阅脚本规范的往返。
            list_errors.append("script_output_policy.python.quiet_flag must be --quiet")

    # 显式模式要求机器可读输出豁免继续存在，避免结构化输出被人类前缀污染。
    if require_explicit and "machine_readable_exemption" not in policy:

        # 回显例外开关缺失，提醒调用方恢复机器输出保护。
        list_errors.append("script_output_policy.machine_readable_exemption must be explicitly set")

    # 读取机器可读输出例外值，后续确认它仍然保持布尔真值。
    bool_machine_readable_exemption = policy.get("machine_readable_exemption")  # 机器可读输出例外值

    # 该例外必须显式为布尔真值，否则 JSON 等机器输出仍可能被前缀污染。
    if not isinstance(bool_machine_readable_exemption, bool) or not bool_machine_readable_exemption:

        # 用布尔真值要求锁住机器可读输出的安全边界。
        list_errors.append("script_output_policy.machine_readable_exemption must be true")

# 统一校验 script_output_policy，锁住日志前缀、kind 列表和 Python quiet 契约。
def validate_script_output_policy_data(policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    """校验 `script_output_policy` 是否继续约束脚本前缀与 Python 安静模式。

    参数:
        policy: 脚本输出策略配置映射。
        require_explicit: 为 True 时，要求关键字段必须显式存在于输入配置中。

    返回:
        按检查顺序累积的错误消息列表。
    """

    # 空对象说明整块策略缺失，先返回统一根因，避免后续级联噪声。
    if not policy:

        # 直接指出 script_output_policy 缺失，方便调用方先补入口配置。
        return ["script_output_policy must be a non-empty object"]

    # 这里专门累积等级前缀、Kind 注册表和 quiet 例外三类输出协议故障。
    list_errors: list[str] = []  # 输出协议违规总账

    # 先校验 enabled 主键，避免后续把无效策略继续当成开启状态解释。
    append_script_output_policy_enabled_errors(policy, list_errors, require_explicit=require_explicit)

    # 再校验 format 主键和固定前缀，确保日志协议仍然锁定。
    append_script_output_policy_format_errors(policy, list_errors, require_explicit=require_explicit)

    # 继续校验 kinds 列表，守住输出种类的配置来源边界。
    append_script_output_policy_kind_errors(policy, list_errors, require_explicit=require_explicit)

    # 最后校验 Python quiet 与机器可读输出豁免边界。
    append_script_output_policy_runtime_errors(policy, list_errors, require_explicit=require_explicit)

    # 把累计的 script_output_policy 诊断返回给调用方。
    return list_errors

# 分段校验 source_governance 根级字段的脚本治理处理入口。
def append_source_governance_root_errors(data: dict[str, Any], list_errors: list[str]) -> None:
    """补充 `source_governance` 根级字段的结构化错误。

    参数:
        data: 源码治理配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # max_lines 已退役；仍然出现时要引导调用方迁移到按字节计量的上限。
    if "max_lines" in data:

        # 明确提示这是退役字段，避免调用方把 max_lines 误当成仍然生效的上限。
        list_errors.append("source_governance.max_lines is retired; use source_governance.max_bytes")

    # 读取源码体积上限，当前仓库统一按字节做硬限制。
    int_max_bytes = data.get("max_bytes")  # 源码最大字节数

    # 非正整数无法表达稳定的源码体积边界。
    if not isinstance(int_max_bytes, int) or int_max_bytes <= 0:

        # 阻止字符串和零值混入，保持体积门禁的数值契约明确。
        list_errors.append("source_governance.max_bytes must be a positive integer")

    # 读取需要硬失败检查的扩展名列表，决定哪些源码文件进入治理范围。
    list_hard_fail_extensions = data.get("hard_fail_extensions")  # 受治理的扩展名列表

    # 扩展名列表必须非空且每项都以点开头，否则文件发现边界会失真。
    if (
        not isinstance(list_hard_fail_extensions, list)
        or not list_hard_fail_extensions
        or not all(str(item).startswith(".") for item in list_hard_fail_extensions)
    ):

        # 保持错误消息聚焦在扩展名契约本身，方便直接修正列表。
        list_errors.append("source_governance.hard_fail_extensions must be a non-empty extension list")

    # 读取排除根目录列表，允许调用方明确声明不受治理的子树。
    list_excluded_roots = data.get("excluded_roots")  # 排除目录前缀列表

    # 排除列表必须保持列表结构，避免路径过滤逻辑收到不可迭代值。
    if not isinstance(list_excluded_roots, list):

        # 把 excluded_roots 的类型问题直接回显，减少运行时路径判断歧义。
        list_errors.append("source_governance.excluded_roots must be a list")

    # 读取仅限测试目录的模式，保护设计代码不要误落在生产源码路径。
    dict_test_only_patterns = data.get("test_only_patterns")  # 测试专属路径模式

    # path_globs 至少要有一个 glob，才能表达测试代码的白名单边界。
    if (
        not isinstance(dict_test_only_patterns, dict)
        or not isinstance(dict_test_only_patterns.get("path_globs"), list)
        or not dict_test_only_patterns.get("path_globs")
    ):

        # 统一把 test_only_patterns 的缺陷收敛到 path_globs 主契约上。
        list_errors.append("source_governance.test_only_patterns.path_globs must be a non-empty list")

# 细化核对 source_governance.comment_policy_gate 中的语言级注释规则。
def append_source_governance_comment_policy_errors(data: dict[str, Any], list_errors: list[str]) -> None:
    """补充 `source_governance.comment_policy_gate` 的结构化错误。

    参数:
        data: 源码治理配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取注释治理块，继续约束 AI 注释标记与语言特定例外。
    dict_comment_policy_gate = data.get("comment_policy_gate")  # 注释治理配置

    # 注释治理必须是对象，否则无法表达启用开关和语言子块。
    if not isinstance(dict_comment_policy_gate, dict):

        # 根因直接落在 comment_policy_gate，避免继续产生级联错误。
        list_errors.append("source_governance.comment_policy_gate must be an object")

        # comment_policy_gate 不是对象时，继续读取语言子块只会制造级联噪声。
        return

    # enabled 必须明确为布尔值，才能判断注释治理是否启用。
    if not isinstance(dict_comment_policy_gate.get("enabled"), bool):

        # 阻止字符串型 true/false 伪装成治理开关。
        list_errors.append("source_governance.comment_policy_gate.enabled must be boolean")

    # AI 注释标记必须用列表声明，后续扫描器才有稳定输入。
    if not isinstance(dict_comment_policy_gate.get("forbid_ai_comment_markers"), list):

        # 指出标记列表类型错误，方便直接修正扫描输入。
        list_errors.append("source_governance.comment_policy_gate.forbid_ai_comment_markers must be a list")

    # 读取 Python 注释治理子块，检查赋值尾随注释例外的对象契约。
    dict_python_comment_gate = dict_comment_policy_gate.get("python")  # Python 注释治理子块

    # Python 子块承载 trailing comment 例外，必须保持对象结构。
    if not isinstance(dict_python_comment_gate, dict):

        # 缺少 Python 子块时直接报对象契约错误。
        list_errors.append("source_governance.comment_policy_gate.python must be an object")

    # Python 子块结构有效后，再继续核对赋值尾注释例外的布尔契约。
    elif (
        "allow_assignment_trailing_comment" in dict_python_comment_gate
        and not isinstance(dict_python_comment_gate.get("allow_assignment_trailing_comment"), bool)
    ):

        # 该例外一旦存在就必须是布尔值，避免配置语义漂移。
        list_errors.append(
            "source_governance.comment_policy_gate.python.allow_assignment_trailing_comment must be boolean",
        )

    # C/C++ 子块同样必须存在为对象，避免跨语言注释规则失去宿主。
    if not isinstance(dict_comment_policy_gate.get("c_cpp"), dict):

        # 把 c_cpp 子块缺失或类型错误直接回显，保持语言配置对称。
        list_errors.append("source_governance.comment_policy_gate.c_cpp must be an object")

# 细化核对 source_governance.readability_gate 中的可读性阈值门禁。
def append_source_governance_readability_errors(data: dict[str, Any], list_errors: list[str]) -> None:
    """补充 `source_governance.readability_gate` 的结构化错误。

    参数:
        data: 源码治理配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取可读性门禁，继续约束物理行、单行压缩和 minified 密度阈值。
    dict_readability_gate = data.get("readability_gate")  # 可读性门禁配置

    # 可读性门禁必须是对象，否则无法表达启用开关和各类阈值。
    if not isinstance(dict_readability_gate, dict):

        # 根因直接落在 readability_gate 主键上，避免子字段噪声。
        list_errors.append("source_governance.readability_gate must be an object")

        # readability_gate 不是对象时，后续阈值检查已经没有可靠宿主。
        return

    # enabled 必须明确为布尔值，后续扫描器才知道是否执行阈值检查。
    if not isinstance(dict_readability_gate.get("enabled"), bool):

        # 保持开关为布尔契约，避免字符串值混入。
        list_errors.append("source_governance.readability_gate.enabled must be boolean")

    # 这三个阈值共同定义长行、单行压缩和 minified 代码的判定边界。
    for str_threshold_key in ("max_physical_line_bytes", "single_line_min_bytes", "minified_line_min_bytes"):

        # 逐项读取阈值，保持错误顺序与配置顺序一致。
        int_threshold_value = dict_readability_gate.get(str_threshold_key)  # 当前可读性阈值

        # 每个阈值都必须是正整数，否则扫描器无法做稳定比较。
        if not isinstance(int_threshold_value, int) or int_threshold_value <= 0:

            # 逐项指出哪个可读性阈值失效，方便调用方一次补齐对应数值。
            list_errors.append(f"source_governance.readability_gate.{str_threshold_key} must be a positive integer")

# 文件命名配置只能保持或收紧技能默认硬边界。
def append_file_naming_errors(data: dict[str, Any], list_errors: list[str]) -> None:
    """补充文件命名开关、长度、例外和字符模式错误。

    参数：
        data: 待验证的源码治理配置映射。
        list_errors: 由调用方维护的配置错误列表。
    返回：本函数只向错误列表追加诊断，不返回业务值。
    """

    # 文件命名门禁对象集中承载全部不可弱化字段。
    dict_gate = data.get("file_naming_gate")  # 待验证的文件命名配置

    # 非对象配置无法提供稳定字段合同，先报告并停止本组检查。
    if not isinstance(dict_gate, dict):

        # 类型诊断明确定位到文件命名配置根。
        list_errors.append("source_governance.file_naming_gate must be an object")

        # 缺少映射时不能继续安全读取下级字段。
        return

    # 只有布尔真值才能启用不可绕过的命名门禁。
    if not dict_gate.get("enabled"):

        # 禁止项目通过关闭开关弱化技能默认规则。
        list_errors.append("source_governance.file_naming_gate.enabled must be true")

    # 词干上限必须保持在用户指定的三十字符边界内。
    int_max_stem_chars = dict_gate.get("max_stem_chars")  # 当前配置的文件词干字符上限

    # 排除布尔值并拒绝非正数或超过三十的整数。
    if (
        not isinstance(int_max_stem_chars, int)  # 上限必须是整数
        or isinstance(int_max_stem_chars, bool)  # Python 布尔值不能冒充整数
        or not 1 <= int_max_stem_chars <= 30  # 数值必须落在不可弱化范围
    ):

        # 一次说明完整合法区间，避免调用方逐次试错。
        list_errors.append(
            "source_governance.file_naming_gate.max_stem_chars must be an integer from 1 to 30"
        )

    # 例外只覆盖 Python 固定入口文件，不能扩展到任意双下划线名称。
    list_exemptions = dict_gate.get("exemptions")  # 当前配置声明的文件名豁免项

    # 初始化入口与模块执行入口是唯一受管例外。
    set_allowed_exemptions = {"__init__.py", "__main__.py"}  # 不参与功能词干检查的固定文件名

    # 非数组或包含其他文件名都会扩大规则绕过面。
    if (
        not isinstance(list_exemptions, list)  # 豁免项必须使用数组表达
        or not set(str(item) for item in list_exemptions).issubset(set_allowed_exemptions)
    ):

        # 诊断固定列出完整允许集合，便于直接修复配置。
        list_errors.append(
            "source_governance.file_naming_gate.exemptions may contain only __init__.py and __main__.py"
        )

    # 受管正则锁住 Python 与其他源码的功能单词结构。
    dict_expected_patterns = {
        "python_pattern": r"^[a-z]+(?:_[a-z]+)*$",  # Python 小写下划线功能名
        "source_pattern": r"^[a-z]+(?:[_-][a-z]+)*$",  # 其他源码允许下划线或连字符
    }  # 不可由项目放宽的命名模式

    # 分别验证两类源码模式，保留精确字段诊断。
    for str_key, str_expected in dict_expected_patterns.items():

        # 任意正则漂移都可能重新允许数字或无语义字符。
        if dict_gate.get(str_key) != str_expected:

            # 指出发生漂移的模式字段，要求恢复受管值。
            list_errors.append(
                f"source_governance.file_naming_gate.{str_key} must preserve the managed pattern"
            )

    # 功能摘要属于 Agent 判断，不能被确定性正则替代或关闭。
    if not dict_gate.get("semantic_review_required"):

        # 强制 revision-bound 语义证据进入发布审查链。
        list_errors.append(
            "source_governance.file_naming_gate.semantic_review_required must be true"
        )

# 统一校验 source_governance，锁住源码体积、注释治理和可读性门禁的基础契约。
def validate_source_governance_data(data: dict[str, Any]) -> list[str]:
    """校验 `source_governance` 是否保留源码体积与注释治理契约。

    参数:
        data: 源码治理配置映射。

    返回:
        按检查顺序累积的错误消息列表。
    """

    # 空对象说明整块源码治理缺失，先返回统一根因。
    if not isinstance(data, dict) or not data:

        # 直接指出 source_governance 缺失，避免后续子字段错误淹没入口问题。
        return ["source_governance must be a non-empty object"]

    # 这里按源码体积、测试白名单、注释、可读性和命名边界持续累积失败项。
    list_errors: list[str] = []  # 源治理缺口总账

    # 先校验根级体积与测试路径边界。
    append_source_governance_root_errors(data, list_errors)

    # 再校验 comment_policy_gate，守住 AI 注释与语言例外契约。
    append_source_governance_comment_policy_errors(data, list_errors)

    # 最后校验 readability_gate，继续锁住长行与压缩源码阈值。
    append_source_governance_readability_errors(data, list_errors)

    # 文件命名门禁必须保持强制启用且不能放宽三十字符边界。
    append_file_naming_errors(data, list_errors)

    # 这里返回的是 source_governance 全量诊断，供上层决定是否阻断生成与校验。
    return list_errors

# 细化核对 long_python_tasks 中的心跳节奏与收尾策略契约。
def append_long_python_task_errors(dict_long_task_policy: dict[str, Any], list_errors: list[str]) -> None:
    """补充 `long_python_tasks` 的结构化错误。

    参数:
        dict_long_task_policy: 长任务治理配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 长任务自动跟进当前只允许 heartbeat，其他类型会破坏仓库既有约定。
    if dict_long_task_policy.get("automation_kind") != "heartbeat":

        # 把 automation_kind 错误直接指向 long_python_tasks，方便一次修正到位。
        list_errors.append("long_python_tasks.automation_kind must be heartbeat")

    # 这两个分钟阈值决定何时触发心跳与何时视为长任务。
    for str_interval_key in ("default_interval_minutes", "long_running_threshold_minutes"):

        # 逐项读取分钟阈值，保持错误顺序与字段顺序一致。
        int_interval_value = dict_long_task_policy.get(str_interval_key)  # 长任务分钟阈值

        # 非正整数无法表达稳定的时间阈值。
        if not isinstance(int_interval_value, int) or int_interval_value <= 0:

            # 精确回显阈值字段名，减少调用方逐项排查成本。
            list_errors.append(f"long_python_tasks.{str_interval_key} must be a positive integer")

    # 完成检查策略必须是非空对象，否则自动跟进没有可执行的终止判定。
    if (
        not isinstance(dict_long_task_policy.get("completion_check_strategy"), dict)
        or not dict_long_task_policy.get("completion_check_strategy")
    ):

        # 直接指出 completion_check_strategy 为空，避免 heartbeat 配置看似完整却无法收尾。
        list_errors.append("long_python_tasks.completion_check_strategy must be a non-empty object")

# 分段校验旧版 source_file_limits 兼容块的脚本治理处理入口。
def append_source_file_limit_errors(dict_source_limits: dict[str, Any], list_errors: list[str]) -> None:
    """补充旧版 `source_file_limits` 兼容块的结构化错误。

    参数:
        dict_source_limits: 旧版源码体积兼容配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 历史 max_lines 仍出现时，提醒调用方迁移到按字节计量的旧兼容字段。
    if "max_lines" in dict_source_limits:

        # 保留明确迁移提示，避免历史配置继续误导调用方。
        list_errors.append("source_file_limits.max_lines is retired; use source_file_limits.max_bytes")

    # 旧版 source_file_limits 仍然要求正整数 max_bytes，避免兼容层完全失效。
    if not isinstance(dict_source_limits.get("max_bytes"), int) or dict_source_limits.get("max_bytes", 0) <= 0:

        # 把 max_bytes 问题收敛为旧兼容块的数字契约错误。
        list_errors.append("source_file_limits.max_bytes must be a positive integer")

    # included_extensions 必须保持列表结构，旧版发现逻辑才能继续工作。
    if not isinstance(dict_source_limits.get("included_extensions"), list):

        # 明确指出兼容扩展名列表结构错误。
        list_errors.append("source_file_limits.included_extensions must be a list of extensions")

    # excluded_roots 也必须保持列表结构，避免兼容层路径过滤崩掉。
    if not isinstance(dict_source_limits.get("excluded_roots"), list):

        # 用精确字段路径提示旧兼容排除目录配置出错。
        list_errors.append("source_file_limits.excluded_roots must be a list")

    # decomposition_plan_root 是历史超限拆分计划入口，兼容块中仍然必须可解析。
    if not str(dict_source_limits.get("decomposition_plan_root", "")).strip():

        # 缺少拆分计划根目录会让旧版 source limit 兜底失去落点。
        list_errors.append("source_file_limits.decomposition_plan_root must be set")

    # 历史 required_plan_sections 不能为空，否则旧版拆分计划检查无法判定完整性。
    if (
        not isinstance(dict_source_limits.get("required_plan_sections"), list)
        or not dict_source_limits.get("required_plan_sections")
    ):

        # 把 required_plan_sections 收敛为列表契约错误，便于恢复旧计划模板。
        list_errors.append("source_file_limits.required_plan_sections must be a non-empty list")

# 细化核对 tool_script_layout 中的脚本目录与扩展名边界。
def append_tool_script_layout_errors(dict_script_layout: dict[str, Any], list_errors: list[str]) -> None:
    """补充 `tool_script_layout` 的结构化错误。

    参数:
        dict_script_layout: 脚本布局治理配置映射。
        list_errors: 供当前函数追加错误的列表。

    返回:
        无业务返回值；错误会直接追加到 `list_errors`。
    """

    # 读取脚本家族映射，核对各脚本语言都映射到扩展名而不是任意文本。
    dict_script_families = dict_script_layout.get("families")  # 脚本家族到扩展名的映射

    # required_root 决定脚本必须落在哪个目录根下，不能为空白。
    if not str(dict_script_layout.get("required_root", "")).strip():

        # 目录根缺失会让脚本布局治理完全失去锚点。
        list_errors.append("tool_script_layout.required_root must be set")

    # families 必须是非空对象，脚本语言到扩展名的责任边界才是确定的。
    if not isinstance(dict_script_families, dict) or not dict_script_families:

        # 把 families 缺失问题直接回显给脚本布局配置作者。
        list_errors.append("tool_script_layout.families must be a non-empty object")

    # families 结构有效后，再继续核对每个家族值是否仍然保持扩展名写法。
    elif not all(str(obj_extension).startswith(".") for obj_extension in dict_script_families.values()):

        # 禁止把脚本家族值写成目录名或描述文案，保持扩展名契约。
        list_errors.append("tool_script_layout.families values must be extensions")

    # required_pattern 描述 scripts/<family>/ 的文件命名模式，不能为空白。
    if not str(dict_script_layout.get("required_pattern", "")).strip():

        # 缺少 required_pattern 会让脚本布局校验失去匹配模板。
        list_errors.append("tool_script_layout.required_pattern must be set")

    # require_full_triad 控制 triad 完整性检查，必须明确为布尔值。
    if not isinstance(dict_script_layout.get("require_full_triad"), bool):

        # 拒绝字符串型布尔替代，保持 triad 门禁语义稳定。
        list_errors.append("tool_script_layout.require_full_triad must be boolean")

    # gui_exception_manifest 记录 GUI 例外白名单，必须给出可解析路径。
    if not str(dict_script_layout.get("gui_exception_manifest", "")).strip():

        # 缺少 manifest 路径会让 GUI 例外落点消失。
        list_errors.append("tool_script_layout.gui_exception_manifest must be set")

# 汇总校验 global rule overrides，确保各治理子块与兼容字段同时满足仓库契约。
def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:
    """校验全局治理覆盖配置，避免子块契约或兼容字段发生漂移。

    参数:
        data: 全局治理覆盖配置映射。

    返回:
        按检查顺序累积的错误消息列表。
    """

    # 这一份总账会把编码行为、输出协议、长任务与源码治理的跨块缺口合并起来。
    list_errors: list[str] = []  # 跨块失败项总账

    # 读取新版编码行为块，缺失时交给子校验器给出精确根因。
    dict_coding_behavior = mapping_value_or_empty(data, "coding_behavior")  # 编码行为配置

    # 读取脚本输出策略块，后续复用单独的 script_output_policy 校验器。
    dict_script_output_policy = mapping_value_or_empty(data, "script_output_policy")  # 脚本输出策略

    # 读取长任务治理块，继续核对 heartbeat 和完成检查策略。
    dict_long_task_policy = mapping_value_or_empty(data, "long_python_tasks")  # 长任务治理配置

    # 读取源码治理块，复用 source_governance 校验器处理体积和注释门禁。
    dict_source_governance = mapping_value_or_empty(data, "source_governance")  # 源码治理配置

    # 读取旧版 source_file_limits 兼容块，继续约束历史字段的最低契约。
    dict_source_limits = mapping_value_or_empty(data, "source_file_limits")  # 旧版源码体积兼容配置

    # 读取脚本布局块，继续核对 scripts/<family>/ 的目录规则。
    dict_script_layout = mapping_value_or_empty(data, "tool_script_layout")  # 脚本布局治理配置

    # 先复用三个子校验器，保持新版主块的错误消息与其他入口一致。
    list_errors.extend(validate_coding_behavior_data(dict_coding_behavior))

    # 再合并 script_output_policy 的校验结果，继续锁住日志协议。
    list_errors.extend(validate_script_output_policy_data(dict_script_output_policy))

    # 最后合并 source_governance 的校验结果，继续锁住源码治理契约。
    list_errors.extend(validate_source_governance_data(dict_source_governance))

    # 继续校验长任务治理块的 heartbeat 和完成检查契约。
    append_long_python_task_errors(dict_long_task_policy, list_errors)

    # 再校验旧版 source_file_limits 兼容块，守住历史字段兜底契约。
    append_source_file_limit_errors(dict_source_limits, list_errors)

    # 最后校验 tool_script_layout，锁住 scripts/<family>/ 目录规则。
    append_tool_script_layout_errors(dict_script_layout, list_errors)

    # 把累计的全局治理覆盖诊断返回给调用方。
    return list_errors

# 加载并校验本地全局治理覆盖文件，统一处理默认值、兼容迁移和显式门禁。
def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """加载本地治理覆盖文件，并返回路径、合并后数据与显式校验错误。

    参数:
        root: 仓库根目录。
        profile: 可选的设计画像，用于选择兼容默认值。

    返回:
        包含文件路径、是否存在、合并后配置和错误列表的结果映射。
    """

    # 读取画像驱动的默认治理配置，作为本地 JSON 缺失时的稳定基线。
    dict_defaults = legacy_global_rule_overrides(profile)  # 默认治理覆盖配置

    # 定位当前仓库的本地治理覆盖文件路径。
    path_path = global_rule_overrides_path(root, profile)  # 本地治理覆盖文件路径

    # 读取磁盘上的原始 JSON；文件缺失时回落为空对象以复用默认值。
    obj_raw = read_json(path_path) if path_path.exists() else {}  # 原始治理 JSON 载荷

    # 旧版 code_comment_policy 需要先迁移为 coding_behavior，再进入统一校验流程。
    obj_migrated_raw = migrate_code_comment_policy_to_coding_behavior(obj_raw) if isinstance(obj_raw, dict) else obj_raw  # 迁移后的原始载荷

    # 合并默认值与本地覆盖，得到后续所有调用方消费的最终治理配置。
    dict_merged = merge_object(dict_defaults, obj_migrated_raw) if isinstance(obj_migrated_raw, dict) else dict_defaults  # 合并后的治理配置

    # 自定义 structured route 只保留用户显式配置，禁止深度合并自动注入旧三字段。
    dict_raw_coding_behavior = (  # 原始 coding_behavior 配置映射
        obj_migrated_raw.get("coding_behavior", {})  # 从迁移后的 JSON 读取配置块
        if isinstance(obj_migrated_raw, dict)  # 仅对象根节点可提供配置
        else {}  # 非对象根节点使用空配置
    )  # 原始编码行为配置。

    # 从 coding_behavior 中提取用户显式语言路由，保留其原始字段形状。
    dict_raw_language_routing = (  # 原始 language_skill_routing 配置
        dict_raw_coding_behavior.get("language_skill_routing", {})  # 读取语言路由子对象
        if isinstance(dict_raw_coding_behavior, dict)  # 仅映射类型可继续读取
        else {}  # 非映射配置使用空路由
    )  # 原始语言路由配置。

    # 只有用户显式提供非空语言路由且合并结果可写时才保留其字段形状。
    if (
        isinstance(dict_raw_language_routing, dict)
        and dict_raw_language_routing
        and isinstance(dict_merged.get("coding_behavior"), dict)
    ):

        # 保留 custom structured override 的原始字段形状，交给显式校验报告缺失项。
        dict_merged["coding_behavior"]["language_skill_routing"] = dict(  # 保留 custom route 原始字段形状
            dict_raw_language_routing  # 复制用户显式路由映射
        )  # 不自动生成 shared/python/script 平面字段。

    # 先校验合并后的整体配置，保证默认值和覆盖值组合后仍满足契约。
    list_errors = validate_global_rule_overrides_data(dict_merged)  # 合并后配置的错误列表

    # 文件存在时，还要额外校验“本地 JSON 是否显式保留关键块”这一门禁。
    if path_path.exists():

        # 非对象 JSON 不能作为本地治理配置，先报根因并跳过逐字段显式检查。
        if not isinstance(obj_raw, dict):

            # 把本地文件根节点类型错误追加到错误列表末尾。
            list_errors.append("local governance config must be a JSON object")

        # 原始 JSON 是对象时，继续检查关键治理块是否显式保留。
        else:

            # 逐字段显式校验统一基于迁移后的对象视图，避免旧键影响结论。
            dict_explicit_raw = obj_migrated_raw  # 参与显式校验的原始治理对象

            # coding_behavior 是语言技能路由的显式宿主，不能依赖默认值偷偷存在。
            if "coding_behavior" not in dict_explicit_raw:

                # 用 language_skill_routing 作为提示，让缺失原因更贴近真实契约。
                list_errors.append("coding_behavior.language_skill_routing must be present in local governance config")

            # coding_behavior 主键存在时，继续按显式模式校验子字段。
            else:

                # 读取本地文件中的编码行为块，要求所有关键字段都显式保留。
                dict_raw_coding_behavior = dict_explicit_raw.get("coding_behavior")  # 本地编码行为配置

                # 非对象 coding_behavior 无法承载语言技能路由和格式治理。
                if not isinstance(dict_raw_coding_behavior, dict):

                    # 把编码行为块类型问题直接回显给本地治理文件作者。
                    list_errors.append("coding_behavior must be a non-empty object")

                # 编码行为块结构有效时，进入 require_explicit 模式核对完整性。
                else:

                    # 在显式模式下校验本地编码行为块，确保关键字段没有被默认值偷偷补齐。
                    list_errors.extend(validate_coding_behavior_data(dict_raw_coding_behavior, require_explicit=True))

            # script_output_policy 必须显式出现在本地 JSON 中，防止日志协议退回默认值。
            if "script_output_policy" not in obj_raw:

                # 直接指出策略块缺失，便于调用方恢复脚本输出治理。
                list_errors.append("script_output_policy must be present in local governance config")

            # script_output_policy 主键存在时，继续按显式模式校验细项。
            else:

                # 读取本地脚本输出策略块，后续要求 enabled/format/kinds/python 显式保留。
                dict_raw_script_output_policy = obj_raw.get("script_output_policy")  # 本地脚本输出策略

                # 非对象策略块无法表达固定前缀和 Python quiet 约束。
                if not isinstance(dict_raw_script_output_policy, dict):

                    # 把策略块类型问题单独回显，避免掺杂子字段噪声。
                    list_errors.append("script_output_policy must be a non-empty object")

                # 策略块结构有效时，继续检查显式字段完整性。
                else:

                    # 在显式模式下校验本地脚本输出策略，确保协议字段没有被静默弱化。
                    list_errors.extend(
                        validate_script_output_policy_data(dict_raw_script_output_policy, require_explicit=True),
                    )

            # source_governance 也必须显式存在，避免源码体积门禁只靠默认值生效。
            if "source_governance" not in obj_raw:

                # 直接指出源码治理块缺失，提醒调用方恢复显式治理配置。
                list_errors.append("source_governance must be present in local governance config")

            # source_governance 主键存在时，继续验证其对象结构。
            elif not isinstance(obj_raw.get("source_governance"), dict):

                # 非对象源码治理块无法表达体积、注释和可读性门禁。
                list_errors.append("source_governance must be a non-empty object")

            # 源码治理块结构有效时，进入现有 source_governance 校验器。
            else:

                # 复用 source_governance 校验器检查本地源码治理块的结构完整性。
                list_errors.extend(validate_source_governance_data(obj_raw["source_governance"]))

    # 返回路径、存在性、合并后数据和累计错误，供调用方统一消费。
    return {"path": path_path, "exists": path_path.is_file(), "data": dict_merged, "errors": list_errors}

# 受管语言路由刷新器只更新完整命中历史默认值的三字段合同。
def refresh_managed_language_skill_routes(dict_existing_raw: dict[str, Any]) -> bool:
    """按当前安装状态刷新仍由生成器管理的语言技能路由。

    参数:
        dict_existing_raw: 磁盘治理配置的可变映射。

    返回:
        三字段路由发生实际变化时为 True，否则为 False。
    """

    # 读取新版编码行为对象，损坏类型不参与受管路由刷新。
    dict_existing_coding = dict_existing_raw.get("coding_behavior", {})  # 现有编码行为配置

    # 只有映射类型才能继续读取语言技能路由。
    dict_existing_routing = (  # 现有语言技能路由配置
        dict_existing_coding.get("language_skill_routing", {})  # 新版路由子对象
        if isinstance(dict_existing_coding, dict)  # 有效编码行为映射
        else {}  # 损坏配置回退为空路由
    )

    # 非映射路由交给配置验证器报告，不在迁移阶段猜测修复。
    if not isinstance(dict_existing_routing, dict):

        # 未发生安全刷新时保持磁盘内容不变。
        return False

    # structured route records 是唯一受管输入，旧字符串只从其 full_text 派生。
    dict_default_structured = _load_structured_route_defaults().get("routes", {})  # packaged 结构化路由默认记录

    # 缺少完整默认记录时不猜测受管字段的替代内容。
    if not isinstance(dict_default_structured, dict) or not dict_default_structured:

        # 保持磁盘治理配置不变，交给上游配置校验器报告缺口。
        return False

    # 读取三类 legacy 文案的历史默认集合，用于判断是否仍由生成器管理。
    tuple_managed_defaults = managed_language_skill_route_defaults()  # legacy 默认文案集合

    # 分别展开 shared、Python 和脚本的历史默认集合。
    set_shared_defaults, set_python_defaults, set_script_defaults = tuple_managed_defaults  # 三类 legacy 集合

    # 只有三个旧字段都命中默认集合时才允许自动刷新。
    bool_legacy_managed = (  # legacy 三字段是否仍属于生成器管理范围
        dict_existing_routing.get("shared") in set_shared_defaults  # 共同门禁采用当前受管默认文案
        and dict_existing_routing.get("python") in set_python_defaults  # Python owner 采用当前受管默认文案
        and dict_existing_routing.get("script") in set_script_defaults  # 脚本 owner 采用当前受管默认文案
    )

    # 读取现有 structured 记录，空对象或默认对象都属于可安全刷新范围。
    dict_existing_structured = dict_existing_routing.get("structured")  # 当前 structured 路由记录

    # 判断 structured 是否仍保持受管默认形状。
    bool_structured_managed = dict_existing_structured in ({}, dict_default_structured)  # structured 可刷新状态

    # 自定义 structured 或 legacy 文案必须由用户显式维护，禁止自动覆盖。
    if not bool_legacy_managed and not bool_structured_managed:

        # 保持用户自定义治理事实不变。
        return False

    # 将内置路由投影为 legacy 字段和完整 structured records。
    dict_current_routes: dict[str, Any] = {}  # 待写回的治理路由字段

    # 逐个读取内置 full_text，保持默认治理 JSON 的三字段兼容形状。
    for str_route_name in ("shared", "python", "script"):

        # 当前目标的 full_text 是 legacy 字段唯一允许的派生来源。
        dict_current_routes[str_route_name] = str(  # 将当前目标的 packaged full_text 写入兼容字段
            dict_default_structured[str_route_name].get("full_text", "")  # 读取当前目标的 packaged 全文
        )  # 当前目标的 legacy 路由文案

    # structured records 必须作为旧字段的唯一派生来源同时写回。
    dict_current_routes["structured"] = dict_default_structured  # 完整结构化路由记录

    # 只有内容实际漂移时才触发治理 JSON 写回。
    if dict_existing_routing == dict_current_routes:

        # 相同合同不属于实际刷新。
        return False

    # 清空旧键后整体写入三个派生字段，避免残留未知受管字段。
    dict_existing_routing.clear()

    # 原子更新确保三个 legacy projection 同时刷新。
    dict_existing_routing.update(dict_current_routes)

    # 返回真实变化供调用方决定是否写盘和重载。
    return True

# 确保本地全局治理覆盖文件与 GUI 例外 manifest 存在，并在需要时执行旧键迁移写回。
def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """确保本地治理覆盖文件存在，并在需要时补齐 GUI 例外 manifest。

    参数:
        root: 仓库根目录。
        profile: 可选的设计画像，用于派生默认治理配置。

    返回:
        最新加载得到的治理覆盖结果映射。
    """

    # 先加载当前治理覆盖视图，后续会基于它决定是否写盘或迁移旧键。
    dict_loaded = load_global_rule_overrides(root, profile)  # 当前加载到的治理覆盖结果

    # 这条路径就是本地覆盖 JSON 的真实落点；后面的新建和迁移写回都只能围绕它执行。
    path_overrides_json = dict_loaded["path"]  # overrides JSON 写盘锚点

    # 先补齐本地治理覆盖文件的父目录，避免首次写盘时因为目录缺失失败。
    path_overrides_json.parent.mkdir(parents=True, exist_ok=True)

    # 治理覆盖文件缺失时，直接把合并后的默认配置写到磁盘。
    if not path_overrides_json.exists():

        # 新文件写入排序后的 UTF-8 JSON，保证仓库中的治理配置稳定可比对。
        path_overrides_json.write_text(
            json.dumps(dict_loaded["data"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # 新文件落盘后立即重载，避免后续返回值仍然停留在写盘前的内存视图。
        dict_loaded = load_global_rule_overrides(root, profile)  # 写盘后的治理覆盖结果

    # 文件已经存在时，只在检测到旧键或缺失 coding_behavior 时执行迁移写回。
    else:

        # 读取磁盘上的现有 JSON，判断是否仍处于旧版 code_comment_policy 形态。
        dict_existing_raw = read_json(path_overrides_json)  # 磁盘上的原始治理 JSON

        # 已知受管默认路由可按当前安装状态安全刷新，用户自定义文本保持原样。
        if isinstance(dict_existing_raw, dict):

            # 独立刷新器只修改完整命中历史默认值的语言路由三元组。
            bool_routes_refreshed = refresh_managed_language_skill_routes(dict_existing_raw)  # 是否需要写回路由

            # 只有实际命中受管默认时才写盘，避免无意义改写用户 JSON。
            if bool_routes_refreshed:

                # 保留用户字段顺序并使用 UTF-8 写回当前默认路由。
                path_overrides_json.write_text(
                    json.dumps(dict_existing_raw, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                # 写盘后重新加载，确保返回值反映磁盘事实。
                dict_loaded = load_global_rule_overrides(root, profile)  # 路由刷新后的治理配置

        # 旧键残留或新版 coding_behavior 缺失时，都需要落盘新版治理结构。
        if isinstance(dict_existing_raw, dict) and (
            "code_comment_policy" in dict_existing_raw or "coding_behavior" not in dict_existing_raw
        ):

            # 写回迁移后的治理配置，让后续所有调用都基于统一键集合。
            path_overrides_json.write_text(
                json.dumps(dict_loaded["data"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            # 迁移写回完成后重新加载，确保返回值与磁盘一致。
            dict_loaded = load_global_rule_overrides(root, profile)  # 迁移后的治理覆盖结果

    # 先解析 GUI 例外 manifest 的相对路径，再拼出仓库里的实际清单文件位置。
    str_gui_manifest_relpath = str(  # GUI 例外 manifest 的相对路径
        dict_loaded["data"]["tool_script_layout"].get(  # 从脚本布局配置里读取 manifest 相对路径
            "gui_exception_manifest",  # GUI 例外 manifest 的配置键
            DEFAULT_GUI_EXCEPTION_MANIFEST,  # GUI 例外 manifest 默认相对路径
        ),
    ).strip()

    # 把相对路径锚定到当前仓库根目录，得到 GUI 例外清单的实际路径。
    path_gui_manifest = root / str_gui_manifest_relpath  # GUI 例外 manifest 路径

    # manifest 父目录需要存在，后续新建默认白名单文件时才不会失败。
    path_gui_manifest.parent.mkdir(parents=True, exist_ok=True)

    # manifest 缺失时写入最小白名单骨架，保持 GUI 例外配置结构稳定。
    if not path_gui_manifest.exists():

        # 默认骨架只保留 gui_startup 数组，方便后续显式追加例外。
        path_gui_manifest.write_text('{\n  "gui_startup": []\n}\n', encoding="utf-8")

    # 返回最新加载到的治理覆盖结果，保证调用方看到的是最终磁盘状态。
    return dict_loaded

# 从设计画像或仓库本地治理中提取实现约束，供生成与校验脚本复用统一边界。
def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    """提取实现约束，优先使用仓库本地治理，其次回落到画像中的兼容默认值。

    参数:
        profile: 可选的设计画像数据。
        root: 可选的仓库根目录；存在时优先读取本地治理覆盖文件。

    返回:
        标准化后的实现约束映射。
    """

    # 读取默认实现约束，作为没有画像或没有本地治理时的最后兜底。
    dict_defaults = default_implementation_constraints()  # 默认实现约束

    # 仓库根目录存在时，优先从本地治理覆盖文件中提取真实生效的实现边界。
    if root is not None:

        # 读取已合并的本地治理配置，避免直接从画像推断过时边界。
        dict_overrides = load_global_rule_overrides(root, profile)["data"]  # 已合并的本地治理配置

        # 取得 source_governance，映射到旧实现约束消费者仍在使用的字段名。
        dict_source_governance = dict_overrides.get("source_governance", {})  # 已合并的源码治理配置

        # 取得脚本布局块，继续映射到旧脚本布局约束结构。
        dict_script_layout = dict_overrides["tool_script_layout"]  # 已合并的脚本布局配置

        # 把本地治理折叠成旧调用方仍然消费的实现约束结构。
        return {
            "source_file_max_bytes": int(
                dict_source_governance.get("max_bytes", dict_defaults["source_file_max_bytes"]),
            ),
            "size_limit_extensions": list(
                dict_source_governance.get("hard_fail_extensions", dict_defaults["size_limit_extensions"]),
            ),
            "size_limit_scope": dict_defaults["size_limit_scope"],
            "size_limit_exclude_roots": list(
                dict_source_governance.get("excluded_roots", dict_defaults["size_limit_exclude_roots"]),
            ),
            "script_layout": {
                "required_root": str(
                    dict_script_layout.get("required_root", dict_defaults["script_layout"]["required_root"]),
                ),
                "families": dict(
                    dict_script_layout.get("families", dict_defaults["script_layout"]["families"]),
                ),
                "required_pattern": str(
                    dict_script_layout.get("required_pattern", dict_defaults["script_layout"]["required_pattern"]),
                ),
                "require_full_triad": bool(
                    dict_script_layout.get(
                        "require_full_triad",
                        dict_defaults["script_layout"]["require_full_triad"],
                    ),
                ),
                "gui_exception_mode": "explicit-manifest",
                "gui_exception_manifest": str(
                    dict_script_layout.get("gui_exception_manifest", DEFAULT_GUI_EXCEPTION_MANIFEST),
                ),
            },
        }

    # 没有可用画像对象时，直接返回默认实现约束。
    if not isinstance(profile, dict):

        # 没有画像对象时，直接回落默认实现约束。
        return dict_defaults

    # 读取画像中的 implementation_constraints 兼容块。
    dict_raw_constraints = profile.get("implementation_constraints", {})  # 画像中的实现约束块

    # implementation_constraints 不是对象时，无法继续合并，直接回落默认值。
    if not isinstance(dict_raw_constraints, dict):

        # 画像中的 implementation_constraints 非对象时，直接回落默认实现约束。
        return dict_defaults

    # 先复制默认值，再用画像中的非 script_layout 字段覆盖顶层实现约束。
    dict_merged_constraints = dict(dict_defaults)  # 合并中的实现约束结果

    # 先合并非 script_layout 顶层字段，保持旧消费者期待的键不丢失。
    dict_merged_constraints.update(
        {str_key: obj_value for str_key, obj_value in dict_raw_constraints.items() if str_key != "script_layout"},
    )

    # script_layout 需要单独按子对象合并，避免丢掉默认布局键。
    dict_merged_constraints["script_layout"] = dict(dict_defaults["script_layout"])  # 合并中的脚本布局约束

    # 读取画像中的 script_layout 子块，只有对象时才允许覆盖默认布局。
    dict_profile_script_layout = dict_raw_constraints.get("script_layout", {})  # 画像中的脚本布局约束

    # script_layout 子块是对象时，把其字段合并进默认脚本布局。
    if isinstance(dict_profile_script_layout, dict):

        # script_layout 子块是对象时，再把局部覆盖合并进默认布局。
        dict_merged_constraints["script_layout"].update(dict_profile_script_layout)

    # 返回最终合并后的实现约束，供生成与校验逻辑共享。
    return dict_merged_constraints
