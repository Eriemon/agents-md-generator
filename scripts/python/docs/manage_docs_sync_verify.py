"""同步并校验 AGENTS、全局 baseline、文档治理和工作区状态。"""

# 延迟注解求值，保持 Python 3.10 运行兼容性。
from __future__ import annotations

# 标准库负责环境读取、文本匹配、子进程调用、路径和类型注解。
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

# 显式导入同步与验证流程依赖的共享文档治理合同。
from manage_docs_shared import (
    # 文档结构、全局 baseline 和 handoff 常量。
    DOC_DIRS,
    GLOBAL_CODEX_AGENTS_BLOCK_END,
    GLOBAL_CODEX_AGENTS_BLOCK_START,
    GLOBAL_CODEX_AGENTS_PREAMBLE,
    HANDOFF_SECTIONS,
    LAST_UPDATED_HEADER_RE,
    LOCAL_PRIVATE_PATH_RE,
    REQUIRED_DOC_FILES,

    # 文档命名、时间和初始化状态函数。
    audit_handoff_naming,
    control_profile,
    current_timestamp,
    docs_governance_initialized,

    # 根入口覆盖文件与全局路径函数。
    ensure_global_rule_overrides_file,
    global_codex_agents_path,
    global_codex_agents_status,
    global_codex_agents_sync_command,

    # 治理脚本定位、元数据和版本函数。
    governance_script_path,
    parse_agents_metadata,
    preferred_skill_version,
    project_profile,
    read_skill_version,

    # 全局模板、同步命令和内容验证函数。
    render_global_codex_agents_template,
    root_agents_sync_command,
    validate_development_record,
    verify_dir_manager,
)
from source_governance import format_source_governance_errors, source_governance_report
from codebase_memory_mcp import enforce_codebase_memory_write_gate

# 版本表达式用于对齐 AGENTS、开发记录和发布文档。
VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")  # 语义版本匹配器

# 全局入口元数据必须明确声明受管 baseline 身份。
GLOBAL_CODEX_AGENTS_META_LINE_RE = re.compile(  # baseline 元数据匹配器
    r"^<!--\s*AGENTS-GENERATED:META\b.*\bbaseline=global-codex-baseline\b.*-->$"  # 受管元数据行
)

# 控制档案区块优先承载目标项目的 skill 版本。
CONTROL_PROFILE_BLOCK_RE = re.compile(  # 受管控制档案区块匹配器
    r"(<!--\s*AGENTS-GENERATED:START\s+control-profile\s*-->)"  # 区块起始标记
    r"(.*?)"  # 可更新的控制档案正文
    r"(<!--\s*AGENTS-GENERATED:END\s+control-profile\s*-->)",  # 区块结束标记
    flags=re.DOTALL | re.IGNORECASE,  # 跨行并兼容历史大小写
)

# 旧版项目区块仍是控制档案版本的兼容读取位置。
PROJECT_BLOCK_RE = re.compile(  # 受管项目区块匹配器
    r"(<!--\s*AGENTS-GENERATED:START\s+project\s*-->)"  # 旧项目区块开头
    r"(.*?)"  # 历史项目档案正文
    r"(<!--\s*AGENTS-GENERATED:END\s+project\s*-->)",  # 旧项目区块结尾
    flags=re.DOTALL | re.IGNORECASE,  # 兼容历史区块的跨行大小写
)

# 版本替换只命中受管区块中的标准 Version 行。
CONTROL_PROFILE_VERSION_RE = re.compile(  # 控制档案版本行匹配器
    r"^-\s+Version:\s*(v\d+\.\d+\.\d+)\.$",  # 标准版本字段
    flags=re.MULTILINE,  # 逐行定位字段
)

# 文档隐私审计覆盖可能记录本地运行信息的治理目录。
DOCS_PRIVACY_ROOTS = [  # 隐私审计相对目录
    "docs/handoff",  # 会话交接记录
    "docs/development",  # 开发过程记录
    "docs/install_configuration",  # 本地安装配置
    "docs/git_manager",  # Git 治理记录
    "docs/dir_manager",  # 目录治理记录
]

# 仅扫描可以安全按文本解码的治理文件。
DOCS_PRIVACY_TEXT_SUFFIXES = {  # 仅这些可解码格式参与 LOCAL_PRIVATE_PATH_RE 泄漏检查
    ".json",  # 可解码的 JSON 治理状态
    ".jsonl",  # 可逐行扫描的事件记录
    ".md",  # 可能承载本地路径的 Markdown 文档
    ".txt",  # 可能记录命令输出的纯文本
    ".yaml",  # 可解码的 YAML 治理配置
    ".yml",  # YAML 配置采用的简写后缀
}

# 从显式参数、控制档案或唯一候选目录解析目标 skill。
def inferred_skill_dir(project: Path, raw_skill_dir: str | Path | None = None) -> Path | None:
    """解析项目中需要参与版本治理的 skill 目录。

    参数：project 为项目根目录，raw_skill_dir 为可选显式 skill 路径。
    返回：解析后的绝对目录；无法唯一确定时返回 None。
    """

    # 显式路径具有最高优先级，并允许以项目根为基准传入相对路径。
    if raw_skill_dir:

        # 路径对象统一承载绝对化和规范化处理。
        path_candidate = Path(raw_skill_dir)  # 显式 skill 路径候选

        # 相对路径必须绑定当前项目，避免依赖调用进程工作目录。
        if not path_candidate.is_absolute():

            # 项目根限定显式相对路径的解释边界。
            path_candidate = project / path_candidate  # 项目内 skill 候选

        # 调用方获得规范化的确定路径。
        return path_candidate.resolve()

    # 控制档案记录的 skill 布局是无显式参数时的主要事实来源。
    profile = project_profile(project)  # 项目控制档案

    # 只有结构化控制档案才能参与布局解析。
    if isinstance(profile, dict):

        # 非字典布局按空配置处理，防止畸形控制档案传播类型错误。
        layout = profile.get("skill_layout") if isinstance(profile.get("skill_layout"), dict) else {}  # skill 布局配置

        # 布局中的 path 可以直接定位多 skill 仓库里的目标目录。
        raw_path = str(layout.get("path") or "").strip()  # 配置中的 skill 相对路径

        # 已配置路径无需再猜测目录名称。
        if raw_path:

            # 控制档案路径始终相对项目根解释。
            return (project / raw_path).resolve()

        # 缺少路径时使用项目身份名称尝试标准 skills 布局。
        name = str(profile.get("name") or "").strip()  # 控制档案项目名称

        # 空名称不能构成可靠目录候选。
        if name:

            # 标准 skill 仓库约定目标位于 skills/<name>。
            path_candidate = project / "skills" / name  # 标准布局候选

            # 只接受实际存在的标准布局目录。
            if path_candidate.exists():

                # 存在的标准候选可以作为版本事实来源。
                return path_candidate.resolve()

    # 最后允许仅含一个 VERSION 候选的简单仓库自动推断。
    skills_root = project / "skills"  # 标准 skills 根目录

    # 不存在 skills 根时无法继续目录枚举。
    if skills_root.is_dir():

        # VERSION 文件将普通目录与可发布 skill 区分开。
        candidates = [path for path in skills_root.iterdir() if (path / "VERSION").is_file()]  # 带版本的 skill 候选

        # 多候选仓库必须由显式路径或控制档案消除歧义。
        if len(candidates) == 1:

            # 唯一候选具备足够的自动推断确定性。
            return candidates[0].resolve()

    # 保留无法唯一解析的状态供上层决定是否跳过或报错。
    return None

# 提取文本中首个标准语义版本。
def first_version(text: str) -> str:
    """读取文本中首个 vX.Y.Z 版本。

    参数：text 为待扫描文本。
    返回：首个匹配版本；未找到时返回空字符串。
    """

    # 共享版本表达式保持各文档检查语义一致。
    match = VERSION_RE.search(text)  # 首个版本匹配结果

    # 空匹配以空字符串表达，便于上层选择跳过比较。
    return match.group(0) if match else ""

# 截取 Git 管理文档中的当前版本章节。
def current_version_section(text: str) -> str:
    """提取 Current Version 二级标题下的正文。

    参数：text 为 Git 管理文档内容。
    返回：当前版本章节正文；标题缺失时返回空字符串。
    """

    # 标题必须独占一行，避免误读正文中的同名短语。
    match = re.search(r"^##\s+Current Version\s*$", text, flags=re.MULTILINE)  # 当前版本标题匹配

    # 缺少正式章节时不从其他位置猜测版本语义。
    if not match:

        # 空值通知调用方跳过该章节检查。
        return ""

    # 标题后的剩余文本用于定位下一个同级章节边界。
    rest = text[match.end() :]  # 当前标题之后的文本

    # 下一个二级标题结束当前版本章节。
    next_section = re.search(r"^##\s+", rest, flags=re.MULTILINE)  # 后续二级标题匹配

    # 文档末尾没有后续标题时保留全部剩余正文。
    return rest[: next_section.start()] if next_section else rest

