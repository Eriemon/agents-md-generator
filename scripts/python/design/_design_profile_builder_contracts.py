"""构建设计访谈生成档案时使用的目录、远程运行与治理合同。"""

# 延迟类型标注求值，支持拼装模块中的跨片段类型引用。
from __future__ import annotations

# 启动阶段需要定位同级任务模块。
import sys
from pathlib import Path

# 拼装入口需要在导入合同依赖前登记兄弟任务模块。
def extend_task_module_search_path() -> None:
    """把 Python 任务子目录加入当前解释器的模块搜索路径。

    Args:
        None: 搜索根由当前文件位置确定。

    Returns:
        None: 函数仅更新当前解释器搜索路径。
    """

    # Python 脚本根包含 design 依赖的公共任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # 各任务分类脚本共同父目录

    # 逐个登记目录，保持历史裸模块导入兼容。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 文件资产不能承载可导入的任务模块。
        if path_task_directory.is_dir():

            # 字符串形式用于与解释器现有搜索路径比较。
            str_task_path = str(path_task_directory)  # 当前任务目录的解释器搜索路径

            # 已登记路径不重复插入，保持既有解析顺序。
            if str_task_path not in sys.path:

                # 兄弟任务模块使用裸模块名维持历史脚本入口兼容。
                sys.path.insert(0, str_task_path)

# 显式执行一次兼容引导，再加载跨任务模块。
extend_task_module_search_path()

# 标准库处理合同序列化、正则解析和开放字段类型。
import json
import re
from typing import Any

# 问题注册表的显式导出同时供后续 assembly 片段使用。
from design_questions import (
    ALIGNMENT_KEY,
    DESIGN_REVIEW_KEY,
    ENGINEERING_RULE_MODES,
    ENGINEERING_RULE_SCOPES,
    ENGINEERING_RULE_SETS,

    # 通用访谈字段控制补充要求与可空答案。
    EXTRA_REQUIREMENTS_KEY,
    OPTIONAL_EMPTY_KEYS,
    REMOTE_DIRECTORY_POLICY_KEYS,
    REMOTE_LEGACY_TASK_NAME,

    # 旧版服务器选择字段用于兼容迁移。
    REMOTE_SELECTED_SERVER_CATEGORY_KEY,
    REMOTE_SELECTED_SERVER_FUNCTIONS_KEY,
    REMOTE_SELECTED_SERVER_ID_KEY,
    REMOTE_SELECTED_SERVER_NAME_KEY,
    REMOTE_SELECTED_SERVER_TASKS_KEY,

    # 远程选择状态字段控制确认和验证门禁。
    REMOTE_SELECTION_CONFIRMED_KEY,
    REMOTE_SERVER_TASK_ROUTES_KEY,
    REMOTE_SSH_GIT_URL,
    REMOTE_SSH_SKILL_NAME,
    REMOTE_VALIDATION_STATUS_KEY,

    # 公共问题工具供合同和 assembly 片段共同调用。
    SKILL_NAME_RE,
    USE_REMOTE_SERVER_KEY,
    empty,
    normalize_extra_requirements,
    questions_for,
    remote_directory_policy_required,
)

# 远程门禁只导入合同构建和 assembly 实际依赖的接口。
from design_remote_gate import (
    normalize_remote_server_registry,
    normalize_remote_task_key,
    normalize_remote_task_list,
    normalize_remote_task_routes,

    # 依赖和服务器选项函数提供实时远程事实。
    remote_choices,
    remote_dependency_summary,
    remote_server_check,
    remote_server_record,
    remote_server_workspace_check,

    # 路由解析函数验证任务到服务器的映射。
    resolve_remote_server_for_task,
    server_registry_map,
    use_remote_server_enabled,
    validate_route_server_ids,
)

# 设计档案基础合同提供全局覆盖配置验证。
from design_profile_contracts import global_rule_overrides_contract

# 公共项目工具负责检查、路径解析和机器可读输出。
from agents_common import (
    emit_json,
    ensure_global_rule_overrides_file,
    inspect_project,
    resolve_project,
)

# 文档治理脚手架创建标准治理目录。
from manage_docs import scaffold as scaffold_docs

# 工作区设置策略隔离本地和远程配置。
from workspace_settings_policy import workspace_settings_contract

# 这些根级工作目录可与标准主项目目录并存。
ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")  # 允许存在的辅助工作目录

# smoke 前缀允许多个隔离验证目录。
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)  # 允许动态创建的工作目录前缀

# 项目类型推断只依赖技能清单，不读取访谈答案。
def infer_kind(project: Path) -> str:
    """根据技能清单位置判断项目属于 skill 还是 engineering。

    Args:
        project: 待检查的项目根目录。

    Returns:
        skill 或 engineering 项目类型。
    """

    # 任一受支持位置存在 SKILL.md 即采用技能项目合同。
    if (
        (project / "SKILL.md").exists()
        or any(path.is_file() for path in project.glob("*/SKILL.md"))
        or any(path.is_file() for path in project.glob("skills/*/SKILL.md"))
    ):

        # 技能标记优先于普通工程目录特征。
        return "skill"

    # 没有技能标记时按工程项目处理。
    return "engineering"

# 治理初始化资产需要从真实项目内容判断中排除。
def meaningful_paths(facts: dict[str, Any]) -> bool:
    """判断项目事实中是否包含治理文件之外的真实工作内容。

    Args:
        facts: inspect_project 返回的文件与目录事实。

    Returns:
        存在非治理内容时返回 True。
    """

    # 文件集合统一转成字符串，便于过滤治理占位资产。
    list_files = [str(item) for item in facts.get("files", []) if str(item)]  # 项目根事实中的文件路径

    # 目录集合使用相同的非空字符串规范。
    list_directories = [str(item) for item in facts.get("directories", []) if str(item)]  # 项目根事实中的目录路径

    # 根级规则与版本控制配置不足以证明项目已有业务内容。
    set_ignored_files = {"AGENTS.md", ".gitignore", ".gitattributes", ".editorconfig"}  # 治理占位文件

    # 排除生成规则和治理状态文件后保留真实文件。
    list_meaningful_files = [  # 非治理文件路径
        str_item  # 当前项目文件
        for str_item in list_files  # 根目录文件事实
        if str_item not in set_ignored_files  # 排除根级治理文件
        and not str_item.startswith(".agents/")  # 排除治理状态文件
    ]

    # docs 与 .agents 本身可能由治理初始化创建，不算现有工作。
    list_meaningful_directories = [  # 可证明存在项目内容的目录路径
        item  # 当前候选目录
        for item in list_directories  # inspect_project 返回的目录集合
        if item  # 忽略空目录名称
        and item not in {"docs", ".agents"}  # 忽略治理根目录
        and not item.startswith("docs/")  # 忽略文档治理子目录
        and not item.startswith(".agents/")  # 忽略生成状态子目录
    ]

    # 文件或目录任一集合非空即可阻止无提示接管。
    return bool(list_meaningful_files or list_meaningful_directories)

