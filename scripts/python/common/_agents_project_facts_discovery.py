"""发现项目文件、会话、工具链和可执行命令事实。"""

# 延迟注解求值，支持分片在聚合模块命名空间内执行。
from __future__ import annotations

# 标准库提供 JSON、模式匹配、路径与类型合同。
import json
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

# 项目共享层提供发现流程所需的稳定公共合同。
from agents_common import (
    # 文件树和会话发现使用的基础路径合同。
    SKIP_DIRS,
    codex_sessions_root,
    display_path,
    global_codex_agents_status,
    managed_scripts_root,
    normalize_path_key,
    # 包管理器和项目配置识别合同。
    package_manager,
    parse_agents_metadata,
    pm_dlx,
    pm_run,
    project_profile,
    # 技能版本、JSON 与显示路径读取合同。
    read_installed_skill_version,
    read_json,
    read_skill_version,
    rel,
    root_agents_sync_command,
    workspace_has_existing_content,
)

# 源码治理报告补充项目实现边界事实。
from source_governance import source_governance_report

# 源码治理配置模块保留兼容的公开转发符号。
import source_governance_config

# 配置合同用于生成和验证项目级规则覆盖。
from source_governance_config import (
    # 默认配置生成与引用解析合同。
    default_global_rule_overrides,
    default_implementation_constraints,
    global_rule_overrides_path,
    global_rule_overrides_reference,
    implementation_constraints_from_profile,
    # 配置加载及数据验证合同。
    load_global_rule_overrides,
    validate_code_comment_policy_data,
    validate_global_rule_overrides_data,
)

# 工作区设置发现器区分本地配置和可部署制品。
from workspace_settings_policy import discover_workspace_settings

# 解析 模块入口 需要的 EPHEMERAL ROOT INPUT FILE RE 项目事实。
EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(  # 项目事实扫描渲染输入值
    (
        r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|"  # 临时输入前缀集合
        r"blocked-change|blocked-remote-change|blocked-remote-source-change)"  # 阻断场景输入前缀集合
        r"(?:-[a-z0-9._-]+)?\.json$"  # 临时输入可选后缀
    ),  # 项目事实扫描临时输入文件模式
    flags=re.IGNORECASE,  # 临时输入前缀不区分大小写。
)

# 兼容治理流程常用的受控根级输入文件名。
ALLOWED_ROOT_FILE_PATTERNS = (
    "answers.json",  # 标准问答输入。
    "*-answers.json",  # 带场景前缀的问答输入。
    "change.json",  # 标准目录变更输入。
    "*-change.json",  # 带状态前缀的变更输入。
    "session.json",  # 会话启动输入。
    "recovery.json",  # 中断恢复输入。
    "handoff.json",  # 交接生成输入。
    "stage.json",  # Git 暂存输入。
    "changelog.json",  # 发布说明输入。
)

# 会话元数据读取器为精确工作目录匹配提供身份事实。
def parse_session_meta(path: Path) -> dict[str, Any]:
    """读取会话 JSONL 中的首个 session_meta 载荷。

    参数：path 为候选会话记录文件。
    返回：有效 payload 映射；无有效元数据或读取失败时返回空映射。
    """

    # 会话历史可能包含截断文件，读取失败按无元数据处理。
    try:

        # 使用宽容解码逐行读取，不让单个非法字符阻断发现流程。
        with path.open("r", encoding="utf-8", errors="ignore") as handle:

            # session_meta 通常位于文件开头，但仍按行查找以兼容旧记录。
            for str_raw in handle:

                # 将当前 JSONL 行解析为事件对象。
                dict_data = json.loads(str_raw)  # 当前会话记录行。

                # 仅 session_meta 事件包含权威会话身份和工作目录。
                if dict_data.get("type") != "session_meta":

                    # 跳过消息和响应事件，继续寻找元数据。
                    continue

                # 提取事件载荷，并拒绝非对象格式。
                payload = dict_data.get("payload", {})  # 候选元数据对象。

                # 有效对象可直接作为会话匹配事实返回。
                if isinstance(payload, dict):

                    # 首个有效元数据事件是该文件的权威身份。
                    return payload

    # 历史文件缺失、损坏或包含非法 JSON 时视为不可匹配。
    except Exception:

        # 空映射让上层发现器安全跳过当前文件。
        return {}

    # 文件读取成功但没有 session_meta 时同样没有匹配证据。
    return {}

# 会话匹配器只接受 cwd 与项目根完全相同的历史记录。
def matched_codex_sessions(root: Path) -> list[dict[str, str]]:
    """查找工作目录与项目根精确匹配的 Codex 会话。

    参数：root 为待匹配项目根目录。
    返回：按发现顺序排列的会话摘要列表。
    """

    # 定位本机 Codex 会话历史根目录。
    sessions_root = codex_sessions_root()  # 可能不存在于新环境。

    # 没有会话历史目录时无需递归扫描。
    if not sessions_root.is_dir():

        # 空列表明确表示未发现精确工作目录会话。
        return []

    # 规范化目标项目路径，消除大小写和分隔符差异。
    key = normalize_path_key(root)  # 当前项目匹配键。

    # 汇总精确匹配会话，供后续恢复与历史事实分析。
    list_matches: list[dict[str, str]] = []  # 精确匹配会话摘要。

    # 按路径排序扫描所有会话文件，保证输出顺序可复现。
    for path in sorted(sessions_root.rglob("*.jsonl")):

        # 只读取每个文件的会话身份载荷。
        dict_payload = parse_session_meta(path)  # 当前文件的身份载荷。

        # 缺失或损坏元数据的历史文件不能参与匹配。
        if not dict_payload:

            # 继续检查其他独立会话记录。
            continue

        # 规范化会话声明的工作目录以执行精确比较。
        cwd_key = normalize_path_key(  # 当前会话工作目录匹配键。
            dict_payload.get("cwd", "")  # 会话声明的原始 cwd。
        )

        # 仅保留工作目录与项目根完全相同的会话。
        if not cwd_key or cwd_key != key:

            # 排除父目录、子目录和无工作目录记录。
            continue

        # 保存稳定的会话身份和记录文件证据。
        list_matches.append(
            {
                "id": str(dict_payload.get("id", "")).strip(),  # 会话标识。
                "cwd": str(dict_payload.get("cwd", "")).strip(),  # 原始工作目录。
                "timestamp": str(dict_payload.get("timestamp", "")).strip(),  # 创建时间。
                "path": path.resolve().as_posix(),  # 会话记录绝对路径。
            }
        )

    # 返回按文件路径稳定排序的精确匹配集合。
    return list_matches

# 消息提取器提供有限且稳定的历史上下文窗口。
def session_message_rows(path: Path, limit: int = 48) -> list[dict[str, str]]:
    """提取会话记录中有限数量的用户与助手消息。

    参数：path 为会话 JSONL 文件，limit 为最大消息数量。
    返回：按记录顺序排列的角色与文本映射列表。
    """

    # 按事件顺序累计可用于上下文分析的对话消息。
    list_rows: list[dict[str, str]] = []  # 最多保留 limit 条。

    # 会话文件可能在写入中或已截断，读取失败安全回退。
    try:

        # 宽容解码保留尽可能多的历史消息证据。
        with path.open("r", encoding="utf-8", errors="ignore") as handle:

            # 逐行处理 JSONL，单行损坏不影响后续事件。
            for str_raw in handle:

                # JSON 解析错误只淘汰当前行。
                try:

                    # 解析当前事件对象。
                    dict_data = json.loads(str_raw)  # 当前待分类的事件对象。

                # 保持对历史损坏行的兼容容错行为。
                except Exception:

                    # 继续读取同一会话的后续有效行。
                    continue

                # 只有 event_msg 承载用户或助手可见消息。
                if dict_data.get("type") != "event_msg":

                    # 跳过会话元数据和工具响应等其他记录类型。
                    continue

                # 提取消息事件载荷。
                payload = dict_data.get("payload", {})  # 候选消息对象。

                # 非对象载荷无法提供命名消息字段。
                if not isinstance(payload, dict):

                    # 跳过非法载荷并继续扫描。
                    continue

                # 规范化事件内消息类型以映射对话角色。
                message_type = str(payload.get("type", "")).strip()  # 原始消息类别。

                # 仅公开用户和代理消息，其他事件映射为空角色。
                role = (  # 标准对话角色。
                    "user"  # 用户输入角色。
                    if message_type == "user_message"  # 用户消息事件。
                    else "assistant"  # 代理输出角色。
                    if message_type == "agent_message"  # 助手消息事件。
                    else ""  # 工具或状态事件不进入消息列表。
                )

                # 提取并清理可见消息文本。
                message = str(payload.get("message", "")).strip()  # 空白消息视为空。

                # 无有效角色或文本的事件不构成对话行。
                if not role or not message:

                    # 继续寻找下一条用户或助手消息。
                    continue

                # 保存标准角色和完整消息文本。
                list_rows.append(  # 保持原始事件顺序。
                    {"role": role, "message": message}
                )

                # 达到调用方上限后停止读取大体积会话文件。
                if len(list_rows) >= limit:

                    # 已收集足够的有限上下文窗口。
                    break

    # 文件访问或外层迭代失败时不提供部分会话结果。
    except Exception:

        # 空列表表示消息历史不可可靠读取。
        return []

    # 返回不超过限制的有效消息序列。
    return list_rows