# 读取受管控制档案或兼容项目区块中的版本字段。
def managed_control_profile_version(text: str) -> str:
    """读取受管 AGENTS 区块声明的项目 skill 版本。

    参数：text 为 AGENTS.md 内容。
    返回：受管区块中的版本；区块或字段缺失时返回空字符串。
    """

    # 新控制档案优先，旧项目区块仅作为兼容回退。
    block_match = CONTROL_PROFILE_BLOCK_RE.search(text) or PROJECT_BLOCK_RE.search(text)  # 受管区块匹配

    # 不读取受管区块外的同名字段，避免改动人工内容。
    if not block_match:

        # 空值表示当前文档没有可治理的版本字段。
        return ""

    # 只在受管正文中搜索标准版本行。
    version_match = CONTROL_PROFILE_VERSION_RE.search(block_match.group(2))  # 受管版本字段匹配

    # 字段缺失与区块缺失统一返回空字符串。
    return version_match.group(1) if version_match else ""

# 在受管区块内替换项目 skill 版本，不触碰人工正文。
def replace_managed_control_profile_version(text: str, version: str) -> str:
    """更新受管控制档案的 Version 字段。

    参数：text 为 AGENTS.md 内容，version 为目标语义版本。
    返回：替换后的完整文本；没有可替换字段时保持原文。
    """

    # 内部替换器保留区块标记，仅更新正文中的首个版本字段。
    def replace_block(match: re.Match[str]) -> str:
        """替换单个受管区块的版本字段。

        参数：match 为完整受管区块匹配。
        返回：保留边界标记的更新区块。
        """

        # count=1 防止畸形区块中的重复字段被批量重写。
        body = CONTROL_PROFILE_VERSION_RE.sub(  # 更新后的受管正文
            f"- Version: {version}.",  # 目标版本字段
            match.group(2),  # 原受管正文
            count=1,  # 只更新首个标准字段
        )

        # 区块起止标记必须原样保留。
        return f"{match.group(1)}{body}{match.group(3)}"

    # 优先更新新版 control-profile 区块。
    updated = CONTROL_PROFILE_BLOCK_RE.sub(replace_block, text, count=1)  # 新版区块替换结果

    # 新版区块发生变化时无需再触碰兼容区块。
    if updated != text:

        # 返回仅包含目标区块变化的完整文档。
        return updated

    # 旧项目区块提供历史仓库的最小兼容路径。
    return PROJECT_BLOCK_RE.sub(replace_block, text, count=1)

# 读取项目目标 skill 的版本及其来源。
def project_skill_version(project: Path, skill_dir_raw: str | Path | None = None) -> tuple[str, str, Path | None]:
    """解析项目 skill 目录并读取 VERSION。

    参数：project 为项目根目录，skill_dir_raw 为可选目标目录。
    返回：版本、来源标签和解析后的 skill 目录。
    """

    # 统一目录推断保证后续版本文件与报告路径指向同一目标。
    skill_dir = inferred_skill_dir(project, skill_dir_raw)  # 目标 skill 目录

    # 无法解析目录时保持可跳过状态，不伪造版本。
    if not skill_dir:

        # unavailable 明确区分无版本与版本不匹配。
        return "", "unavailable", None

    # VERSION 文件是项目 skill 版本的唯一事实来源。
    version = read_skill_version(skill_dir)  # 项目 skill 版本

    # 空 VERSION 保留已解析目录，便于调用方给出准确诊断。
    if not version:

        # 目录存在但缺少有效版本时仍标记 unavailable。
        return "", "unavailable", skill_dir

    # 正常结果标记为 project-skill，区别于 installed fallback。
    return version, "project-skill", skill_dir

# 选择根 AGENTS 元数据版本，同时保留项目 skill 版本供控制档案使用。
def root_metadata_version(
    project: Path,
    installed_skill_dir_override: str | Path | None = None,
) -> tuple[str, str, str, str, Path | None]:
    """解析根元数据版本和目标项目 skill 版本。

    参数：project 为项目根目录，installed_skill_dir_override 为可选安装副本。
    返回：元数据版本及来源、项目版本及来源、项目 skill 目录。
    """

    # 项目 VERSION 独立于生成器安装副本，决定控制档案中的业务版本。
    (
        tuple_project_version,  # 控制档案需要对齐的 VERSION 值
        tuple_project_version_source,  # VERSION 值的项目事实来源
        tuple_project_skill_dir,  # 提供 VERSION 文件的目录
    ) = project_skill_version(project)

    # owner 仓库自身可直接用项目 VERSION 同时校验生成器元数据。
    if (
        installed_skill_dir_override is None
        and tuple_project_skill_dir
        and tuple_project_skill_dir.name == "agents-md-generator"
    ):

        # 同一目录提供元数据和项目控制档案的版本事实。
        return (
            tuple_project_version,  # 根元数据期望版本
            tuple_project_version_source,  # 根元数据版本来源
            tuple_project_version,  # 项目控制档案版本
            tuple_project_version_source,  # owner 元数据版本来源
            tuple_project_skill_dir,  # owner skill 目录
        )

    # 外部项目使用安装副本版本校验生成器元数据。
    metadata_version, version_source = preferred_skill_version(  # 生成器元数据版本与来源
        override_dir=installed_skill_dir_override  # 可选安装副本覆盖
    )

    # 两套版本事实分别服务生成器元数据和目标项目控制档案。
    return (
        metadata_version,  # 外部项目根元数据的生成器版本
        version_source,  # 安装副本或覆盖目录来源
        tuple_project_version,  # 外部项目控制档案的业务版本
        tuple_project_version_source,  # 外部项目 VERSION 的读取来源
        tuple_project_skill_dir,  # 被治理的外部 skill 位置
    )