# 接管判断把版本漂移与真实项目内容同时纳入决策。
def takeover_required(project: Path) -> tuple[bool, dict[str, Any]]:
    """判断版本不匹配的现有项目是否必须进入接管流程。

    Args:
        project: 待检查的项目根目录。

    Returns:
        接管标志与完整项目事实。
    """

    # 项目事实同时供版本触发判断和调用方后续报告使用。
    dict_facts = inspect_project(project)  # 当前项目检查事实

    # 仅生成器或规则版本不匹配会触发接管候选。
    set_reasons = {str(item) for item in dict_facts.get("root_agents_md_trigger_reasons", [])}  # 根规则触发原因

    # 交集把其他根规则诊断排除在接管决定之外。
    bool_triggered = bool(set_reasons & {"agents_version_mismatch", "generator_version_mismatch"})  # 是否命中版本接管条件

    # 没有版本触发时保持普通检查路径。
    if not bool_triggered:

        # 项目事实仍返回给调用方复用。
        return False, dict_facts

    # 空壳治理目录不需要以现有项目接管方式处理。
    if not meaningful_paths(dict_facts):

        # 空项目允许直接完成规则初始化。
        return False, dict_facts

    # 版本不匹配且存在真实内容时要求显式接管。
    return True, dict_facts

# 缺失答案计算遵循问题注册表中的条件字段规则。
def missing_answers(answers: dict[str, Any], kind: str) -> list[str]:
    """返回指定项目类型仍缺少的设计访谈答案键。

    Args:
        answers: 当前已确认的访谈答案。
        kind: skill 或 engineering 项目类型。

    Returns:
        按问题顺序排列的缺失答案键。
    """

    # 缺失项保持问题定义顺序，便于访谈稳定续问。
    list_missing: list[str] = []  # 按问题顺序收集的缺失答案键

    # 未启用远程目录策略时跳过其条件问题。
    bool_remote_policy_required = remote_directory_policy_required(answers)  # 是否需要远程目录策略答案

    # 问题注册表是不同项目类型必填键的事实源。
    for item in questions_for(kind):

        # answer_key 是问题与档案字段之间的稳定关联键。
        str_key = str(item["answer_key"])  # 当前问题对应的答案键

        # 语言与远程开关由专用流程处理，不作为普通缺失项。
        if str_key in {"default_conversation_language", USE_REMOTE_SERVER_KEY}:

            # 跳过专用路由字段，继续检查注册表后续问题。
            continue

        # 未启用远程结构时不要求填写远程目录模板。
        if str_key in REMOTE_DIRECTORY_POLICY_KEYS and not bool_remote_policy_required:

            # 条件不成立的远程问题不进入缺失列表。
            continue

        # 可选空字段只要求键存在，不要求非空文本。
        if str_key in OPTIONAL_EMPTY_KEYS and str_key in answers:

            # 已显式回答的可选字段满足访谈合同。
            continue

        # 其他字段缺键或值为空时形成待续问项。
        if str_key not in answers or empty(answers[str_key]):

            # 保持问题注册表顺序追加缺失键。
            list_missing.append(str_key)

    # 所有内容答案完成后仍需独立的目标对齐确认。
    if ALIGNMENT_KEY not in answers:

        # 对齐键放在普通问题之后，形成最终确认步骤。
        list_missing.append(ALIGNMENT_KEY)

    # 调用方按该有序列表决定下一轮问题组。
    return list_missing

# SKILL.md 名称解析只读取前置元数据，不猜测正文内容。
def parse_skill_name(skill_path: Path) -> str:
    """读取 SKILL.md 前置元数据中的技能名称。

    Args:
        skill_path: 待读取的 SKILL.md 路径。

    Returns:
        name 字段文本；前置元数据无效时返回空字符串。
    """

    # 容错读取让布局诊断能够继续报告损坏的技能文件。
    str_text = skill_path.read_text(encoding="utf-8", errors="ignore")  # SKILL.md 原始文本

    # 只解析文件开头的 YAML 前置元数据边界。
    match_frontmatter = re.search(r"^---\s*\n(.*?)\n---", str_text, flags=re.DOTALL)  # 前置元数据匹配结果

    # 缺少完整边界时不猜测正文中的 name 文本。
    if not match_frontmatter:

        # 空值交由布局合同生成名称不匹配诊断。
        return ""

    # 前置元数据逐行定位顶层 name 字段。
    for str_line in match_frontmatter.group(1).splitlines():

        # 首个 name 字段决定技能标识。
        if str_line.strip().startswith("name:"):

            # 去除 YAML 引号以便与目录名直接比较。
            return str_line.split(":", 1)[1].strip().strip("\"'")

    # 合法前置元数据未声明 name 时返回空值。
    return ""

# 技能文件发现排除发布历史、参考副本和解释器缓存。
def discover_skill_files(project: Path) -> list[Path]:
    """发现项目内参与布局治理的 SKILL.md 文件。

    Args:
        project: 待扫描的项目根目录。

    Returns:
        排除历史产物和缓存后的有序技能文件路径。
    """

    # 发布包、参考材料与缓存中的副本不属于源码布局。
    set_skip = {".git", "dist", "ref", "__pycache__"}  # 不参与源码布局验证的目录名

    # 收集结果最后统一排序，保证跨平台诊断稳定。
    list_files: list[Path] = []  # 真实源码 SKILL.md 路径

    # 技能文件可能位于根、一级子目录或标准 skills 子树。
    for path in project.rglob("SKILL.md"):

        # 相对路径用于判断是否穿过排除目录。
        path_relative = path.relative_to(project)  # 相对项目根的技能文件路径

        # 任一排除目录片段命中时忽略该副本。
        if set(path_relative.parts) & set_skip:

            # 继续扫描其他源码技能文件。
            continue

        # 保留真实源码候选供布局合同逐项验证。
        list_files.append(path)

    # 固定路径顺序使错误报告与测试断言可重复。
    return sorted(list_files)