# 文件快照限制扫描深度并排除治理忽略目录。
def list_files(root: Path, max_depth: int = 3) -> list[str]:
    """递归列出限定深度内未被忽略的项目文件。

    参数：root 为项目根，max_depth 为最大相对目录深度。
    返回：稳定排序的仓库相对文件路径列表。
    """

    # 累计符合忽略和深度约束的相对文件路径。
    list_out: list[str] = []  # 最终按字典序返回。

    # 遍历项目树并在结果层过滤治理忽略目录。
    for path in root.rglob("*"):

        # 缓存相对路径组成，供忽略和深度规则复用。
        set_parts = set(path.relative_to(root).parts)  # 当前路径组成集合。

        # 任一组成属于跳过目录时排除整个成员。
        if set_parts & SKIP_DIRS:

            # 不把缓存、版本控制或构建目录暴露为项目事实。
            continue

        # 超过扫描深度的成员不进入轻量项目快照。
        if len(path.relative_to(root).parts) > max_depth:

            # 深层源码由专用治理扫描器负责。
            continue

        # 仅文件成员加入文件事实列表。
        if path.is_file():

            # 保存跨平台统一的项目相对路径。
            list_out.append(rel(path, root))  # 当前有效文件。

    # 稳定排序保证渲染和测试结果可复现。
    return sorted(list_out)

# 目录快照为渲染和治理验证提供轻量结构事实。
def list_dirs(root: Path, max_depth: int = 2) -> list[str]:
    """递归列出限定深度内未被忽略的项目目录。

    参数：root 为项目根，max_depth 为最大相对目录深度。
    返回：稳定排序的仓库相对目录路径列表。
    """

    # 累计符合忽略和深度约束的相对目录路径。
    list_out: list[str] = []  # 目录快照最终按字典序返回。

    # 遍历项目树并只处理目录成员。
    for path in root.rglob("*"):

        # 文件成员不属于目录事实集合。
        if not path.is_dir():

            # 继续检查下一个文件系统成员。
            continue

        # 计算仓库相对路径供过滤和输出复用。
        relative = path.relative_to(root)  # 当前目录相对位置。

        # 排除缓存、版本控制和构建产物目录。
        if set(relative.parts) & SKIP_DIRS:

            # 忽略目录及其后代不应成为项目结构事实。
            continue

        # 只保留调用方要求深度内的目录。
        if len(relative.parts) <= max_depth:

            # 输出统一使用正斜杠形式。
            list_out.append(relative.as_posix())  # 当前有效目录。

    # 稳定排序保证结构事实可比较。
    return sorted(list_out)

# 多候选存在性检查用于识别工具链配置族。
def has_any(root: Path, names: list[str]) -> bool:
    """判断项目根下是否存在任一候选相对路径。

    参数：root 为项目根，names 为候选相对路径列表。
    返回：至少一个候选存在时为真。
    """

    # 任一候选存在即可证明对应工具或配置族存在。
    return any(  # 短路返回首个存在性证据。
        (root / name).exists()  # 将候选解析到项目根。
        for name in names  # 按调用方候选顺序检查。
    )

# 候选筛选器保留声明顺序以稳定输出协议。
def existing_paths(root: Path, names: list[str]) -> list[str]:
    """筛选项目根下真实存在的候选相对路径。

    参数：root 为项目根，names 为候选相对路径列表。
    返回：保持输入顺序的已存在路径列表。
    """

    # 保持候选声明顺序，仅筛除不存在的路径。
    return [
        name  # 返回原始相对路径文本。
        for name in names  # 遍历全部候选。
        if (root / name).exists()  # 只保留真实文件系统成员。
    ]

# 根文件白名单同时支持项目声明和受控临时输入命名。
def is_allowed_root_file(name: str, allowed_root_files: set[str]) -> bool:
    """判断根级文件是否属于允许集合或临时输入模式。

    参数：name 为根级文件名，allowed_root_files 为项目允许集合。
    返回：文件名被治理规则允许时为真。
    """

    # 清理调用方文件名空白，避免绕过精确和模式匹配。
    normalized = str(name).strip()  # 规范根级文件名。

    # 项目计划显式允许的根文件优先放行。
    if normalized in allowed_root_files:

        # 精确白名单命中无需再检查临时模式。
        return True

    # 治理工作流生成的临时 JSON 输入按受控命名放行。
    if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(normalized):

        # 命名正则已限制前缀、字符和扩展名。
        return True

    # 最后检查兼容的固定文件名和通配模式。
    return any(  # 任一兼容模式命中即允许。
        fnmatch(normalized, pattern)  # 对规范文件名执行模式匹配。
        for pattern in ALLOWED_ROOT_FILE_PATTERNS  # 遍历受控根文件模式。
    )

# JavaScript 识别器根据依赖键返回框架和项目类型。
def javascript_stack(root: Path) -> dict[str, Any]:
    """识别 package.json 项目的语言、框架和类型。

    参数：root 为项目根目录。
    返回：不存在包配置时为空映射，否则返回 TypeScript 栈事实。
    """

    # package.json 是 JavaScript 栈识别的权威输入。
    dict_package = read_json(root / "package.json")  # 包项目配置。

    # 无包配置时不覆盖其他生态事实。
    if not dict_package:

        # 空映射表示未发现 JavaScript 栈。
        return {}

    # 合并运行和开发依赖以识别框架。
    dict_dependencies: dict[str, Any] = {}  # 全部依赖键。

    # 两类依赖都可能声明项目框架。
    for str_key in ("dependencies", "devDependencies"):

        # 当前依赖分组必须是对象才能合并。
        dict_value = dict_package.get(str_key, {})  # 候选依赖映射。

        # 非对象依赖字段不提供包名事实。
        if isinstance(dict_value, dict):

            # 版本值不影响框架键存在判断。
            dict_dependencies.update(dict_value)

    # 框架分类按特异性从高到低匹配。
    if "next" in dict_dependencies:

        # Next.js 使用专用框架和项目类型。
        return {"framework": "next.js", "project_type": "typescript-nextjs"}

    # React 依赖证明通用 React 前端项目。
    if "react" in dict_dependencies:

        # 返回 React 项目栈事实。
        return {"framework": "react", "project_type": "typescript-react"}

    # Vue 依赖证明 Vue 前端项目。
    if "vue" in dict_dependencies:

        # Vue 命中后公开其前端框架分类。
        return {"framework": "vue", "project_type": "typescript-vue"}

    # Express 依赖证明 Node 服务项目。
    if "express" in dict_dependencies:

        # 返回 Express 服务栈事实。
        return {"framework": "express", "project_type": "typescript-node"}

    # 未识别框架时仍保留通用 TypeScript 项目事实。
    return {"framework": "none", "project_type": "typescript"}