# 校验项目 VERSION 与所有声明当前版本的受管文档一致。
def version_alignment_gate(project: Path, skill_dir_raw: str | Path | None = None) -> dict[str, Any]:
    """核对项目 skill 版本与 AGENTS 和发布记录的一致性。

    参数：project 为项目根目录，skill_dir_raw 为可选目标 skill 路径。
    返回：检查范围、版本来源、错误清单和最终结论。
    """

    # 目标 skill VERSION 是本门禁的比较基准。
    tuple_expected, tuple_version_source, tuple_skill_dir = project_skill_version(  # 版本基准与目录
        project,  # 当前项目根
        skill_dir_raw,  # 可选显式 skill 路径
    )

    # 检查路径写入报告，便于判断门禁覆盖范围。
    list_checked: list[str] = []  # 已检查相对路径

    # 所有不一致一次收集，避免调用方逐项重跑。
    list_errors: list[str] = []  # 版本对齐错误

    # 缺少 VERSION 时保持兼容跳过，并明确记录原因。
    if not tuple_expected:

        # 跳过结果不能伪装成已检查的版本对齐证明。
        return {
            "project": str(project),  # 项目根目录
            "skill_dir": str(tuple_skill_dir) if tuple_skill_dir else "",  # 已解析目标目录
            "expected_version": "",  # 没有可比较版本
            "version_source": tuple_version_source,  # 版本缺失来源
            "checked": list_checked,  # 实际检查范围为空
            "errors": [],  # 兼容跳过不产生错误
            "ok": True,  # 保持旧项目可运行
            "skipped": "no skill VERSION found",  # 跳过原因
        }

    # VERSION 文件本身必须出现在覆盖清单中。
    version_path = tuple_skill_dir / "VERSION"  # 项目版本文件

    # 项目内路径优先报告为稳定的相对路径。
    if tuple_skill_dir.is_relative_to(project):

        # 相对路径使报告在不同机器之间可比较。
        str_checked_version_path = str(version_path.relative_to(project).as_posix())  # 项目内 VERSION 路径

    # 外部显式 skill 目录必须保留绝对路径避免歧义。
    else:

        # 绝对路径准确指向项目边界外的版本事实。
        str_checked_version_path = str(version_path)  # 外部 VERSION 路径

    # 首先登记版本事实文件本身。
    list_checked.append(str_checked_version_path)

    # 根 AGENTS 的控制档案版本属于正式对齐范围。
    agents = project / "AGENTS.md"  # 版本声明所在的根规则文件

    # 缺少根文件由其他治理门禁处理，本函数只校验存在的声明。
    if agents.is_file():

        # 根文件已实际读取，加入覆盖清单。
        list_checked.append("AGENTS.md")

        # 容错解码保证历史文档中的坏字符不会中止版本审计。
        agents_text = agents.read_text(encoding="utf-8", errors="ignore")  # 用于提取控制档案版本的规则文本

        # 控制档案的标准 Version 字段承载项目 skill 版本。
        control_match = re.search(  # AGENTS 控制档案中待与 tuple_expected 比较的版本匹配项
            r"^-\s+Version:\s*(v\d+\.\d+\.\d+)",  # 控制档案版本行格式
            agents_text,  # 已读取的根规则全文
            flags=re.MULTILINE,  # 允许从完整 Markdown 中逐行定位
        )

        # 仅当文件实际声明版本时比较，缺失字段由 AGENTS 验证器处理。
        if control_match and control_match.group(1) != tuple_expected:

            # 错误同时报告实际值和 VERSION 基准。
            list_errors.append(
                f"AGENTS.md control profile version {control_match.group(1)} "
                f"does not match project skill VERSION {tuple_expected}"
            )

    # 开发记录和变更日志的首个版本应跟随项目 VERSION。
    list_docs_checks = [  # 常规版本文档及诊断标签
        ("docs/development/DEVELOPMENT.md", "development record"),  # 开发记录
        ("docs/git_manager/CHANGELOG.md", "changelog"),  # 变更日志
    ]

    # 逐个检查实际存在的常规版本文档。
    for rel_path, label in list_docs_checks:

        # 相对路径统一绑定项目根。
        path = project / rel_path  # 当前版本文档路径

        # 可选文档不存在时交由文档结构门禁处理。
        if not path.is_file():

            # 当前门禁继续检查其他已有版本声明。
            continue

        # 记录已读取文档以证明覆盖范围。
        list_checked.append(rel_path)

        # 常规文档以首个标准版本作为当前声明。
        str_actual = first_version(path.read_text(encoding="utf-8", errors="ignore"))  # 文档声明版本

        # 空声明不在此处重复报错，已有但不一致才属于版本漂移。
        if str_actual and str_actual != tuple_expected:

            # 诊断保留文档角色，便于调用方定位修复位置。
            list_errors.append(
                f"{rel_path} {label} version {str_actual} "
                f"does not match project skill VERSION {tuple_expected}"
            )

    # Git 管理说明只比较 Current Version 正式章节。
    git_manager = project / "docs" / "git_manager" / "GIT_MANAGER.md"  # Git 管理说明路径

    # 可选 Git 管理说明存在时才读取章节。
    if git_manager.is_file():

        # 将章节检查纳入可审计覆盖清单。
        list_checked.append("docs/git_manager/GIT_MANAGER.md")

        # 先隔离当前版本章节，再从中提取语义版本。
        str_actual = first_version(  # Git 管理文档当前版本
            current_version_section(  # 当前版本章节正文
                git_manager.read_text(encoding="utf-8", errors="ignore")  # Git 管理文档内容
            )
        )

        # 历史章节中的旧版本不会触发当前版本漂移。
        if str_actual and str_actual != tuple_expected:

            # 当前章节漂移需要显式指向项目 VERSION 基准。
            list_errors.append(
                f"docs/git_manager/GIT_MANAGER.md current version {str_actual} "
                f"does not match project skill VERSION {tuple_expected}"
            )

    # 汇总完整覆盖范围和所有发现的不一致。
    return {
        "project": str(project),  # 执行版本对齐审计的仓库位置
        "skill_dir": str(tuple_skill_dir),  # 提供权威 VERSION 的 skill 位置
        "expected_version": tuple_expected,  # VERSION 基准
        "version_source": tuple_version_source,  # 版本来源标签
        "checked": list_checked,  # 已检查路径
        "errors": list_errors,  # 版本漂移清单
        "ok": not list_errors,  # 无漂移时通过
    }

# 生成根 AGENTS 同步失败时的稳定报告结构。
def _root_sync_error(
    project: Path,
    agents_path: Path,
    repair_command: str,
    message: str,
    *,
    version_context: tuple[str, str, str, Path | None] = ("unavailable", "", "unavailable", None),
) -> dict[str, Any]:
    """构造无法执行根元数据同步时的报告。

    参数：project 为项目根，agents_path 为目标文件，repair_command 为修复命令。
    参数：message 为阻断原因，version_context 汇总生成器与项目版本事实。
    返回：与正常同步报告兼容的失败字典。
    """

    # 版本上下文保持与正常报告相同的字段顺序。
    tuple_version_source, tuple_project_version, tuple_project_source, tuple_project_dir = version_context  # 失败报告所需的四项版本事实

    # 失败报告保留已知事实，同时明确没有执行写入。
    return {
        "project": str(project),  # 无法同步的项目根
        "agents_path": str(agents_path),  # 目标 AGENTS 路径
        "expected_version": "",  # 当前没有可用元数据版本
        "version_source": tuple_version_source,  # 生成器元数据版本的解析状态
        "project_skill_version": tuple_project_version,  # 失败前获得的业务 VERSION 值
        "project_version_source": tuple_project_source,  # 业务版本对应的事实来源
        "project_skill_dir": str(tuple_project_dir) if tuple_project_dir else "",  # VERSION 文件所在目录
        "sync_required": False,  # 无法计算可靠同步需求
        "updated": False,  # 未发生文件写入
        "reasons": [],  # 没有可用漂移分类
        "errors": [message],  # 阻断同步的准确原因
        "repair_command": repair_command,  # 建议修复命令
    }

# 根据根文件元数据和项目版本事实收集同步原因。
def _root_sync_reasons(
    text: str,
    metadata_version: str,
    project_version: str,
) -> tuple[list[str], str, str, str]:
    """分析根 AGENTS 的时间戳、元数据和控制档案版本。

    参数：text 为根文件内容，metadata_version 和 project_version 为版本基准。
    返回：同步原因、原更新时间、原验证时间和默认语言。
    """

    # 结构化元数据决定版本与语言字段是否完整。
    metadata = parse_agents_metadata(text)  # 根 AGENTS 元数据

    # 时间头同时承载更新时间和最近验证时间。
    last_updated_match = LAST_UPDATED_HEADER_RE.search(text)  # 时间头匹配

    # 缺少时间头时使用空值触发补写。
    last_updated_raw = last_updated_match.group(1).strip() if last_updated_match else ""  # 原更新时间

    # 历史文件没有验证时间时沿用 never 语义。
    last_verified = last_updated_match.group(2).strip() if last_updated_match else "never"  # 原验证时间

    # 空语言字段回退中文，但仍由原因清单要求补齐元数据。
    default_language = metadata.get("default_language", "中文").strip() or "中文"  # 根默认语言

    # 原因顺序保持稳定，便于测试和调用方展示。
    list_reasons: list[str] = []  # 根元数据漂移原因

    # 缺失时间头需要插入标准受管行。
    if not last_updated_match:

        # 使用稳定代码表达缺失类型。
        list_reasons.append("missing_last_updated_header")

    # 旧日期格式没有 ISO 时间分隔符，需要规范化。
    elif "T" not in last_updated_raw:

        # 单独分类兼容格式漂移。
        list_reasons.append("legacy_last_updated_format")

    # agents_version 必须存在并等于当前生成器版本。
    if not metadata.get("agents_version"):

        # 缺失与不匹配使用不同修复原因。
        list_reasons.append("missing_agents_version")

    # 已声明的旧 agents_version 需要同步升级。
    elif metadata.get("agents_version") != metadata_version:

        # 版本漂移保留独立诊断代码。
        list_reasons.append("agents_version_mismatch")

    # generator_version 同样必须显式存在。
    if not metadata.get("generator_version"):

        # 缺失生成器字段会使来源无法审计。
        list_reasons.append("missing_generator_version")

    # 生成器字段必须跟随当前元数据版本。
    elif metadata.get("generator_version") != metadata_version:

        # 旧生成器版本需要重写受管元数据行。
        list_reasons.append("generator_version_mismatch")

    # 默认语言是强控制项目的必填元数据。
    if not metadata.get("default_language"):

        # 缺失时补入已经计算的语言回退值。
        list_reasons.append("missing_default_language")

    # 受管控制档案版本独立跟随目标项目 VERSION。
    str_control_profile_version = managed_control_profile_version(text)  # 当前受管档案的项目版本

    # 只有两端版本都存在时判断控制档案漂移。
    if project_version and str_control_profile_version and str_control_profile_version != project_version:

        # 项目版本漂移不能用生成器版本替代。
        list_reasons.append("control_profile_version_mismatch")

    # 调用方需要原时间与语言来构造幂等更新。
    return list_reasons, last_updated_raw, last_verified, default_language