# 技能布局合同同时校验目录名、前置元数据名称和接管模式。
def skill_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """验证技能项目采用标准目录并返回布局合同。

    Args:
        project: 待验证的项目根目录。
        name: 访谈确认的技能名称。
        answers: 当前设计访谈答案。

    Returns:
        标准技能路径合同与布局错误列表。
    """

    # 所有布局发现一次性返回，减少逐项修复循环。
    list_errors: list[str] = []  # 技能目录与名称错误

    # 接管模式允许治理旧项目尚未采用标准目录。
    bool_takeover_mode = bool(answers.get("takeover_mode"))  # 是否已确认接管现有项目

    # 技能名称必须可同时用于目录与前置元数据。
    if not SKILL_NAME_RE.fullmatch(name):

        # 名称格式错误不阻止继续收集其他布局发现。
        list_errors.append("skill name must use lowercase letters, digits, and hyphens only")

    # 标准技能文件必须位于 skills/<name>/SKILL.md。
    path_expected = project / "skills" / name / "SKILL.md"  # 期望技能文件路径

    # 项目内所有真实技能文件用于检查旧布局冲突。
    list_files = discover_skill_files(project)  # 参与布局治理的技能文件

    # 标准路径已存在时优先验证其元数据名称。
    if path_expected.exists():

        # 前置元数据名称必须与请求名称完全一致。
        str_skill_name = parse_skill_name(path_expected)  # 标准路径声明的技能名称

        # 不一致时保留标准合同并附加诊断。
        if str_skill_name != name:

            # 调用方可在同一轮修复名称而无需重新发现路径。
            list_errors.append(f"SKILL.md name must match folder name: {name}")

        # 标准路径存在后无需遍历其他兼容候选。
        return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, list_errors

    # 非接管的已有项目必须提前具备标准技能文件布局。
    if answers.get("has_existing_work") == "yes" and not bool_takeover_mode:

        # 完全找不到技能文件时给出标准目标路径。
        if not list_files:

            # 长诊断拆行以保持源码可读宽度。
            list_errors.append(
                "skill projects with existing work must already place the skill "
                "under skills/<skill-name>/SKILL.md"
            )

        # 每个发现文件独立检查目录层级与名称一致性。
        for skill_file in list_files:

            # 相对路径用于生成不依赖工作区位置的诊断。
            str_relative = skill_file.relative_to(project).as_posix()  # 诊断使用的 POSIX 相对路径

            # 路径片段用于确认 skills/<folder>/SKILL.md 层级。
            tuple_parts = skill_file.relative_to(project).parts  # 技能文件相对路径片段

            # 标准 skills 子树中的文件继续验证目录名。
            if len(tuple_parts) >= 3 and tuple_parts[0] == "skills":

                # 第二个路径片段是技能目录标识。
                str_folder = tuple_parts[1]  # 标准 skills 下的技能目录名

                # 文件内名称必须与目录名相互印证。
                str_skill_name = parse_skill_name(skill_file)  # 候选文件声明的技能名称

                # 请求名称不同表示项目主技能目录选错。
                if str_folder != name:

                    # 诊断始终给出访谈确认的目标目录。
                    list_errors.append(f"skill folder must match requested skill name: skills/{name}/")

                # 元数据名称不同表示技能包自身不一致。
                if str_skill_name != str_folder:

                    # 目录名作为源码布局的权威名称。
                    list_errors.append(f"SKILL.md name must match folder name: {str_folder}")

            # 根级或任意其他层级均不满足标准技能项目合同。
            else:

                # 相对路径帮助用户定位需要移动的文件。
                list_errors.append(f"skill projects must use skills/<skill-name>/SKILL.md; found {str_relative}")

    # 即使存在错误也返回确定的目标布局供修复流程使用。
    return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, list_errors

# 目录策略明确主项目根与允许存在的辅助治理目录。
def directory_layout_policy(kind: str, name: str) -> dict[str, Any]:
    """构造项目类型对应的目录创建与根级可选路径策略。

    Args:
        kind: skill 或 engineering 项目类型。
        name: 项目或技能名称。

    Returns:
        目录管理器消费的布局策略。
    """

    # 主项目根由项目类型决定，其他目录仅作为受控辅助路径。
    str_primary = f"skills/{name}/" if kind == "skill" else f"engineering/{name}/"  # 标准主项目根

    # 目录管理器直接消费该结构化白名单。
    return {
        "primary_project_root": str_primary,
        "allowed_new_paths": [
            str_primary,
            "tests/",
            "smoke/",
            "reports/",
            "runs/",
            "dist/",
            "docs/",
            ".agents/",
            "ref/",
        ],
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "enforce_primary_project_root": True,
    }

# 工程布局只在已有工作且未接管时强制标准主目录。
def engineering_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> list[str]:
    """验证已有工程项目位于标准 engineering 子树。

    Args:
        project: 待验证的项目根目录。
        name: 访谈确认的工程名称。
        answers: 当前设计访谈答案。

    Returns:
        工程目录布局错误列表。
    """

    # 工程布局当前只有一个可独立修复的阻断条件。
    list_errors: list[str] = []  # 工程主目录错误

    # 现有工程必须已经采用标准主项目目录。
    path_expected = project / "engineering" / name  # 期望工程根目录

    # 非接管现有工程缺少标准目录时阻断档案生成。
    if (
        answers.get("has_existing_work") == "yes"
        and not path_expected.exists()
        and not bool(answers.get("takeover_mode"))
    ):

        # 错误明确给出标准 engineering 路径合同。
        list_errors.append(
            "engineering projects with existing work must already place the project "
            "under engineering/<project-name>/"
        )

    # 空列表表示布局满足或已进入显式接管模式。
    return list_errors