# PHP 识别器依据 Composer 类型和依赖返回框架事实。
def php_stack(root: Path) -> dict[str, Any]:
    """识别 Composer 项目的框架和项目类型。

    参数：root 为项目根目录。
    返回：不存在 Composer 配置时为空映射，否则返回 PHP 栈事实。
    """

    # PHP 框架判断只信任项目 Composer 清单。
    dict_composer = read_json(root / "composer.json")  # PHP 依赖与包类型配置。

    # 无有效配置时不覆盖先前生态事实。
    if not dict_composer:

        # 缺失 Composer 事实时退出 PHP 分类。
        return {}

    # require 必须是对象才能检查框架包名。
    dict_require = (  # PHP 运行依赖。
        dict_composer.get("require", {})  # 读取运行依赖字段。
        if isinstance(dict_composer.get("require"), dict)  # 仅接受对象。
        else {}  # 非对象依赖不提供框架包证据。
    )

    # Composer 类型用于区分 TYPO3 扩展。
    str_composer_type = str(  # TYPO3 扩展识别所需包类型。
        dict_composer.get("type", "")  # 读取 Composer 顶层包类型。
    )

    # TYPO3 入口或核心依赖均证明 TYPO3 项目。
    if (root / "ext_emconf.php").exists() or "typo3/cms-core" in dict_require:

        # 扩展类型保留专用项目分类。
        str_project_type = (  # TYPO3 项目类型。
            "php-typo3-extension"  # TYPO3 扩展项目。
            if str_composer_type == "typo3-cms-extension"  # 扩展包类型。
            else "php-typo3"  # 普通 TYPO3 项目。
        )

        # 返回 TYPO3 框架事实。
        return {"framework": "typo3", "project_type": str_project_type}

    # Laravel 核心依赖证明 Laravel 项目。
    if "laravel/framework" in dict_require:

        # 返回 Laravel 栈事实。
        return {"framework": "laravel", "project_type": "php-laravel"}

    # Symfony bundle 依赖证明 Symfony 项目。
    if "symfony/framework-bundle" in dict_require:

        # Symfony 命中后公开专用 PHP 类型。
        return {"framework": "symfony", "project_type": "php-symfony"}

    # 未识别框架时保留通用 PHP 类型且不覆盖既有框架。
    return {"framework": "", "project_type": "php"}

# 项目栈发现器从配置、技能入口和 CI 文件汇总基础技术事实。
def project_stack_facts(root: Path) -> dict[str, Any]:
    """识别项目配置、语言、框架、类型、CI 与 AI 配置。

    参数：root 为项目根目录。
    返回：供项目检查入口合并的基础技术事实映射。
    """

    # 常见生态配置只在真实存在时加入输出。
    list_config_files = [
        str_name  # 保留标准相对文件名。
        for str_name in [  # 受支持配置候选。
            "package.json",  # JavaScript 包清单用于识别脚本与前端框架。
            "pnpm-lock.yaml",  # pnpm 锁文件用于确认实际包管理器。
            "package-lock.json",  # npm 依赖解析快照。
            "yarn.lock",  # Yarn 安装所需的确定性版本记录。
            "bun.lock",  # Bun 文本锁文件用于确认 Bun 工具链。
            "bun.lockb",  # Bun 二进制锁文件用于兼容旧版工具链。
            "pyproject.toml",  # Python 配置用于识别框架和质量工具。
            "uv.lock",  # uv 解析生成的 Python 锁定结果。
            "poetry.lock",  # Poetry 环境复现使用的依赖锁定结果。
            "composer.json",  # Composer 使用的 PHP 包清单。
            "go.mod",  # Go 模块清单用于识别后端语言与命令。
            "Makefile",  # Makefile 用于发现仓库公开的标准任务。
            "justfile",  # Just 命令配方入口。
        ]
        if (root / str_name).exists()  # 仅公开实际文件。
    ]

    # 工作区设置由专用策略发现并追加。
    list_config_files.extend(discover_workspace_settings(root))

    # 语言顺序表达主语言优先级。
    list_languages: list[str] = []  # 配置驱动语言集合。

    # 缺少框架证据时保持显式 none。
    str_framework = "none"  # 当前框架识别结果。

    # 缺少项目类型证据时保持 unknown。
    str_project_type = "unknown"  # 当前项目类型。

    # JavaScript 专用识别器返回框架和项目类型。
    dict_javascript = javascript_stack(root)  # 包项目栈事实。

    # 有效包配置保持 TypeScript 语言优先级。
    if dict_javascript:

        # 包项目语言沿用既有 TypeScript 标识。
        list_languages.append("typescript")

        # JavaScript 识别结果初始化框架和项目类型。
        str_framework = str(dict_javascript["framework"])  # 包项目框架。

        # 包项目类型与框架识别结果保持配套。
        str_project_type = str(dict_javascript["project_type"])  # 包项目类型。

    # pyproject 存在时补充 Python 语言与框架。
    path_pyproject = root / "pyproject.toml"  # Python 工具命令发现配置。

    # 配置存在才读取 Python 工具和依赖文本。
    if path_pyproject.exists():

        # 多生态仓库在既有语言后追加 Python。
        list_languages.append("python")

        # 小写配置文本用于框架关键词匹配。
        str_pyproject = path_pyproject.read_text(  # Python 配置文本。
            encoding="utf-8",  # Python 配置文本编码。
            errors="ignore",  # 忽略个别非法字节。
        ).lower()

        # Python Web 框架按明确关键词分类。
        if "django" in str_pyproject:

            # Django 依赖优先确定 Python Web 框架。
            str_framework = "django"  # 保存 Django 分类结果。

        # 未命中 Django 时检查 FastAPI。
        elif "fastapi" in str_pyproject:

            # FastAPI 依赖确定异步 API 框架分类。
            str_framework = "fastapi"  # 标记该项目采用异步 API 框架。

        # 最后检查 Flask 框架声明。
        elif "flask" in str_pyproject:

            # Flask 依赖确定轻量 Web 框架分类。
            str_framework = "flask"  # 标记该项目采用轻量 WSGI 框架。

        # Python 配置存在即采用 Python 项目类型。
        str_project_type = "python"  # Python 项目类型覆盖包生态类型。

    # Composer 生态事实由独立 PHP 识别器提供。
    dict_php = php_stack(root)  # PHP 项目栈事实。

    # 有效 Composer 配置追加 PHP 并覆盖项目类型。
    if dict_php:

        # Composer 配置把 PHP 追加到多语言顺序。
        list_languages.append("php")

        # PHP 类型始终覆盖先前通用生态类型。
        str_project_type = str(dict_php["project_type"])  # 采用 Composer 识别的项目细分类。

        # 通用 PHP 不覆盖先前已识别框架。
        if dict_php["framework"]:

            # 只有明确 PHP 框架才覆盖先前框架值。
            str_framework = str(dict_php["framework"])  # PHP 框架类型。

    # go.mod 直接证明 Go 模块项目。
    if (root / "go.mod").exists():

        # 多生态仓库追加 Go 语言。
        list_languages.append("go")

        # cmd 目录区分常见 CLI 布局。
        str_project_type = (  # Go 项目布局类型。
            "go-cli" if (root / "cmd").exists() else "go"  # cmd 目录表明命令行布局。
        )

        # Go 生态没有额外框架分类时使用 go。
        str_framework = "go"  # Go 模块框架标识。

    # 收集根级和 skills 子树中的技能入口。
    list_skill_files = sorted(  # 第一层技能入口。
        path  # 第一层技能入口路径。
        for path in root.glob("*/SKILL.md")  # 扫描根级子目录。
        if path.is_file()  # 只接受真实 SKILL 文件。
    )

    # 追加标准 skills 目录下的技能入口。
    list_skill_files.extend(
        sorted(path for path in root.glob("skills/*/SKILL.md") if path.is_file())
    )

    # 任一技能入口存在时将仓库识别为技能项目。
    if (root / "SKILL.md").exists() or list_skill_files:

        # 避免多入口重复 skill 语言。
        if "skill" not in list_languages:

            # 首次发现技能入口时追加语言类别。
            list_languages.append("skill")

        # 技能事实覆盖通用生态项目类型。
        str_project_type = "skill-repo"  # 技能仓库项目类型。

        # 未识别更具体框架时使用 Codex skill 框架。
        if str_framework == "none":

            # 通用技能仓库采用 Codex skill 框架标识。
            str_framework = "codex-skill"  # 技能框架类型。

    # CI 类型按标准配置文件存在性发现。
    list_ci: list[str] = []  # 持续集成提供方列表。

    # GitHub workflows 目录证明 Actions 配置。
    if (root / ".github" / "workflows").exists():

        # 保存 GitHub Actions 提供方标识。
        list_ci.append("github_actions")

    # GitLab 根配置证明 GitLab CI。
    if (root / ".gitlab-ci.yml").exists():

        # 根配置命中后记录 GitLab 流水线提供方。
        list_ci.append("gitlab_ci")

    # AI 规则和工具配置只公开真实存在项。
    list_ai_configs = [
        str_name  # 输出调用方可直接展示的相对名称。
        for str_name in [  # 枚举受支持的代理工具配置候选。
            "AGENTS.md",  # Codex 根规则证明仓库启用代理治理。
            "CLAUDE.md",  # Claude 项目规则证明对应助手已配置。
            "GEMINI.md",  # Gemini 仓库级指令。
            ".github/copilot-instructions.md",  # Copilot 指令证明 GitHub 助手已配置。
            ".cursor",  # Cursor 目录证明编辑器代理规则已配置。
            ".claude",  # Claude 本地配置目录。
            ".windsurf",  # Windsurf 编辑器配置目录。
        ]
        if (root / str_name).exists()  # 仅公开实际配置。
    ]

    # 返回基础技术事实供总检查入口继续补充治理状态。
    return {
        "config_files": list_config_files,  # 项目配置文件。
        "languages": list_languages,  # 配置驱动语言顺序。
        "framework": str_framework,  # 最终框架分类。
        "project_type": str_project_type,  # 最终项目类型。
        "ci": list_ci,  # CI 提供方。
        "ai_configs": list_ai_configs,  # AI 协作配置。
    }