# 重写受管时间头和元数据行，并按需更新控制档案版本。
def _rewrite_root_agents(
    str_text: str, metadata_version: str, project_version: str,
    default_language: str, timestamps: tuple[str, str],
    *,
    sync_required: bool,
    mark_verified: bool,
) -> str:
    """生成同步后的根 AGENTS 文本。

    参数：str_text 为原文，metadata_version 和 project_version 为两类版本。
    参数：default_language 为语言，timestamps 保存原更新时间和验证时间。
    参数：sync_required 和 mark_verified 控制两个时间戳的刷新行为。
    返回：规范化且以换行结尾的完整根文件文本。
    """

    # 时间二元组来自同一次根文件分析，避免字段交叉混用。
    last_updated_raw, last_verified = timestamps  # 原更新时间与最近验证时间

    # 发生漂移或缺少原时间时刷新更新时间，否则保持原值。
    updated_raw = current_timestamp() if sync_required or not last_updated_raw else last_updated_raw  # 新更新时间

    # 只有显式 mark_verified 才刷新验证时间。
    verified_raw = current_timestamp() if mark_verified else last_verified  # 新验证时间

    # 标准时间头合并两个生命周期时间戳。
    new_last_line = f"<!-- Last updated: {updated_raw} | Last verified: {verified_raw} -->"  # 新时间头

    # 根元数据同时声明生成器兼容版本和默认对话语言。
    new_metadata_line = (  # 新 AGENTS 元数据行
        f"<!-- AGENTS-METADATA: agents_version={metadata_version}; "  # AGENTS 兼容版本
        f"generator_version={metadata_version}; default_language={default_language} -->"  # 生成器与语言
    )

    # 项目控制档案只在现有受管字段与 VERSION 不一致时更新。
    str_control_profile_version = managed_control_profile_version(str_text)  # 重写前受管档案版本

    # 版本存在且漂移时执行受管区块内的外科式替换。
    if project_version and str_control_profile_version and str_control_profile_version != project_version:

        # 替换函数保证受管区块之外的正文保持不变。
        str_text = replace_managed_control_profile_version(str_text, project_version)  # 已对齐项目版本的规则文本

    # 逐行去重并替换已有受管头部。
    list_rewritten: list[str] = []  # 重写后的文件行

    # 两个标志防止畸形文件中的重复头被重复保留。
    bool_last_inserted = False  # 是否已写入时间头

    # 元数据行与时间头分别去重。
    bool_metadata_inserted = False  # 是否已写入元数据行

    # 按原顺序保留所有非受管头部正文。
    for line in str_text.splitlines():

        # 去除首尾空白仅用于识别受管注释行。
        stripped = line.strip()  # 当前行识别文本

        # 第一个旧时间头替换为新值，其余重复项删除。
        if stripped.startswith("<!-- Last updated:"):

            # 尚未写入时在原位置保留标准时间头。
            if not bool_last_inserted:

                # 新时间头取代第一个旧时间头。
                list_rewritten.append(new_last_line)

                # 标记阻止后续重复时间头进入结果。
                bool_last_inserted = True  # 时间头已写入

            # 旧时间头行本身不再保留。
            continue

        # 第一个旧元数据行替换为当前版本与语言。
        if stripped.startswith("<!-- AGENTS-METADATA:"):

            # 尚未写入时在原位置保留标准元数据。
            if not bool_metadata_inserted:

                # 新元数据行取代第一个旧值。
                list_rewritten.append(new_metadata_line)

                # 标记阻止后续重复元数据进入结果。
                bool_metadata_inserted = True  # 元数据已写入

            # 旧元数据行本身不再保留。
            continue

        # 普通正文和其他受管区块保持原顺序。
        list_rewritten.append(line)

    # 缺失的受管头插入到文件顶部连续注释之后。
    if not bool_last_inserted or not bool_metadata_inserted:

        # 插入位置越过现有文件级注释头。
        int_insert_at = 0  # 受管头插入索引

        # 连续 HTML 注释构成原文件头，不应被拆开。
        while int_insert_at < len(list_rewritten) and list_rewritten[int_insert_at].startswith("<!--"):

            # 向后移动直到首个非注释行。
            int_insert_at += 1  # 下一条候选头部位置

        # 仅收集当前缺失的头部，保持操作幂等。
        list_missing_lines: list[str] = []  # 待插入受管头

        # 没有时间头时先插入生命周期信息。
        if not bool_last_inserted:

            # 时间头排在元数据之前。
            list_missing_lines.append(new_last_line)

        # 没有元数据行时补齐版本与语言合同。
        if not bool_metadata_inserted:

            # 元数据紧随时间头或原文件注释头。
            list_missing_lines.append(new_metadata_line)

        # 切片赋值在确定位置一次插入缺失头部。
        list_rewritten[int_insert_at:int_insert_at] = list_missing_lines  # 在正文前补齐缺失头部

    # 规范化文件尾，只保留一个终止换行。
    return "\n".join(list_rewritten).rstrip() + "\n"

# 根规则写入器只重写受管头部并返回实际文本与更新状态。
def apply_root_agents_sync(
    # 文件路径和原文限定唯一写入目标。
    path_agents: Path,
    str_text: str,
    # 版本与生命周期元组保持公开字段来源分组。
    tuple_versions: tuple[str, str],
    tuple_lifecycle: tuple[str, str, str],
    # 三个控制标志决定重写、写入和验证刷新。
    bool_sync_required: bool,
    write: bool,
    mark_verified: bool,
) -> tuple[str, bool]:
    """按写入条件生成并可选落盘根 AGENTS 受管元数据。

    参数：path_agents 为目标文件，str_text 为原文，tuple_versions 为两套版本，
    tuple_lifecycle 为语言和时间，bool_sync_required、write、mark_verified 为控制状态。
    返回：报告使用的文本与是否实际更新文件。
    """

    # 检查模式默认保持原文且不产生写入。
    str_synced_text = str_text  # 检查模式下的规则文本

    # 实际更新状态仅由内容差异和写模式共同决定。
    bool_updated = False  # 是否实际更新根文件

    # 无写入请求或无需同步时直接返回原始状态。
    if not write or (not bool_sync_required and not mark_verified):

        # 检查模式不触碰文件系统。
        return str_synced_text, bool_updated

    # 重写器只触碰受管头部和受管控制档案版本。
    str_synced_text = _rewrite_root_agents(  # 写模式生成的候选根规则文本
        str_text,  # 原根规则文本

        # 两个版本分别维护兼容元数据和项目控制档案。
        tuple_versions[0],  # 生成器兼容版本
        tuple_versions[1],  # 项目业务版本

        # 生命周期字段保持语言、更新时间和验证时间顺序。
        tuple_lifecycle[0],  # 默认语言
        (tuple_lifecycle[1], tuple_lifecycle[2]),  # 更新时间和验证时间

        # 关键字标志控制两类时间头刷新。
        sync_required=bool_sync_required,  # 是否刷新更新时间
        mark_verified=mark_verified,  # 是否刷新验证时间
    )

    # 幂等结果与原文相同时无需落盘。
    if str_synced_text == str_text:

        # 返回候选文本供报告读取实际时间头。
        return str_synced_text, bool_updated

    # UTF-8 写入保持治理文档编码统一。
    path_agents.write_text(str_synced_text, encoding="utf-8")

    # 内容差异已经形成实际文件更新。
    return str_synced_text, True

# 根同步报告构造器保持版本、时间和修复字段的稳定顺序。
def root_agents_sync_report(
    # 项目和目标路径形成报告身份。
    project: Path,
    path_agents: Path,
    # 修复命令与上下文提供全部报告值。
    str_repair_command: str,
    dict_context: dict[str, Any],
) -> dict[str, Any]:
    """构造成功路径的根 AGENTS 同步报告。

    参数：project 为项目根，path_agents 为目标文件，str_repair_command 为修复命令，
    dict_context 为版本、分析、同步文本和写入状态上下文。
    返回：保持既有字段顺序的成功同步报告。
    """

    # 写入后重新读取时间头，用实际结果支撑报告。
    match_refreshed = LAST_UPDATED_HEADER_RE.search(dict_context["synced_text"])  # 实际报告文本中的时间头

    # 无匹配时保留分析阶段读取的原更新时间。
    str_refreshed_raw = match_refreshed.group(1).strip() if match_refreshed else dict_context["analysis"][1]  # 报告更新时间

    # 正常报告覆盖同步决策、版本事实和实际写入结果。
    return {
        "project": str(project),  # 完成根同步检查的项目
        "agents_path": str(path_agents),  # 本次检查或更新的规则文件
        "expected_version": dict_context["versions"][0],  # AGENTS 兼容元数据基准
        "version_source": dict_context["versions"][1],  # 兼容版本的安装事实来源
        "project_skill_version": dict_context["versions"][2],  # Control Profile 业务版本
        "project_version_source": dict_context["versions"][3],  # 业务版本事实来源
        "project_skill_dir": str(dict_context["versions"][4]) if dict_context["versions"][4] else "",  # 业务 VERSION 所在 skill
        "default_language": dict_context["analysis"][3],  # 根元数据声明的语言
        "last_updated_raw": str_refreshed_raw,  # 报告中的更新时间
        "sync_required": bool(dict_context["analysis"][0]),  # 检查时是否发现漂移
        "updated": dict_context["updated"],  # 本次是否实际写入
        "mark_verified": dict_context["mark_verified"],  # 是否请求刷新验证时间
        "reasons": dict_context["analysis"][0],  # 本次检查识别的漂移原因
        "errors": [],  # 正常路径没有阻断错误
        "repair_command": str_repair_command,  # 可重复执行的修复命令
    }