# 摘要字段提取保持调用方指定顺序并忽略未回答项。
def summarize_fields(answers: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """提取已存在的指定访谈答案字段。

    Args:
        answers: 完整访谈答案映射。
        keys: 需要进入摘要的字段顺序。

    Returns:
        仅包含已回答字段的有序摘要映射。
    """

    # 字典推导保持 keys 顺序并跳过尚未回答的字段。
    return {key: answers[key] for key in keys if key in answers}

# 审查摘要区分当前问题组、已确认字段和最终整体确认。
def review_summary(
    answers: dict[str, Any] | None,
    kind: str | None = None,
    current_keys: list[str] | None = None,
    confirmed_keys: list[str] | None = None,
    final: bool = False,
) -> dict[str, Any]:
    """构造设计访谈在当前轮次展示的审查摘要。

    Args:
        answers: 可选的当前访谈答案。
        kind: 可选项目类型覆盖值。
        current_keys: 本轮新增或修改的字段。
        confirmed_keys: 已完成确认的字段。
        final: 是否生成最终整体确认提示。

    Returns:
        包含当前答案、确认状态和项目事实的审查摘要。
    """

    # 空输入按尚未回答的访谈处理。
    dict_answers = answers or {}  # 参与摘要生成的答案映射

    # 当前问题组可为空，表示没有局部确认提示。
    list_current_keys = current_keys or []  # 本轮展示字段键

    # 已确认字段与当前字段分开展示。
    list_confirmed_keys = confirmed_keys or []  # 历史确认字段键

    # 历史确认摘要用于显示已锁定的访谈事实。
    dict_confirmed = summarize_fields(dict_answers, list_confirmed_keys)  # 已确认字段摘要

    # 当前摘要限制在本轮问题组，避免重复展示全部答案。
    dict_current = summarize_fields(dict_answers, list_current_keys)  # 当前问题组字段摘要

    # 最终阶段要求用户确认整份访谈已一致。
    if final:

        # 最终提示强调修正后必须重新确认。
        str_summary = "请确认完整设计访谈已经一致；如需修正，请提交修正字段后重新确认。"  # 整体确认提示

    # 非最终阶段优先确认当前问题组。
    elif list_current_keys:

        # 局部提示把修正范围限制在本轮字段。
        str_summary = "请确认当前问题组的答案是否正确；如果否，请修正本组字段并重新确认。"  # 问题组确认提示

    # 没有当前字段时退回通用理解确认。
    else:

        # 通用提示用于接管或兼容流程中的摘要展示。
        str_summary = "请用户确认以上理解是否正确；如果否，请修正对应字段后重新确认。"  # 通用理解确认提示

    # 结构化摘要供 CLI 展示与设计审查哈希共同使用。
    return {
        "kind": kind or dict_answers.get("development_type", "unconfirmed"),
        "current_group_fields": dict_current,
        "confirmed_fields": dict_confirmed,
        "summary": str_summary,
    }

# 对齐字段补充在现有载荷上，保持调用方对象引用不变。
def attach_alignment(
    payload: dict[str, Any],
    answers: dict[str, Any] | None = None,
    kind: str | None = None,
) -> dict[str, Any]:
    """把目标对齐确认状态附加到设计档案载荷。

    Args:
        payload: 待补充的设计档案载荷。
        answers: 可选访谈答案。
        kind: 可选项目类型。

    Returns:
        已写入对齐状态的原载荷。
    """

    # 未提供答案时生成空确认摘要而非修改调用合同。
    dict_answers = answers or {}  # 用于对齐判断的答案映射

    # 对齐标志本身不应出现在业务字段确认摘要中。
    list_confirmed_keys = [key for key in dict_answers if key != ALIGNMENT_KEY]  # 已确认业务答案键

    # 通用确认摘要展示当前已理解的全部业务答案。
    payload["review_summary"] = review_summary(dict_answers, kind, [], list_confirmed_keys, final=False)  # 对齐审查摘要

    # 兼容字段复用摘要中的已确认映射。
    payload["confirmed_so_far"] = payload["review_summary"]["confirmed_fields"]  # 已确认答案兼容视图

    # 固定问题文本要求否定回答同时给出修正字段。
    payload["confirmation_question"] = "请确认以上理解是否正确？如果正确回答是；如果不正确回答否并指出需要修正的字段。"  # 用户对齐确认问题

    # 只有显式真值才能关闭对齐确认门禁。
    payload["needs_alignment_confirmation"] = not bool(dict_answers.get(ALIGNMENT_KEY))  # 是否仍需用户确认目标理解

    # 原载荷补充完成后交回后续档案拼装流程。
    return payload

# 工程规则合同拒绝多主规则集和完整书籍规则粘贴。
def engineering_rule_contract(answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """验证并构造工程规则集选择合同。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        可选工程规则合同与验证错误列表。
    """

    # 主规则集原始值需要先拒绝多选列表。
    object_primary_raw = answers.get("engineering_rule_primary", "none")  # 用户提供的主规则集值

    # 主规则集只能选择一个稳定标识。
    if isinstance(object_primary_raw, list):

        # 列表输入无法确定唯一压缩与作用域策略。
        return None, ["engineering_rule_primary must name one primary rule set, not a list"]

    # 空主规则集规范成显式 none。
    str_primary = str(object_primary_raw).strip().lower() or "none"  # 规范化主规则集名称

    # 已选择规则集时默认使用 mini 压缩模式。
    str_mode = str(  # 规则内容压缩模式
        answers.get(  # 用户选择或规则集对应默认值
            "engineering_rule_mode",  # 规则模式答案键
            "none" if str_primary == "none" else "mini",  # 主规则集对应默认模式
        )
    ).strip().lower()  # 规范化规则压缩模式

    # 未明确作用域时仅按需应用，避免扩张全局基线。
    str_scope = str(answers.get("engineering_rule_scope", "on-demand")).strip().lower()  # 规则应用作用域

    # 自由说明保留原文本，仅去除首尾空白。
    str_notes = str(answers.get("engineering_rule_notes", "")).strip()  # 工程规则补充说明

    # 未配置主规则集时其他字段必须保持禁用语义。
    if str_primary in {"", "none", "not-configured"}:

        # none 主规则集不能同时声明激活模式。
        if str_mode != "none":

            # 冲突输入返回空合同，防止渲染出伪激活状态。
            return None, ["engineering_rule_mode must be none when engineering_rule_primary is none"]

        # 显式禁用合同仍保留压缩与兼容边界。
        return {
            "primary": "none",
            "mode": "none",
            "scope": "on-demand",
            "notes": str_notes,
            "full_reference_allowed_in_agents": False,
            "compatibility_policy": "no active book-derived rule set configured",
            "compression_policy": "keep only decision-changing rules in generated AGENTS.md",
        }, []

    # 激活规则集的所有字段一次性完成验证。
    list_errors: list[str] = []  # 工程规则选择错误

    # 分隔符表示调用方试图同时激活多个规则集。
    if "," in str_primary or "+" in str_primary:

        # 单主规则合同拒绝组合标识。
        list_errors.append("engineering_rule_primary must choose one primary active rule set")

    # 主规则集必须来自问题注册表允许集合。
    if str_primary not in ENGINEERING_RULE_SETS:

        # 未知名称不能进入生成规则。
        list_errors.append(f"unknown engineering_rule_primary: {str_primary}")

    # 完整书籍内容只能作为引用材料，不能直接渲染。
    if str_mode == "full":

        # full 模式违反 AGENTS 压缩边界。
        list_errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")

    # 激活规则集仅支持 mini 或 nano 两种压缩粒度。
    elif str_mode not in ENGINEERING_RULE_MODES or str_mode == "none":

        # none 只允许出现在未配置主规则集的分支。
        list_errors.append("engineering_rule_mode must be mini or nano")

    # 作用域必须能映射为稳定的生成规则位置。
    if str_scope not in ENGINEERING_RULE_SCOPES:

        # 非法作用域会导致规则泄漏到错误目录层级。
        list_errors.append("engineering_rule_scope must be project-baseline, scoped, or on-demand")

    # 任一验证失败时不返回部分有效合同。
    if list_errors:

        # 调用方使用完整错误集合修正访谈答案。
        return None, list_errors

    # 验证通过的合同明确禁止把完整参考内容写入 AGENTS。
    return {
        "primary": str_primary,
        "mode": str_mode,
        "scope": str_scope,
        "notes": str_notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": (
            "one primary active rule set; use other rule sets only as scoped "
            "or on-demand guidance"
        ),
        "compression_policy": (
            "decision-equivalent compression: keep decision-changing, trigger, "
            "tradeoff, and checklist rules"
        ),
    }, []

# 列表规范化统一处理数组与中英文逗号分隔文本。
def normalize_list(value: Any) -> list[str]:
    """把字符串或序列输入规范化为非空字符串列表。

    Args:
        value: 待规范化的任意访谈输入。

    Returns:
        去除空白与空项后的字符串列表。
    """

    # 原生列表保持元素顺序并删除空字符串。
    if isinstance(value, list):

        # 所有元素转为去空白文本以便稳定序列化。
        return [str(item).strip() for item in value if str(item).strip()]

    # 标量输入转成逗号分隔文本处理。
    str_raw = str(value).strip()  # 待拆分的规范化文本

    # 空标量对应空列表而不是单个空元素。
    if not str_raw:

        # 调用方可直接按列表长度判断是否提供内容。
        return []

    # 中英文逗号归一后过滤空片段。
    return [item.strip() for item in str_raw.replace("，", ",").split(",") if item.strip()]

# 远程路径模板必须相对工作区且不包含 shell 风险字符。
def invalid_remote_relative_template_reason(raw: str) -> str | None:
    """检查远程相对目录模板是否违反路径安全合同。

    Args:
        raw: 待验证的相对路径模板。

    Returns:
        首个失败原因；模板有效时返回 None。
    """

    # 原始模板仅移除首尾空白，保留内部字符用于诊断。
    str_raw_value = str(raw).strip()  # 待验证的远程相对路径模板

    # 统一分隔符便于跨平台检查父级与重复路径。
    str_normalized = str_raw_value.replace("\\", "/")  # POSIX 风格模板文本

    # 空模板无法定位远程环境或归档目录。
    if not str_raw_value:

        # 返回稳定原因供字段级错误包装。
        return "template must not be empty"

    # Windows 盘符与根斜杠都表示绝对路径。
    if re.match(r"^[A-Za-z]:[/\\]", str_raw_value) or str_normalized.startswith("/"):

        # 远程目录必须绑定所选服务器的工作区根。
        return "template must stay relative to the remote workspace root"

    # 独立父级片段可能逃逸工作区。
    if ".." in str_normalized.split("/"):

        # 拒绝父级遍历而不尝试路径折叠。
        return "template must not contain parent traversal"

    # 通配符与管道字符可能改变 shell 命令含义。
    if any(char in str_raw_value for char in "*?|"):

        # 路径模板只允许普通目录字符和受控占位符。
        return "template must not contain wildcard or unsafe shell characters"

    # 重复分隔符会产生不稳定的规范化结果。
    if "//" in str_normalized:

        # 调用方必须提供明确单分隔符路径。
        return "template must not contain repeated path separators"

    # 所有安全检查通过时不返回错误原因。
    return None

# 未配置远程结构时写入显式环境禁用合同。
def skill_design_contract(answers: dict[str, Any]) -> dict[str, Any]:
    """构造技能项目的触发、职责与验证设计合同。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        技能设计专用合同映射。
    """

    # 技能合同只保留可持久化的规范化访谈结果。
    return {
        "trigger_scenarios": str(answers["trigger_scenarios"]).strip(),
        "patterns": normalize_list(answers["skill_design_patterns"]),
        "resource_plan": str(answers["resource_plan"]).strip(),
        "progressive_disclosure_policy": str(answers["progressive_disclosure_policy"]).strip(),
        "validation_gates": str(answers["validation_gates"]).strip(),
        "validation_method": str(answers["validation_method"]).strip(),
        "validation_granularity": str(answers["validation_granularity"]).strip(),
        "forward_testing_policy": str(answers["forward_testing_policy"]).strip(),
        "reference_material_policy": (
            "temporary inputs only; distill durable constraints and remove "
            "local reference paths from generated AGENTS.md"
        ),
    }

# 文档合同集中维护各治理子目录的固定布局。
def docs_contract(name: str) -> dict[str, Any]:
    """构造项目文档目录、入口与生命周期合同。

    Args:
        name: 项目或技能名称。

    Returns:
        文档治理工具消费的目录与文件合同。
    """

    # 发布子合同嵌入统一的分支隔离策略。
    dict_branch_policy = git_branch_policy()  # 发布流程采用的分支隔离策略

    # 固定目录和命令元数据由脚手架与验证器共同消费。
    dict_contract = {  # 完整文档治理合同
        "root": "docs",  # 文档治理根目录
        "handoff": {  # 会话交接文档布局
            "current": "docs/handoff/HANDOFF.md",  # 当前交接文档
            "history": "docs/handoff/history_handoff",  # 历史交接归档目录
            "archive_pattern": "HANDOFF-YYYYMMDD-HHMMSS.md",  # 历史文件命名模式
            "required_sections": [  # 交接文档必需章节
                "original_plan_and_steps",  # 原始计划与步骤
                "current_step",  # 当前执行位置
                "problems",  # 已发现问题
                "resolved_problems",  # 已解决问题
                "remaining_problems",  # 剩余问题
                "next_work",  # 后续工作
                "verification_evidence",  # 验证证据
            ],
        },
        "development": {  # 开发状态文档布局
            "folder": "docs/development",  # 开发文档目录
            "current": "docs/development/DEVELOPMENT.md",  # 当前开发文档
            "history": "docs/development/history_development",  # 开发历史目录
            "history_pattern": "YYYYMMDD-HHMMSS/DEVELOPMENT.md",  # 开发归档模式
            "when": (  # 开发文档刷新时机
                "Write and iteratively refresh the latest DEVELOPMENT.md at "
                "installable release time or stage completion."
            ),
        },
        "install_configuration": {  # 安装配置文档布局
            "folder": "docs/install_configuration",  # 安装配置目录
            "targets": ["Codex", "Claude", "OpenClaw"],  # 支持的代理目标
        },
        "git_manager": {  # Git 与发布管理布局
            "folder": "docs/git_manager",  # Git 管理文档目录
            "branch_model": "master-and-dist-release",  # 发布分支模型
            "branch_policy": dict_branch_policy,  # 分支治理策略
            "change_log": "docs/git_manager/CHANGELOG.md",  # 变更日志
            "history": "docs/git_manager/history_git_manager",  # Git 历史目录
            "dist_folder": "dist",  # 发布包根目录
            "release_folder_pattern": f"{name}-vx.x.x",  # 版本目录模式
            "zip_required": True,  # 发布必须生成压缩包
        },
        "dir_manager": {  # 目录治理布局
            "folder": "docs/dir_manager",  # 目录管理文档根
            "current_structure": "docs/dir_manager/current_structure.json",  # 当前结构快照
            "planned_structure": "docs/dir_manager/planned_structure.json",  # 规划结构快照
            "history": "docs/dir_manager/history_dir_manager",  # 目录审查历史
            "review_required_for": ["create", "move", "delete", "rename"],  # 受审操作
            "block_on_failed_review": True,  # 审查失败默认阻断
            "force_override_requires_user_confirmation": True,  # 强制覆盖需用户确认
            "archive_before_force_override": True,  # 强制覆盖前保存证据
        },
        "workspace_settings": workspace_settings_contract(),  # 工作区设置隔离策略
    }

    # 返回单一合同对象，避免调用方重新拼装字段。
    return dict_contract

# 记忆合同把启用状态与持久化位置绑定在一起。
def memory_contract(answers: dict[str, Any]) -> dict[str, Any]:
    """构造项目记忆后端、根目录与维护命令合同。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        项目记忆治理合同。
    """

    # 开关同时控制记忆初始化和策略验证。
    bool_enabled = bool(answers.get("memory_enabled"))  # 是否启用项目记忆

    # 空后端值回退到仓库唯一受支持的组合存储。
    str_backend = (  # 规范化后的记忆存储后端
        str(answers.get("memory_storage_backend", "sqlite-plus-jsonl")).strip()  # 用户后端答案
        or "sqlite-plus-jsonl"  # 空答案采用受支持默认值
    )

    # 路径字段保持稳定，供初始化、读取和压缩命令复用。
    return {
        "enabled": bool_enabled,
        "folder": "docs/memory",
        "storage_backend": str_backend,
        "database": "docs/memory/memory.sqlite3",
        "events": "docs/memory/events.jsonl",
        "summaries": "docs/memory/summaries.md",
        "guide": "docs/memory/MEMORY.md",
        "capture_scope": str(answers.get("memory_capture_scope", "")).strip(),
        "read_policy": str(answers.get("memory_read_policy", "")).strip(),
        "sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),
        "compress_after_events": 20,
    }

# 记忆策略验证仅在启用记忆时强制检查后端。
def memory_policy_errors(answers: dict[str, Any]) -> list[str]:
    """验证项目记忆启用状态与后端选择的一致性。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        项目记忆策略错误列表。
    """

    # 禁用态不需要配置任何持久化后端。
    if not bool(answers.get("memory_enabled")):

        # 明确返回空错误列表，便于调用方直接合并。
        return []

    # 启用态读取用户明确选择的存储后端。
    str_backend = str(answers.get("memory_storage_backend", "")).strip()  # 用户选择的记忆后端

    # 启用态必须使用支持事件追踪与查询的组合后端。
    if str_backend != "sqlite-plus-jsonl":

        # 返回字段级错误以指导重新访谈。
        return ["memory_storage_backend must be sqlite-plus-jsonl when memory_enabled is true"]

    # 后端匹配时记忆策略有效。
    return []

# Git 合同固定发布前的分支和工作树约束。
def git_branch_policy() -> dict[str, Any]:
    """返回分支隔离与禁止额外 worktree 的 Git 合同。

    Args:
        None: Git 合同由仓库治理固定定义。

    Returns:
        Git 分支和工作树策略映射。
    """

    # 调用方将该映射直接写入设计档案。
    return {
        "protected_branches": ["master", "release"],
        "development_branches_allowed": True,
        "additional_worktrees_forbidden": True,
        "forbidden_worktree_directory_names": [
            ".worktrees",
            "worktrees",
            ".git-worktrees",
            "git-worktrees",
        ],
        "release_requires_committed_worktree": True,
        "release_requires_merge_to_master": True,
        "delete_other_local_branches_before_release": True,
        "release_prepare_auto_commit": True,
        "release_prepare_commit_message_template": "release-prepare: stage {branch} for {version}",
        "release_prepare_merge_message_template": "release-prepare: merge {branch} into master for {version}",
        "release_prepare_allowed_paths": ["<primary-project-root>", "tests", "docs", ".agents", "AGENTS.md", "dist"],
        "install_requires_release_artifact": True,
        "source_install_forbidden": True,
        "remote_branch_cleanup_allowed": False,
        "rule": (
            "Before releasing an installable dist package, commit all work, merge "
            "development branches into master, record the release, and delete local "
            "branches other than master and release."
        ),
    }

# 目录管理合同定义需要审查的变更边界。
def dir_manager_contract() -> dict[str, Any]:
    """返回目录变更审查、阻断与证据保存合同。

    Args:
        None: 目录管理合同由治理工具固定定义。

    Returns:
        目录管理器命令与策略映射。
    """

    # 固定合同供目录审查器和 AGENTS 渲染器共享。
    return {
        "folder": "docs/dir_manager",
        "current_structure": "docs/dir_manager/current_structure.json",
        "planned_structure": "docs/dir_manager/planned_structure.json",
        "history": "docs/dir_manager/history_dir_manager",
        "review_required_for": [
            "create top-level directories",
            "move directories",
            "delete directories",
            "rename directories",
            "change ownership, generated, release, or governance directories",
        ],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "archive_before_force_override": True,
    }

# 禁用远程服务器时使用稳定的空路由合同。
def disabled_remote_server_contract() -> dict[str, Any]:
    """返回无需远程依赖和验证的禁用态合同。

    Args:
        None: 禁用态合同没有外部输入。

    Returns:
        关闭远程任务路由的合同映射。
    """

    # 显式保留所有状态字段，避免消费方推断缺失值。
    return {
        "enabled": False,
        "dependency_required": False,
        "dependency_status": "not_required",
        "server_registry": [],
        "task_routes": [],
        "validation_required": False,
        "validation_status": "not_required",
        "unmatched_task_policy": "block-and-update-agents",
        "failover_policy": "auto-fallback",
        "enforce_remote_task_routing": False,
    }

# 旧版单服务器答案需要转换成当前任务路由结构。
def legacy_remote_answer_errors(
    answers: dict[str, Any],
    str_selected_id: str,
    str_selected_name: str,
) -> list[str]:
    """验证旧版远程选择的必填字段和确认状态。

    Args:
        answers: 当前设计访谈答案。
        str_selected_id: 用户选择的服务器标识。
        str_selected_name: 用户选择的服务器名称。

    Returns:
        阻止旧版答案迁移的字段错误。
    """

    # 各必填字段独立诊断，便于一次修正全部旧答案。
    list_errors: list[str] = []  # 旧版选择字段错误

    # 服务器标识用于关联实时注册记录。
    if not str_selected_id:

        # 缺失标识时返回对应访谈键。
        list_errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_ID_KEY}")

    # 名称用于生成可读的服务器注册表。
    if not str_selected_name:

        # 缺失名称时返回对应访谈键。
        list_errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_NAME_KEY}")

    # 用户必须显式确认所选服务器。
    if not bool(answers.get(REMOTE_SELECTION_CONFIRMED_KEY)):

        # 未确认选择不能进入实时验证。
        list_errors.append(
            f"{REMOTE_SELECTION_CONFIRMED_KEY} must be true when use_remote_server is enabled"
        )

    # 已验证状态证明选择流程完成了连通性检查。
    if str(answers.get(REMOTE_VALIDATION_STATUS_KEY, "")).strip().lower() != "verified":

        # 状态漂移时要求重新完成远程验证。
        list_errors.append(
            f"{REMOTE_VALIDATION_STATUS_KEY} must be verified when use_remote_server is enabled"
        )

    # 聚合结果供迁移函数决定是否读取实时服务器。
    return list_errors