# 根 AGENTS 识别器汇总版本触发、会话和全局基线状态。
def root_agents_facts(root: Path, profile: dict[str, Any]) -> tuple[Any, ...]:
    """检查根 AGENTS 版本、修复触发、会话历史和全局基线。

    参数：root 为项目根，profile 为项目控制配置。
    返回：保持 inspect_project 输出所需顺序的根规则事实元组。
    """

    # 根 AGENTS 文件是版本与受管元数据的权威来源。
    path_agents = root / "AGENTS.md"  # 根规则文件路径。

    # 文件缺失时使用空文本解析为空元数据。
    str_agents = (  # 根规则文件文本。
        path_agents.read_text(encoding="utf-8", errors="ignore")  # 读取现有规则文本。
        if path_agents.is_file()  # 仅真实文件可读取。
        else ""  # 缺失文件解析为空元数据。
    )

    # 解析生成器版本、规则版本和默认语言字段。
    dict_metadata = parse_agents_metadata(str_agents)  # 受管元数据。

    # 分别读取安装、运行时和项目源码版本以确定期望值。
    str_installed_version = read_installed_skill_version()  # 已安装技能版本。

    # 当前分片运行版本用于输出环境事实。
    str_runtime_version = read_skill_version()  # 运行时技能版本。

    # 仓库内技能源码版本优先参与新鲜度比较。
    str_project_version = read_skill_version(  # 项目源码技能版本。
        root / "skills" / "agents-md-generator"  # 项目技能源码目录。
    )

    # 项目源码版本优先，缺失时采用已安装版本。
    str_expected_version = str_project_version or str_installed_version  # 期望版本。

    # 按稳定顺序累计需要重新生成或修复的原因。
    list_reasons: list[str] = []  # 根规则触发原因。

    # 缺失根文件直接要求生成。
    if not path_agents.is_file():

        # 记录根规则文件缺失原因。
        list_reasons.append("missing_root_agents_md")

    # 根文件存在时检查其受管版本字段。
    else:

        # 已有文件必须同时声明规则和生成器版本。
        str_agents_version = str(dict_metadata.get("agents_version", ""))  # 规则版本。

        # 生成器版本独立于规则版本参与新鲜度判断。
        str_generator_version = str(  # 元数据生成器版本。
            dict_metadata.get("generator_version", "")  # 原始字段值。
        )

        # 缺失规则版本需要受管修复。
        if not str_agents_version:

            # 记录规则版本字段缺失。
            list_reasons.append("missing_agents_version")

        # 缺失生成器版本无法证明文件新鲜度。
        if not str_generator_version:

            # 记录生成器版本字段缺失。
            list_reasons.append("missing_generator_version")

        # 无可用期望版本时不能执行一致性比较。
        if not str_expected_version:

            # 记录安装与项目版本均不可用。
            list_reasons.append("installed_skill_version_unavailable")

        # 有期望版本时比较两个受管版本字段。
        else:

            # 已声明规则版本必须与期望技能版本一致。
            if str_agents_version and str_agents_version != str_expected_version:

                # 记录根规则版本漂移。
                list_reasons.append("agents_version_mismatch")

            # 已声明生成器版本也必须与期望版本一致。
            if str_generator_version and str_generator_version != str_expected_version:

                # 记录生成器版本漂移。
                list_reasons.append("generator_version_mismatch")

    # 只有版本类漂移能够由同步命令自动修复。
    set_repair_reasons = {  # 根规则同步能够消除的版本原因集合。
        "missing_agents_version",  # 根规则未声明自身版本。
        "missing_generator_version",  # 根规则未声明生成器版本。
        "agents_version_mismatch",  # 根规则版本与安装版本不一致。
        "generator_version_mismatch",  # 生成器版本与安装版本不一致。
    }

    # 任一可修复原因命中时提供根规则同步命令。
    str_repair_command = (  # 可选受管修复命令。
        root_agents_sync_command(root, profile)  # 受管根规则同步命令。
        if any(  # 检查是否存在可自动修复原因。
            str_reason in set_repair_reasons  # 当前原因属于版本漂移。
            for str_reason in list_reasons  # 遍历全部触发原因。
        )
        else ""  # 非版本原因不提供自动命令。
    )

    # 精确 cwd 会话为历史 bootstrap 提供来源证据。
    list_sessions = matched_codex_sessions(root)  # 匹配会话列表。

    # 仅已有内容且缺根规则的项目需要历史会话 bootstrap。
    bool_session_bootstrap = (  # 会话历史 bootstrap 状态。
        not path_agents.is_file()  # 根规则缺失。
    ) and workspace_has_existing_content(root)

    # 全局 Codex AGENTS 状态由共享治理合同检查。
    dict_global = global_codex_agents_status(  # 全局基线状态。
        project_root=root,  # 将当前根传给全局基线检查器。
        profile=profile,  # 使用同一份控制配置解析全局合同。
    )

    # 返回总检查入口继续使用的根规则事实。
    return (
        path_agents,  # 供入口判断根规则是否存在的路径。

        # 元数据映射保留受管版本声明。
        dict_metadata,  # 供入口公开的受管版本元数据。

        # 安装版本用于判断生成规则是否需要升级。
        str_installed_version,  # 参与版本漂移比较的安装版本。

        # 运行时版本用于解释当前生成器行为。
        str_runtime_version,  # 参与运行环境诊断的实际版本。

        # 原因列表驱动后续提示和修复决策。
        list_reasons,  # 触发同步或人工检查的根规则原因。

        # 修复命令仅在安全的版本漂移场景公开。
        str_repair_command,  # 仅版本漂移时可执行的同步命令。

        # 会话列表支撑缺失规则时的历史恢复判断。
        list_sessions,  # 与项目 cwd 精确匹配的历史会话。

        # bootstrap 标志通知调用方是否需要导入历史会话。
        bool_session_bootstrap,  # 缺根规则项目是否需要导入历史。

        # 全局状态独立保留 Codex 基线检查证据。
        dict_global,  # 全局 Codex 基线的独立检查结果。
    )