# 根同步预检器在任何 AGENTS 写入前执行知识图谱与覆盖配置门禁。
def root_agents_sync_preflight(
    project: Path,
    path_agents: Path,
    profile: dict[str, Any],
    write: bool,
    confirm_untrack: bool,
) -> dict[str, Any] | None:
    """执行根规则同步前置门禁并返回可选阻断报告。

    参数：project 为项目根，path_agents 为目标，profile 为档案，write 为写模式，
    confirm_untrack 为解除知识图谱产物跟踪的用户确认。
    返回：门禁失败报告；无需阻断时返回 None。
    """

    # 检查模式或未受管项目不执行写入前门禁。
    if not write or not profile:

        # None 表示无需运行任何写入型门禁。
        return None

    # 共享门禁先验证依赖、索引证据和 Git 产物边界。
    dict_codebase_gate = enforce_codebase_memory_write_gate(  # 根规则写入前知识图谱门禁
        project,  # 待同步根规则的项目
        profile,  # 当前强控制画像
        apply=True,  # 执行必要忽略规则修复
        confirm_untrack=confirm_untrack,  # 用户解除跟踪确认
    )

    # 失败载荷直接返回，确保根规则尚未发生写入。
    if not dict_codebase_gate.get("ok"):

        # 阻断报告保留知识图谱门禁的全部诊断字段。
        return {
            "project": str(project),
            "agents_path": str(path_agents),
            "updated": False,
            **dict_codebase_gate,
        }

    # 写模式下保证全局规则覆盖文件与当前档案同步。
    ensure_global_rule_overrides_file(project, profile)

    # None 表示所有前置门禁均已通过。
    return None

# 根同步版本解析器统一处理缺失文件和生成器版本错误。
def root_agents_sync_version_context(
    project: Path,
    path_agents: Path,
    str_repair_command: str,
    installed_skill_dir_override: str | Path | None,
) -> dict[str, Any]:
    """解析根同步所需版本并返回可选阻断报告。

    参数：project 为项目根，path_agents 为目标，str_repair_command 为修复命令，
    installed_skill_dir_override 为可选安装副本。
    返回：包含 values 五元组或 error 报告的互斥映射。
    """

    # 缺少根文件时不能安全创建项目规则内容。
    if not path_agents.exists():

        # 失败报告要求先完成正式渲染或写入。
        return {"error": _root_sync_error(
            project,
            path_agents,
            str_repair_command,
            "root AGENTS.md does not exist; render or write AGENTS.md before syncing metadata",
        )}

    # 元数据版本与项目版本分别从其权威来源解析。
    tuple_versions = root_metadata_version(project, installed_skill_dir_override)  # 根同步版本上下文

    # 有生成器版本时返回完整五元组供后续分析。
    if tuple_versions[0]:

        # values 键与 error 键保持互斥。
        return {"values": tuple_versions}

    # 缺少生成器版本时报告仍保留项目版本上下文。
    return {"error": _root_sync_error(
        project,
        path_agents,
        str_repair_command,
        "agents-md-generator version is unavailable; cannot sync root AGENTS metadata",
        version_context=(
            tuple_versions[1],
            tuple_versions[2],
            tuple_versions[3],
            tuple_versions[4],
        ),
    )}

# 检查并按需同步根 AGENTS 的受管元数据。
def sync_root_agents(
    project: Path,
    write: bool = False,
    installed_skill_dir_override: str | Path | None = None,
    *,
    mark_verified: bool = False,
    confirm_codebase_memory_untrack: bool = False,
) -> dict[str, Any]:
    """检查或写入根 AGENTS 的版本、语言和验证时间。

    参数：project 为项目根，write 控制写入。
    参数：installed_skill_dir_override 指定安装副本，mark_verified 刷新验证时间，confirm_codebase_memory_untrack 表示用户是否确认解除本地产物的 Git 跟踪。
    返回：同步需求、实际更新、版本来源和修复命令。
    """

    # 根文件是所有受管元数据更新的唯一写入目标。
    agents_path = project / "AGENTS.md"  # 本次同步唯一允许写入的根规则文件

    # 项目档案用于同步全局规则覆盖并构造修复命令。
    profile = project_profile(project)  # 用于覆盖规则和修复命令的项目档案

    # 前置门禁在任何根规则写入前完成知识图谱和覆盖配置检查。
    dict_preflight = root_agents_sync_preflight(  # 可选根同步阻断报告
        project,  # 前置门禁所属仓库
        agents_path,  # 唯一根规则目标
        profile,  # 项目治理档案
        write,  # 写入请求状态
        confirm_codebase_memory_untrack,  # 本地产物解除跟踪确认
    )

    # 失败报告直接返回，确保目标文件尚未变化。
    if dict_preflight is not None:

        # 前置门禁报告已经具备完整项目与错误上下文。
        return dict_preflight

    # 无论检查成功与否都向调用方提供可执行修复命令。
    repair_command = root_agents_sync_command(  # 根元数据修复命令
        project,  # 修复命令的目标仓库
        profile,  # 修复命令采用的规则档案
        installed_skill_dir_override,  # 可选安装副本
    )

    # 版本解析器统一返回成功五元组或完整阻断报告。
    dict_version_context = root_agents_sync_version_context(  # 根同步版本解析结果
        project,  # 版本解析所属仓库
        agents_path,  # 根规则目标文件
        repair_command,  # 同步修复命令
        installed_skill_dir_override,  # 安装版本查找覆盖值
    )

    # 解析失败时直接返回既有错误协议。
    if "error" in dict_version_context:

        # error 值已经包含项目、目标和修复命令。
        return dict_version_context["error"]

    # 成功五元组按既有位置恢复具名变量。
    (
        tuple_metadata_version,  # AGENTS 兼容性元数据基准
        tuple_version_source,  # 生成器版本来源
        tuple_project_version,  # Control Profile 应声明的业务版本
        tuple_project_version_source,  # 项目版本来源
        tuple_project_skill_dir,  # 项目 skill 目录
    ) = dict_version_context["values"]

    # 容错读取允许检查包含历史坏字符的 Markdown。
    str_text = agents_path.read_text(encoding="utf-8", errors="ignore")  # 原根 AGENTS 内容

    # 分析结果同时提供同步原因和需要保留的原始字段。
    (
        tuple_list_reasons,  # 分析结果中的同步原因
        tuple_last_updated_raw,  # 分析结果中的原更新时间
        tuple_last_verified,  # 分析结果中的原验证时间
        tuple_default_language,  # 分析结果中的默认语言
    ) = _root_sync_reasons(str_text, tuple_metadata_version, tuple_project_version)

    # 任一原因存在即表示受管元数据需要同步。
    bool_sync_required = bool(tuple_list_reasons)  # 是否检测到元数据漂移

    # 写入器隔离候选文本生成、幂等比较和实际落盘。
    tuple_sync_result = apply_root_agents_sync(  # 根规则同步文本与更新状态
        agents_path,  # 受管头实际落盘路径
        str_text,  # 同步前原文

        # 版本元组区分生成器兼容版本和项目业务版本。
        (tuple_metadata_version, tuple_project_version),  # 兼容与业务版本

        # 生命周期元组保持语言、更新时间和验证时间。
        (tuple_default_language, tuple_last_updated_raw, tuple_last_verified),  # 生命周期元数据

        # 三个标志决定是否以及如何写入。
        bool_sync_required,  # 是否存在版本或语言漂移
        write,  # 是否允许实际写入
        mark_verified,  # 是否显式刷新复核时间
    )

    # 报告上下文集中保存版本、分析和写入结果。
    dict_report_context = {  # 根同步成功报告上下文
        "versions": (  # 兼容与业务版本上下文
            tuple_metadata_version,  # 报告槽位一的期望版本
            tuple_version_source,  # 报告槽位二的版本证据
            tuple_project_version,  # 控制档案声明基准
            tuple_project_version_source,  # 业务版本证据位置
            tuple_project_skill_dir,  # VERSION 所属技能根
        ),
        "analysis": (  # 漂移原因与生命周期分析
            tuple_list_reasons,  # 元数据同步原因序列
            tuple_last_updated_raw,  # 重写前更新时间原文
            tuple_last_verified,  # 重写前验证时间原文
            tuple_default_language,  # 规则声明的默认语言
        ),
        "synced_text": tuple_sync_result[0],  # 写入器返回的最终文本
        "updated": tuple_sync_result[1],  # 实际文件更新状态
        "mark_verified": mark_verified,  # 调用方复核刷新请求
    }

    # 成功报告构造器保持既有字段顺序和值来源。
    return root_agents_sync_report(
        project,  # 完成同步检查的项目
        agents_path,  # 根 AGENTS 目标
        repair_command,  # 报告复用的同步命令
        dict_report_context,  # 聚合后的成功路径证据
    )