# 实时服务器事实用于补齐并验证旧版选择字段。
def enrich_legacy_remote_selection(
    path_skill_dir: Path,
    dict_choices: dict[str, Any],
    dict_selection: dict[str, Any],
) -> list[str]:
    """使用实时服务器记录补齐旧版远程选择。

    Args:
        path_skill_dir: 已安装远程 SSH 技能目录。
        dict_choices: 远程技能提供的服务器选项。
        dict_selection: 可原位补齐的旧版选择字段。

    Returns:
        服务器存在性、连通性和工作目录错误。
    """

    # 服务器标识是关联实时注册记录的稳定键。
    str_selected_id = str(dict_selection["id"])  # 已规范化的服务器标识

    # 实时记录用于确认服务器没有被删除或改名。
    dict_record = remote_server_record(  # 服务器实时记录
        dict_choices.get("servers", []),  # 当前服务器选项
        str_selected_id,  # 待确认的服务器标识
    )

    # 已失效的选择需要用户重新完成服务器访谈。
    if dict_record is None:

        # 单一错误清楚标出无法关联的服务器标识。
        return [
            "selected remote server is no longer available in erie-remote-ssh "
            f"choices: {str_selected_id}"
        ]

    # 连通性检查确认服务器凭据和网络可用。
    dict_check_data, list_check_errors = remote_server_check(  # 连通性结果与错误
        path_skill_dir,  # 执行连通性命令的技能根
        str_selected_id,  # 连通性检查目标
    )

    # 工作目录检查确认远程运行根满足合同。
    dict_workspace_data, list_workspace_errors = remote_server_workspace_check(  # 工作目录结果与错误
        path_skill_dir,  # 执行目录探测的技能根
        str_selected_id,  # 工作目录检查目标
    )

    # 实时记录补齐旧答案可能缺少的展示字段。
    dict_selection["name"] = (  # 最终服务器名称
        dict_selection["name"] or str(dict_record.get("name", "")).strip()  # 名称答案优先
    )

    # 类别采用与名称相同的答案优先策略。
    dict_selection["category"] = (  # 最终服务器类别
        dict_selection["category"] or str(dict_record.get("category", "")).strip()  # 类别答案优先
    )

    # 未保存能力列表时使用服务器注册能力。
    if not dict_selection["functions"] and isinstance(dict_record.get("functions"), list):

        # 实时能力写回共享选择对象供路由生成使用。
        dict_selection["functions"] = normalize_remote_task_list(  # 最终能力列表
            dict_record.get("functions", [])  # 补齐缺失能力的实时来源
        )

    # 未指定任务时沿用服务器能力作为兼容任务。
    if not dict_selection["tasks"] and isinstance(dict_record.get("functions"), list):

        # 任务回退保证旧答案仍能生成明确路由。
        dict_selection["tasks"] = normalize_remote_task_list(  # 最终任务列表
            dict_record.get("functions", [])  # 推导兼容任务的能力来源
        )

    # 两类实时错误统一返回，检查数据只用于执行成功判定。
    return list_check_errors + list_workspace_errors