# 目录结构检查器根据项目合同识别需确认的根级漂移。
def structure_fix_facts(root: Path, profile: dict[str, Any]) -> tuple[bool, list[str]]:
    """检查主项目根、根级成员和旧文档路径漂移。

    参数：root 为项目根，profile 为项目控制配置。
    返回：是否要求结构修复确认及对应原因列表。
    """

    # 默认结构状态无需额外确认。
    bool_required = False  # 结构修复确认状态。

    # 按扫描顺序累计所有结构漂移原因。
    list_reasons: list[str] = []  # 目录结构原因。

    # 非对象控制配置不声明目录合同。
    if not isinstance(profile, dict):

        # 无合同项目保持默认结构状态。
        return bool_required, list_reasons

    # directory_contract 必须是对象才能读取路径规则。
    dict_contract = (  # 项目目录合同。
        profile.get("directory_contract", {})  # 读取目录合同字段。
        if isinstance(profile.get("directory_contract"), dict)  # 拒绝非映射目录合同。
        else {}  # 非对象合同不声明路径规则。
    )

    # 规范主项目根的相对路径表示。
    str_primary_root = (  # 合同声明的业务根。
        str(dict_contract.get("primary_project_root", "")).strip().strip("/")  # 规范相对根。
    )

    # 根文件白名单使用合同声明或稳定默认集合。
    set_allowed_files = {  # 允许保留在工作区根的文件名。
        str(item).strip()  # 规范允许文件名。
        for item in dict_contract.get(  # 读取合同白名单或默认值。
            "allowed_root_files",  # 合同可覆盖默认根文件集合。
            [  # 未配置白名单时采用稳定的治理与工具文件集合。
                "AGENTS.md",  # Codex 根规则允许位于工作区根。
                "CLAUDE.md",  # Claude 项目指令是受支持的根级规则文件。
                "GEMINI.md",  # Gemini 项目指令纳入默认根文件白名单。
                ".gitignore",  # Git 忽略规则属于标准根文件。
                ".gitattributes",  # Git 属性合同属于标准根文件。
                ".editorconfig",  # 编辑器格式合同属于标准根文件。
            ],
        )
        if str(item).strip()  # 排除空白配置项。
    }

    # 强制业务根缺失时要求结构修复确认。
    if str_primary_root and not (root / str_primary_root).exists():

        # 记录缺失的批准业务根。
        bool_required = True  # 缺失业务根需要确认。

        # 保存缺失业务根诊断。
        list_reasons.append(f"missing primary project root `{str_primary_root}/`")

    # 允许新路径的首段构成顶层目录白名单。
    set_allowed_roots = {  # 允许的顶层目录名。
        str(item).strip().strip("/").split("/", 1)[0]  # 提取顶层目录段。
        for item in dict_contract.get("allowed_new_paths", [])  # 遍历批准路径。
        if str(item).strip()  # 排除空白路径。
    }

    # 只有非空顶层白名单才启用根成员审查。
    if set_allowed_roots:

        # 检查每个实际根级成员。
        for path_child in root.iterdir():

            # 根级文件采用独立文件白名单。
            if path_child.is_file():

                # 未批准文件要求人工确认。
                if not is_allowed_root_file(path_child.name, set_allowed_files):

                    # 标记根文件结构漂移。
                    bool_required = True  # 根级文件越界需要目录审查确认。

                    # 保存具体根文件诊断。
                    list_reasons.append(f"root-level file requires review: `{path_child.name}`")

                # 文件已经分类，不进入目录规则。
                continue

            # 治理目录和忽略目录不属于业务根漂移。
            if path_child.name in SKIP_DIRS or path_child.name in {".agents", "AGENTS.md"}:

                # 保留治理目录并继续检查其他根成员。
                continue

            # 未批准顶层目录要求人工确认。
            if path_child.name not in set_allowed_roots:

                # 标记顶层目录结构漂移。
                bool_required = True  # 顶层目录越界需要目录审查确认。

                # 保存具体顶层目录诊断。
                list_reasons.append(f"top-level path requires review: `{path_child.name}`")

    # 旧版 handoff、development 和 experience 位置必须迁移。
    for path_legacy in [
        root / "HANDOFF.md",
        root / "DEVELOPMENT.md",
        root / "experience",
        root / "docs" / "HANDOFF.md",
        root / "docs" / "DEVELOPMENT.md",
    ]:

        # 仅实际存在的旧路径形成迁移原因。
        if path_legacy.exists():

            # 标记遗留文档布局漂移。
            bool_required = True  # 遗留文档迁移需要目录变更确认。

            # 保存遗留路径及其项目相对显示值。
            list_reasons.append(
                f"legacy docs path requires migration: `{display_path(path_legacy, root)}`"
            )

    # 返回完整结构确认状态和原因。
    return bool_required, list_reasons