# 判断全局 baseline 前方是否只含可随区块替换的受管元数据。
def global_codex_between_is_replaceable_meta(text: str) -> bool:
    """检查 preamble 与 baseline 之间是否只有受管元数据行。

    参数：text 为两个受管标记之间的文本。
    返回：空白或纯受管元数据时为 True，含人工内容时为 False。
    """

    # 首尾空白不影响是否可以扩大替换边界。
    stripped = text.strip()  # 待判定的中间文本

    # 空区域允许把相邻 preamble 一并替换。
    if not stripped:

        # 没有人工内容需要保留。
        return True

    # 每一行都必须是生成器声明的 baseline 元数据。
    for line in stripped.splitlines():

        # 任意非受管行都会阻止扩大替换范围。
        if not GLOBAL_CODEX_AGENTS_META_LINE_RE.fullmatch(line.strip()):

            # 保守保留无法确认归属的内容。
            return False

    # 所有行均可由新模板安全取代。
    return True

# 替换全局 Codex AGENTS 中已存在的受管 baseline 区块。
def replace_global_codex_block(text: str, rendered: str) -> str:
    """以最新模板替换现有受管全局 baseline。

    参数：text 为现有全局 AGENTS 内容，rendered 为完整新版受管模板。
    返回：替换后的文本；受管边界无效时保持原文。
    """

    # 局部别名使后续切片表达式保持紧凑。
    current = text  # 现有全局 AGENTS 内容

    # 起止标记共同限定生成器拥有的正文范围。
    start = current.find(GLOBAL_CODEX_AGENTS_BLOCK_START)  # baseline 起始索引

    # 结束位置暂时指向结束标记开头。
    end = current.find(GLOBAL_CODEX_AGENTS_BLOCK_END)  # baseline 结束索引

    # 标记缺失或倒置时禁止猜测替换范围。
    if start == -1 or end == -1 or end < start:

        # 保留原文并由状态检查报告异常。
        return current

    # 向前搜索连续的生成器 preamble 和元数据，清理历史重复头。
    search_end = start  # preamble 反向搜索上界

    # 每轮只在确认中间没有人工内容后扩大边界。
    while True:

        # 查找当前边界之前最近的受管 preamble。
        preamble_start = current.rfind(  # 最近 preamble 索引
            GLOBAL_CODEX_AGENTS_PREAMBLE,  # 受管 preamble 文本
            0,  # 从文件开头搜索
            search_end,  # 不越过当前替换边界
        )

        # 没有更早 preamble 时停止扩大范围。
        if preamble_start == -1:

            # 当前 start 已是最早安全边界。
            break

        # preamble 与 baseline 之间只允许生成器元数据。
        between = current[  # 候选边界之间的文本
            preamble_start + len(GLOBAL_CODEX_AGENTS_PREAMBLE) : start  # 排除 preamble 本身
        ]

        # 人工内容阻止继续向前吞并。
        if not global_codex_between_is_replaceable_meta(between):

            # 保留该 preamble 及其后人工内容。
            break

        # 已确认的 preamble 纳入本次模板替换。
        start = preamble_start  # 扩大后的替换起点

        # 下一轮只搜索更早区域，避免重复命中同一位置。
        search_end = preamble_start  # 新反向搜索上界

    # 替换切片必须包含结束标记本身。
    end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)  # 将结束标记纳入替换切片

    # 文件尾规范化为单个换行，其他人工内容保持不变。
    return (current[:start] + rendered + current[end:]).rstrip() + "\n"

# 检查或写入用户 Codex 全局 AGENTS baseline。
def sync_global_codex_agents(project: Path, write: bool = False, codex_home: str | None = None) -> dict[str, Any]:
    """同步全局 Codex AGENTS 中的受管 baseline。

    参数：project 为当前项目根，write 控制写入，codex_home 可覆盖用户目录。
    返回：同步前后状态、确认要求、目标路径和实际更新标志。
    """

    # 全局目标路径由共享规则统一解析。
    target = global_codex_agents_path(codex_home)  # 用户全局 AGENTS 路径

    # 项目档案影响全局入口所需的双技能与治理路由。
    profile = project_profile(project)  # 当前项目控制档案

    # 初始状态决定能否自动写入或必须请求用户确认。
    status = global_codex_agents_status(  # 同步前全局入口状态
        codex_home,  # 状态检查使用的用户 Codex 根
        project_root=project,  # 为修复提示提供的 owner 项目
        profile=profile,  # 决定全局入口规则集的控制档案
    )

    # 修复命令随结果返回，供只读检查直接提示用户。
    repair_command = global_codex_agents_sync_command(project, profile)  # 全局入口修复命令

    # 基础报告合并共享状态和本次调用上下文。
    dict_result = {  # 全局入口同步报告
        "project": str(project),  # 发起全局入口同步的 owner 仓库
        "target_path": str(target),  # 全局 AGENTS 路径
        "updated": False,  # 尚未发生写入
        "write_requested": write,  # 调用方写入意图
        "requires_user_confirmation": status["requires_user_confirmation"],  # 是否需授权
        "user_message": status["user_message"],  # 面向用户的状态说明
        "repair_command": repair_command,  # 可执行修复命令
        **status,  # 完整共享状态字段
    }

    # 只读模式直接返回检查结果。
    if not write:

        # 不创建目录、不修改用户全局文件。
        return dict_result

    # 写模式确保 Codex 主目录存在。
    target.parent.mkdir(parents=True, exist_ok=True)

    # 同名目录或其他非文件目标不能被覆盖。
    if target.exists() and not target.is_file():

        # 错误附加到兼容报告结构中。
        return {**dict_result, "errors": [f"global Codex AGENTS target is not a file: {target}"]}

    # 最新模板包含完整受管 preamble、元数据和 baseline。
    rendered = render_global_codex_agents_template()  # 最新全局入口模板

    # 新文件以空文本进入写入分支，旧文件容错读取。
    current = target.read_text(encoding="utf-8", errors="ignore") if target.is_file() else ""  # 原全局入口内容

    # 缺失或空文件可以直接写入完整模板。
    if not target.exists() or status["empty"]:

        # 完整模板成为新文件全部内容。
        str_new_text = rendered  # 待写入完整模板

    # 已受管文件仅替换生成器拥有的 baseline 区块。
    elif status["managed"]:

        # 人工维护内容保留在受管区块之外。
        str_new_text = replace_global_codex_block(current, rendered)  # 替换后的全局入口

    # 未受管非空文件必须先获得用户确认并由其他流程接管。
    else:

        # 原状态已经包含确认要求和用户提示。
        return dict_result

    # 内容发生变化时才实际写入。
    if str_new_text != current:

        # UTF-8 编码保持跨平台一致。
        target.write_text(str_new_text, encoding="utf-8")

        # 报告标记本次调用已改变全局入口。
        dict_result["updated"] = True  # 已写入新内容

    # 写入后重新检查，以实际文件状态作为最终证据。
    refreshed = global_codex_agents_status(  # 同步后全局入口状态
        codex_home,  # 写入后重新检查的 Codex 根
        project_root=project,  # 最终状态关联的 owner 仓库
        profile=profile,  # 写入后应满足的规则档案
    )

    # 最终报告覆盖同步前的状态字段。
    dict_result.update(refreshed)

    # 共享状态可能不含项目上下文修复命令，因此显式恢复。
    dict_result["repair_command"] = repair_command  # 写入后仍可重复执行的 baseline 同步命令

    # 调用方获得写入后的权威状态。
    return dict_result

