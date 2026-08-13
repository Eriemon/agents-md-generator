"""提供 AGENTS 治理脚本共享的路径、版本、元数据与命令构造能力。"""

# 延迟注解解析避免直接执行时提前加载共享类型。
from __future__ import annotations

# 标准库覆盖命令行、序列化、环境、文本匹配和子进程能力。
import argparse
import json
import os
import re
import subprocess
import sys

# 日期类型分别支撑日粒度和秒粒度的治理时间戳。
from datetime import date, datetime

# 路径与动态载荷类型用于共享文件系统合同。
from pathlib import Path
from typing import Any

# 直接执行兼容层只负责注册兄弟任务模块，不承载业务判断。
def extend_task_module_search_path() -> None:
    """注册共享脚本的兄弟任务目录。

    Args:
        无。

    Returns:
        无。
    """

    # Python 脚本根目录包含 detect、docs、verify 等任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # Python 脚本根目录

    # 每个实际任务目录都作为顶层模块来源注册一次。
    for path_task_dir in path_scripts_python_root.iterdir():

        # 文件和已注册目录不参与搜索路径变更。
        if not path_task_dir.is_dir():

            # 非目录项不能成为 Python 模块搜索根。
            continue

        # 字符串路径用于与 sys.path 的公开表示直接比较。
        str_task_path = str(path_task_dir)  # 任务模块搜索路径

        # 保持已有搜索顺序，避免重复插入同一目录。
        if str_task_path in sys.path:

            # 已注册路径保持原优先级，避免重复项改变导入顺序。
            continue

        # 兄弟任务模块应优先于环境中的同名第三方模块。
        sys.path.insert(0, str_task_path)

# 后续兄弟模块导入前完成一次搜索路径设置。
extend_task_module_search_path()

# 项目内容探测忽略版本库、依赖、缓存、构建产物与参考材料目录。
SKIP_DIRS = set(  # 项目内容探测排除目录
    ".git .hg .svn .cache .venv .conda __pycache__ node_modules vendor dist build target ref".split()  # 排除名称序列
)

# 元数据区块表达式提取根 AGENTS 注释中的完整键值载荷。
AGENTS_METADATA_RE = re.compile(  # AGENTS 元数据区块表达式
    r"<!--\s*AGENTS-METADATA:\s*(.*?)\s*-->",  # 元数据注释匹配模式
    flags=re.IGNORECASE,  # 元数据标签大小写不敏感
)

# 键值表达式按分号边界解析单个元数据字段。
AGENTS_METADATA_PAIR_RE = re.compile(r"([a-zA-Z0-9_]+)\s*=\s*([^;]+)")  # AGENTS 元数据键值表达式

# 发布核心规则禁止额外 worktree，并将常见污染目录列为阻断项。
RELEASE_CORE_WORKTREE_RULE = (
    "Do not create or use additional Git worktrees. Do not run `git worktree add` or "
    "repoint with `git config core.worktree`. Keep all work in the current working folder "
    "and use local branches for isolation. Treat `.worktrees`, `worktrees`, "
    "`.git-worktrees`, and `git-worktrees` in the project root or its parent as blocking pollution."
)

# 全局文件前言标记人工内容必须位于受管区块之外。
GLOBAL_CODEX_AGENTS_PREAMBLE = (  # 全局 AGENTS 前言
    "<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->"  # 前言文本
)

# 生成器元标记固定当前全局基线 schema 和版本。
GLOBAL_CODEX_AGENTS_META = (  # 全局 AGENTS 元标记
    "<!-- AGENTS-GENERATED:META generator=agents-md-generator schema=1 "
    "baseline=global-codex-baseline baseline_version=5 -->"
)

# 起始标记限定全局基线的受管写入边界。
GLOBAL_CODEX_AGENTS_BLOCK_START = "<!-- AGENTS-GENERATED:START global-codex-baseline -->"  # 受管区块起始标记

# 结束标记保护区块外的用户维护内容。
GLOBAL_CODEX_AGENTS_BLOCK_END = "<!-- AGENTS-GENERATED:END global-codex-baseline -->"  # 受管区块结束标记

# 占位路径用于在渲染命令中表达安装态治理运行时。
INSTALLED_GOVERNANCE_RUNTIME_PLACEHOLDER = "<codex-home>/skills/agents-md-generator"  # 安装态运行时占位路径

# 脚本名称映射到其所属任务目录，供安装态命令构造复用。
SCRIPT_TASK_BY_NAME = dict(  # 脚本名称到任务目录映射
    str_line.split("=", 1)  # 单行脚本名与任务名
    for str_line in """inspect_project.py=detect
detect_scopes.py=detect
extract_commands.py=detect
extract_context.py=detect
check_freshness.py=detect
codex_token_usage_review.py=detect
task_rating_gate.py=detect
collect_design_profile.py=design
design_questions.py=design
design_profile_builder.py=design
design_profile_contracts.py=design
design_remote_gate.py=design
design_review_gate.py=design
design_takeover.py=design
design_interview_state.py=design
design_interview_payload.py=design
render_agents.py=render
create_agent_shims.py=render
manage_docs.py=docs
manage_docs_shared.py=docs
manage_docs_memory.py=docs
manage_docs_release.py=docs
manage_docs_scaffold_session.py=docs
manage_docs_sync_verify.py=docs
manage_dirs.py=dirs
manage_dirs_state.py=dirs
manage_dirs_review.py=dirs
manage_dirs_remote.py=dirs
quick_validate.py=verify
audit_skill.py=verify
verify_agents.py=verify
verify_agents_policy.py=verify
evaluate_skill.py=verify
check_source_governance.py=verify
source_governance.py=verify
source_governance_config.py=verify
review_governance.py=verify
run_confidence_gate.py=verify
run_skill_evals.py=verify
eval_runtime_core.py=verify
eval_runtime_foundation_cases.py=verify
eval_runtime_policy_cases.py=verify
eval_runtime_fixtures.py=verify
install_skill.py=release
release_content_policy.py=release
select_engineering_rules.py=release
agents_common.py=common
tester_worker_profile.py=common
agents_decisions.py=common
agents_project_facts.py=common
workspace_settings_policy.py=common
git_worktree_policy.py=common""".splitlines()
)

# 所有命令入口共用同一项目目录存在性校验。
def resolve_project(raw: str | Path) -> Path:
    """解析并确认项目目录存在。

    Args:
        raw: 用户传入的项目目录。

    Returns:
        规范化后的项目绝对路径。

    Raises:
        SystemExit: 目录不存在或不是目录时终止命令。
    """

    # 绝对路径消除调用方工作目录对后续文件访问的影响。
    path_project = Path(raw).resolve()  # 已规范化的项目根目录

    # 项目参数必须指向真实目录，文件路径不能继续参与治理。
    if not path_project.exists() or not path_project.is_dir():

        # 命令行错误沿用治理输出前缀，便于日志分类。
        raise SystemExit(f"> ERR: [Python] Project directory does not exist: {path_project}")

    # 调用方只接收已经验证的绝对目录。
    return path_project