# 项目检查入口组合基础技术事实、AGENTS 状态与源码治理报告。
def inspect_project(root: Path) -> dict[str, Any]:
    """扫描项目并汇总技术栈、治理状态与工作区事实。

    参数：root 为待检查项目根目录。
    返回：供设计、渲染和验证流程共享的完整项目事实映射。
    异常：权威配置或项目文件无法读取时传播对应异常。
    """

    # 基础技术栈由独立发现器一次性汇总。
    dict_stack = project_stack_facts(root)  # 配置、语言、框架和 CI 事实。

    # 复制语言列表，允许后续源码后缀发现安全追加。
    list_languages = list(dict_stack["languages"])  # 可变语言优先级列表。

    # 项目控制配置驱动根规则、目录和源码治理检查。
    dict_profile = read_json(  # 当前项目控制配置。
        root / ".agents" / "agents-control.json"  # 项目治理控制文件。
    )

    # 根规则识别器返回版本、会话和全局基线事实。
    tuple_agents = root_agents_facts(root, dict_profile)  # 根规则事实元组。

    # 辅助合同首项是根规则文件位置。
    path_root_agents = tuple_agents[0]  # 当前项目根 AGENTS 路径。

    # 第二项承载解析后的受管元数据。
    dict_agents_metadata = tuple_agents[1]  # 规则版本与默认语言字段。

    # 第三项记录本地 Codex 已安装技能版本。
    str_installed_version = tuple_agents[2]  # 安装副本版本证据。

    # 第四项记录当前源码运行版本。
    str_runtime_version = tuple_agents[3]  # 运行环境技能版本。

    # 第五项保留根规则触发原因顺序。
    list_trigger_reasons = tuple_agents[4]  # 生成或修复触发原因。

    # 第六项是版本漂移对应的同步命令。
    str_repair_command = tuple_agents[5]  # 可选根规则修复命令。

    # 第七项保存精确工作目录会话证据。
    list_matched_sessions = tuple_agents[6]  # 历史会话摘要列表。

    # 第八项标识是否需要历史 bootstrap。
    bool_session_bootstrap = tuple_agents[7]  # 会话历史引导状态。

    # 末项承载全局 Codex AGENTS 基线检查。
    dict_global_codex = tuple_agents[8]  # 全局规则治理报告。

    # 目录合同识别器返回结构确认状态和原因。
    tuple_structure = structure_fix_facts(root, dict_profile)  # 结构审查结果。

    # 结构结果首项标识是否需要用户确认。
    bool_structure_fix_confirmation_required = tuple_structure[0]  # 目录修复确认状态。

    # 结构结果第二项保留全部漂移原因。
    list_structure_fix_reasons = tuple_structure[1]  # 结构漂移原因。

    # 从控制配置解析实现边界。
    dict_constraints = implementation_constraints_from_profile(  # 实现约束。
        dict_profile,  # 提供实现边界与例外声明。
        root,  # 用于规范合同内的项目相对路径。
    )

    # 扫描源码尺寸、测试边界和注释策略。
    dict_source_governance = source_governance_report(  # 源码治理报告。
        root,  # 限定源码治理扫描范围。
        dict_profile,  # 提供尺寸阈值和排除合同。
    )

    # 检查工具脚本布局和三元组合同。
    dict_script_layout = script_layout_facts(  # 脚本布局报告。
        root,  # 定位项目中的脚本目录。
        dict_profile,  # 提供脚本家族、后缀与例外规则。
    )

    # 加载并验证项目全局规则覆盖。
    dict_overrides = load_global_rule_overrides(  # 规则覆盖报告。
        root,  # 解析覆盖文件的项目基准路径。
        dict_profile,  # 提供覆盖文件位置与必填字段合同。
    )

    # 从源码后缀补充语言事实，覆盖无 pyproject/package 配置的小项目。
    dict_source_suffix_languages = {
        ".py": "python",  # Python 源文件补充 Python 语言路由。
        ".c": "c",  # C 实现文件补充本地编译语言路由。
        ".cc": "cpp",  # 双字符后缀的 C++ 文件。
        ".cpp": "cpp",  # 常规 C++ 实现文件补充 C++ 路由。
        ".cxx": "cpp",  # 扩展 C++ 后缀兼容多种构建约定。
        ".h": "c",  # C 头文件为无实现样例补充语言证据。
        ".hpp": "cpp",  # C++ 头文件为接口仓库补充语言证据。
        ".v": "verilog",  # Verilog 源码触发 RTL 专用技能路由。
        ".sv": "systemverilog",  # SystemVerilog RTL 或验证源码。
        ".bat": "script",  # Windows 批处理文件触发脚本技能路由。
        ".cmd": "script",  # Windows 命令文件纳入批处理治理。
        ".sh": "script",  # Shell 命令脚本触发脚本技能路由。
        ".ps1": "script",  # PowerShell 入口脚本纳入脚本治理。
        ".psm1": "script",  # PowerShell 模块文件纳入脚本治理。
        ".tcl": "script",  # Tcl 工具脚本触发脚本技能路由。
    }

    # 遍历源码文件并忽略缓存、版本控制和构建目录。
    for path_source in root.rglob("*"):

        # 非文件和忽略目录成员不提供语言证据。
        if not path_source.is_file() or any(
            str_part in SKIP_DIRS  # 忽略目录名命中。
            for str_part in path_source.relative_to(root).parts  # 相对路径组成。
        ):

            # 继续检查下一个独立文件系统成员。
            continue

        # 将规范化后缀映射为语言类别。
        str_language = dict_source_suffix_languages.get(  # 当前文件语言。
            path_source.suffix.lower()  # 规范化当前文件后缀。
        )

        # 新语言按首次发现顺序追加。
        if str_language and str_language not in list_languages:

            # 保持配置驱动语言优先于后缀补充语言。
            list_languages.append(str_language)

    # 返回技术栈、规则状态、会话和源码治理的完整事实协议。
    return {
        "project_root": str(root),
        "root_agents_md_exists": path_root_agents.is_file(),
        "root_agents_md_metadata": dict_agents_metadata,
        "root_agents_md_version": dict_agents_metadata.get("agents_version", ""),
        "root_agents_md_generator_version": dict_agents_metadata.get(
            "generator_version", ""
        ),
        "root_agents_md_default_language": dict_agents_metadata.get("default_language", ""),
        "current_skill_version": str_runtime_version,
        "installed_skill_version": str_installed_version,
        "root_agents_md_trigger_required": bool(list_trigger_reasons),
        "root_agents_md_trigger_reasons": list_trigger_reasons,
        "root_agents_md_rebuild_required": bool(list_trigger_reasons),
        "root_agents_md_rebuild_reasons": list_trigger_reasons,
        "root_agents_md_repair_command": str_repair_command,
        "global_codex_agents_exists": dict_global_codex["exists"],
        "global_codex_agents_empty": dict_global_codex["empty"],
        "global_codex_agents_managed": dict_global_codex["managed"],
        "global_codex_agents_baseline_ok": dict_global_codex["baseline_ok"],
        "global_codex_agents_repair_required": dict_global_codex["repair_required"],
        "global_codex_agents_repair_reasons": dict_global_codex["repair_reasons"],
        "global_codex_agents_repair_command": dict_global_codex["repair_command"],
        "global_codex_agents_requires_user_confirmation": dict_global_codex[
            "requires_user_confirmation"
        ],
        "session_history_bootstrap_required": bool_session_bootstrap,
        "session_history_match_scope": "exact-cwd",
        "matched_session_count": len(list_matched_sessions),
        "matched_session_ids": [
            item["id"] for item in list_matched_sessions if item["id"]
        ],
        "matched_session_paths": [item["path"] for item in list_matched_sessions],
        "structure_fix_confirmation_required": bool_structure_fix_confirmation_required,
        "structure_fix_default": "yes",
        "structure_fix_reasons": list_structure_fix_reasons,
        "implementation_constraints": dict_constraints,
        "global_rule_overrides_path": dict_overrides["path"]
        .relative_to(root)
        .as_posix(),
        "global_rule_overrides_exists": dict_overrides["exists"],
        "global_rule_overrides_valid": not dict_overrides["errors"],
        "global_rule_overrides_errors": list(dict_overrides["errors"]),
        "global_rule_overrides": dict_overrides["data"],
        "source_governance": dict_source_governance,
        "oversized_source_files": dict_source_governance["oversized_source_files"],
        "test_code_boundary_violations": dict_source_governance[
            "test_code_boundary_violations"
        ],
        "comment_policy_violations": dict_source_governance["comment_policy_violations"],
        "tool_script_layout_violations": dict_script_layout[
            "tool_script_layout_violations"
        ],
        "script_triad_gaps": dict_script_layout["script_triad_gaps"],
        "gui_script_exemptions": dict_script_layout["gui_script_exemptions"],
        "primary_language": list_languages[0] if list_languages else "unknown",
        "languages": sorted(set(list_languages)),
        "package_manager": package_manager(root),
        "framework": dict_stack["framework"],
        "project_type": dict_stack["project_type"],
        "ci": dict_stack["ci"],
        "ai_configs": dict_stack["ai_configs"],
        "config_files": dict_stack["config_files"],
        "directories": list_dirs(root),
        "files": list_files(root),
    }

# 命令条目构造器集中维护发现结果的字段协议和默认时长。
def command_entry(
    task: str, command: str, source: str, notes: str = "", seconds: str = ""
) -> dict[str, str]:
    """构造带任务、来源和可选时长的规范命令条目。

    参数：task 为任务名，command 为命令，source 为来源，notes 为说明，seconds 为时长。
    返回：供命令发现结果使用的稳定字段映射。
    """

    # 返回所有命令来源共享的稳定字段集合。
    return {
        "task": task,  # 面向用户的任务类别。
        "command": command,  # 原始可执行命令。
        "source": source,  # 发现命令的配置文件。
        "notes": notes,  # 可选执行说明。
        "time": seconds or "~30s",  # 默认短任务时长估计。
        "verified": "false",  # 发现不等同于实际执行验证。
    }

# 任务候选匹配器为不同配置生态复用“首个已声明名称”规则。
def mapped_commands(
    dict_mapping: dict[str, list[str]],
    set_available: set[str],
    command_factory: Any,
) -> list[dict[str, str]]:
    """按任务映射选择首个可用名称并构造命令。

    参数：dict_mapping 为任务候选，set_available 为已声明名称，command_factory 构造条目。
    返回：每个任务最多一个命令条目。
    """

    # 按映射声明顺序累计稳定命令集合。
    list_commands: list[dict[str, str]] = []  # 匹配结果。

    # 每个任务只选择第一个可用候选。
    for str_task, list_names in dict_mapping.items():

        # 候选顺序表达项目工具的偏好优先级。
        for str_name in list_names:

            # 未声明名称不能形成可执行命令。
            if str_name not in set_available:

                # 继续检查当前任务的下一个兼容名称。
                continue

            # 使用生态专属工厂生成规范命令条目。
            list_commands.append(  # 当前任务唯一匹配。
                command_factory(str_task, str_name)
            )

            # 已找到最高优先级候选，不再重复同类任务。
            break

    # 返回任务映射产生的命令条目。
    return list_commands

# Makefile 发现器把常见目标映射为统一任务类别。
def make_commands(root: Path) -> list[dict[str, str]]:
    """从 Makefile 目标发现常用项目命令。

    参数：root 为项目根目录。
    返回：匹配到的 Make 任务条目。
    """

    # 标准 Makefile 是目标发现的唯一输入。
    path_makefile = root / "Makefile"  # Make 配置路径。

    # 没有 Makefile 时不产生该生态命令。
    if not path_makefile.exists():

        # 空集合供总发现器直接合并。
        return []

    # 宽容读取并提取行首目标名称。
    str_text = path_makefile.read_text(  # 用于提取目标的 Makefile 文本。
        encoding="utf-8",  # 按项目文本编码读取。
        errors="ignore",  # Makefile 探测不因局部编码异常中断。
    )

    # 提取行首目标并去重，忽略目标依赖内容。
    set_targets = set(  # 已声明 Make 目标集合。
        re.findall(  # 搜索全部目标声明。
            r"^([A-Za-z0-9_.-]+):",  # 合法目标名模式。
            str_text,  # Makefile 完整文本。
            flags=re.MULTILINE,  # 每行开头均可匹配。
        )
    )

    # 任务映射保持旧实现的候选优先级。
    dict_mapping = {
        "Setup": ["setup", "install"],  # 环境准备目标。
        "Run": ["dev", "serve", "run"],  # 本地运行目标。
        "Format": ["format", "fmt"],  # 格式化目标。
        "Lint": ["lint", "check"],  # 静态检查目标。
        "Test (all)": ["test", "tests"],  # 完整测试目标。
        "Build": ["build"],  # 构建目标。
        "Typecheck": ["typecheck", "types"],  # 类型检查目标。
    }

    # 工厂闭包保留 Makefile 来源字段。
    return mapped_commands(
        dict_mapping,  # 通用任务候选。
        set_targets,  # 实际目标集合。
        lambda task, name: command_entry(task, f"make {name}", "Makefile"),  # 条目工厂。
    )