# 检查治理文档中是否残留未经脱敏的本地绝对路径。
def audit_docs_private_paths(project: Path) -> dict[str, Any]:
    """扫描受管 docs 文本中的本地私有路径。

    参数：project 为项目根目录。
    返回：已检查文件和需要脱敏的错误清单。
    """

    # 覆盖清单记录实际扫描到的文本文件。
    list_checked: list[str] = []  # 已扫描文档路径

    # 每个命中文件产生一条稳定诊断。
    list_errors: list[str] = []  # 私有路径错误

    # 仅遍历配置声明的治理目录。
    for rel_root in DOCS_PRIVACY_ROOTS:

        # 相对目录统一绑定当前项目根。
        root = project / rel_root  # 当前隐私审计目录

        # 可选治理目录不存在时继续检查其他范围。
        if not root.exists():

            # 缺失目录由文档结构门禁负责报告。
            continue

        # 稳定排序保证报告在不同文件系统上可复现。
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):

            # 二进制或未知格式不按文本扫描。
            if path.suffix.lower() not in DOCS_PRIVACY_TEXT_SUFFIXES:

                # 跳过不在安全文本后缀集合中的文件。
                continue

            # 项目内路径优先用于稳定报告。
            try:

                # POSIX 形式避免平台路径分隔符差异。
                str_rel_path = path.relative_to(project).as_posix()  # 可复现的项目内文档位置

            # 外部符号链接目标无法相对化时保留完整路径。
            except ValueError:

                # 绝对路径准确标识越界文件。
                str_rel_path = str(path)  # 无法相对化的越界文件位置

            # 只有实际读取的文件进入覆盖清单。
            list_checked.append(str_rel_path)

            # 容错解码允许扫描历史治理记录。
            text = path.read_text(encoding="utf-8", errors="ignore")  # 当前文档文本

            # 原始本地绝对路径必须在提交或发布前脱敏。
            if LOCAL_PRIVATE_PATH_RE.search(text):

                # 诊断指出具体文件而不回显私有路径本身。
                list_errors.append(f"{str_rel_path}: raw local private path must be redacted")

    # 调用方据此证明扫描覆盖范围并阻断泄漏。
    return {"checked": list_checked, "errors": list_errors}

# 合并文档结构、handoff、memory、隐私和版本一致性检查。
def verify_docs(project: Path) -> dict[str, Any]:
    """执行项目 docs 治理的完整本地验证。

    参数：project 为项目根目录。
    返回：项目、覆盖清单、错误清单和 handoff 命名审计。
    """

    # 延迟导入避免文档模块初始化时形成循环依赖。
    from manage_docs_memory import verify_memory

    # 所有门禁错误一次聚合，便于单次修复。
    list_errors: list[str] = []  # 文档治理错误

    # 覆盖清单证明实际检查了哪些受管资产。
    list_checked: list[str] = []  # 已检查文档路径

    # 必需治理目录逐项确认存在。
    for rel_path in DOC_DIRS:

        # 配置中的每个目录都属于验证范围。
        list_checked.append(rel_path)

        # 非目录或缺失路径均违反治理结构。
        if not (project / rel_path).is_dir():

            # 诊断保留缺失的相对目录。
            list_errors.append(f"missing docs governance directory: {rel_path}")

    # 必需治理文件与目录采用相同的覆盖语义。
    for rel_path in REQUIRED_DOC_FILES:

        # 先登记检查意图，再判断文件存在性。
        list_checked.append(rel_path)

        # 同名目录不能满足必需文件合同。
        if not (project / rel_path).is_file():

            # 诊断指向缺失的治理文件。
            list_errors.append(f"missing docs governance file: {rel_path}")

    # handoff 命名审计覆盖当前文件和历史归档。
    handoff_naming = audit_handoff_naming(project)  # handoff 命名审计结果

    # 去重合并 handoff 实际检查路径。
    list_checked.extend(item for item in handoff_naming["checked"] if item not in list_checked)

    # 去重合并命名冲突，避免同一错误重复展示。
    list_errors.extend(item for item in handoff_naming["errors"] if item not in list_errors)

    # 当前开发记录需要满足章节与状态合同。
    development_current = project / "docs" / "development" / "DEVELOPMENT.md"  # 当前开发记录

    # 文件存在时执行内容验证，缺失已由必需文件检查报告。
    if development_current.exists():

        # 共享验证器返回可直接合并的错误列表。
        list_errors.extend(validate_development_record(development_current))

    # 当前 handoff 必须保留所有标准章节。
    handoff = project / "docs" / "handoff" / "HANDOFF.md"  # 当前 handoff 路径

    # 文件存在时检查章节，缺失仍由必需文件检查负责。
    if handoff.exists():

        # 容错读取支持迁移前的历史编码内容。
        text = handoff.read_text(encoding="utf-8", errors="ignore")  # 当前 handoff 文本

        # 标准章节顺序由共享合同定义。
        for section in HANDOFF_SECTIONS:

            # 缺少任一章节都会削弱跨会话恢复信息。
            if f"## {section}" not in text:

                # 诊断明确给出缺失标题。
                list_errors.append(f"docs/handoff/HANDOFF.md: missing section ## {section}")

    # 目录管理器验证实际结构、计划结构和审查记录。
    dir_result = verify_dir_manager(project)  # 目录治理验证结果

    # 目录验证器已经提供稳定覆盖清单。
    list_checked.extend(dir_result["checked"])

    # 目录治理错误直接纳入文档总门禁。
    list_errors.extend(dir_result["errors"])

    # memory 验证确认数据库、事件流和摘要可恢复。
    memory_result = verify_memory(project)  # 项目 memory 验证结果

    # memory 路径去重后加入覆盖清单。
    list_checked.extend(item for item in memory_result.get("checked", []) if item not in list_checked)

    # memory 错误去重后加入总错误清单。
    list_errors.extend(item for item in memory_result.get("errors", []) if item not in list_errors)

    # 隐私审计防止治理记录泄露本地绝对路径。
    dict_privacy_result = audit_docs_private_paths(project)  # 受管文档的路径脱敏审计结果

    # 隐私扫描覆盖路径合并到总报告。
    list_checked.extend(item for item in dict_privacy_result.get("checked", []) if item not in list_checked)

    # 私有路径错误去重后阻断验证。
    list_errors.extend(item for item in dict_privacy_result.get("errors", []) if item not in list_errors)

    # 版本门禁核对 VERSION 与各受管文档声明。
    dict_version_result = version_alignment_gate(project)  # 文档版本对齐结果

    # 版本检查范围纳入总覆盖清单。
    list_checked.extend(dict_version_result["checked"])

    # 任一版本漂移都纳入文档错误清单。
    list_errors.extend(dict_version_result["errors"])

    # 旧顶层文档路径必须迁移到正式治理布局。
    list_legacy_paths = [  # verify_docs 需要逐项拒绝的四个旧版文件位置
        project / "HANDOFF.md",  # 应迁移到 docs/handoff 的根交接文件
        project / "DEVELOPMENT.md",  # 应迁移到 docs/development 的根开发记录
        project / "docs" / "HANDOFF.md",  # 缺少 handoff 子目录的旧交接文件
        project / "docs" / "DEVELOPMENT.md",  # 缺少 development 子目录的旧开发记录
    ]

    # 检查每个历史位置是否仍有残留。
    for legacy in list_legacy_paths:

        # 只有实际存在的旧路径需要迁移诊断。
        if legacy.exists():

            # 项目内路径优先输出相对形式。
            try:

                # 相对路径使诊断可以跨机器比较。
                str_legacy_path = legacy.relative_to(project).as_posix()  # 旧路径报告值

            # 越界符号链接无法相对化时保留完整路径。
            except ValueError:

                # 完整路径准确指向需要迁移的资产。
                str_legacy_path = str(legacy)  # 外部旧路径报告值

            # 所有旧位置统一使用同一迁移诊断格式。
            list_errors.append(f"legacy docs path must be migrated into governed docs layout: {str_legacy_path}")

    # 总报告保留 handoff 子结果供调用方展示细节。
    return {
        "project": str(project),  # 本次 docs 验证对应的项目
        "checked": list_checked,  # 完整覆盖清单
        "errors": list_errors,  # 聚合治理错误
        "handoff_naming": handoff_naming,  # handoff 命名详情
    }