# 旧版迁移过程独立于当前格式路由，便于逐步淘汰兼容入口。
def legacy_remote_routes(
    path_skill_dir: Path,
    answers: dict[str, Any],
    dict_choices: dict[str, Any],
    list_registry: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """验证旧版远程选择答案并生成兼容任务路由。

    Args:
        path_skill_dir: 已安装远程 SSH 技能目录。
        answers: 当前设计访谈答案。
        dict_choices: 远程技能提供的服务器选项。
        list_registry: 已规范化的服务器注册表。

    Returns:
        任务路由、可能补全的注册表与错误列表。
    """

    # 服务器标识先去除空白以便关联注册记录。
    str_selected_id = str(  # 待迁移的服务器标识
        answers.get(REMOTE_SELECTED_SERVER_ID_KEY, "")  # 旧答案中的服务器标识
    ).strip()  # 去除标识首尾空白

    # 名称保留用于生成兼容注册记录。
    str_selected_name = str(  # 服务器名称
        answers.get(REMOTE_SELECTED_SERVER_NAME_KEY, "")  # 旧答案中的服务器名称
    ).strip()  # 规范化服务器名称

    # 类别可以从实时记录补齐。
    str_selected_category = str(  # 服务器类别
        answers.get(REMOTE_SELECTED_SERVER_CATEGORY_KEY, "")  # 旧答案中的服务器类别
    ).strip()  # 规范化服务器类别

    # 能力字段仅接受旧合同规定的列表形式。
    list_selected_functions = (  # 用户确认的服务器能力
        normalize_remote_task_list(  # 规范化旧版能力答案
            answers.get(REMOTE_SELECTED_SERVER_FUNCTIONS_KEY, [])  # 旧答案中的能力列表
        )
        if isinstance(answers.get(REMOTE_SELECTED_SERVER_FUNCTIONS_KEY, []), list)  # 仅列表有效
        else []  # 非列表能力答案按空列表处理
    )  # 规范化能力列表

    # 路由任务允许公共规范化器处理空值。
    list_selected_tasks = normalize_remote_task_list(  # 用户指定的路由任务
        answers.get(REMOTE_SELECTED_SERVER_TASKS_KEY, [])  # 旧答案中的路由任务
    )  # 规范化任务列表

    # 字段错误在远程调用前一次性收集。
    list_errors = legacy_remote_answer_errors(  # 旧版答案的字段和实时检查错误
        answers,  # 字段验证使用的完整答案
        str_selected_id,  # 必填标识验证值
        str_selected_name,  # 必填名称验证值
    )

    # 可变选择对象承载实时记录补齐后的最终字段。
    dict_selection = {  # 旧版服务器选择状态
        "id": str_selected_id,  # 实时记录关联键
        "name": str_selected_name,  # 可补齐的展示名称
        "category": str_selected_category,  # 可补齐的服务器类别
        "functions": list_selected_functions,  # 可补齐的能力列表
        "tasks": list_selected_tasks,  # 可补齐的任务列表
    }

    # 字段有效后再查询实时服务器记录和工作目录。
    if not list_errors:

        # 实时检查错误追加到字段错误列表。
        list_errors.extend(  # 聚合实时服务器错误
            enrich_legacy_remote_selection(path_skill_dir, dict_choices, dict_selection)
        )

    # 实时检查失败时不构造部分有效的路由。
    if list_errors:

        # 保留注册表并返回完整错误，禁止产生部分路由。
        return [], list_registry, list_errors

    # 过滤空能力名称，保持生成合同稳定。
    list_functions = [  # 路由能力
        str(item).strip()  # 当前规范化能力名称
        for item in dict_selection["functions"]  # 旧答案或实时记录中的能力
        if str(item).strip()  # 忽略空能力名称
    ]

    # 显式任务优先于能力推导结果。
    list_tasks = (  # 路由任务
        dict_selection["tasks"] or normalize_remote_task_list(list_functions)  # 显式任务优先
    )

    # 路由至少需要一个任务或能力标签。
    if not list_tasks:

        # 无路由目标时返回可操作的字段错误。
        return [], list_registry, [
            f"use_remote_server=true requires non-empty {REMOTE_SELECTED_SERVER_TASKS_KEY} "
            "or remote server functions"
        ]

    # 旧选择不在规范化注册表时补建兼容记录。
    if not list_registry and str_selected_id:

        # 新记录只包含后续路由解析所需的稳定字段。
        list_registry = [  # 补建的兼容服务器注册表
            {
                "id": str_selected_id,  # 注册记录稳定标识
                "name": dict_selection["name"],  # 最终展示名称
                "category": dict_selection["category"],  # 注册记录服务器类别
                "functions": list_functions,  # 最终能力清单
                "enabled": True,  # 补建记录保持启用
                "validation_status": "verified",  # 补建记录已通过实时验证
                "workspace_status": "ok",  # 补建记录的工作目录可用
            }
        ]

    # 单服务器旧答案映射成统一的默认任务路由。
    list_routes = [  # 兼容任务路由
        {
            "task_name": REMOTE_LEGACY_TASK_NAME,  # 兼容路由展示名称
            "task_key": normalize_remote_task_key(REMOTE_LEGACY_TASK_NAME),  # 规范化路由键
            "primary_server_id": str_selected_id,  # 旧选择的主服务器
            "fallback_server_ids": [],  # 旧合同没有回退服务器
            "route_tasks": list_tasks,  # 兼容路由任务集合
            "route_functions": list_functions,  # 兼容路由能力集合
            "selection_confirmed": True,  # 旧选择已由用户确认
            "validation_status": "verified",  # 旧选择已通过实时验证
        }
    ]

    # 返回兼容路由以及可能补建的注册表。
    return list_routes, list_registry, []

# 每条远程任务路由必须能解析到当前可用服务器。
def validate_remote_routes(
    path_skill_dir: Path,
    list_registry: list[dict[str, Any]],
    list_routes: list[dict[str, Any]],
) -> list[str]:
    """补齐路由能力并执行服务器解析验证。

    Args:
        path_skill_dir: 已安装远程 SSH 技能目录。
        list_registry: 当前服务器注册表。
        list_routes: 待验证的任务路由。

    Returns:
        所有路由验证错误。
    """

    # 聚合错误和注册索引在遍历前只初始化一次。
    list_errors: list[str] = []  # 所有路由的聚合错误

    # 注册索引支持按主服务器标识快速查询。
    dict_registry = server_registry_map(list_registry)  # 按服务器标识索引的注册表

    # 独立验证各路由，确保一次报告全部无效选择。
    for dict_route in list_routes:

        # 先检查路由声明引用的所有服务器标识。
        list_errors.extend(validate_route_server_ids(dict_route, dict_registry))

        # 主服务器记录用于补齐路由能力。
        dict_primary_server = dict_registry.get(  # 主服务器注册记录
            str(dict_route.get("primary_server_id", "")).strip(),  # 主服务器标识
            {},  # 未找到时使用空记录
        )

        # 非映射记录不能提供任何服务器能力。
        list_primary_functions = (  # 主服务器声明的能力
            normalize_remote_task_list(dict_primary_server.get("functions", []))  # 规范化能力
            if isinstance(dict_primary_server, dict)  # 仅映射记录可读取能力
            else []  # 非映射主服务器不提供能力
        )

        # 缺省任务和能力从主服务器事实补齐。
        if not dict_route.get("route_tasks"):

            # 无显式任务时使用主服务器能力或任务名称。
            dict_route["route_tasks"] = list_primary_functions or [  # 最终路由任务
                str(dict_route.get("task_name", "")).strip()  # 任务名称兜底
            ]

        # 能力为空时沿用主服务器能力清单。
        if not dict_route.get("route_functions"):

            # 能力补齐结果原位写入当前路由。
            dict_route["route_functions"] = list_primary_functions  # 最终路由能力

        # 实时解析证明主服务器或回退服务器当前可用。
        dict_resolution = resolve_remote_server_for_task(  # 当前路由的实时解析结果
            {
                "enabled": True,  # 临时解析合同启用远程路由
                "server_registry": list_registry,  # 当前服务器事实
                "task_routes": [dict_route],  # 单条待验证路由
                "unmatched_task_policy": "block-and-update-agents",  # 未匹配任务阻断
                "failover_policy": "auto-fallback",  # 主服务器失败时自动回退
            },
            str(dict_route.get("task_name", "")),  # 待解析任务名称
            path_skill_dir,  # 远程技能目录
        )

        # 解析失败信息进入统一错误列表。
        if not dict_resolution.get("ok"):

            # 解析器的详细失败优先于通用兜底消息。
            list_errors.extend(
                dict_resolution.get("failures", [])
                or [str(dict_resolution.get("message", "remote route validation failed"))]
            )

        # 成功解析证明当前选择已确认且路由可用。
        else:

            # 首先记录用户选择已经通过实时解析。
            dict_route["selection_confirmed"] = True  # 当前选择已确认

            # 随后标记路由验证门禁已经通过。
            dict_route["validation_status"] = "verified"  # 当前路由已验证

    # 调用方据此决定是否输出启用态合同。
    return list_errors

# 远程服务器合同协调依赖检查、兼容迁移和实时路由验证。
def remote_server_contract(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """验证远程服务器选择并构造任务路由合同。

    Args:
        project: 受管项目根目录。
        answers: 当前设计访谈答案。

    Returns:
        远程服务器选择合同与验证错误列表。
    """

    # 启用开关决定是否需要读取外部远程技能。
    bool_enabled = use_remote_server_enabled(answers)  # 是否启用远程任务路由

    # 禁用态不读取外部技能或服务器配置。
    if not bool_enabled:

        # 返回字段完整的禁用态合同。
        return disabled_remote_server_contract(), []

    # 安装摘要提供技能目录和依赖状态。
    dict_dependency = remote_dependency_summary()  # 远程 SSH 技能安装状态

    # 启用态必须依赖可用的远程 SSH 技能。
    if not dict_dependency["installed"]:

        # 缺失依赖时提供安装来源以便修复。
        return {}, [
            f"use_remote_server=true requires installed {REMOTE_SSH_SKILL_NAME} "
            f"({REMOTE_SSH_GIT_URL})"
        ]

    # 依赖有效后读取服务器选项与现有路由。
    path_skill_dir = Path(str(dict_dependency["skill_dir"]))  # 已安装远程技能目录

    # 服务器选项读取同时返回可展示记录和配置错误。
    dict_choices, list_choice_errors = remote_choices(path_skill_dir)  # 远程技能发现结果

    # 无选项错误时才规范化服务器记录。
    list_registry = (  # 规范化服务器注册表
        normalize_remote_server_registry(dict_choices.get("servers", []))  # 规范化当前服务器记录
        if not list_choice_errors  # 选项读取成功后才建立注册表
        else []  # 选项读取失败时不生成注册记录
    )

    # 当前格式路由优先于旧版单服务器字段。
    list_routes = normalize_remote_task_routes(  # 当前格式的任务路由
        answers.get(REMOTE_SERVER_TASK_ROUTES_KEY, [])  # 当前格式路由答案
    )

    # 没有当前格式路由时兼容迁移旧版单服务器答案。
    if not list_routes:

        # 迁移结果先整体保存，再按合同顺序解包。
        tuple_legacy_result = legacy_remote_routes(  # 兼容迁移结果
            path_skill_dir,  # 已安装远程技能根
            answers,  # 需要迁移的访谈答案
            dict_choices,  # 兼容迁移使用的服务器发现结果
            list_registry,  # 当前规范化注册表
        )

        # 第一分量替换空路由集合。
        list_routes = tuple_legacy_result[0]  # 迁移生成的任务路由

        # 第二分量可能包含旧服务器补建记录。
        list_registry = tuple_legacy_result[1]  # 兼容服务器注册表

        # 第三分量决定迁移是否可以进入实时解析。
        list_legacy_errors = tuple_legacy_result[2]  # 兼容迁移错误

    # 已有当前格式路由时跳过兼容迁移。
    else:

        # 空列表保持后续错误聚合路径一致。
        list_legacy_errors = []  # 空兼容迁移错误

    # 选项读取、兼容迁移和实时解析错误统一返回。
    # 合并服务器选项和旧版迁移错误。
    list_errors = list_choice_errors + list_legacy_errors  # 当前合同的全部验证错误

    # 实时路由解析错误追加到同一列表。
    list_errors.extend(validate_remote_routes(path_skill_dir, list_registry, list_routes))

    # 任何错误都阻止输出看似可用的启用态合同。
    if list_errors:

        # 不泄露部分有效的远程合同。
        return {}, list_errors

    # 全部依赖和路由通过后生成远程执行合同。
    return {
        "enabled": True,
        "dependency_required": True,
        "dependency_status": "installed",
        "server_registry": list_registry,
        "task_routes": list_routes,
        "validation_required": True,
        "validation_status": "verified",
        "unmatched_task_policy": "block-and-update-agents",
        "failover_policy": "auto-fallback",
        "enforce_remote_task_routing": True,
    }, []