# JavaScript 命令发现器读取包管理器、scripts 和单测框架。
def package_commands(root: Path) -> list[dict[str, str]]:
    """从 package.json 发现安装、脚本和单文件测试命令。

    参数：root 为项目根目录。
    返回：JavaScript 包管理命令条目。
    """

    # 读取 package.json；缺失或非法对象按无命令处理。
    dict_package = read_json(root / "package.json")  # 包配置对象。

    # 空配置不提供脚本或依赖事实。
    if not dict_package:

        # 返回空集合供聚合器继续其他生态。
        return []

    # scripts 必须是对象才能进行名称匹配。
    dict_scripts = (  # 规范脚本映射。
        dict_package.get("scripts", {})  # 读取 scripts 字段。
        if isinstance(dict_package.get("scripts"), dict)  # 拒绝非映射脚本声明。
        else {}  # 非对象脚本配置按空映射处理。
    )

    # 根据锁文件识别项目实际包管理器及命令前缀。
    str_pm = package_manager(root)  # 项目实际 JavaScript 包管理器。

    # 根据包管理器生成脚本运行前缀。
    str_run = pm_run(str_pm)  # package.json 脚本执行前缀。

    # 根据包管理器生成一次性工具执行前缀。
    str_dlx = pm_dlx(str_pm)  # 单文件测试工具执行前缀。

    # 累计安装、脚本和测试框架命令。
    list_commands: list[dict[str, str]] = []  # JavaScript 命令结果。

    # 存在任一脚本时提供依赖安装入口。
    if dict_scripts:

        # 安装命令来源同时依赖锁文件和 package.json。
        list_commands.append(
            command_entry(
                "Setup",  # 环境准备任务。
                f"{str_pm} install",  # 包管理器安装命令。
                "lockfile/package.json",  # 发现来源。
                "~install dependencies",  # 执行说明。
            )
        )

    # 常见 scripts 映射保持项目原有任务分类。
    dict_script_map = {
        "Run": ["dev", "start"],  # 本地运行脚本。
        "Format": ["format", "fmt"],  # 格式化脚本。
        "Lint": ["lint"],  # 静态检查脚本。
        "Test (all)": ["test"],  # 完整测试脚本。
        "Build": ["build"],  # 构建脚本。
        "Typecheck": ["typecheck", "type-check", "types"],  # 类型脚本。
    }

    # 工厂根据测试任务和包管理器保留 npm/pnpm 特殊命令。
    def package_entry(str_task: str, str_name: str) -> dict[str, str]:
        """构造 package.json 脚本命令。

        参数：str_task 为任务类别，str_name 为脚本名。
        返回：规范命令条目。
        """

        # npm 与 pnpm 的 test 采用直接子命令，其余脚本使用 run 前缀。
        str_command = (  # 实际包脚本命令。
            f"{str_pm} test"  # npm 与 pnpm 的直接测试命令。
            if str_task == "Test (all)" and str_pm in {"npm", "pnpm"}  # 测试特例。
            else f"{str_run} {str_name}"  # 通用脚本运行命令。
        )

        # 返回 package.json 来源的命令条目。
        return command_entry(str_task, str_command, "package.json")

    # 合并每类任务的最高优先级脚本。
    list_commands.extend(
        mapped_commands(dict_script_map, set(dict_scripts), package_entry)
    )

    # 序列化完整配置以识别开发依赖中的测试框架。
    str_dependencies = json.dumps(dict_package)  # 包依赖检索文本。

    # Vitest 优先于 Jest，保持旧发现顺序。
    if "vitest" in str_dependencies:

        # 添加快速单文件 Vitest 入口。
        list_commands.append(
            command_entry(
                "Test (single)", f"{str_dlx} vitest run", "package.json", "~single test file", "~2s"
            )
        )

    # 未发现 Vitest 时再检查 Jest。
    elif "jest" in str_dependencies:

        # 未配置 Vitest 时提供 Jest 单文件测试入口。
        list_commands.append(
            command_entry(
                "Test (single)", f"{str_dlx} jest", "package.json", "~single test file", "~2s"
            )
        )

    # 返回 JavaScript 生态全部命令。
    return list_commands

# Python 项目发现器从 pyproject 工具声明和 tests 目录推导命令。
def python_commands(root: Path) -> list[dict[str, str]]:
    """从 pyproject.toml 和 tests 目录发现 Python 命令。

    参数：root 为项目根目录。
    返回：Python 格式、检查、类型和测试命令。
    """

    # pyproject 是 Python 工具声明的权威输入。
    path_pyproject = root / "pyproject.toml"  # Python 命令发现的配置入口。

    # 没有 pyproject 时保持旧实现的不发现行为。
    if not path_pyproject.exists():

        # tests 目录本身不足以在无 pyproject 时启用分支。
        return []

    # 宽容读取工具声明文本。
    str_text = path_pyproject.read_text(  # Python 工具声明检索文本。
        encoding="utf-8",  # 按 pyproject 标准文本编码读取。
        errors="ignore",  # 工具探测跳过局部非法字节。
    )

    # 按工具声明顺序累计命令。
    list_commands: list[dict[str, str]] = []  # pyproject 工具命令结果。

    # Ruff 同时提供检查和格式化命令。
    if "[tool.ruff" in str_text:

        # 保留旧实现的两条 Ruff 任务。
        list_commands.extend(
            [
                command_entry("Lint", "ruff check .", "pyproject.toml", "", "~10s"),
                command_entry("Format", "ruff format .", "pyproject.toml", "", "~5s"),
            ]
        )

    # mypy 声明启用类型检查入口。
    if "mypy" in str_text:

        # 添加项目级 mypy 命令。
        list_commands.append(
            command_entry("Typecheck", "mypy .", "pyproject.toml", "", "~15s")
        )

    # pytest 配置或 tests 目录证明完整测试入口可用。
    if "pytest" in str_text or (root / "tests").exists():

        # 添加完整 pytest 命令。
        list_commands.append(
            command_entry("Test (all)", "pytest", "pyproject.toml/tests", "", "~30s")
        )

    # 返回 Python 工具命令集合。
    return list_commands

# PHP 与 Go 命令发现保持各自配置生态的固定任务映射。
def backend_commands(root: Path) -> list[dict[str, str]]:
    """发现 Composer 与 Go 模块提供的后端命令。

    参数：root 为项目根目录。
    返回：PHP 和 Go 命令条目。
    """

    # 聚合两个独立后端生态的命令。
    list_commands: list[dict[str, str]] = []  # 后端命令结果。

    # Composer 配置可能声明命名脚本。
    dict_composer = read_json(root / "composer.json")  # Composer 项目配置对象。

    # 有效 Composer 对象才参与脚本发现。
    if dict_composer:

        # scripts 必须是对象才能匹配名称。
        dict_scripts = (
            dict_composer.get("scripts", {})  # 读取 Composer 中可执行的命名任务。
            if isinstance(dict_composer.get("scripts"), dict)  # 仅映射类型支持按任务名检索。
            else {}  # 畸形脚本字段不生成任何 Composer 命令。
        )

        # PHP 任务候选保持旧实现优先级。
        dict_mapping = {
            "Lint": ["lint", "cs:check"],  # 代码规范检查。
            "Format": ["format", "cs:fix"],  # 代码格式修复。
            "Test (all)": ["test"],  # 完整测试。
            "Typecheck": ["phpstan", "stan"],  # 静态类型分析。
        }

        # 合并每类 Composer 任务的首个脚本。
        list_commands.extend(
            mapped_commands(
                dict_mapping,
                set(dict_scripts),
                lambda task, name: command_entry(task, f"composer run {name}", "composer.json"),
            )
        )

    # go.mod 存在时提供标准格式、测试和构建命令。
    if (root / "go.mod").exists():

        # Go 工具链命令不依赖额外配置解析。
        list_commands.extend(
            [
                command_entry("Format", "gofmt -w .", "go.mod", "", "~5s"),
                command_entry("Test (all)", "go test ./...", "go.mod", "", "~30s"),
                command_entry("Build", "go build ./...", "go.mod", "", "~30s"),
            ]
        )

    # 返回 PHP 与 Go 命令集合。
    return list_commands