# 在项目根执行输出 JSON 的治理子命令。
def run_json_command(project: Path, argv: list[str]) -> dict[str, Any]:
    """运行治理命令并解析其 JSON 标准输出。

    参数：project 为命令工作目录，argv 为不经 shell 的参数列表。
    返回：命令、退出码、标准流和解析后的 JSON 字典。
    """

    # 禁用字节码写入，避免治理检查污染目标仓库。
    dict_environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")  # 子进程环境

    # 参数列表直接交给 subprocess，避免 shell 注入与转义差异。
    command_result = subprocess.run(  # 治理命令执行结果
        argv,  # 完整参数列表
        cwd=project,  # 项目根工作目录
        text=True,  # 以文本形式捕获输出
        capture_output=True,  # 保留标准输出与错误
        check=False,  # 退出码由聚合门禁解释
        env=dict_environment,  # 禁止生成字节码的环境
    )

    # 解析失败时保持空字典，原始输出仍进入报告。
    dict_parsed: dict[str, Any] = {}  # 默认没有可用 JSON 对象

    # 尝试读取命令声明的机器可读结果。
    try:

        # 标准输出应当是单个 JSON 值。
        loaded = json.loads(command_result.stdout)  # 子命令 JSON 值

        # 聚合门禁只接受对象形结果。
        dict_parsed = loaded if isinstance(loaded, dict) else {}  # 结构化命令结果

    # 非 JSON 输出由退出码和原始标准流共同诊断。
    except json.JSONDecodeError:

        # 空字典避免调用方误读部分文本。
        dict_parsed = {}  # 无可用结构化结果

    # 完整执行证据供上层门禁判断。
    return {
        "argv": argv,  # 实际执行参数
        "returncode": command_result.returncode,  # 子命令退出码
        "stdout": command_result.stdout,  # 原始标准输出
        "stderr": command_result.stderr,  # 原始标准错误
        "json": dict_parsed,  # 解析后的 JSON 对象
    }

# 聚合开始开发或发布前必须满足的工作目录门禁。
def work_folder_gate(project: Path, skill_dir_raw: str, mode: str = "development") -> dict[str, Any]:
    """检查会话、文档、目录、分支、版本、源码和 freshness 状态。

    参数：project 为项目根，skill_dir_raw 为目标 skill，mode 为开发或发布模式。
    返回：各子门禁证据、聚合错误和最终通过状态。
    """

    # 延迟导入避免 docs、dirs 和 release 模块初始化循环。
    from manage_dirs import structure_gate
    from manage_docs_release import branch_gate
    from manage_docs_scaffold_session import resume_check

    # 目标 skill 目录用于版本对齐和发布模式约束。
    skill_dir = inferred_skill_dir(project, skill_dir_raw)  # 发布与版本门禁共同采用的 skill 根

    # 活跃会话状态作为报告证据，但不会阻断当前进行中的会话。
    resume = resume_check(project)  # 会话恢复检查结果

    # 仅在已初始化 docs 治理时执行完整文档验证。
    docs_verify = (  # 文档治理验证结果
        verify_docs(project)  # 已初始化项目的完整验证
        if docs_governance_initialized(project)  # 是否存在正式治理结构
        else {"project": str(project), "checked": [], "errors": []}  # 未初始化兼容结果
    )

    # 结构门禁核对受管目录合同。
    structure = structure_gate(project)  # 项目结构门禁结果

    # 目录管理器独立验证快照和计划状态。
    dir_manager = verify_dir_manager(project)  # 目录管理验证结果

    # 分支门禁阻止受保护分支上的高风险操作。
    branch = branch_gate(project)  # Git 分支门禁结果

    # 项目 VERSION 必须与受管文档保持一致。
    dict_version = version_alignment_gate(project, skill_dir)  # 版本对齐门禁结果

    # 源码治理根据当前控制档案检查生产文件边界。
    source_governance = source_governance_report(  # 源码治理报告
        project,  # 源码边界扫描所在仓库
        control_profile(project),  # 声明生产路径与例外的控制档案
    )

    # 优先采用项目治理配置解析的 freshness 脚本路径。
    str_freshness_script = governance_script_path(project, "check_freshness.py")  # freshness 脚本配置值

    # 路径对象用于判断配置脚本是否在当前环境实际存在。
    path_freshness_candidate = Path(str_freshness_script)  # freshness 脚本候选

    # 相对配置路径统一以项目根解释。
    if not path_freshness_candidate.is_absolute():

        # 绑定项目根后才能可靠检查文件存在性。
        path_freshness_candidate = project / path_freshness_candidate  # 按仓库根解释后的检测入口

    # 占位路径或缺失脚本回退到已安装 skill 运行时。
    if str_freshness_script.startswith("<codex-home>") or not path_freshness_candidate.exists():

        # 环境覆盖优先，否则使用当前 owner skill 根。
        fallback_dir = os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR") or Path(__file__).resolve().parents[3]  # freshness 运行时根

        # 回退脚本使用当前 skill 的正式 scripts/python 布局。
        str_freshness_script = str(  # 可执行 freshness 脚本路径
            Path(fallback_dir) / "scripts" / "python" / "detect" / "check_freshness.py"  # 标准检测入口
        )

    # 子命令以当前 Python 解释器运行并返回 JSON 证据。
    dict_freshness_command = run_json_command(  # freshness 命令执行证据
        project,  # 子进程工作目录
        [sys.executable, str_freshness_script, str(project)],  # 不经 shell 的参数列表
    )

    # 空 JSON 将由非零退出码或缺失 stale 字段保持保守状态。
    freshness = dict_freshness_command["json"]  # freshness 结构化结果

    # 所有子门禁错误合并到稳定顺序的清单。
    list_errors: list[str] = []  # 工作目录聚合错误

    # 当前会话允许继续执行，但报告应提醒新任务先做 resume-check。
    dict_resume_policy = {  # 活跃会话聚合策略
        "blocking": False,  # 不阻断当前进行中的任务
        "reason": (  # 策略说明
            "work-folder-gate reports active-session state but does not block the "  # 当前会话例外
            "current in-progress session; run resume-check before starting new work."  # 新任务入口要求
        ),
    }

    # 真正的恢复阻断原因仍应进入聚合错误。
    if resume.get("blocking"):

        # 前缀保留错误所属子门禁。
        list_errors.extend(f"resume-check: {item}" for item in resume.get("reasons", []))

    # 文档验证错误始终参与聚合。
    list_errors.extend(f"docs-verify: {item}" for item in docs_verify.get("errors", []))

    # 未批准结构意味着目录合同尚未闭合。
    if not structure.get("approved", True):

        # 结构原因保留独立前缀。
        list_errors.extend(f"structure-gate: {item}" for item in structure.get("reasons", []))

    # 目录快照与计划错误直接参与聚合。
    list_errors.extend(f"dir-manager: {item}" for item in dir_manager.get("errors", []))

    # 未批准分支会阻止开发或发布操作。
    if not branch.get("approved", True):

        # 分支原因保留独立前缀。
        list_errors.extend(f"branch-gate: {item}" for item in branch.get("reasons", []))

    # VERSION 与文档声明漂移必须先修复。
    list_errors.extend(f"version-gate: {item}" for item in dict_version.get("errors", []))

    # 源码治理格式化器负责稳定的错误编码与路径表达。
    list_errors.extend(format_source_governance_errors(source_governance, prefix="source-governance"))

    # freshness 子命令自身失败时不能信任其 JSON。
    if dict_freshness_command["returncode"] != 0:

        # 聚合错误明确指出外部检查未成功执行。
        list_errors.append("check_freshness command failed")

    # 成功执行但报告 stale 同样阻断继续工作。
    if freshness.get("stale"):

        # 需要先同步根 AGENTS 的时间和元数据。
        list_errors.append("AGENTS.md freshness check is stale")

    # 发布模式必须能够确定实际 skill 目录。
    if mode == "release" and not skill_dir:

        # 无目标目录时无法证明发布内容边界。
        list_errors.append("release work-folder gate requires a resolved skill directory")

    # 最终报告保留每个子门禁的原始证据。
    return {
        "project": str(project),  # 聚合门禁实际检查的工作目录
        "mode": mode,  # 当前门禁模式
        "skill_dir": str(skill_dir) if skill_dir else "",  # 解析后的目标 skill
        "ok": not list_errors,  # 无聚合错误时通过
        "errors": list_errors,  # 稳定顺序的聚合错误
        "resume_check": resume,  # 会话恢复证据
        "resume_policy": dict_resume_policy,  # 当前会话例外策略
        "docs_verify": docs_verify,  # 文档治理证据
        "structure_gate": structure,  # 结构合同证据
        "dir_manager": dir_manager,  # 目录管理证据
        "branch_gate": branch,  # 分支治理证据
        "version_gate": dict_version,  # 版本对齐证据
        "source_governance": source_governance,  # 源码治理证据
        "freshness": freshness,  # AGENTS freshness 证据
    }