# 机器接口集中使用稳定 JSON 排序，避免命令间格式漂移。
def emit_json(data: dict[str, Any]) -> None:
    """向标准输出写入稳定排序的 JSON。

    Args:
        data: 待序列化的机器可读结果。

    Returns:
        无。
    """

    # 该函数输出的是机器合同，不附加人类日志前缀。
    sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")

# 可选治理配置读取失败时采用空对象，由上层决定默认策略。
def read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 对象并把无效文件降级为空对象。

    Args:
        path: JSON 文件路径。

    Returns:
        文件中的 JSON 对象；读取或解析失败时为空对象。
    """

    # 文件缺失、权限或内容错误均属于可恢复的可选配置失败。
    try:

        # 成功路径保留文件中的完整对象结构。
        return json.loads(path.read_text(encoding="utf-8"))

    # 可选配置的文件系统或解析错误均回退为空对象。
    except Exception:

        # 空对象触发各调用方既有默认值，不伪造部分配置。
        return {}

# Codex 主目录解析顺序固定为显式值、环境变量、用户默认目录。
def codex_home_root(raw: str | None = None) -> Path:
    """解析显式值、环境变量或默认 Codex 主目录。

    Args:
        raw: 可选的主目录覆盖值。

    Returns:
        Codex 主目录绝对路径。
    """

    # 显式覆盖优先，空覆盖仍回退到 CODEX_HOME。
    str_env_home = raw.strip() if raw else os.environ.get("CODEX_HOME", "").strip()  # Codex 主目录文本

    # 非空配置统一展开用户目录并转为绝对路径。
    if str_env_home:

        # 显式配置路径不要求预先存在，以支持初始化流程。
        return Path(str_env_home).expanduser().resolve()

    # 未配置时遵循 Codex 的用户目录约定。
    return (Path.home() / ".codex").resolve()

# 会话发现逻辑从统一 Codex 主目录派生固定子目录。
def codex_sessions_root() -> Path:
    """返回 Codex 会话记录目录。

    Args:
        无。

    Returns:
        当前 Codex 主目录下的 sessions 路径。
    """

    # sessions 子目录无需存在即可供后续初始化或查询使用。
    return codex_home_root() / "sessions"

# 当前文件层级是 common 模块，向上三级即技能发布根。
def skill_root() -> Path:
    """定位当前 agents-md-generator 技能根目录。

    Args:
        无。

    Returns:
        包含 SKILL.md 与 VERSION 的技能目录。
    """

    # 使用文件位置而非当前工作目录，确保直接执行结果稳定。
    return Path(__file__).resolve().parents[3]

# 治理技能名集中定义，避免路径和元数据使用不同拼写。
def governance_skill_name() -> str:
    """提供治理技能的稳定注册名称。

    Args:
        无。

    Returns:
        agents-md-generator 技能名。
    """

    # 返回发布清单与安装目录共同采用的规范名称。
    return "agents-md-generator"

# VERSION 文件位置由可覆盖的技能根统一派生。
def skill_version_file(root: Path | None = None) -> Path:
    """定位指定技能根目录的版本文件。

    Args:
        root: 可选技能根目录；缺省时使用当前技能。

    Returns:
        VERSION 文件路径。
    """

    # 未传根目录时读取当前源码或安装态技能自身版本。
    return (root or skill_root()) / "VERSION"

# 版本读取保持缺失可恢复，避免状态查询因未安装而中断。
def read_skill_version(root: Path | None = None) -> str:
    """读取技能版本声明。

    Args:
        root: 可选技能根目录。

    Returns:
        去除空白的版本号；文件不存在时为空字符串。
    """

    # 版本文件路径只解析一次，供存在性和读取共用。
    path_version = skill_version_file(root)  # 技能版本文件

    # 缺失版本声明表示该候选目录不能提供版本证据。
    if not path_version.exists():

        # 空字符串由版本选择器识别为不可用来源。
        return ""

    # 发布版本是单行文本，读取后去除尾部换行。
    return path_version.read_text(encoding="utf-8", errors="ignore").strip()

# 安装目录解析优先接受调用方覆盖，其次读取标准 Codex 技能位置。
def installed_skill_dir(
    skill_name: str = "agents-md-generator",
    override_dir: str | Path | None = None,
) -> Path | None:
    """查找覆盖路径或 Codex 主目录中的已安装技能。

    Args:
        skill_name: 待查找的技能目录名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        存在的安装目录绝对路径；未安装时为 None。
    """

    # 显式参数优先于环境覆盖，空值则继续使用默认 Codex 根目录。
    str_override = (  # 安装目录覆盖文本
        str(override_dir).strip()  # 显式覆盖值
        if override_dir is not None  # 调用方提供覆盖目录
        else os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR", "").strip()  # 环境覆盖值
    )

    # 覆盖目录只有实际存在时才构成安装证据。
    if str_override:

        # 展开用户目录并规范化，避免同一路径出现多种表示。
        path_override = Path(str_override).expanduser().resolve()  # 规范化覆盖目录

        # 不存在的覆盖目录按未安装处理。
        return path_override if path_override.exists() else None

    # CODEX_HOME 未设置时回退到用户主目录下的标准位置。
    str_codex_home = os.environ.get("CODEX_HOME", "").strip()  # Codex 主目录配置

    # 两种来源都规范化为绝对路径后再拼接技能目录。
    path_home_root = (  # Codex 主目录
        Path(str_codex_home).expanduser().resolve()  # 环境配置主目录
        if str_codex_home  # 环境已配置 Codex 主目录
        else (Path.home() / ".codex").resolve()  # 用户默认 Codex 主目录
    )

    # 安装态技能遵循 CODEX_HOME/skills/<name> 目录合同。
    path_installed = path_home_root / "skills" / skill_name  # 安装态技能候选目录

    # 仅返回有文件系统证据的安装目录。
    return path_installed if path_installed.exists() else None

# 治理目录列表保持源码态优先，并去除与安装态相同的物理路径。
def current_governance_skill_dirs(
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> list[Path]:
    """汇总当前源码态与安装态治理技能目录。

    Args:
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        去重且保持源码优先顺序的目录列表。
    """

    # 未指定名称时从当前技能元数据读取治理技能身份。
    str_target_name = skill_name or governance_skill_name()  # 安装目录目标技能名

    # 源码运行时始终作为首个治理候选。
    list_dirs: list[Path] = []  # 有序治理技能目录

    # 规范化源码目录便于与安装目录做路径去重。
    path_runtime = skill_root().resolve()  # 源码治理技能目录

    # 候选顺序决定版本和模板的选择优先级。
    list_dirs.append(path_runtime)

    # 安装态候选可能因未安装而为空。
    path_installed = installed_skill_dir(  # 规范化前安装态目录
        str_target_name,  # 待探测安装的技能名
        override_dir=override_dir,  # 安装目录覆盖值
    )

    # 仅对存在的安装目录执行规范化和去重。
    if path_installed is not None:

        # 规范化安装路径，消除相对路径和用户目录差异。
        path_installed_resolved = path_installed.resolve()  # 规范化安装目录

        # 同一目录不能同时以源码态和安装态重复出现。
        if all(path_existing != path_installed_resolved for path_existing in list_dirs):

            # 安装态候选排在源码态之后。
            list_dirs.append(path_installed_resolved)

    # 返回值保持确定顺序，供调用方依次探测。
    return list_dirs

# 源码仓库候选必须同时满足技能身份、版本和项目控制档案证据。
def source_repo_governance_owner_candidate(project: Path, candidate: Path, target_name: str) -> bool:
    """判断源码仓库内候选目录是否拥有治理合同。

    Args:
        project: 被治理项目根目录。
        candidate: 候选技能目录。
        target_name: 期望的技能名称。

    Returns:
        候选目录同时满足技能身份和治理脚本证据时为 True。
    """

    # SKILL.md 与 VERSION 是技能身份的最小文件证据。
    path_skill_md = candidate / "SKILL.md"  # 候选技能说明文件

    # 任一身份文件缺失即不能成为治理 owner。
    if not path_skill_md.is_file() or not (candidate / "VERSION").is_file():

        # 缺失证据按非 owner 返回，不抛出探测异常。
        return False

    # frontmatter 名称从技能说明原文中验证。
    str_skill_text = path_skill_md.read_text(encoding="utf-8", errors="ignore")  # 技能说明文本

    # 名称不匹配时拒绝借用其他技能的运行时。
    if not re.search(rf"(?m)^name:\s*{re.escape(target_name)}\s*$", str_skill_text):

        # 身份不一致属于普通候选失败。
        return False

    # 项目控制档案可以直接证明候选技能拥有当前治理合同。
    path_profile = project / ".agents" / "agents-control.json"  # 项目控制档案

    # 控制档案存在时优先使用结构化身份判断。
    if path_profile.is_file():

        # 损坏的控制档案不能构成 owner 证据。
        try:

            # JSON 载荷只读取一次供 kind 和 name 联合判断。
            dict_profile = json.loads(path_profile.read_text(encoding="utf-8"))  # 项目控制档案载荷

        # 非法 JSON 表示治理状态不可采信。
        except json.JSONDecodeError:

            # 候选验证采用保守失败策略。
            return False

        # skill 类型且名称匹配即可确认源码 owner。
        if dict_profile.get("kind") == "skill" and dict_profile.get("name") == target_name:

            # 结构化项目身份优先于脚本布局回退。
            return True

    # 旧项目缺少控制档案时使用两项核心治理脚本作为兼容证据。
    path_scripts_dir = candidate / "scripts"  # 候选脚本根目录

    # Python 任务目录承载验证与文档治理入口。
    path_scripts_python_dir = path_scripts_dir / "python"  # 候选 Python 脚本目录

    # 两个核心入口必须同时存在，避免普通 skill 被误判为治理 owner。
    return (
        (path_scripts_python_dir / "verify" / "verify_agents.py").is_file()
        and (path_scripts_python_dir / "docs" / "manage_docs.py").is_file()
    )

# 演进模板 owner 识别区分源码仓库、安装技能和非 owner 项目。
def evolution_owner_status(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:
    """识别演进模板应由源码仓库还是安装态技能持有。

    Args:
        project: 当前项目根目录。
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        包含启用状态、所有权模式与技能目录的报告。
    """

    # 调用方未指定名称时使用当前治理技能身份。
    str_target_name = skill_name or governance_skill_name()  # 演进落点目标技能名

    # 项目路径规范化后再与候选技能目录比较。
    path_resolved_project = project.resolve()  # 规范化项目根目录

    # 活跃目录同时覆盖源码运行时和可用安装态运行时。
    list_active_skill_dirs = current_governance_skill_dirs(  # 活跃治理技能目录
        str_target_name,  # owner 状态目标技能名
        override_dir=override_dir,  # owner 探测安装覆盖值
    )

    # 标准源码 owner 位于项目的 skills/<name> 子目录。
    path_source_repo_skill_dir = path_resolved_project / "skills" / str_target_name  # 源码技能候选目录

    # 只有真实目录才进入源码 owner 校验。
    if path_source_repo_skill_dir.is_dir():

        # 规范化候选路径供活跃目录和内容证据联合判断。
        path_candidate = path_source_repo_skill_dir.resolve()  # 规范化源码候选

        # 活跃运行时命中或仓库内容合同成立均确认源码 owner。
        if any(
            path_candidate == path_active
            for path_active in list_active_skill_dirs
        ) or source_repo_governance_owner_candidate(
            path_resolved_project,
            path_candidate,
            str_target_name,
        ):

            # 源码 owner 报告保留项目根和实际技能目录。
            return {
                "enabled": True,
                "mode": "source-repo",
                "project_root": str(path_resolved_project),
                "owner_skill_dir": str(path_candidate),
            }

    # 项目根本身是活跃技能目录时按安装态 owner 处理。
    if any(path_resolved_project == path_active for path_active in list_active_skill_dirs):

        # 安装态技能以自身目录同时充当项目根和 owner 根。
        return {
            "enabled": True,
            "mode": "installed-skill",
            "project_root": str(path_resolved_project),
            "owner_skill_dir": str(path_resolved_project),
        }

    # 普通被治理项目不得写入演进模板。
    return {
        "enabled": False,
        "mode": "non-owner",
        "project_root": str(path_resolved_project),
        "owner_skill_dir": "",
    }

# 可写性探针在目标目录内创建并清理一个短生命周期文件。
def path_is_writable(path: Path) -> bool:
    """用可删除探针确认目标目录可写。

    Args:
        path: 目录或其下文件路径。

    Returns:
        探针可以创建并删除时为 True。
    """

    # 文件路径探测其父目录，目录路径则直接作为目标。
    path_target = path if path.suffix == "" else path.parent  # 可写性探测目录

    # 文件系统异常统一折叠为不可写结果。
    try:

        # 允许为尚未创建的合法目标补齐父目录。
        path_target.mkdir(parents=True, exist_ok=True)

        # 固定探针名只在目标目录内短暂存在。
        path_probe = path_target / ".write-probe.tmp"  # 可写性探针文件

        # 成功写入证明目录接受文件创建。
        path_probe.write_text("ok\n", encoding="utf-8")

        # 验证后立即删除探针，不污染目标项目。
        path_probe.unlink()

        # 创建与清理均成功才确认可写。
        return True

    # 权限、路径和文件系统错误均表示当前不可写。
    except Exception:

        # 探测函数不向状态查询调用方传播环境异常。
        return False

# 安装态治理目录解析在通用安装探测之上补充名称默认值和规范化。
def installed_governance_skill_dir(
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> Path | None:
    """解析已安装治理技能的规范目录。

    Args:
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        已安装技能绝对路径；未找到时为 None。
    """

    # 空名称沿用当前技能 frontmatter 中的治理身份。
    str_target_name = skill_name or governance_skill_name()  # 目标治理技能名

    # 通用安装探测负责处理显式覆盖和 CODEX_HOME 回退。
    path_installed = installed_skill_dir(str_target_name, override_dir=override_dir)  # 安装态候选目录

    # 对存在目录返回规范绝对路径，缺失状态保持 None。
    return path_installed.resolve() if path_installed is not None else None

# 演进模板优先写入 owner，本地不可用时降级到安装态或导出等待。
def evolution_template_sink(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:
    """选择演进模板的可写落点或导出等待模式。

    Args:
        project: 发起演进操作的项目根目录。
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        描述落点模式、模板目录和导入导出位置的报告。
    """

    # 演进落点使用同一技能名解析 owner 与安装态候选。
    str_target_name = skill_name or governance_skill_name()  # 演进落点技能名

    # owner 状态决定是否允许直接修改技能模板资产。
    dict_status = evolution_owner_status(  # 演进 owner 状态
        project,  # 发起演进的项目根
        skill_name=str_target_name,  # owner 状态技能名
        override_dir=override_dir,  # 演进 owner 安装覆盖值
    )

    # 落点报告统一关联发起演进的规范项目根。
    path_project_root = project.resolve()  # 演进源项目根目录

    # owner 项目直接使用其技能资产目录作为模板落点。
    if dict_status.get("enabled"):

        # owner 路径来自前置身份校验结果。
        path_owner_skill_dir = Path(str(dict_status.get("owner_skill_dir", ""))).resolve()  # owner 技能目录

        # 演进模板固定存放在技能资产树下。
        path_template_root = path_owner_skill_dir / "assets" / "templates" / "evolution"  # owner 模板目录

        # owner-local 报告包含实际可写性证据。
        return {
            "mode": "owner-local",
            "project_root": str(path_project_root),
            "owner_skill_dir": str(path_owner_skill_dir),
            "installed_skill_dir": str(path_owner_skill_dir),
            "template_root": str(path_template_root),
            "export_root": ".agents/evolution-export",
            "import_request_path": ".agents/evolution-import-request.json",
            "source_workspace": str(path_project_root),
            "writable": path_is_writable(path_template_root),
        }

    # 非 owner 项目可尝试把模板演进写入可写安装态技能。
    path_installed = installed_governance_skill_dir(  # 安装态治理技能目录
        str_target_name,  # 安装落点技能名
        override_dir=override_dir,  # 演进落点安装覆盖值
    )

    # 未安装时直接进入导出等待模式。
    if path_installed is not None:

        # 安装态模板遵循与源码 owner 相同的资产布局。
        path_template_root = path_installed / "assets" / "templates" / "evolution"  # 安装态模板目录

        # 只有真实可写的安装目录才能充当直接落点。
        if path_is_writable(path_template_root):

            # installed-sink 报告明确 owner 为空，避免误称源码所有权。
            return {
                "mode": "installed-sink",
                "project_root": str(path_project_root),
                "owner_skill_dir": "",
                "installed_skill_dir": str(path_installed),
                "template_root": str(path_template_root),
                "export_root": ".agents/evolution-export",
                "import_request_path": ".agents/evolution-import-request.json",
                "source_workspace": str(path_project_root),
                "writable": True,
            }

    # 没有可写技能目录时仅允许生成待导入的项目本地导出物。
    return {
        "mode": "export-pending",
        "project_root": str(path_project_root),
        "owner_skill_dir": "",
        "installed_skill_dir": str(path_installed) if path_installed is not None else "",
        "template_root": "",
        "export_root": ".agents/evolution-export",
        "import_request_path": ".agents/evolution-import-request.json",
        "source_workspace": str(path_project_root),
        "writable": True,
    }

# 安装态版本读取允许缺失，并保持空字符串兼容合同。
def read_installed_skill_version(
    skill_name: str = "agents-md-generator",
    override_dir: str | Path | None = None,
) -> str:
    """读取已安装技能的版本号。

    Args:
        skill_name: 技能目录名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        安装态版本号；目录不可用时为空字符串。
    """

    # 先解析实际安装目录，避免直接假设 CODEX_HOME 布局存在。
    path_installed = installed_skill_dir(skill_name, override_dir=override_dir)  # 安装态技能目录

    # 未安装状态不属于异常，由调用方选择其他版本来源。
    if path_installed is None:

        # 空值表示安装态版本不可用。
        return ""

    # 安装目录存在时复用统一 VERSION 读取合同。
    return read_skill_version(path_installed)

# 版本选择优先采用安装证据，再回退到当前运行时源码。
def preferred_skill_version(
    skill_name: str = "agents-md-generator",
    override_dir: str | Path | None = None,
) -> tuple[str, str]:
    """选择治理元数据采用的版本来源。

    Args:
        skill_name: 技能目录名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        首选版本号及其来源标签。
    """

    # 安装态版本是治理元数据的首选事实来源。
    str_installed = read_installed_skill_version(  # 安装态技能版本
        skill_name,  # 待读取版本的技能名
        override_dir=override_dir,  # 版本读取安装覆盖值
    )

    # 安装态存在时保留显式覆盖与默认安装两种来源标签。
    if str_installed:

        # 来源标签帮助生成物解释版本选择依据。
        return str_installed, "installed-override" if override_dir else "installed"

    # 运行时源码是安装态缺失后的第二优先级。
    str_runtime = read_skill_version()  # 当前运行时技能版本

    # 当前源码 VERSION 存在时作为回退证据。
    if str_runtime:

        # runtime 标签区分未安装的源码执行场景。
        return str_runtime, "runtime"

    # 两种来源均不可用时返回显式不可用状态。
    return "", "unavailable"

# 项目控制档案缺失时返回空对象，便于只读探测继续执行。
def project_profile(root: Path) -> dict[str, Any]:
    """读取项目的 agents-control 治理档案。

    Args:
        root: 项目根目录。

    Returns:
        治理档案对象；文件不可用时为空对象。
    """

    # 控制档案位置由项目根和固定治理目录合同决定。
    path_profile = root / ".agents" / "agents-control.json"  # 项目控制档案路径

    # 仅对真实文件调用严格 JSON 读取器。
    return read_json(path_profile) if path_profile.exists() else {}

# 首要项目根只从结构化目录合同读取。
def primary_project_root_from_profile(profile: dict[str, Any] | None) -> str:
    """从治理档案提取首要项目相对根。

    Args:
        profile: 可选治理档案。

    Returns:
        规范化的项目相对根字符串。
    """

    # 非字典输入没有可读取的目录合同。
    if not isinstance(profile, dict):

        # 空字符串表示没有配置首要项目根。
        return ""

    # 目录合同是治理档案中的独立结构化区块。
    dict_directory_contract = profile.get("directory_contract", {})  # 目录合同载荷

    # 异常类型不能参与路径拼接。
    if not isinstance(dict_directory_contract, dict):

        # 非法合同按未配置处理。
        return ""

    # 去除外围分隔符，保留项目相对根表达。
    return str(dict_directory_contract.get("primary_project_root", "")).strip().strip("/\\")

# 治理运行根优先指向源码 owner，否则使用安装态占位路径。
def governance_runtime_root(
    root: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> str:
    """确定项目应引用的治理技能运行根。

    Args:
        root: 当前项目根目录。
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        相对项目路径、绝对路径或 Codex 安装占位路径。
    """

    # 默认名称来自当前技能身份。
    str_target_name = skill_name or governance_skill_name()  # 运行根目标技能名

    # 运行根解析使用 owner 状态中的实际技能目录。
    dict_status = evolution_owner_status(  # 运行根 owner 状态
        root,  # 当前项目根
        skill_name=str_target_name,  # owner 路由技能身份
        override_dir=override_dir,  # 运行根安装覆盖值
    )

    # 已确认 owner 时尽量生成项目内相对路径。
    if dict_status.get("enabled"):

        # 状态报告中的 owner 路径已通过身份校验。
        path_owner_skill_dir = Path(str(dict_status.get("owner_skill_dir", ""))).resolve()  # 运行根 owner 目录

        # 当前项目根是 owner 相对路径的计算基准。
        path_resolved_root = root.resolve()  # 运行根相对基准

        # owner 即项目根时使用最短当前目录表达。
        if path_owner_skill_dir == path_resolved_root:

            # 点路径保持已有命令合同。
            return "."

        # 项目内 owner 优先返回可移植相对路径。
        try:

            # 正斜杠输出可直接嵌入治理命令。
            return path_owner_skill_dir.relative_to(path_resolved_root).as_posix()

        # 项目外 owner 无法相对化时保留绝对路径。
        except ValueError:

            # POSIX 表达避免 Windows 反斜杠影响命令文本。
            return path_owner_skill_dir.as_posix()

    # 非 owner 项目通过占位路径引用本地安装技能。
    return f"<codex-home>/skills/{str_target_name}"

# 脚本名称映射决定治理运行根下的任务子目录。
def governance_script_path(
    root: Path,
    script_name: str,
    *,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> str:
    """把治理脚本名映射到运行根中的任务目录。

    Args:
        root: 当前项目根目录。
        script_name: 目标脚本文件名。
        skill_name: 可选治理技能名。
        override_dir: 可选安装目录覆盖值。

    Returns:
        可用于命令行的治理脚本路径。
    """

    # owner 路由结果决定脚本路径前缀。
    str_runtime_root = governance_runtime_root(  # 治理运行根文本
        root,  # 脚本调用项目根
        skill_name=skill_name,  # 脚本路由技能身份
        override_dir=override_dir,  # 脚本路由安装覆盖值
    )

    # 技能自身运行时以当前目录为根，路径无需重复技能前缀。
    if str_runtime_root == ".":

        # 已知脚本名映射到 detect、docs 等任务目录。
        str_local_task_name = SCRIPT_TASK_BY_NAME.get(Path(script_name).name, "")  # 本地任务目录名

        # 已知任务使用分层脚本布局。
        if str_local_task_name:

            # 本地路径从 scripts/python 起算。
            return f"scripts/python/{str_local_task_name}/{script_name}"

        # 未知脚本保持兼容的 Python 根目录回退。
        return f"scripts/python/{script_name}"

    # 外部项目在治理运行根后附加相同任务布局。
    str_task_name = SCRIPT_TASK_BY_NAME.get(Path(script_name).name, "")  # 外部运行任务目录名

    # 已登记脚本使用所属任务目录。
    if str_task_name:

        # 运行根可能是绝对路径、相对路径或安装占位路径。
        return f"{str_runtime_root}/scripts/python/{str_task_name}/{script_name}"

    # 未登记脚本回退到治理运行根的 Python 目录。
    return f"{str_runtime_root}/scripts/python/{script_name}"

# 被治理项目优先使用根 scripts，工程子根则遵循目录合同。
def managed_scripts_root(root: Path, profile: dict[str, Any] | None = None) -> str:
    """定位被治理项目自身的脚本相对根。

    Args:
        root: 当前项目根目录。
        profile: 可选治理档案。

    Returns:
        项目脚本目录的正斜杠相对路径。
    """

    # 已存在的根脚本目录拥有最高优先级。
    if (root / "scripts").is_dir():

        # 返回项目相对路径，避免绑定绝对工作区。
        return "scripts"

    # 未提供有效档案时从项目控制文件加载。
    dict_effective_profile = profile if isinstance(profile, dict) else project_profile(root)  # 生效治理档案

    # 工程型项目可能把脚本放在首要项目子根内。
    str_primary_root = primary_project_root_from_profile(dict_effective_profile)  # 首要项目相对根

    # 仅在目录合同明确配置时拼接子根脚本目录。
    if str_primary_root:

        # 实际目录存在时从文件系统计算规范相对路径。
        path_primary_scripts = root / str_primary_root / "scripts"  # 首要项目脚本目录

        # 已落地目录使用 Path 的相对化结果。
        if path_primary_scripts.is_dir():

            # 正斜杠结果适用于跨平台命令和文档。
            return path_primary_scripts.relative_to(root).as_posix()

        # 未落地目录仍按合同返回预期路径。
        return f"{str_primary_root}/scripts"

    # 无目录合同的项目保持根 scripts 默认值。
    return "scripts"

# 治理命令始终通过解析后的治理运行时脚本路径执行。
def script_command(
    root: Path,
    script_name: str,
    *args: str,
    profile: dict[str, Any] | None = None,
    override_dir: str | Path | None = None,
) -> str:
    """构造调用治理脚本的 Python 命令。

    Args:
        root: 当前项目根目录。
        script_name: 目标治理脚本名。
        args: 传递给脚本的位置参数。
        profile: 保留的兼容参数，不参与运行路径选择。
        override_dir: 可选安装目录覆盖值。

    Returns:
        可复制执行的命令字符串。
    """
    # 治理运行命令不再通过目标项目 scripts 目录解析。
    del profile

    # 运行路径由 owner/安装态路由统一解析。
    str_script_path = governance_script_path(  # 治理脚本运行路径
        root,  # 命令目标项目根
        script_name,  # 命令目标脚本名
        override_dir=override_dir,  # 命令脚本安装覆盖值
    )

    # 空参数不进入最终命令，非空参数保持调用顺序。
    list_segments = [  # 命令分段
        "python",  # Python 解释器命令
        str_script_path,  # 治理脚本路径
        *[str(item) for item in args if str(item).strip()],  # 非空脚本参数
    ]

    # 单空格连接生成可复制的命令文本。
    return " ".join(list_segments)

# 根 AGENTS 同步命令可附带安装技能覆盖目录用于精确验证。
def root_agents_sync_command(
    root: Path,
    profile: dict[str, Any] | None = None,
    installed_skill_dir_override: str | Path | None = None,
) -> str:
    """构造项目根 AGENTS 同步命令。

    Args:
        root: 当前项目根目录。
        profile: 可选治理档案。
        installed_skill_dir_override: 可选安装目录覆盖值。

    Returns:
        带写入开关的同步命令。
    """

    # 根同步固定调用 manage_docs 的写入子命令。
    str_command = script_command(  # 根 AGENTS 同步命令
        root,  # 同步目标项目根
        "manage_docs.py",  # 文档治理入口
        "sync-root-agents",  # 根规则同步动作
        ".",  # 根同步项目参数
        "--write",  # 落盘项目根规则
        profile=profile,  # 兼容治理档案
        override_dir=installed_skill_dir_override,  # 安装技能覆盖目录
    )

    # 显式安装目录需要同时传给同步脚本作为验证证据。
    if installed_skill_dir_override is not None:

        # POSIX 路径避免反斜杠转义进入命令文本。
        str_command += (  # 附带安装技能目录的同步命令
            f" --installed-skill-dir {Path(installed_skill_dir_override).as_posix()}"  # 安装技能覆盖参数
        )

    # 返回完整写入命令供治理文档引用。
    return str_command

# 全局基线同步始终通过 manage_docs 的正式写入入口。
def global_codex_agents_sync_command(root: Path, profile: dict[str, Any] | None = None) -> str:
    """构造全局 Codex AGENTS 基线同步命令。

    Args:
        root: 当前项目根目录。
        profile: 可选治理档案。

    Returns:
        带写入开关的全局同步命令。
    """

    # 命令参数固定为当前项目和显式写入模式。
    return script_command(
        root,
        "manage_docs.py",
        "sync-global-codex-agents",
        ".",  # 当前项目同步目标
        "--write",  # 落盘全局 Codex 基线
        profile=profile,
    )

# 全局 AGENTS 路径固定在 Codex 主目录根部。
def global_codex_agents_path(codex_home: str | None = None) -> Path:
    """定位全局 Codex AGENTS 文件。

    Args:
        codex_home: 可选 Codex 主目录覆盖值。

    Returns:
        全局 AGENTS.md 路径。
    """

    # 主目录解析复用显式值、环境变量和用户默认值优先级。
    return codex_home_root(codex_home) / "AGENTS.md"

# 全局基线模板固定存放在技能资产目录。
def global_codex_agents_template_path(root: Path | None = None) -> Path:
    """定位技能内置的全局 AGENTS 模板。

    Args:
        root: 可选技能根目录。

    Returns:
        全局基线模板路径。
    """

    # 未指定根目录时使用当前技能运行时。
    return (root or skill_root()) / "assets" / "templates" / "global-codex-agents.md"

# 全局模板读取规范化尾部换行并验证包内资产存在。
def render_global_codex_agents_template(root: Path | None = None) -> str:
    """读取并规范化全局 AGENTS 模板文本。

    Args:
        root: 可选技能根目录。

    Returns:
        以单个换行结尾的模板内容。

    Raises:
        SystemExit: 模板文件缺失时终止命令。
    """

    # 模板路径由显式技能根或当前运行时根决定。
    path_template = global_codex_agents_template_path(root)  # 全局 AGENTS 模板路径

    # 缺失模板属于不可恢复的技能包完整性错误。
    if not path_template.is_file():

        # CLI 错误使用固定 Python 前缀。
        raise SystemExit(f"> ERR: [Python] Missing global Codex AGENTS template: {path_template}")

    # 输出统一保留且只保留一个尾部换行。
    return path_template.read_text(encoding="utf-8", errors="ignore").rstrip() + "\n"

# 受管区块提取要求起止标记均存在且顺序有效。
def extract_global_codex_managed_block(text: str) -> str:
    """提取全局 AGENTS 中完整的受管基线区块。

    Args:
        text: 全局 AGENTS 文件内容。

    Returns:
        含起止标记的区块；标记无效时为空字符串。
    """

    # 起始偏移用于验证标记完整性和切片边界。
    int_start = text.find(GLOBAL_CODEX_AGENTS_BLOCK_START)  # 受管区块起始偏移

    # 结束偏移先指向结束标记首字符。
    int_end = text.find(GLOBAL_CODEX_AGENTS_BLOCK_END)  # 受管区块结束偏移

    # 任一标记缺失或顺序反转均视为无有效区块。
    if int_start == -1 or int_end == -1 or int_end < int_start:

        # 空值让状态检查进入修复分支。
        return ""

    # 切片尾界扩展到完整结束标记之后。
    int_end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)  # 完整区块切片尾界

    # 返回值包含两端标记，供模板与现状直接比较。
    return text[int_start:int_end]

# 全局基线诊断器按互斥优先级返回首个修复原因和确认提示。
def global_codex_agents_repair_details(
    bool_exists: bool,
    bool_empty: bool,
    bool_managed: bool,
    bool_meta_ok: bool,
    str_actual_block: str,
    str_expected_block: str,
) -> tuple[list[str], bool, str]:
    """诊断全局 AGENTS 基线并返回确定性的首个修复动作。

    Args:
        bool_exists: 全局文件是否存在。
        bool_empty: 已存在文件是否为空。
        bool_managed: 文件是否包含完整受管边界。
        bool_meta_ok: 文件是否包含当前基线元标记。
        str_actual_block: 当前受管区块文本。
        str_expected_block: 当前技能期望的受管区块文本。

    Returns:
        修复原因列表、用户确认状态和确认提示文本。
    """

    # 缺失文件可直接用受管模板创建。
    if not bool_exists:

        # 缺失状态不涉及人工内容确认。
        return ["missing_global_codex_agents_md"], False, ""

    # 空文件同样可以安全写入完整模板。
    if bool_empty:

        # 空文件原因保留与缺失文件的诊断差异。
        return ["empty_global_codex_agents_md"], False, ""

    # 有人工内容但没有边界标记时必须确认插入位置。
    if not bool_managed:

        # 提示明确建议插入而不是覆盖现有文件。
        str_user_message = (  # 用户确认提示
            "Global .codex/AGENTS.md has manual content but no managed baseline block; "
            "insert the generated baseline block near the top of the file after any opening comments."
        )

        # 人工内容场景公开确认门禁及其唯一修复原因。
        return ["missing_global_codex_agents_managed_block"], True, str_user_message

    # 受管区块缺少当前 v5 元标记时需要版本升级。
    if not bool_meta_ok:

        # 元标记缺失优先于文本漂移诊断。
        return ["missing_global_codex_agents_v5_meta"], False, ""

    # 元标记存在但文本不同属于基线漂移。
    if str_actual_block != str_expected_block:

        # 文本漂移需要重新同步当前模板。
        return ["outdated_global_codex_agents_baseline"], False, ""

    # 基线完全一致时不需要修复或确认。
    return [], False, ""

# 全局状态报告区分缺失、空文件、无受管块和版本漂移。
def global_codex_agents_status(
    codex_home: str | None = None,
    project_root: Path | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """比较全局 AGENTS 与当前技能基线的状态。

    Args:
        codex_home: 可选 Codex 主目录覆盖值。
        project_root: 可选项目根目录。
        profile: 可选治理档案。

    Returns:
        包含存在性、版本和同步命令的状态报告。
    """

    # 全局文件路径允许测试通过 codex_home 覆盖。
    path_agents = global_codex_agents_path(codex_home)  # 全局 AGENTS 文件路径

    # 缺失文件使用空文本参与后续确定性判断。
    str_text = (  # 全局 AGENTS 文件文本
        path_agents.read_text(encoding="utf-8", errors="ignore")  # 已存在文件内容
        if path_agents.is_file()  # 全局 AGENTS 已存在
        else ""  # 缺失文件回退文本
    )

    # 存在性单独保留，避免混淆缺失与空文件。
    bool_exists = path_agents.is_file()  # 全局文件是否存在

    # 只有存在文件才可能进入空文件状态。
    bool_empty = bool_exists and not str_text.strip()  # 全局文件是否为空

    # 两端标记同时出现才声明文件受管。
    bool_managed = (  # 是否包含完整受管标记
        GLOBAL_CODEX_AGENTS_BLOCK_START in str_text  # 起始标记存在
        and GLOBAL_CODEX_AGENTS_BLOCK_END in str_text  # 结束标记存在
    )

    # 当前技能模板代表期望发布态基线。
    str_expected_block = extract_global_codex_managed_block(  # 当前模板受管区块
        render_global_codex_agents_template()  # 当前技能模板文本
    )

    # 实际区块仅在标记完整时提取。
    str_actual_block = extract_global_codex_managed_block(str_text) if bool_managed else ""  # 当前受管区块

    # v5 元标记是版本符合性的独立证据。
    bool_meta_ok = GLOBAL_CODEX_AGENTS_META in str_text  # v5 元标记是否存在

    # 通过状态要求受管、版本正确且区块文本完全一致。
    bool_baseline_ok = bool_managed and bool_meta_ok and str_actual_block == str_expected_block  # 基线是否一致

    # 诊断器保持修复原因优先级并隔离人工内容确认分支。
    tuple_repair_details = global_codex_agents_repair_details(  # 全局基线修复诊断元组
        bool_exists,  # 文件存在性
        bool_empty,  # 空文件状态
        bool_managed,  # 受管边界状态
        bool_meta_ok,  # v4 版本证据判断
        str_actual_block,  # 现状文本比较输入
        str_expected_block,  # 模板文本比较输入
    )

    # 首项保存唯一的修复原因列表。
    list_repair_reasons = tuple_repair_details[0]  # 全局基线修复原因

    # 第二项控制人工内容场景的用户确认门禁。
    bool_requires_user_confirmation = tuple_repair_details[1]  # 是否需要用户确认

    # 末项提供需要确认时的可执行提示。
    str_user_message = tuple_repair_details[2]  # 全局基线修复提示

    # 任一诊断原因都表示基线需要修复。
    bool_repair_required = bool(list_repair_reasons)  # 是否需要修复全局基线

    # 同步命令在状态和建议动作中复用，避免两处 fallback 文本漂移。
    str_repair_command = (  # 全局 AGENTS 同步修复命令
        global_codex_agents_sync_command(project_root, profile)  # 多行表达式输入文本
        if project_root  # 项目根存在时使用仓库内命令
        else (  # 项目根缺失时使用已安装治理运行时占位命令
            f"python {INSTALLED_GOVERNANCE_RUNTIME_PLACEHOLDER}/scripts/python/docs/manage_docs.py "  # 已安装治理运行时脚本前缀
            "sync-global-codex-agents . --write"  # 全局 AGENTS 基线写入动作
        )
    )

    # 返回稳定字段供 inspect、render 和 verify 入口共享。
    return {
        "path": str(path_agents),
        "exists": bool_exists,
        "empty": bool_empty,
        "managed": bool_managed,
        "baseline_version": "5" if bool_meta_ok else "",
        "baseline_ok": bool_baseline_ok,
        "repair_required": bool_repair_required,
        "repair_reasons": list_repair_reasons,
        "repair_command": str_repair_command,
        "recommended_action": str_repair_command,
        "requires_user_confirmation": bool_requires_user_confirmation,
        "user_message": str_user_message,
    }

# 元数据解析只接受生成器注释区块中的分号分隔键值。
def parse_agents_metadata(text: str) -> dict[str, str]:
    """解析 AGENTS-METADATA 注释中的键值对。

    Args:
        text: AGENTS 文件内容。

    Returns:
        元数据键值映射；标记缺失时为空映射。
    """

    # 首个元数据区块作为根 AGENTS 的权威声明。
    match_metadata = AGENTS_METADATA_RE.search(text)  # 元数据区块匹配

    # 缺失标记时返回空映射供调用方报告未治理状态。
    if not match_metadata:

        # 探测函数不因缺失元数据抛出异常。
        return {}

    # 捕获组仅包含注释标记内部的键值正文。
    str_body = match_metadata.group(1)  # 元数据正文

    # 结果映射保留最后一次出现的同名字段。
    dict_data: dict[str, str] = {}  # 已解析元数据映射

    # 每个匹配项分别清理键和值外围空白。
    for str_key, str_raw_value in AGENTS_METADATA_PAIR_RE.findall(str_body):

        # 规范化字段后写入稳定字符串映射。
        dict_data[str_key.strip()] = str_raw_value.strip()  # 规范化元数据字段

    # 返回解析完成的元数据字段。
    return dict_data

# 相对路径输出统一使用正斜杠。
def rel(path: Path, root: Path) -> str:
    """生成相对项目根的正斜杠路径。

    Args:
        path: 待转换路径。
        root: 项目根目录。

    Returns:
        相对路径字符串。
    """

    # 两端先规范化再计算相对关系。
    return path.resolve().relative_to(root.resolve()).as_posix()

# 展示路径优先相对项目根，路径不在项目内时回退绝对路径。
def display_path(path: Path, root: Path | None = None) -> str:
    """生成优先相对、必要时绝对的展示路径。

    Args:
        path: 待展示路径。
        root: 可选相对基准目录。

    Returns:
        采用正斜杠的路径字符串。
    """

    # 有相对基准时先尝试生成更短的项目内表达。
    if root is not None:

        # Path.relative_to 只在目标位于基准目录下时成功。
        try:

            # 项目内路径使用正斜杠相对表示。
            return path.resolve().relative_to(root.resolve()).as_posix()

        # 项目外路径属于预期情况，继续使用绝对表示。
        except ValueError:

            # 不需要修复异常，仅选择下方展示回退。
            root = None  # 禁用不可用的相对路径基准

    # 无可用相对表达时返回规范绝对路径。
    return path.resolve().as_posix()

# 路径比较键统一展开用户目录、解析点段并应用平台大小写规则。
def normalize_path_key(raw: str | Path) -> str:
    """规范化用于路径比较和去重的键。

    Args:
        raw: 原始路径值。

    Returns:
        去除冗余分隔符和点段的路径字符串。
    """

    # 字符串化后先去除调用方传入的外围空白。
    str_raw_value = str(raw).strip()  # 原始路径文本

    # 空路径不能参与文件系统解析。
    if not str_raw_value:

        # 空输入保持为空比较键。
        return ""

    # resolve 失败时保留已展开用户目录的非严格路径。
    try:

        # 正常路径解析为规范绝对形式。
        path_resolved = Path(str_raw_value).expanduser().resolve()  # 规范化路径

    # 非法或环境相关路径仍可形成稳定的词法键。
    except Exception:

        # 回退路径不访问文件系统真实性。
        path_resolved = Path(str_raw_value).expanduser()  # 词法回退路径

    # Windows 下折叠大小写，其他平台保持原语义。
    return os.path.normcase(str(path_resolved))

# 工作区内容探测忽略治理文件、缓存和构建产物。
def workspace_has_existing_content(root: Path) -> bool:
    """判断工作区是否包含应保留的既有项目内容。

    Args:
        root: 工作区根目录。

    Returns:
        排除缓存与构建目录后仍有内容时为 True。
    """

    # .agents 属于治理状态，不证明业务项目已经落地。
    set_ignored = set(SKIP_DIRS) | {".agents"}  # 内容探测排除名称

    # 根目录任一非排除项即可证明存在需保留内容。
    for path_entry in root.iterdir():

        # 缓存、依赖和治理状态不计入业务内容。
        if path_entry.name in set_ignored:

            # 排除项继续扫描其他根目录成员。
            continue

        # 单独存在的根 AGENTS 也不代表项目实现已落地。
        if path_entry.name == "AGENTS.md":

            # 控制文件之外仍需寻找真实项目内容。
            continue

        # 找到第一个业务项即可结束探测。
        return True

    # 所有根目录成员均被排除时视为新工作区。
    return False

# 包管理器识别优先采用 packageManager 声明，再按锁文件证据排序。
def package_manager(root: Path) -> str:
    """依据项目声明与锁文件识别包管理器。

    Args:
        root: 项目根目录。

    Returns:
        npm、pnpm、yarn 或 bun 名称。
    """

    # package.json 提供显式包管理器声明。
    dict_package_json = read_json(root / "package.json")  # 包清单载荷

    # packageManager 字段可以显式携带工具名和版本。
    str_field = dict_package_json.get("packageManager", "")  # 包管理器及版本声明

    # 合法声明优先于任何锁文件推断。
    if isinstance(str_field, str) and "@" in str_field:

        # @ 前缀部分是规范工具名。
        return str_field.split("@", 1)[0]

    # 证据表顺序保留现有前端、后端和语言工具优先级。
    tuple_manager_evidence = (  # 包管理器文件证据
        ("pnpm", ("pnpm-lock.yaml",)),  # pnpm 锁文件证据
        ("yarn", ("yarn.lock",)),  # Yarn 通过唯一锁文件识别
        ("bun", ("bun.lockb", "bun.lock")),  # Bun 新旧锁文件证据
        ("npm", ("package-lock.json", "package.json")),  # npm 锁文件或包清单证据
        ("composer", ("composer.json",)),  # Composer 包清单证据
        ("uv", ("uv.lock",)),  # uv 项目由专用锁文件识别
        ("poetry", ("poetry.lock",)),  # Poetry 项目依赖其锁定清单
        ("go", ("go.mod",)),  # Go 模块清单证据
    )

    # 首个存在任一证据文件的工具即为识别结果。
    for str_manager, tuple_filenames in tuple_manager_evidence:

        # 同一工具允许多个等价锁文件名称。
        if any((root / str_filename).exists() for str_filename in tuple_filenames):

            # 返回值与历史分支保持一致。
            return str_manager

    # 无声明或锁文件证据时明确返回 unknown。
    return "unknown"

# 项目脚本执行前缀覆盖常用 JavaScript 包管理器。
def pm_run(pm: str) -> str:
    """返回包管理器执行项目脚本的命令前缀。

    Args:
        pm: 包管理器名称。

    Returns:
        对应的 run 命令片段。
    """

    # 未识别工具保持 npm run 兼容默认值。
    return {"pnpm": "pnpm", "yarn": "yarn", "bun": "bun run"}.get(pm, "npm run")

# 临时依赖执行前缀映射到各工具的原生命令。
def pm_dlx(pm: str) -> str:
    """返回包管理器临时执行依赖的命令前缀。

    Args:
        pm: 包管理器名称。

    Returns:
        对应的 dlx 或 npx 命令片段。
    """

    # 未识别工具使用 npm 生态的 npx 回退。
    return {"pnpm": "pnpm dlx", "yarn": "yarn dlx", "bun": "bunx"}.get(pm, "npx")

# Git 调用固定捕获文本输出且不因非零退出码抛出异常。
def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """在项目目录执行非交互 Git 子命令。

    Args:
        root: Git 工作目录。
        args: git 后续参数。

    Returns:
        捕获文本输出的进程结果。
    """

    # 调用方根据 returncode、stdout 和 stderr 决定治理结果。
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

# 日粒度治理记录使用本地日期的 ISO 表达。
def today() -> str:
    """返回当前本地日期。

    Args:
        无。

    Returns:
        YYYY-MM-DD 日期字符串。
    """

    # ISO 日期保持 YYYY-MM-DD 稳定格式。
    return date.today().isoformat()

# 秒粒度治理事件使用不带微秒的本地 ISO 时间。
def current_timestamp() -> str:
    """返回当前秒级本地时间戳。

    Args:
        无。

    Returns:
        ISO 8601 时间字符串。
    """

    # 秒精度足以区分治理事件且避免无意义微秒噪声。
    return datetime.now().isoformat(timespec="seconds")

# 通用 CLI 解析器统一提供可选项目根位置参数。
def parse_args(description: str) -> argparse.ArgumentParser:
    """创建带统一项目参数的命令行解析器。

    Args:
        description: 命令帮助摘要。

    Returns:
        已注册 project 位置参数的解析器。
    """

    # 调用方描述文本直接进入 argparse 帮助摘要。
    argument_parser = argparse.ArgumentParser(description=description)  # 通用参数解析器

    # 项目参数默认当前目录，保持现有脚本直接执行合同。
    argument_parser.add_argument("project", nargs="?", default=".", help="Target project directory")

    # 调用方可继续在返回解析器上注册专用参数。
    return argument_parser

# 项目事实能力在本模块基础合同定义完成后导入，避免循环导入初始化失败。
from agents_project_facts import (
    # 项目命令、默认约束和分解计划事实。
    command_entry,
    default_implementation_constraints,
    default_global_rule_overrides,
    decomposition_plan_path,
    detect_scopes,
    ensure_global_rule_overrides_file,
    # 路径、命令、上下文和全局规则事实。
    existing_paths,
    extract_commands,
    extract_context,
    global_rule_overrides_path,
    global_rule_overrides_reference,
    has_any,
    # 实现约束、项目探测和源码文件遍历能力。
    implementation_constraints_from_profile,
    inspect_project,
    iter_handwritten_code_files,
    list_dirs,
    list_files,
    load_global_rule_overrides,
    # 脚本根、会话和脚本治理事实。
    managed_script_roots,
    matched_codex_sessions,
    parse_session_meta,
    script_governance_exceptions,
    script_layout_facts,
    # 会话消息、覆盖校验和工作流记录能力。
    session_message_rows,
    validate_global_rule_overrides_data,
    workflow_runs,
)