# CI 命令分类器依据命令文本映射稳定任务类别。
def ci_task(str_command: str) -> str:
    """根据工作流命令文本返回 CI 任务类别。

    参数：str_command 为单行工作流命令。
    返回：CI Lint、CI Test、CI Build、CI Typecheck 或 CI Command。
    """

    # 小写文本用于不区分大小写的工具关键词匹配。
    str_lowered = str_command.lower()  # 规范命令文本。

    # 静态检查工具优先分类为 CI Lint。
    if any(token in str_lowered for token in ("lint", "eslint", "ruff", "phpstan")):

        # 返回静态检查任务类别。
        return "CI Lint"

    # 常见测试工具和子命令分类为 CI Test。
    if any(token in str_lowered for token in ("test", "pytest", "vitest", "jest", "go test")):

        # 返回测试任务类别。
        return "CI Test"

    # 构建和编译关键词分类为 CI Build。
    if any(token in str_lowered for token in ("build", "compile")):

        # 返回构建任务类别。
        return "CI Build"

    # 类型检查工具和关键词分类为 CI Typecheck。
    if any(token in str_lowered for token in ("typecheck", "type-check", "tsc", "mypy")):

        # 返回类型检查任务类别。
        return "CI Typecheck"

    # 未命中特定工具的可执行行保留通用类别。
    return "CI Command"

# 去重器按任务和命令组合保留首个来源证据。
def unique_commands(list_commands: list[dict[str, str]]) -> list[dict[str, str]]:
    """按任务和命令字段稳定去重命令条目。

    参数：list_commands 为按发现顺序排列的命令条目。
    返回：保留首个来源的唯一命令列表。
    """

    # 集合记录已经公开的任务与命令组合。
    set_seen: set[tuple[str, str]] = set()  # 去重键集合。

    # 结果列表保留原始发现顺序。
    list_unique: list[dict[str, str]] = []  # 唯一命令结果。

    # 逐项保留首个未见组合。
    for dict_item in list_commands:

        # 来源和说明不参与去重，延续旧协议。
        tuple_key = (dict_item["task"], dict_item["command"])  # 唯一组合键。

        # 已见组合不重复公开。
        if tuple_key in set_seen:

            # 保留首个发现来源并跳过当前重复项。
            continue

        # 登记新组合并保存完整条目。
        set_seen.add(tuple_key)

        # 保存首个来源的完整命令条目。
        list_unique.append(dict_item)

    # 返回稳定去重结果。
    return list_unique

# 命令发现入口聚合各配置生态和工作流来源。
def extract_commands(root: Path) -> dict[str, Any]:
    """从项目配置、任务文件和工作流中提取可执行命令。

    参数：root 为待扫描项目根目录。
    返回：包含去重命令条目的发现结果。
    异常：项目配置无法读取时传播对应解析或文件异常。
    """

    # 按旧实现顺序聚合 Make、JavaScript、Python 和后端命令。
    list_commands = [  # 所有本地配置来源的命令。
        *make_commands(root),  # Make 目标命令。
        *package_commands(root),  # JavaScript 包脚本命令。
        *python_commands(root),  # Python 工具命令。
        *backend_commands(root),  # PHP 与 Go 后端命令。
    ]

    # 工作流命令在本地配置命令之后追加并分类。
    for dict_run in workflow_runs(root):

        # 工作流来源和命令由专用发现器保证存在。
        str_command = dict_run["command"]  # 当前 CI 命令。

        # 构造带 CI 分类和工作流来源的规范条目。
        list_commands.append(
            command_entry(
                ci_task(str_command),  # 文本驱动的 CI 类别。
                str_command,  # 工作流单行命令。
                dict_run["workflow"],  # 工作流相对路径。
            )
        )

    # 返回按任务与命令稳定去重的发现结果。
    return {"commands": unique_commands(list_commands)}

# 工作流命令发现器只提取可直接执行的单行 run 声明。
def workflow_runs(root: Path) -> list[dict[str, str]]:
    """提取 GitHub Actions 工作流中的 run 命令。

    参数：root 为项目根目录。
    返回：带工作流相对路径来源的命令条目列表。
    """

    # 按工作流和声明顺序累计命令来源证据。
    list_rules: list[dict[str, str]] = []  # 最终命令条目列表。

    # GitHub Actions 的标准目录是唯一扫描边界。
    workflow_dir = root / ".github" / "workflows"  # 工作流配置根。

    # 项目没有工作流目录时直接返回空发现结果。
    if not workflow_dir.exists():

        # 空列表保持调用方聚合协议稳定。
        return list_rules

    # 按文件名稳定扫描 YAML 与 YML 工作流。
    for workflow in sorted(workflow_dir.glob("*.y*ml")):

        # 宽容读取工作流文本，避免非 UTF-8 字节阻断项目发现。
        text = workflow.read_text(  # 当前工作流完整文本。
            encoding="utf-8",  # GitHub 工作流通常采用 UTF-8。
            errors="ignore",  # 忽略无法解码的个别字节。
        )

        # 同时匹配步骤列表和映射内的单行 run 字段。
        for tuple_raw in re.findall(
            r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$",  # 两种 YAML 行形态。
            text,  # 当前工作流文本。
            flags=re.MULTILINE,  # 逐行锚定 run 字段。
        ):

            # 两个捕获组中只有一个包含实际命令文本。
            str_command = (  # 清理 YAML 外层引号和空白。
                tuple_raw[0] or tuple_raw[1]  # 选择实际命中的捕获组。
            ).strip().strip("'\"")

            # 空命令和多行块标记不能作为完整单行命令执行。
            if not str_command or str_command.startswith(("|", ">")):

                # 多行块由 YAML 解析器才能可靠恢复，此处保守跳过。
                continue

            # 即使输入异常包含换行，也只公开第一条可执行命令。
            first_line = str_command.splitlines()[0].strip()  # 规范单行命令。

            # 清理后仍有文本时保存其工作流来源。
            if first_line:

                # 相对路径使结果可在不同工作区位置比较。
                list_rules.append(
                    {
                        "workflow": rel(workflow, root),  # 命令来源文件。
                        "command": first_line,  # 可执行首行文本。
                    }
                )

    # 返回按文件名和声明顺序排列的工作流命令。
    return list_rules

# 兼容转发函数保持聚合模块原有公开 API。
def default_global_rule_overrides() -> dict[str, Any]:
    """返回源码治理模块提供的默认全局规则覆盖映射。

    参数：无。
    返回：默认全局规则覆盖映射。
    """

    # 权威默认值仍由源码治理配置模块拥有。
    return source_governance_config.default_global_rule_overrides()

# 实现约束转发避免调用方直接依赖配置分片。
def default_implementation_constraints() -> dict[str, Any]:
    """返回源码治理模块提供的默认实现约束映射。

    参数：无。
    返回：默认实现约束映射。
    """

    # 从权威配置模块读取默认实现边界。
    return source_governance_config.default_implementation_constraints()

# 规则引用转发保持控制配置到显示路径的统一解析。
def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:
    """返回控制配置对应的全局规则覆盖显示引用。

    参数：profile 为可选项目控制配置。
    返回：供 AGENTS 文本使用的规则文件引用。
    """

    # 委托权威配置模块处理缺省和自定义引用。
    return source_governance_config.global_rule_overrides_reference(profile)

# 规则路径转发把显示合同解析为项目内绝对位置。
def global_rule_overrides_path(
    root: Path, profile: dict[str, Any] | None = None
) -> Path:
    """解析项目全局规则覆盖文件的绝对路径。

    参数：root 为项目根，profile 为可选项目控制配置。
    返回：全局规则覆盖 JSON 路径。
    """

    # 委托权威配置模块解析控制配置中的相对路径。
    return source_governance_config.global_rule_overrides_path(root, profile)
