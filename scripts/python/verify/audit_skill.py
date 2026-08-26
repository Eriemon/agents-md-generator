"""审计 agents-md-generator 技能包的结构、引用和治理规则一致性。"""

# 导入 技能审计 所需的依赖模块。
from __future__ import annotations

# 导入 技能审计 所需的依赖模块。
import argparse
import ast

# 动态导入和类型标注支撑延迟加载的运行时合同。
import importlib
import json
import re

# 路径与模块类型用于约束跨任务依赖的边界。
from pathlib import Path
import sys
from types import ModuleType

# 直接脚本执行时延迟登记兄弟任务目录，模块导入本身保持无副作用。
def load_runtime_dependencies() -> None:
    """在 CLI 或完整审计启动时加载兄弟任务模块。

    参数：无。
    返回：无；所需公共契约会登记到当前模块命名空间。
    """

    # Python 任务根包含 common、design、verify 等平级模块目录。
    path_python_root = Path(__file__).resolve().parents[1]  # 兄弟任务共同根目录

    # 只在真实执行审计时建立现有脚本布局的导入搜索路径。
    for path_task_dir in path_python_root.iterdir():

        # 根目录中的普通文件不能作为模块搜索目录。
        if not path_task_dir.is_dir():

            # 跳过非目录成员并继续检查其余任务目录。
            continue

        # sys.path 使用字符串形式保存绝对搜索位置。
        str_task_dir = str(path_task_dir)  # 当前兄弟任务目录

        # 已存在的路径保持原优先级，不重复登记。
        if str_task_dir not in sys.path:

            # 源码任务目录优先于环境中可能存在的同名模块。
            sys.path.insert(0, str_task_dir)

    # 公共 CLI 契约提供路径解析、JSON 输出和脚本登记表。
    module_type_agents_common: ModuleType = importlib.import_module("agents_common")  # 公共 CLI 模块

    # 项目事实模块提供分解计划位置和全局覆盖配置。
    module_type_project_facts: ModuleType = importlib.import_module("agents_project_facts")  # 项目事实模块

    # 源码治理模块负责验证默认输出策略配置。
    module_type_source_governance: ModuleType = importlib.import_module(  # 源码治理配置模块
        "source_governance_config"  # 输出策略治理模块入口
    )

    # 版本策略模块统一判断发布目录的语义版本合法性。
    module_type_version_policy: ModuleType = importlib.import_module("version_policy")  # 版本策略模块

    # 延迟绑定保持既有模块级调用点兼容，同时避免 import-time 加载。
    global script_task_by_name
    global decomposition_plan_path
    global func_emit_json
    global func_load_global_rule_overrides
    global func_resolve_project
    global validate_script_output_policy_data
    global func_version_policy_error

    # 脚本登记表驱动审计器检查每个入口是否位于声明的任务目录。
    script_task_by_name = module_type_agents_common.SCRIPT_TASK_BY_NAME  # 脚本到任务目录映射

    # JSON 输出函数维护 CLI 的机器可读标准输出协议。
    func_emit_json = module_type_agents_common.emit_json  # 结构化结果输出函数

    # 项目解析函数拒绝越界路径并返回规范目标目录。
    func_resolve_project = module_type_agents_common.resolve_project  # 项目路径解析函数

    # 分解计划定位器读取仓库治理配置中的计划根。
    decomposition_plan_path = module_type_project_facts.decomposition_plan_path  # 分解计划路径函数

    # 全局覆盖加载器提供源码规模等仓库事实。
    func_load_global_rule_overrides = (  # 全局规则覆盖加载函数
        module_type_project_facts.load_global_rule_overrides  # 绑定共享配置实现
    )

    # 默认输出策略验证器返回配置合同错误列表。
    validate_script_output_policy_data = (
        module_type_source_governance.validate_script_output_policy_data  # 输出策略验证函数
    )

    # 版本校验函数为目录名和 VERSION 一致性提供同一规则来源。
    func_version_policy_error = module_type_version_policy.version_policy_error  # 版本策略函数

    # 公开文件门禁复用发布策略的单一事实源，避免审计与打包分叉。
    global validate_public_skill_files

    # 发布策略模块提供受管理技能公开文件的唯一校验实现。
    module_type_release_content_policy: ModuleType = importlib.import_module("release_content_policy")  # 发布内容策略模块

    # 将公开文件校验函数绑定到延迟加载的模块命名空间。
    validate_public_skill_files = module_type_release_content_policy.validate_public_skill_files  # 公开文件校验函数

# 所有被审计技能至少需要主说明文件。
CORE_REQUIRED_FILES = [  # 通用技能必需文件
    "SKILL.md",  # 通用技能主说明
]

# 自身技能额外要求完整产品、治理和验证资源。
SELF_REQUIRED_FILES = [  # 自身技能必需资源
    Path("VERSION"),  # 自身技能版本文件
    Path("config") / "agent-platforms.json",  # 平台目录
    Path("config") / "render-manifest.json",  # 渲染产物清单
    Path("evals") / "evals.json",  # 效果测试案例配置
    Path("references") / "agents-md-guidance.md",  # AGENTS 规则编写指南
    Path("references") / "book-rules-coverage.md",  # 书籍规则覆盖说明
    Path("references") / "capability-coverage.md",  # 技能能力覆盖矩阵
    Path("references") / "coding-behavior-language-routing.md",  # 编码语言技能路由说明
    Path("references") / "skill-design-coverage.md",  # 技能设计模式覆盖说明
    Path("references") / "question-bank.md",  # 设计访谈问题库
    Path("references") / "review-checklist.md",  # 治理审查清单
    Path("references") / "script-guide.md",  # 脚本命令与发布流程指南
    Path("references") / "evaluation-scenarios.md",  # 效果测试场景说明
    Path("assets") / "templates" / "root-agents.md",  # 根 AGENTS 渲染模板
    Path("assets") / "templates" / "scoped-agents.md",  # 目录作用域 AGENTS 模板
    Path("assets") / "templates" / "global-codex-agents.md",  # 全局 Codex 基线模板
    Path("config") / "source-governance.json",  # 源码治理规则配置
    Path("config") / "script-output-policy-default.json",  # 默认脚本输出策略
    Path("config") / "content-quality-policy.json",  # Markdown 精炼预算与政策所有者
    Path("scripts") / "python" / "verify" / "check_source_governance.py",  # 源码治理检查入口
    Path("scripts") / "python" / "detect" / "codex_token_usage_review.py",  # Token 用量统计入口
    Path("scripts") / "python" / "detect" / "inspect_project.py",  # 项目事实检测入口
    Path("scripts") / "python" / "design" / "collect_design_profile.py",  # 设计访谈采集入口
    Path("scripts") / "python" / "design" / "design_review_gate.py",  # 设计审查门禁入口
    Path("scripts") / "python" / "detect" / "extract_commands.py",  # 项目命令提取入口
    Path("scripts") / "python" / "detect" / "extract_context.py",  # 项目上下文提取入口
    Path("scripts") / "python" / "detect" / "detect_scopes.py",  # 指令作用域检测入口
    Path("scripts") / "python" / "render" / "render_agents.py",  # AGENTS 规则渲染入口
    Path("scripts") / "python" / "docs" / "manage_docs.py",  # 文档生命周期治理入口
    Path("scripts") / "python" / "docs" / "memory_write.py",  # memory 事务写入分片
    Path("scripts") / "python" / "dirs" / "manage_dirs.py",  # 目录结构治理入口
    Path("scripts") / "python" / "dirs" / "manage_dirs_review.py",  # 目录变更审查入口
    Path("scripts") / "python" / "dirs" / "manage_dirs_state.py",  # 目录治理状态验证入口
    Path("scripts") / "python" / "common" / "agents_decisions.py",  # AGENTS 决策事实模块
    Path("scripts") / "python" / "release" / "install_skill.py",  # 技能发布安装入口
    Path("scripts") / "python" / "verify" / "review_governance.py",  # 治理审查编排入口
    Path("scripts") / "python" / "release" / "select_engineering_rules.py",  # 工程规则选择入口
    Path("scripts") / "python" / "verify" / "verify_agents.py",  # AGENTS 一致性验证入口
    Path("scripts") / "python" / "detect" / "check_freshness.py",  # 规则新鲜度检查入口
    Path("scripts") / "python" / "verify" / "quick_validate.py",  # 技能快速验证入口
    Path("scripts") / "python" / "verify" / "run_confidence_gate.py",  # 完整信心门禁入口
    Path("scripts") / "python" / "verify" / "source_governance.py",  # 源码规模与可读性入口
    Path("scripts") / "python" / "verify" / "source_governance_config.py",  # 源码治理配置验证模块
    Path("scripts") / "python" / "render" / "create_agent_shims.py",  # 兼容代理规则垫片入口
    Path("scripts") / "python" / "verify" / "audit_skill.py",  # 技能包完整审计入口
    Path("scripts") / "python" / "verify" / "agent_platform_gate.py",  # 活动路径硬编码门禁
    Path("scripts") / "python" / "verify" / "evaluate_skill.py",  # 技能效果评估入口
]

# 自身技能根拒绝与 SKILL.md 重复的安装和变更文档。
SELF_DISALLOWED_ROOT_DOCS = {  # 自身技能根禁止文档
    "CHANGELOG.md",  # 与主说明重复的变更文档
    "INSTALL.md",  # 与主说明重复的安装文档
    "INSTALLATION.md",  # 另一种重复安装文档名
}

# 编译缓存不得进入技能源码或发布快照。
DISALLOWED_CACHE_SUFFIXES = {".pyc", ".pyo"}  # 禁止进入发布物的缓存后缀

# 本地绝对路径和历史参考目录不得进入可发布文档。
LOCAL_REFERENCE_RE = re.compile(  # 本地引用识别模式
    r"G:[/\\]html|ref[/\\](agent-rules|html)|\b[A-Za-z]:[/\\][^\s`'\"<>)]*",  # 本地引用模式
    flags=re.IGNORECASE,  # 本地路径匹配忽略大小写
)

# 技能名采用小写字母、数字和连字符的产品命名合同。
SKILL_NAME_RE = re.compile(r"^[a-z0-9-]+$")  # 技能名称格式

# 模板占位符使用全大写标识，便于与普通正文区分。
TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{([A-Z0-9_]+)}}")  # 模板占位符模式

# 每个模板只允许其渲染器明确支持的占位符集合。
KNOWN_TEMPLATE_PLACEHOLDERS = {  # 模板到允许占位符的映射
    "root-agents.md": {  # 根规则模板允许的占位符
        "GENERATED_BODY",  # 根规则生成正文
        "TIMESTAMP",  # 根规则生成时间
        "VERIFIED_TIMESTAMP",  # 根规则最近核验时间
        "PROJECT_OVERVIEW",  # 项目概览渲染内容
        "CONTROL_PROFILE",  # 控制配置渲染内容
        "DIRECTORY_CONTRACT",  # 目录治理合同正文
        "REMOTE_SERVER_CONTRACT",  # 远程服务器治理合同
        "RELEASE_CONTRACT",  # 发布治理合同正文
        "ENGINEERING_RULE_CONTRACT",  # 工程编码规则合同
        "SKILL_DESIGN_CONTRACT",  # 技能设计模式治理合同
        "CONVERSATION_COMPLETION_CONTRACT",  # 会话完成与交接合同
        "MEMORY_CONTRACT",  # 项目记忆治理合同
        "CODING_BEHAVIOR_BASELINE",  # 编码行为基线渲染内容
        "SCRIPT_OUTPUT_POLICY",  # 脚本输出前缀治理合同
        "DOCUMENTATION_GOVERNANCE_CONTRACT",  # 文档生命周期治理合同
        "VERIFICATION_STATUS",  # 最近治理验证状态
        "COMMAND_SOURCE",  # 命令来源渲染内容
        "COMMAND_ROWS",  # 命令清单渲染行
        "FILE_MAP",  # 文件路径映射渲染内容
        "GOLDEN_SAMPLE_ROWS",  # 黄金样例渲染行
        "UTILITY_ROWS",  # 辅助命令渲染行
        "HEURISTIC_ROWS",  # 启发式命令渲染行
        "REPOSITORY_SETTINGS",  # 仓库设置渲染内容
        "HOOK_POLICY",  # Git 钩子策略渲染内容
        "CI_RULES",  # 持续集成规则渲染内容
        "GITHUB_SETTINGS",  # GitHub 分支保护和合并约束
        "DIRECTORY_COVERAGE",  # 目录覆盖清单渲染内容
        "KEY_DECISIONS",  # 关键治理决策渲染内容
        "EVOLUTION_TEMPLATE_GUIDANCE",  # 规则演进模板指导
        "ALWAYS_RULES",  # 无条件生效规则渲染内容
        "ASK_FIRST_RULES",  # 需先询问规则渲染内容
        "NEVER_RULES",  # 绝对禁止规则渲染内容
        "CODEBASE_STATE",  # 代码库状态渲染内容
        "TERMINOLOGY_ROWS",  # 术语规范渲染行
        "SCOPE_INDEX",  # 指令作用域索引内容
    },
    "scoped-agents.md": {  # 作用域模板允许占位符
        "TIMESTAMP",  # 作用域规则生成时间
        "VERIFIED_TIMESTAMP",  # 作用域规则核验时间
        "SCOPE_NAME",  # 目录作用域名称
        "SCOPE_PATH",  # 目录作用域相对路径
        "SCOPE_OVERVIEW",  # 目录作用域概览内容
        "LOCAL_COMMANDS",  # 作用域本地命令清单
        "TESTING_RULES",  # 作用域测试规则内容
        "LOCAL_STRUCTURE",  # 作用域本地目录结构
        "CODE_STYLE",  # 作用域编码风格规则
        "GIT_WORKFLOW",  # 作用域 Git 工作流规则
        "LOCAL_BOUNDARIES",  # 作用域本地操作边界
        "SCOPE_PURPOSE",  # 作用域用途说明
    },
}

# 分组解析器接受技能与工程两类固定引导标签。
COMMON_GROUP_LABELS = (  # 可识别的公共分组标签
    "Skill development groups are",  # 技能开发分组标签
    "Engineering development groups are",  # 工程开发分组标签
)

# 旧版入口可能仍携带问题组正文，审计必须识别其配置漂移而不复制当前编号。
PROFILE_GROUP_LABELS: tuple[tuple[str, str, str], ...] = (
    ("Skill development groups are", "SKILL_GROUPS", "skill"),  # 技能开发旧入口的组标签与变量名。
    ("Engineering development groups are", "ENGINEERING_GROUPS", "engineering"),  # 工程开发旧入口的组标签与变量名。
)

# 当前入口只引用配置驱动组，由单一声明替代 SKILL.md 中易漂移的编号清单。
PARAMETERIZED_GROUP_CONTRACT: str = "Skill and Engineering development groups come from the selected profile"  # 参数化问题组合同文本。

# Markdown 内容预算防止入口和生成模板重新膨胀。
GLOBAL_TEMPLATE_MAX_BYTES = 8 * 1024  # 全局受管基线预算。

# 技能简介遵循标准 UI 元数据字符边界。
OPENAI_SHORT_DESCRIPTION_MIN_CHARS = 25  # 技能简介最少字符数。

# 技能简介的上限与标准 skill-creator 合同保持一致。
OPENAI_SHORT_DESCRIPTION_MAX_CHARS = 64  # 技能简介最多字符数。

# 默认提示词仅承担单句启动职责，避免复制完整技能正文。
OPENAI_DEFAULT_PROMPT_MAX_BYTES = 256  # 技能默认提示词 UTF-8 预算。

# 每类参考只验证自身职责，不要求多表面镜像整段政策。
REFERENCE_ALIGNMENT_RULES = {  # 参考文档单一职责锚点。
    "references/review-checklist.md": ("## Verification", "## Content"),  # 审查证据与内容边界
    "references/script-guide.md": ("## Detect", "## Render", "## Verify"),  # 命令流程入口
    "references/skill-design-coverage.md": ("map, not a manual", "## Patterns"),  # 设计模式索引
}

# 语言路由的完整正文只由专用参考负责；其他表面只需指向该所有者。
LANGUAGE_SKILL_ROUTING_ALIGNMENT_RULES = {
    "references/coding-behavior-language-routing.md": (  # 语言路由说明对齐规则
        "shared",  # 共同门禁字段
        "rendered as `Shared language gates` only once",  # 共同门禁单次渲染
        "Python",  # Python 目标语言声明
        "readable-python-generator",  # Python 可读性技能
        "readable-script-generator",  # 脚本可读性技能
        "bat/cmd",  # Windows 批处理目标
        "shell/bash",  # POSIX 命令行脚本目标
        "PowerShell",  # PowerShell 脚本目标
        "Tcl",  # Tcl 文件路由范围
        "A script wrapper that invokes an external Python command",  # Python 子命令不改变脚本归属
        "do not join statements, comments, or functions together",  # 代码结构分隔要求
        "compress code into one line",  # 禁止单行压缩代码要求
        "obfuscated code",  # 禁止晦涩代码表达
    ),
}

# SKILL.md 必须保留结构修复与远程变更边界。
SKILL_REQUIRED_SNIPPETS = (  # 主说明必需治理片段。
    "root-level files outside the governed primary project root require review",  # 根目录越界规则。
    "allow the conservative structure-fix attempt",  # 保守结构修复授权
    "rerun `structure-gate`",  # 结构修复后复验要求
    "every remote `create`, `move`, `delete`, or `rename` must keep both source and "
    "target paths inside the governed remote plan",  # 远程变更两端路径边界
    "allowed_root_files",  # 根文件白名单配置
    "remote_deployment.protected_path_classes",  # 远程受保护路径类别
)

# 中文主说明必须完整描述 Token 用量统计的触发边界。
SKILL_TOKEN_USAGE_SNIPPETS = (  # 用于验证 SKILL.md 的 Token 统计命令和意图边界。
    "If the user explicitly asks for Codex Token usage statistics",  # 技能正文限定显式统计请求。
    "registry instruction `detect.token-usage-review`",  # 技能正文路由到结构化注册指令。
    "do not enter the AGENTS design interview",  # 技能正文要求统计意图旁路访谈。
    "only when the configured agent sessions directory exists",  # 技能正文要求会话目录可用。
    "keep any sessions-root override inside that active sessions tree",  # 技能正文限制统计参数边界。
)

# 旧 numbered shard 名称不得残留在运行时源码引用中。
STALE_NUMBERED_SHARD_RE = re.compile(  # 陈旧 numbered shard 模式
    r"(?:^|[_./\\])part\d+\.py\b|eval_runtime_cases_part\d|_version_policy_part\d"  # 陈旧分片引用模式
)

# frontmatter 解析器仅提取审计所需的顶层标量和折叠文本。
def parse_frontmatter(text: str) -> dict[str, str]:
    """解析 SKILL.md 顶部的简化 YAML frontmatter。

    参数：text 为完整技能说明文本。
    返回：顶层字段到字符串值的映射；边界缺失时返回空映射。
    """

    # 非 frontmatter 文本不参与技能元数据审计。
    if not text.startswith("---\n"):

        # 空映射让调用方统一报告必填字段缺失。
        return {}

    # 第二个分隔符限定元数据区间，避免扫描正文中的冒号。
    int_end: int = text.find("\n---\n", 4)  # frontmatter 结束偏移

    # 缺少闭合分隔符时拒绝解析不完整头部。
    if int_end == -1:

        # 不完整元数据不产生部分可信结果。
        return {}

    # 字段映射保留审计器关心的最终字符串表示。
    dict_data: dict[str, str] = {}  # 已解析 frontmatter 字段

    # 多行字段键用于接收后续缩进内容。
    current_key: str | None = None  # 当前折叠字段名

    # 分段保存折叠文本，字段结束时再连接。
    list_current_multiline: list[str] = []  # 当前多行字段内容

    # 按物理行识别顶层字段和缩进续行。
    for line in text[4:int_end].splitlines():

        # 已进入多行字段时优先消费其缩进内容。
        if current_key is not None:

            # 缩进行仍属于当前 YAML block scalar。
            if line.startswith((" ", "\t")):

                # 去除结构缩进，仅保留实际说明文本。
                list_current_multiline.append(line.strip())

                # 当前续行处理完毕后读取下一物理行。
                continue

            # 遇到下一个顶层字段前提交已收集的折叠文本。
            dict_data[current_key] = " ".join(  # 当前多行字段的单行审计值
                part for part in list_current_multiline if part  # 当前字段的非空续行
            ).strip()

            # 字段提交后退出多行采集状态。
            current_key = None  # 当前不再等待续行

            # 清空缓存，防止内容泄漏到下一个字段。
            list_current_multiline = []  # 下一多行字段的初始缓存

        # 无冒号的顶层行不构成受支持的键值字段。
        if ":" not in line:

            # 跳过注释、空行和不受支持的 YAML 结构。
            continue

        # 首个冒号分离字段名和原始标量内容。
        key, raw_value = line.split(":", 1)  # 当前 frontmatter 键值片段

        # 字段名去除 YAML 排版空白后用于结果索引。
        normalized_key = key.strip()  # 规范化字段名

        # 审计比较不需要外层双引号和首尾空白。
        normalized_value = raw_value.strip().strip('"')  # 规范化字段值

        # block scalar 标记表示实际值位于后续缩进行。
        if normalized_value in {">", ">-", "|", "|-"}:

            # 记录即将接收续行的字段名。
            current_key = normalized_key  # 当前多行字段名

            # 为该字段建立独立的内容缓存。
            list_current_multiline = []  # 当前多行字段的新缓存

            # 标记行本身不写入结果映射。
            continue

        # 普通标量可直接进入审计结果。
        dict_data[normalized_key] = normalized_value  # 当前单行字段值

    # 文件头可能以多行字段结束，需要在循环后提交。
    if current_key is not None:

        # 合并最后一个字段的非空片段。
        dict_data[current_key] = " ".join(  # 末尾多行字段的单行审计值
            part for part in list_current_multiline if part  # 末尾字段的非空续行
        ).strip()

    # 返回仅包含受支持顶层字段的稳定映射。
    return dict_data

# 引用提取器只接受技能包内部、无模板占位符的代码路径。
def referenced_paths(skill_text: str) -> set[str]:
    """提取 SKILL.md 代码标记中的技能包相对路径。

    参数：skill_text 为技能说明全文。
    返回：references、assets、scripts 或 agents 下的唯一相对路径集合。
    """

    # 集合消除同一路径在说明中的重复引用。
    set_paths: set[str] = set()  # 技能说明声明的内部路径

    # 代码标记是技能文档引用文件时采用的稳定语法边界。
    for raw in re.findall(r"`([^`]+)`", skill_text):

        # 引用比较忽略代码标记内侧空白。
        raw_value = raw.strip()  # 当前候选引用

        # 带尖括号的示例或占位符不是实际文件契约。
        if "<" in raw_value or ">" in raw_value:

            # 跳过不能在包内解析的模板路径。
            continue

        # 仅审计技能标准允许声明的内部资源目录。
        if raw_value.startswith(("references/", "assets/", "scripts/", "agents/")):

            # 收集后续存在性检查所需的规范路径文本。
            set_paths.add(raw_value)

    # 返回去重后的内部文件引用。
    return set_paths

# 本地绝对路径检测阻止开发机细节进入可分发技能内容。
def contains_local_reference(text: str) -> bool:
    """判断文本是否包含受禁止的本地路径引用。

    参数：text 为待扫描文本。
    返回：命中本地路径模式时为真，否则为假。
    """

    # 正则集中维护跨平台本地路径判定规则。
    return bool(LOCAL_REFERENCE_RE.search(text))

# 目录检查仅观察文档开头，避免正文中的普通“目录”用词误报。
def has_toc(lines: list[str]) -> bool:
    """判断文档前部是否声明目录。

    参数：lines 为文档物理行。
    返回：前三十行包含中英文目录标识时为真。
    """

    # 目录标识应位于读者进入文档时可见的前部区域。
    return any(
        "table of contents" in line.lower() or "目录" in line for line in lines[:30]
    )

# 自举技能需要比通用技能执行更完整的仓库专属合同。
def is_agents_md_generator_skill(
    skill_dir: Path, frontmatter: dict[str, str] | None = None
) -> bool:
    """判断目标是否为 agents-md-generator 自身技能包。

    参数：skill_dir 为目标目录，frontmatter 为可选元数据映射。
    返回：目录名或声明名称匹配自身技能名时为真。
    """

    # 元数据名称允许版本化发布目录仍识别为自身技能。
    name = (frontmatter or {}).get("name", "").strip()  # 技能身份声明名称

    # 两种身份来源任一匹配即可启用自举专属审计。
    return skill_dir.name == "agents-md-generator" or name == "agents-md-generator"

# 目录命名允许开发/安装名称以及带语义版本的发布快照名称。
def skill_directory_name_matches(skill_dir: Path, name: str) -> bool:
    """校验技能目录名是否符合声明名称及版本契约。

    参数：skill_dir 为技能目录，name 为 frontmatter 声明名称。
    返回：普通目录或经 VERSION 佐证的版本目录匹配时为真。
    """

    # 空名称交给调用方的 name 格式门禁处理。
    if not name:

        # 缺少声明名称时无法建立目录身份。
        return False

    # 普通安装目录必须与 frontmatter name 完全一致。
    if skill_dir.name == name:

        # 普通技能目录与声明一致时直接通过。
        return True

    # versioned release 目录采用 <name>-vX.Y.Z，必须由 VERSION 文件佐证。
    str_prefix = f"{name}-"  # 版本化目录的技能名前缀

    # 非对应技能名前缀不能作为该技能的发布快照。
    if not skill_dir.name.startswith(str_prefix):

        # 前缀不符直接结束命名校验。
        return False

    # 目录名剩余部分必须是仓库认可的版本字符串。
    str_version_suffix = skill_dir.name[len(str_prefix) :]  # 目录声明版本

    # 非法语义版本不能通过发布目录兼容路径。
    if func_version_policy_error(str_version_suffix):

        # 版本策略错误使目录身份无效。
        return False

    # 定位 version path 的文件边界，供 skill_directory_name_matches 后续读写校验使用。
    version_path = skill_dir / "VERSION"  # 发布快照版本文件

    # 版本化目录必须同时携带权威 VERSION 文件。
    if not version_path.is_file():

        # 无版本文件时不能证明目录后缀来源。
        return False

    # 文件内容必须与目录后缀完全一致。
    str_declared_version = version_path.read_text(  # 发布目录身份校验所用版本
        encoding="utf-8", errors="ignore"  # 容错读取版本文件
    ).strip()

    # 一致的双重声明完成发布目录身份校验。
    return str_declared_version == str_version_suffix

# OpenAI 界面解析器只读取 interface 下的一级标量字段。
def parse_openai_interface(text: str) -> dict[str, str] | None:
    """解析 agents/openai.yaml 的 interface 标量字段。

    参数：text 为 openai.yaml 全文。
    返回：interface 字段映射；未声明 interface 时返回 None。
    """

    # 保留缩进以识别 interface 区块边界。
    lines = text.splitlines()  # OpenAI 配置物理行

    # interface 入口可能不存在，使用迭代器精确定位首个声明。
    try:

        # 顶层 interface 行确定后续缩进字段的起点。
        int_start: int = next(  # interface 声明行索引
            index  # interface 顶层声明的物理行索引
            for index, line in enumerate(lines)  # 带物理行索引的配置行
            if line.strip() == "interface:"  # 仅定位顶层界面区块
        )

    # 缺失入口属于可报告的配置合同缺口，不是解析器异常。
    except StopIteration:

        # None 区分“无 interface”与“存在但为空”。
        return None

    # 映射仅保存审计所需的一级字符串值。
    dict_data: dict[str, str] = {}  # interface 配置字段

    # 从入口下一行开始读取其缩进子项。
    for line in lines[int_start + 1 :]:

        # 空行不结束 YAML 区块，也不产生字段。
        if not line.strip():

            # 继续寻找下一个有效 interface 子项。
            continue

        # 首个非缩进行表示已离开 interface 区块。
        if not line.startswith((" ", "\t")):

            # 后续顶层配置不属于界面契约。
            break

        # 去除结构缩进后解析单行键值。
        stripped = line.strip()  # 当前 interface 子项文本

        # 不含冒号的复杂 YAML 行不在简化解析范围内。
        if ":" not in stripped:

            # 跳过列表或其他非标量语法。
            continue

        # 首个冒号分离字段名和值，保留值内部冒号。
        key, raw_value = stripped.split(":", 1)  # 当前界面键值片段

        # 外层单双引号不参与合同文本比较。
        dict_data[key.strip()] = raw_value.strip().strip('"').strip("'")  # 界面字段值

    # 返回可供必填字段与提示词对齐检查使用的映射。
    return dict_data

# 问题组解析只接受模块级列表字面量，避免执行目标源码。
def parse_group_assignment(script_text: str, name: str) -> list[list[str]] | None:
    """从设计问题源码中解析指定列表字面量赋值。

    参数：script_text 为源码全文，name 为模块级变量名。
    返回：字符串问题组列表；缺失或结构不合法时返回 None。
    """

    # 正则仅定位单个模块级赋值表达式，不执行源码。
    match = re.search(  # 指定问题组赋值
        rf"^{name}\s*=\s*(.+)$",  # 指定问题组的模块级赋值模式
        script_text,  # 待解析问题定义源码
        flags=re.MULTILINE,  # 按物理行匹配模块级赋值
    )

    # 未找到声明时由上层生成明确的对齐错误。
    if not match:

        # None 表示变量声明不可用。
        return None

    # literal_eval 将输入限制为 Python 字面量结构。
    try:

        # 将赋值右侧转换为不执行代码的原生值。
        str_literal = match.group(1).split("#", 1)[0].strip()  # 去除赋值行尾的语义注释。

        # 只把字面量转换成数据，禁止执行设计源码中的任意表达式。
        raw_value = ast.literal_eval(str_literal)  # 设计问题组的未规范化字面量。

    # 非字面量或语法错误均视为不可审计结构。
    except (SyntaxError, ValueError):

        # 上层统一报告变量无法解析。
        return None

    # 问题组容器必须保持列表顺序。
    if not isinstance(raw_value, list):

        # 其他容器不能证明设计问卷的稳定顺序。
        return None

    # 规范结果将每个问题编号统一转成字符串。
    list_groups: list[list[str]] = []  # 已验证问题组

    # 每个顶层元素都必须是一个问题编号列表。
    for item in raw_value:

        # 非列表元素破坏组边界合同。
        if not isinstance(item, list):

            # 任一结构错误使整项声明不可信。
            return None

        # 保留原顺序并统一编号比较类型。
        list_groups.append([str(part) for part in item])

    # 返回可与 SKILL.md 声明进行精确比较的问题组。
    return list_groups

# 文档中的问题组使用统一紧凑格式，便于对齐检查。
def format_group_list(groups: list[list[str]]) -> str:
    """把问题组列表格式化为 SKILL.md 使用的代码标记序列。

    参数：groups 为按顺序排列的问题编号组。
    返回：逗号分隔的 Markdown 代码标记文本。
    """

    # 每组内部不插入空格，以匹配技能文档的规范表示。
    return ", ".join(f"`[{','.join(group)}]`" for group in groups)

# 公共问题组文案比较独立成 helper，避免主校验函数承担两类循环。
def _validate_common_group_text(
    str_formatted_common: str,
    skill_text: str,
    errors: list[str],
) -> None:
    """校验技能正文中的公共问题组文案。

    参数：
        str_formatted_common: 从设计问题源码解析出的公共组文本。
        skill_text: 当前 SKILL.md 正文。
        errors: 接收文档漂移诊断的列表。
    返回：
        无；漂移时向 errors 追加一条诊断。
    """

    # 技能开发和工程开发两处说明都必须引用权威公共组。
    for str_label in COMMON_GROUP_LABELS:

        # 从对应标签截取当前句的问题组内容。
        object_match = re.search(  # 当前文档公共问题组段落。
            rf"{re.escape(str_label)}\s+(.+?)\.",  # 标签后的公共组正文。
            skill_text,  # 待对齐的技能说明正文。
            flags=re.DOTALL,  # 允许文档组列表跨行。
        )

        # 参数化正文不需要重复展开易漂移的公共编号。
        if object_match is None and PARAMETERIZED_GROUP_CONTRACT in skill_text:

            # 当前配置驱动正文已声明问题组来源。
            continue

        # 标签存在时必须包含源码解析出的完整公共组列表。
        if object_match is None or str_formatted_common not in object_match.group(1):

            # 单条错误覆盖两个文档入口的共同对齐要求。
            errors.append("SKILL.md common question groups must match collect_design_profile.py")

            # 首个漂移已足够定位，无需产生重复错误。
            break

# 兼容旧正文的专属问题组比较独立成 helper，减少主流程分支复杂度。
def _validate_profile_group_text(
    group_text: str,
    skill_text: str,
    errors: list[str],
) -> None:
    """校验技能和工程专属问题组的旧版文案。

    参数：
        group_text: 设计问题源码全文。
        skill_text: 当前 SKILL.md 正文。
        errors: 接收文档漂移诊断的列表。
    返回：
        无；兼容旧正文漂移时向 errors 追加诊断。
    """

    # 兼容旧正文时仍校验技能/工程专属问题组。
    for str_label, str_group_name, str_scope_name in PROFILE_GROUP_LABELS:

        # 只有文档显式包含旧组正文时才比较具体编号。
        object_match = re.search(  # 兼容文档中的专属问题组段落。
            rf"{re.escape(str_label)}\s+(.+?)\.",  # 当前专属标签后的问题组正文。
            skill_text,  # 待检查的技能说明正文。
            flags=re.DOTALL,  # 允许旧版组列表跨行。
        )

        # 缺失旧版标签时由参数化正文承担问题组来源。
        if object_match is None:

            # 参数化正文由运行时设计配置提供问题组，不需要复制当前编号。
            continue

        # 读取文档正文对应的实际组，并与设计配置中的同名组比较。
        list_profile_groups = parse_group_assignment(group_text, str_group_name) or []  # 源码中的专属问题组。

        # 将专属问题组转换成文档比较使用的紧凑文本。
        str_formatted_profile = format_group_list(list_profile_groups)  # 专属问题组规范文本。

        # 组列表为空或文档正文未包含完整组序列时报告漂移。
        if not list_profile_groups or str_formatted_profile not in object_match.group(1):

            # 明确区分专属问题组漂移和公共组漂移。
            errors.append(
                f"SKILL.md {str_scope_name} question groups must match collect_design_profile.py"
            )

# 问题组对齐门禁保证文档、普通访谈和接管访谈使用同一序列。
def validate_skill_contract_alignment(
    skill_dir: Path, skill_text: str, errors: list[str]
) -> None:
    """校验技能文档与设计问题组源码是否保持一致。

    参数：skill_dir 为技能根目录，skill_text 为说明全文，errors 接收错误。
    返回：无；发现的合同漂移追加到 errors。
    """

    # 采集入口存在性代表目标技能采用当前设计访谈布局。
    collect_path = (  # 设计访谈 CLI 路径
        skill_dir / "scripts" / "python" / "design" / "collect_design_profile.py"  # 设计访谈 CLI 文件
    )

    # 问题定义模块是组顺序的运行时事实来源。
    questions_path = (  # 设计问题源码路径
        skill_dir / "scripts" / "python" / "design" / "design_questions.py"  # 问题组事实来源
    )

    # 通用技能没有自举访谈布局时跳过该专属对齐项。
    if not collect_path.exists() or not questions_path.exists():

        # 缺少整个功能布局不在此函数重复报告。
        return

    # 读取源码文本供安全字面量解析，不导入目标模块。
    group_text = questions_path.read_text(  # 设计问题源码文本
        encoding="utf-8", errors="ignore"  # 容错读取问题定义源码
    )

    # 普通生成流程声明基础问题组顺序。
    list_common_groups: list[list[str]] = parse_group_assignment(  # 普通访谈问题组
        group_text, "COMMON_GROUPS"  # 普通访谈基础问题组
    ) or []

    # 接管流程必须继承同一基础组，避免治理问题被跳过。
    list_takeover_common_groups: list[list[str]] = parse_group_assignment(  # 接管访谈问题组
        group_text, "TAKEOVER_COMMON_GROUPS"  # 接管访谈基础问题组
    ) or []

    # 任一声明无法解析时不能继续做内容比较。
    if not list_common_groups or not list_takeover_common_groups:

        # 错误指向运行时事实来源，便于修复声明结构。
        errors.append(
            "scripts/python/design/design_questions.py: unable to parse COMMON_GROUPS "
            "and TAKEOVER_COMMON_GROUPS for audit alignment"
        )

        # 缺少可信组数据时终止本项对齐检查。
        return

    # 普通和接管入口不得因模式不同丢失基础治理问题。
    if list_common_groups != list_takeover_common_groups:

        # 报告两个源码声明之间的直接漂移。
        errors.append(
            "scripts/python/design/design_questions.py: COMMON_GROUPS and TAKEOVER_COMMON_GROUPS must stay aligned"
        )

    # 文档比较使用 SKILL.md 约定的紧凑代码标记形式。
    str_formatted_common = format_group_list(list_common_groups)  # 规范问题组文本

    # 让独立 helper 校验公共问题组文案。
    _validate_common_group_text(str_formatted_common, skill_text, errors)

    # 让独立 helper 校验兼容旧正文的专属问题组。
    _validate_profile_group_text(group_text, skill_text, errors)

# 引用文档必须同步关键入口政策，防止 SKILL.md 与操作指南表达分叉。
def validate_reference_alignment(skill_dir: Path, errors: list[str]) -> None:
    """校验引用文档中的治理说明是否与技能入口对齐。

    参数：skill_dir 为技能根目录，errors 接收发现的错误。
    返回：无；缺失的政策片段追加到 errors。
    """

    # 首组规则覆盖默认语言和远程服务器治理说明。
    for rel_path, snippets in REFERENCE_ALIGNMENT_RULES.items():

        # 每条规则绑定一个技能包内引用文档。
        path = skill_dir / rel_path  # 当前治理引用文件

        # 文件缺失由必需文件或引用存在性门禁统一报告。
        if not path.exists():

            # 避免为同一缺失文件追加内容漂移噪声。
            continue

        # 内容扫描采用容错读取，使审计可报告其他独立问题。
        text = path.read_text(encoding="utf-8", errors="ignore")  # 当前引用正文

        # 所有规定片段都必须同时存在才能证明政策闭合。
        if not all(snippet in text for snippet in snippets):

            # 错误指出该文档缺少语言或远程治理对齐内容。
            errors.append(
                f"{rel_path}: missing aligned default-language and remote-server governance guidance"
            )

    # 第二组规则独立覆盖 Python 与脚本双技能路由合同。
    for rel_path, snippets in LANGUAGE_SKILL_ROUTING_ALIGNMENT_RULES.items():

        # 路由规则同样逐文档执行完整片段检查。
        path = skill_dir / rel_path  # 当前语言路由引用文件

        # 缺失文件的结构错误由其他门禁负责。
        if not path.exists():

            # 仅对实际存在的文档做内容对齐审计。
            continue

        # 读取当前文档以核对双技能预检和最终归属表述。
        text = path.read_text(encoding="utf-8", errors="ignore")  # 路由说明正文

        # 任一必需片段缺失都意味着入口和引用政策存在漂移。
        if not all(snippet in text for snippet in snippets):

            # 将错误绑定到具体引用文档。
            errors.append(
                f"{rel_path}: missing language skill routing governance guidance"
            )

# SKILL.md 自身必须保留本地边界、远程变更和 Token 统计的硬化路由。
def validate_skill_rule_hardening(text: str, errors: list[str]) -> None:
    """校验技能入口是否保留关键安全和工具路由说明。

    参数：text 为 SKILL.md 全文，errors 接收发现的错误。
    返回：无；缺失的硬化合同追加到 errors。
    """

    # 自然语言锚点按大小写不敏感比较，避免句首大小写制造无意义耦合。
    str_normalized_text = text.lower()  # 技能入口规范比较文本。

    # 本地根边界与远程变更规则必须作为一个完整合同出现。
    if not all(snippet.lower() in str_normalized_text for snippet in SKILL_REQUIRED_SNIPPETS):

        # 缺失任一安全片段即报告入口硬化不完整。
        errors.append(
            "SKILL.md: missing local-root or remote-mutation hardening guidance"
        )

    # Token 用量请求需要独立只读路由，不能误入设计访谈。
    if not all(snippet.lower() in str_normalized_text for snippet in SKILL_TOKEN_USAGE_SNIPPETS):

        # 报告明确的工具分支合同缺口。
        errors.append("SKILL.md: missing explicit Codex token usage routing guidance")

# OpenAI 界面合同验证器返回字段和提示词错误。
def openai_yaml_contract_errors(interface: dict[str, str]) -> list[str]:
    """验证界面必填字段及简短技能启动提示合同。

    参数：interface 为解析后的 OpenAI 界面字段。
    返回：保持字段、长度、启动前缀和单句规则顺序的错误列表。
    """

    # 当前 helper 的诊断仅覆盖有效 interface 映射。
    list_errors: list[str] = []  # OpenAI 界面合同错误

    # 三个用户可见字段必须均存在且不能保留占位文本。
    for str_key in ("display_name", "short_description", "default_prompt"):

        # 统一去除外围空白后判断真实内容。
        str_value = interface.get(str_key, "").strip()  # 当前界面字段内容

        # 空值表示必填界面字段未配置。
        if not str_value:

            # 错误携带具体字段路径。
            list_errors.append(f"agents/openai.yaml: missing interface.{str_key}")

        # 常见占位词不能作为发布文案通过审计。
        elif str_value.lower() in {"todo", "tbd", "placeholder"}:

            # 报告仍需人工完成的界面字段。
            list_errors.append(f"agents/openai.yaml: interface.{str_key} is a placeholder")

    # 简介长度按用户可见字符计算，不以 UTF-8 字节误判中文。
    str_short_description = interface.get("short_description", "").strip()  # 技能简介正文

    # 占位简介已经由字段循环报告，长度门禁只处理真实文案。
    bool_description_ready = (  # 简介是否适合执行长度检查
        bool(str_short_description)  # 简介不能是空值
        and str_short_description.lower() not in {"todo", "tbd", "placeholder"}  # 简介不能是占位词
    )

    # 仅对真实简介追加长度诊断，避免同一根因产生重复错误。
    if bool_description_ready:

        # 实际字符数进入稳定错误，便于直接修复边界。
        int_description_chars = len(str_short_description)  # 技能简介实际字符数

        # 标准技能元数据要求简介落在闭区间 25 到 64。
        bool_description_length_valid = (  # 简介长度是否符合标准
            OPENAI_SHORT_DESCRIPTION_MIN_CHARS  # 标准允许的最少字符数
            <= int_description_chars  # 当前简介的实际字符数
            <= OPENAI_SHORT_DESCRIPTION_MAX_CHARS  # 标准允许的最多字符数
        )

        # 超出任一边界都报告范围和当前事实。
        if not bool_description_length_valid:

            # 字段级诊断同时报告标准范围和当前字符数。
            list_errors.append(
                "agents/openai.yaml: short_description must contain 25-64 characters "
                f"({int_description_chars})"
            )

    # 默认提示词原文用于字节预算、启动前缀和句子数检查。
    str_prompt = interface.get("default_prompt", "").strip()  # 默认提示词正文

    # UTF-8 字节预算直接限制产品入口上下文成本。
    int_prompt_bytes = len(str_prompt.encode("utf-8"))  # 默认提示词实际字节数

    # 超限内容必须下沉到 SKILL.md 或引用文档。
    if int_prompt_bytes > OPENAI_DEFAULT_PROMPT_MAX_BYTES:

        # 稳定诊断给出预算和实际字节数。
        list_errors.append(
            "agents/openai.yaml: default_prompt exceeds 256 UTF-8 bytes "
            f"({int_prompt_bytes})"
        )

    # 产品入口应直接展示可复制的显式技能调用。
    if str_prompt and not str_prompt.startswith("Use $agents-md-generator"):

        # 前缀错误比宽松的任意位置包含更可执行。
        list_errors.append(
            "agents/openai.yaml: default_prompt must start with Use $agents-md-generator"
        )

    # 句末标点只识别空白或字符串结尾前的英文标点，不误判 AGENTS.md。
    list_sentence_endings = re.findall(r"[!?]|[.](?=\s|$)", str_prompt)  # 提示词句末标点

    # 非空提示词必须是恰好一个完整句子。
    if str_prompt and len(list_sentence_endings) != 1:

        # 单句职责门禁阻止治理手册重新进入 UI 元数据。
        list_errors.append("agents/openai.yaml: default_prompt must be one sentence")

    # 调用方把合同错误追加到完整审计结果。
    return list_errors

# OpenAI 界面门禁只对本技能启用，通用技能不继承产品专属提示词。
def validate_openai_yaml(path: Path, errors: list[str], *, self_skill: bool) -> None:
    """校验自身技能的 OpenAI 界面字段和默认提示词合同。

    参数：path 为 openai.yaml 路径，errors 接收错误，self_skill 标识自身包。
    返回：无；界面或提示词缺口追加到 errors。
    """

    # 通用技能审计不强加 agents-md-generator 的产品文案。
    if not self_skill:

        # 非自身技能直接跳过专属界面检查。
        return

    # 文件缺失由技能必需文件门禁报告，避免重复诊断。
    if not path.exists():

        # 无内容可解析时结束本项检查。
        return

    # 读取完整配置以解析 interface 一级字段。
    text = path.read_text(encoding="utf-8", errors="ignore")  # OpenAI 配置正文

    # 简化解析结果足以验证必填显示字段和默认提示词。
    obj_object_interface: object = parse_openai_interface(text)  # interface 解析结果

    # 缺少整个 interface 区块时不能继续字段级检查。
    if obj_object_interface is None:

        # 报告产品界面入口缺失。
        errors.append("agents/openai.yaml: missing interface section")

        # 无字段映射时终止后续提示词验证。
        return

    # 将已确认的映射收窄为字段合同使用的具体类型。
    dict_interface: dict[str, str] = obj_object_interface if isinstance(obj_object_interface, dict) else {}  # interface 字段映射

    # 字段和提示词 helper 保持既有诊断顺序。
    errors.extend(openai_yaml_contract_errors(dict_interface))

# 全局基线必须包含的跨仓库通用规则片段。
def _required_baseline_snippets() -> tuple[str, ...]:
    """返回全局基线必须包含的跨仓库规则片段。

    参数：无。
    返回：按审计顺序排列的必需规则片段。
    """

    # 使用返回值承载多行字符串集合，避免赋值注释要求污染规则正文。
    return (
    "AGENTS-GENERATED:META generator=agents-md-generator schema=1 "
    "baseline=global-codex-baseline baseline_version=6",
    "## Instruction Scope",
    "## Managed Repository Entry",
    "## Execution Mode",
    "Prefer existing repository patterns, tools, libraries, templates",
    "non-trivial enough for rating to affect execution mode",
    "advisory",
    "timed follow-up",
    "must not compress code into one line",
    "clever or obfuscated code",
    "repository governance",
    "Coding Behavior Baseline",
    "Guidelines for avoiding common LLM coding mistakes",
    "### 1. Think Before Coding",
    (
        "For difficult implementation problems, check library documentation and reuse "
        "supported APIs before replacement code; avoid custom substitutes that add debugging cost"
    ),
    "Minimum code that solves the problem. Nothing speculative.",
    "### 3. Surgical Changes",
    "### 4. Work Toward Verifiable Goals",
    "fabricating test cases, outputs, or verification evidence",
    "### Done When",
    "Every changed line must trace directly to the request",
    "## Comments And Documentation",
    "Comment public contracts",
    "key invariants, non-obvious decisions, generation boundaries, and risk boundaries",
    "do not restate obvious code",
    "Update stale comments and documentation when behavior changes",
    "readable-python-generator",
    "readable-script-generator",
    "Markdown documentation formulas",
    "## Environment And Dependency Safety",
    "isolated project environment",
    "create an isolated environment under the remote workspace",
    "Never install into system Python",
    "conda `base`",
    "sudo pip",
    "pip install --user",
    "installed skill directories",
    "$CODEX_HOME/skills",
    "Always obtain exactly one explicit user confirmation",
    "Routine test-hash confirmation is prohibited.",
    "## Scope Discipline",
    "freeze `Goal`, `Success Criteria`, `In Scope`, and `Out of Scope`",
    "Treat every other feature, refactor, abstraction",
    "Reviewers may identify omissions, contradictions, risks, or unverifiable steps",
    "## Governed Planning And Testing",
    "Do not use non-testing subagents by default",
    "request in the current task authorizes non-testing subagents",
    "generic request to \"use multi-agent\"",
    "use exactly three",
    "explicit user-provided count overrides",
    "New tests use `<work-folder>/tests/<feature>/test_<behavior>.<ext>` under one root `tests/`",
    "Choose prose, tables, Mermaid flowcharts, or a combination",
    "execution needs no new design choice",
    "### Plan consistency review",
    "Resolve directly actionable contradictions first",
    "Never upload the whole work folder or a workspace bundle",
    )

# 全局基线必需规则片段集合。
REQUIRED_BASELINE_SNIPPETS: tuple[str, ...] = _required_baseline_snippets()  # 规则片段事实源

# 全局基线禁止出现的本仓库专属细节片段。
def _forbidden_baseline_snippets() -> tuple[str, ...]:
    """返回全局基线禁止出现的本仓库专属片段。

    参数：无。
    返回：按审计顺序排列的禁止泄漏片段。
    """

    # 使用独立返回值保持禁止清单可审查且不改变原有顺序。
    return (
    ".agents/script-governance-exceptions.json",
    "docs/development/decomposition-plans",
    "skills/agents-md-generator",
    "64KB UTF-8 size limit",
    "scripts/python/<function>/<name>.py",
    "scripts/shell/<function>/<name>.sh",
    "scripts/bat/<function>/<name>.bat",
    "scripts/powershell/<function>/<name>.ps1",
    "do not put formulas in fenced code blocks",
    )

# 全局基线禁止泄漏片段集合。
FORBIDDEN_BASELINE_SNIPPETS: tuple[str, ...] = _forbidden_baseline_snippets()  # 禁止片段事实源

# 全局基线模板必须保持跨仓库通用，不得泄漏本仓库实现细节。
def validate_global_baseline_template(path: Path, errors: list[str]) -> None:
    """校验全局 AGENTS 基线的必需规则和禁止内容。

    参数：path 为全局基线模板路径，errors 接收发现的错误。
    返回：无；规则缺口或仓库细节泄漏追加到 errors。
    """

    # 非自身技能快照可能不携带全局模板，缺失时由布局检查决定是否报错。
    if not path.exists():

        # 缺少模板时不执行内容级验证。
        return

    # 读取模板正文供通用规则与泄漏片段比对。
    text = path.read_text(encoding="utf-8", errors="ignore")  # 待审计全局基线正文

    # 预算只计受管基线正文；管理声明和元数据不属于生成规则内容。
    str_managed_text = text.split(  # 从模板中截取受管基线起点后的正文
        "AGENTS-GENERATED:START global-codex-baseline -->",  # 受管基线起点
        1,  # 只切分首个起点声明
    )[-1]  # 起点之后的候选受管正文

    # 终点之前的部分才参与生成内容预算。
    str_managed_text = str_managed_text.split(  # 从候选正文中移除受管终点后的内容
        "<!-- AGENTS-GENERATED:END global-codex-baseline",  # 受管基线终点
        1,  # 只切分首个终点声明
    )[0]  # 终点之前的受管正文

    # UTF-8 字节数与最终落盘体积保持同一口径。
    int_template_bytes = len(str_managed_text.encode("utf-8"))  # 受管基线实际字节数。

    # 超限时仍继续执行语义锚点检查，一次返回完整诊断。
    if int_template_bytes > GLOBAL_TEMPLATE_MAX_BYTES:

        # 固定预算写入错误，便于测试和维护者理解边界。
        errors.append(
            "assets/templates/global-codex-agents.md: exceeds 8192 UTF-8 bytes "
            f"({int_template_bytes})"
        )

    # 逐项报告缺失片段，便于维护者直接定位基线合同缺口。
    for snippet in REQUIRED_BASELINE_SNIPPETS:

        # 每个必需规则都必须出现在模板正文中。
        if snippet not in text:

            # 追加 validate_global_baseline_template 的技能审计诊断。
            errors.append(
                f"assets/templates/global-codex-agents.md: missing global baseline rule snippet `{snippet}`"
            )

    # 逐项检查仓库专属细节，避免全局规则污染其他项目。
    for snippet in FORBIDDEN_BASELINE_SNIPPETS:

        # 命中任一禁止片段都表示模板边界泄漏。
        if snippet in text:

            # 错误携带具体泄漏片段，便于直接移除。
            errors.append(
                f"assets/templates/global-codex-agents.md: must not leak repository-specific detail `{snippet}`"
            )

# 单案例验证隔离 ID、必填字段和设计模式合同。
def validate_eval_case(
    case: object,
    index: int,
    set_ids: set[str],
    set_duplicate_ids: set[str],
    set_covered_patterns: set[str], set_allowed_patterns: set[str],
    errors: list[str],
) -> None:
    """校验一个 eval case 并累计全局覆盖事实。

    参数：case 为原始案例；index 为位置；set_ids 累计唯一 ID；
    set_duplicate_ids 累计重复 ID；set_covered_patterns 与 set_allowed_patterns 管理模式覆盖；errors 接收错误。
    返回：无；案例错误和有效覆盖写入传入容器。
    """

    # 每个案例必须采用 JSON object，才能承载命名字段。
    if not isinstance(case, dict):

        # 错误使用位置标识无法读取 ID 的无效案例。
        errors.append(f"evals/evals.json: case {index} must be an object")

        # 非映射案例没有可继续验证的字段。
        return

    # 案例 ID 是效果测试选择和缺失检查的稳定主键。
    case_id = str(case.get("id", "")).strip()  # 当前案例标识

    # 空 ID 不能进入唯一性集合。
    if not case_id:

        # 使用物理位置帮助定位缺少主键的案例。
        errors.append(f"evals/evals.json: case {index} is missing id")

    # 已见 ID 表示案例选择会产生歧义。
    elif case_id in set_ids:

        # 集合去重重复诊断中的同一 ID。
        set_duplicate_ids.add(case_id)

    # 首次出现的有效 ID 参与必需案例覆盖比较。
    else:

        # 保存唯一案例身份供文件级汇总。
        set_ids.add(case_id)

    # 执行类别、处理器和说明是每个案例的最小可运行元数据。
    for key in ("kind", "handler", "description"):

        # 空白字符串与缺失字段都视为合同缺口。
        if not str(case.get(key, "")).strip():

            # 有 ID 时优先使用稳定主键，否则回退到位置。
            errors.append(
                f"evals/evals.json: case {case_id or index} is missing {key}"
            )

    # patterns 声明案例覆盖的技能设计模式类别。
    patterns = case.get("patterns")  # 当前案例模式列表

    # 模式必须以非空列表声明，避免无覆盖案例混入。
    if not isinstance(patterns, list) or not patterns:

        # 错误绑定案例身份并说明必须列出设计模式。
        errors.append(
            f"evals/evals.json: case {case_id or index} must list Skill design patterns"
        )

        # 无模式列表时不参与模式覆盖汇总。
        return

    # 规范化字符串并丢弃空模式值。
    normalized_patterns = {  # 当前案例有效模式集合
        str(pattern).strip()  # 当前案例的非空设计模式
        for pattern in patterns  # 案例声明的原始模式值
        if str(pattern).strip()  # 过滤空模式声明
    }

    # 列表可能只包含空字符串，仍不构成有效覆盖。
    if not normalized_patterns:

        # 与缺失列表采用同一稳定合同错误。
        errors.append(
            f"evals/evals.json: case {case_id or index} must list Skill design patterns"
        )

        # 空规范集合不能更新文件级覆盖。
        return

    # 识别未在技能设计合同中声明的模式名称。
    unknown_patterns = sorted(  # 当前案例未知模式
        normalized_patterns - set_allowed_patterns  # 未声明设计模式差集
    )

    # 未知名称通常意味着拼写错误或未治理扩展。
    if unknown_patterns:

        # 报告完整未知集合，便于一次修复同一案例。
        errors.append(
            f"evals/evals.json: case {case_id or index} uses unknown Skill design patterns {unknown_patterns}"
        )

    # 只有权威模式名称才能证明文件级覆盖。
    set_covered_patterns.update(
        normalized_patterns & set_allowed_patterns
    )

# eval 合同验证自身技能的案例身份、结构与设计模式覆盖。
def validate_evals_contract(path: Path, errors: list[str], *, self_skill: bool) -> None:
    """校验自身技能 eval 文件的结构和必需覆盖。

    参数：path 为 evals.json 路径，errors 接收错误，self_skill 标识自身包。
    返回：无；JSON、案例或覆盖缺口追加到 errors。
    异常：文件读取错误由调用环境传播；JSON 语法错误转为审计诊断。
    """

    # 通用技能或缺失 eval 文件时不启用自身效果测试合同。
    if not self_skill or not path.exists():

        # 结构缺失由必需文件门禁负责，避免重复错误。
        return

    # 独立 evaluation contract 是必需覆盖和模式白名单的唯一来源。
    path_contract = path.parent.parent / "config" / "evaluation" / "contract.json"  # 独立合同路径

    # 读取独立合同并把文件错误转换为审计诊断。
    try:

        # 解析独立合同 JSON，作为必需案例和模式白名单来源。
        dict_contract = json.loads(path_contract.read_text(encoding="utf-8"))  # 独立评估合同对象

    # 合同不可读或 JSON 损坏时保持 fail-closed 审计结果。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 记录合同读取失败并结束本项检查。
        errors.append("evaluation contract: unable to load independent contract")

        # 没有白名单就不能继续比较案例集合。
        return

    # 合同根必须是对象，后续字段读取才有稳定语义。
    if not isinstance(dict_contract, dict):

        # 记录根形状错误并终止当前验证。
        errors.append("evaluation contract: root must be a JSON object")

        # 结构错误时不猜测 required_case_ids 或 allowed_patterns。
        return

    # 从合同读取必需案例 ID，避免实现维护当前案例枚举。
    set_required_case_ids = {
        str(item).strip()  # 规范化必需案例标识
        for item in dict_contract.get("required_case_ids", [])  # 合同声明的必需案例
        if str(item).strip()  # 丢弃空标识
    }

    # 从合同读取允许的设计模式名称，作为唯一白名单。
    set_allowed_patterns = {
        str(item).strip()  # 规范化允许模式名称
        for item in dict_contract.get("allowed_patterns", [])  # 合同声明的允许模式
        if str(item).strip()  # 丢弃空模式
    }

    # JSON 解析错误需要转为稳定审计诊断。
    try:

        # 读取并解析完整 eval 配置。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # eval 案例配置根对象

    # 无效 JSON 不能继续执行结构和覆盖检查。
    except json.JSONDecodeError as exc:

        # 报告解析器提供的核心错误信息。
        errors.append(f"evals/evals.json: invalid JSON: {exc.msg}")

        # 根数据不可用时结束本项验证。
        return

    # eval 根必须是带 cases 字段的对象。
    if not isinstance(dict_data, dict):

        # 非对象根无法承载命名合同字段。
        errors.append("evals/evals.json: root must be a JSON object")

        # 结构类型错误后不再访问 cases。
        return

    # cases 是所有效果测试场景的有序集合。
    cases = dict_data.get("cases")  # eval 案例列表

    # 至少一个案例才能形成可运行的效果测试包。
    if not isinstance(cases, list) or not cases:

        # 缺少非空列表时报告文件级结构错误。
        errors.append("evals/evals.json: cases must be a non-empty list")

        # 无案例数据时不能继续汇总覆盖。
        return

    # 唯一 ID 集合用于必需案例和重复身份检查。
    set_ids: set[str] = set()  # 已见有效案例 ID

    # 重复集合单独保存，避免同一 ID 多次产生噪声。
    set_duplicate_ids: set[str] = set()  # 重复案例 ID

    # 模式覆盖集合汇总所有案例声明的权威设计模式。
    set_covered_patterns: set[str] = set()  # 已覆盖技能设计模式

    # 单案例助手隔离字段分支，文件级函数只编排覆盖汇总。
    for index, case in enumerate(cases):

        # 传入共享集合以累积唯一 ID、重复 ID 和设计模式覆盖。
        validate_eval_case(
            case, index,
            set_ids, set_duplicate_ids,
            set_covered_patterns, set_allowed_patterns,
            errors,
        )

    # 任一重复 ID 都会使案例选择和结果归属产生歧义。
    if set_duplicate_ids:

        # 排序输出保证错误文本跨运行稳定。
        errors.append(
            f"evals/evals.json: duplicate case ids {sorted(set_duplicate_ids)}"
        )

    # 必需案例差集表示关键治理能力没有效果测试。
    missing_cases = sorted(set_required_case_ids - set_ids)  # 缺失必需案例 ID

    # 非空差集作为发布阻断错误。
    if missing_cases:

        # 一次报告完整缺失集合。
        errors.append(
            f"evals/evals.json: missing required effectiveness cases {missing_cases}"
        )

    # 模式差集证明 eval 是否覆盖技能设计合同的全部类别。
    missing_patterns = sorted(  # 文件级缺失设计模式
        set_allowed_patterns - set_covered_patterns  # 文件级模式覆盖差集
    )

    # 每个核心模式至少需要一个案例声明。
    if missing_patterns:

        # 报告未被任何案例覆盖的模式集合。
        errors.append(
            f"evals/evals.json: missing required Skill design pattern coverage {missing_patterns}"
        )

# 默认输出策略必须符合统一 Kind、前缀和机器协议边界。
def validate_script_output_default_config(path: Path, errors: list[str]) -> None:
    """校验默认脚本输出策略配置。

    参数：path 为默认策略 JSON 路径，errors 接收发现的错误。
    返回：无；配置解析或策略验证错误追加到 errors。
    异常：文件读取错误由调用环境传播；JSON 语法错误转为审计诊断。
    """

    # 直接导入本模块的调用点也需要绑定延迟加载的策略验证器。
    load_runtime_dependencies()

    # 非自身技能快照可不包含默认策略，存在时才执行内容校验。
    if not path.is_file():

        # 缺少默认策略时由布局门禁统一报告。
        return

    # JSON 语法错误转为稳定诊断，避免审计命令因输入损坏崩溃。
    try:

        # 解析默认策略对象供共享配置验证器检查。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # 默认输出策略对象

    # JSON 解析失败必须转为审计错误而不是中断命令。
    except json.JSONDecodeError as exc:

        # 保留解析器提供的简洁错误原因，供用户修复配置。
        errors.append(
            f"config/script-output-policy-default.json: invalid JSON: {exc.msg}"
        )

        # 无有效对象可继续检查，结束本项验证。
        return

    # 策略根必须是对象，后续字段校验不接受数组或标量。
    if not isinstance(dict_data, dict):

        # 根类型错误写入稳定的配置路径诊断。
        errors.append(
            "config/script-output-policy-default.json: root must be a JSON object"
        )

        # 非对象根无法进入字段级策略验证。
        return

    # 复用运行时策略校验器，确保审计和实际加载采用同一合同。
    for item in validate_script_output_policy_data(dict_data, require_explicit=True):

        # 每个共享验证错误都补充默认配置文件上下文。
        errors.append(f"config/script-output-policy-default.json: {item}")

# 运行时分片检查阻止已退役的 numbered shard 名称重新出现。
def validate_runtime_shard_references(skill_dir: Path, errors: list[str]) -> None:
    """阻止运行时入口继续引用 numbered shard 名称。

    参数：skill_dir 为技能根目录，errors 接收发现的陈旧引用错误。
    返回：无；每个陈旧源码引用追加到 errors。
    """

    # 运行时源码根是 numbered shard 引用扫描的唯一范围。
    scripts_python_root = skill_dir / "scripts" / "python"  # Python 运行时根目录

    # 安装快照若无 Python 运行时目录，则没有需要扫描的源码。
    if not scripts_python_root.is_dir():

        # 无生产 Python 目录时不存在分片引用检查对象。
        return

    # 稳定遍历全部 Python 源码，保证诊断顺序可复现。
    for path in sorted(scripts_python_root.rglob("*.py")):

        # 相对路径用于生成可在源码和发布快照间复用的诊断。
        rel_path = path.relative_to(skill_dir).as_posix()  # 技能根相对诊断路径

        # 文件正文是陈旧分片正则的唯一扫描输入。
        text = path.read_text(encoding="utf-8", errors="ignore")  # 当前源码文本

        # numbered shard 已被稳定模块名取代，任何残留引用都阻断发布。
        if STALE_NUMBERED_SHARD_RE.search(text):

            # 报告具体源码路径，阻止陈旧运行时依赖进入发布物。
            errors.append(f"{rel_path}: stale numbered shard reference")

# 发布目录和源码目录通过结构锚点解析所属项目根。
def skill_project_root(skill_dir: Path) -> Path:
    """解析技能目录所属的仓库根目录。

    参数：skill_dir 为源码、安装或发布快照技能目录。
    返回：包含技能源码布局的项目根；无法识别时返回技能目录本身。
    """

    # 源码布局以 skills/<name> 表示技能目录，其上两级即项目根。
    if skill_dir.parent.name == "skills":

        # 标准源码布局从技能目录向上两级得到仓库根。
        return skill_dir.parents[1]

    # 发布包和安装副本以技能目录自身作为项目边界。
    return skill_dir

# 仓库治理标记决定是否启用分解计划等项目级门禁。
def has_repo_governance(project_root: Path) -> bool:
    """判断项目根是否声明 agents-md-generator 仓库治理。

    参数：project_root 为候选项目根目录。
    返回：存在权威治理配置时为真。
    """

    # 权威规则覆盖文件是启用仓库级治理的最小稳定标记。
    return (project_root / ".agents" / "global-rule-overrides.json").is_file()

# 超限源码的分解计划必须位于治理配置指定位置并包含完整章节。
def validate_decomposition_plan(project_root: Path, relative_path: str) -> list[str]:
    """校验指定源码对应的分解计划是否完整。

    参数：project_root 为项目根，relative_path 为项目相对源码路径。
    返回：分解计划路径、覆盖或章节错误列表。
    """

    # 治理配置根据源文件相对路径确定权威分解计划位置。
    plan_path = decomposition_plan_path(project_root, relative_path)  # 分解计划路径

    # 超限源码没有对应计划时直接返回可操作的治理错误。
    if not plan_path.is_file():

        # 返回所需计划位置，指导维护者补齐治理文档。
        return [
            f"{relative_path} exceeds configured size limit and requires decomposition "
            f"plan `{plan_path.relative_to(project_root).as_posix()}`"
        ]

    # 读取计划正文以检查配置声明的章节覆盖。
    text = plan_path.read_text(encoding="utf-8", errors="ignore")  # 分解计划正文

    # 必需章节由仓库配置提供，禁止在审计器中复制业务枚举。
    list_required_sections: list[str] = func_load_global_rule_overrides(project_root)["data"][  # 必需计划章节
        "source_file_limits"  # 源码规模治理配置区块
    ].get("required_plan_sections", [])

    # 计划必须包含配置声明的每个治理章节。
    missing = [  # 缺失分解计划章节
        section  # 计划正文缺失的治理章节
        for section in list_required_sections  # 配置要求的计划章节
        if f"## {section}" not in text  # 仅保留正文缺失章节
    ]

    # 缺失章节以单条聚合诊断返回，保留完整缺口集合。
    if missing:

        # 聚合返回全部缺失章节，避免逐次修复。
        return [
            f"{plan_path.relative_to(project_root).as_posix()}: missing decomposition plan sections {missing}"
        ]

    # 文件存在且章节完整时，分解计划合同通过。
    return []

# 必需文件检查同时拒绝自身技能根中的冗余治理文档。
def audit_required_layout(
    skill_dir: Path,
    bool_self_skill: bool,
    list_checked: list[str],
    list_errors: list[str],
) -> None:
    """校验技能必需文件与自身技能根目录边界。

    参数：skill_dir 为技能根，bool_self_skill 控制专属合同，
    list_checked 累计已检查路径，list_errors 累计错误。
    返回：无；检查路径和错误写入传入列表。
    """

    # 自身技能在通用入口之外还需完整产品和治理资源。
    list_required_files = [Path(item) for item in CORE_REQUIRED_FILES] + (  # 当前身份要求的文件集合
        SELF_REQUIRED_FILES if bool_self_skill else []  # 自身技能额外必需文件
    )

    # 平台 metadata 按已解析配置选择；通用发布包则要求目录声明的全部候选。
    if bool_self_skill:

        # 自身技能的平台配置决定发布包中的 metadata 文件清单。
        from agent_platform import load_agent_config

        # 读取发布平台清单，异常时保持统一布局错误。
        try:

            # 读取当前平台声明的技能 metadata 相对路径。
            list_metadata: list[str] = list(load_agent_config(skill_dir).skill_metadata)  # 平台 metadata 路径

        # 配置合同错误不能继续推导必需文件集合。
        except ValueError as object_error:

            # 将配置解析异常转换为可定位的审计错误。
            list_errors.append(f"config/agent.json: {object_error}")

            # 配置错误不应阻止通用和自身必需文件继续聚合报告。
            list_metadata = []  # 配置不可用时不追加平台特有路径

        # 将平台声明的相对路径加入统一检查集合。
        list_required_files.extend(Path(str_metadata) for str_metadata in list_metadata)

    # 每个必需相对路径都进入覆盖清单并检查存在性。
    for path_relative in list_required_files:

        # 组合技能根得到当前必需文件的实际位置。
        path = skill_dir / path_relative  # 当前必需文件路径

        # 对外诊断统一使用 POSIX 风格相对路径。
        str_rel_path = path_relative.as_posix()  # 当前必需资源相对路径

        # 无论存在与否都记录本次门禁已经检查该路径。
        list_checked.append(str_rel_path)

        # 缺失文件直接破坏技能包结构合同。
        if not path.exists():

            # 错误保留相对路径以适配源码和发布目录。
            list_errors.append(f"missing required file: {str_rel_path}")

    # 自身技能根还要拒绝与 SKILL.md 重复的额外文档。
    if bool_self_skill:

        # 逐个检查已明确退役的根文档名称。
        for name in SELF_DISALLOWED_ROOT_DOCS:

            # 实际存在即表示发布内容边界漂移。
            if (skill_dir / name).exists():

                # 错误直接指出多余文档名。
                list_errors.append(f"disallowed extra root documentation file: {name}")

    # 技能包根不得携带用于仓库开发的 AGENTS.md。
    if bool_self_skill and (skill_dir / "AGENTS.md").exists():

        # 防止仓库治理文件被误打入可安装技能。
        list_errors.append("disallowed skill root AGENTS.md")

# SKILL.md 入口检查元数据、大小、引用和自身技能硬化合同。
def audit_skill_document(
    skill_dir: Path,
    skill_path: Path,
    frontmatter: dict[str, str],
    bool_self_skill: bool,
    list_checked: list[str],
    list_errors: list[str],
) -> None:
    """校验 SKILL.md 元数据、引用和自身技能入口合同。

    参数：skill_dir 为技能根，skill_path 为入口文档，frontmatter 为元数据，
    bool_self_skill 为身份标识，list_checked 累计路径，list_errors 累计错误。
    返回：无；文档错误写入传入列表。
    """

    # 缺失主说明已由布局门禁报告，此处没有可验证内容。
    if not skill_path.exists():

        # 避免对不存在文件产生读取异常。
        return

    # 完整正文用于长度、引用和本地路径扫描。
    text = skill_path.read_text(encoding="utf-8", errors="ignore")  # SKILL.md 完整审计正文

    # frontmatter 只允许标准 name 和 description 字段。
    if set(frontmatter) != {"name", "description"}:

        # 额外或缺失字段都会破坏技能标准元数据边界。
        list_errors.append("SKILL.md frontmatter must contain only name and description")

    # 技能名称决定目录身份和触发引用。
    name = frontmatter.get("name", "")  # frontmatter 技能名称

    # 名称仅允许小写字母、数字和连字符。
    if not SKILL_NAME_RE.fullmatch(name):

        # 非法名称不能作为可安装技能标识。
        list_errors.append("SKILL.md name must match [a-z0-9-]+")

    # 合法名称还必须与普通或版本化目录身份一致。
    if name and not skill_directory_name_matches(skill_dir, name):

        # 目录漂移会破坏安装和发现路径。
        list_errors.append("SKILL.md name must match the skill directory name")

    # 描述承担技能触发条件，必须保持标准开头和长度。
    description = frontmatter.get("description", "")  # 技能触发描述

    # “Use when” 前缀让代理能稳定识别使用场景。
    if not description.startswith("Use when"):

        # 缺失触发前缀违反技能标准。
        list_errors.append("SKILL.md description must start with 'Use when'")

    # 过长描述会增加每轮技能发现上下文成本。
    if len(description) > 1024:

        # 描述上限以字符数执行。
        list_errors.append("SKILL.md description must be 1024 characters or fewer")

    # 主技能说明保持在五百行以内以控制加载成本。
    if len(text.splitlines()) > 500:

        # 超限正文应把细节下沉到 references。
        list_errors.append("SKILL.md must stay under 500 lines")

    # 代码标记中的内部资源引用必须真实存在。
    for rel_path in referenced_paths(text):

        # 引用路径也计入本次审计覆盖清单。
        list_checked.append(rel_path)

        # 缺失资源会导致技能说明中的工作流不可执行。
        if not (skill_dir / rel_path).exists():

            # 错误保留 SKILL.md 声明的相对路径。
            list_errors.append(f"SKILL.md references missing resource: {rel_path}")

    # 主说明不得绑定开发机绝对路径或本地 ref 目录。
    if contains_local_reference(text):

        # 本地依赖会使安装后的技能不可移植。
        list_errors.append("SKILL.md must not depend on local reference folders")

    # 具备设计访谈源码的技能都需要核对问题组，不能只按技能目录名跳过。
    validate_skill_contract_alignment(skill_dir, text, list_errors)

    # 自身技能额外核对入口硬化说明。
    if bool_self_skill:

        # 本地/远程边界与 Token 路由必须保留。
        validate_skill_rule_hardening(text, list_errors)

# 自身技能专属检查集中版本、界面、引用、eval 和运行时分片合同。
def audit_self_contracts(
    skill_dir: Path, bool_self_skill: bool, list_errors: list[str]
) -> None:
    """校验 agents-md-generator 自身专属合同。

    参数：skill_dir 为技能根，bool_self_skill 为身份标识，list_errors 接收错误。
    返回：无；专属合同错误写入 list_errors。
    """

    # 版本文件是自身技能目录名和发布标识的权威来源。
    version_path = skill_dir / "VERSION"  # 自身技能语义版本文件

    # 仅自身技能需要校验 VERSION 内容，通用审计不强加版本策略。
    if bool_self_skill and version_path.exists():

        # 规范化版本文本供格式和策略两层校验共用。
        version_text = version_path.read_text(  # 当前语义版本文本
            encoding="utf-8", errors="ignore"  # 容错读取自身版本文本
        ).strip()  # 当前版本文本

        # 基础格式先提供直观错误，版本策略再检查具体支持范围。
        if not re.fullmatch(r"v\d+\.\d+\.\d+", version_text):

            # 非语义版本格式不能进入自身技能发布流程。
            list_errors.append("VERSION must use semantic format vX.Y.Z")

        # 仓库版本策略进一步验证当前版本是否受支持。
        str_version_error = func_version_policy_error(version_text)  # 版本策略诊断

        # 策略校验器以空值表示通过，仅追加真实错误。
        if str_version_error:

            # 仅在策略返回真实错误时追加诊断。
            list_errors.append(str_version_error)

    # 平台 metadata 只验证当前投影选择；Codex 额外执行 OpenAI 界面合同。
    if bool_self_skill:

        # 自身技能的平台配置决定本轮要检查的 metadata 文件。
        from agent_platform import load_agent_config

        # 当前平台合同仅在读取成功后继续展开。
        try:

            # 读取平台配置对象，供后续选择 OpenAI 专属合同。
            profile_agent = load_agent_config(skill_dir)  # 当前平台配置对象

            # 保留平台声明顺序供逐项存在性检查。
            list_metadata: list[str] = list(profile_agent.skill_metadata)  # 当前 metadata 路径

        # 配置合同错误不能继续推导 metadata 文件。
        except ValueError as object_error:

            # 记录配置文件错误并结束本项平台检查。
            list_errors.append(f"config/agent.json: {object_error}")

            # 配置错误不应阻止后续 metadata 和 OpenAI interface 缺口聚合。
            profile_agent = None  # 平台画像不可用时进入通用 interface 缺口检查

            # 无法读取平台清单时不追加平台特有文件。
            list_metadata = []  # 配置异常下的平台 metadata 空集合

        # 逐项核对平台声明的 metadata 文件是否存在且非空。
        for str_metadata in list_metadata:

            # 组合技能根目录得到当前平台 metadata 文件。
            path_metadata: Path = skill_dir / str_metadata  # 当前 metadata 文件路径

            # 缺失或空文件都不能满足平台发布合同。
            if not path_metadata.is_file() or not path_metadata.read_text(encoding="utf-8", errors="ignore").strip():

                # 记录具体平台 metadata 相对路径。
                list_errors.append(f"{str_metadata}: metadata file is missing or empty")

        # Codex 平台额外要求 OpenAI 界面合同完整。
        if profile_agent is None or profile_agent.agent == "codex":

            # 复用统一 interface 校验器，避免平台分支漂移。
            validate_openai_yaml(skill_dir / "agents" / "openai.yaml", list_errors, self_skill=True)

    # 通用技能审计到此结束，避免套用 agents-md-generator 私有资产合同。
    if not bool_self_skill:

        # 通用技能不适用自身技能专属资产合同。
        return

    # 自身技能引用清单必须与实际文件及 SKILL.md 导航一致。
    validate_reference_alignment(skill_dir, list_errors)

    # 全局基线模板必须保持必需通用规则且不得泄漏项目细节。
    validate_global_baseline_template(
        skill_dir / "assets" / "templates" / "global-codex-agents.md", list_errors
    )

    # eval 契约覆盖用例标识、提示词和预期行为的发布稳定性。
    validate_evals_contract(
        skill_dir / "evals" / "evals.json", list_errors, self_skill=True
    )

    # 默认输出策略与运行时验证器必须共享统一配置合同。
    validate_script_output_default_config(
        skill_dir / "config" / "script-output-policy-default.json", list_errors
    )

    # 运行时源码不得重新引入已经淘汰的 numbered shard 引用。
    validate_runtime_shard_references(skill_dir, list_errors)

# 脚本检查覆盖任务目录布局、语法和超限源码分解计划。
def audit_script_sources(
    skill_dir: Path,
    path_project_root: Path,
    bool_self_skill: bool,
    list_checked: list[str],
    list_errors: list[str],
) -> None:
    """校验技能 Python 脚本布局、语法和分解计划。

    参数：skill_dir 为技能根，path_project_root 为仓库根，
    bool_self_skill 为身份标识，list_checked 累计路径，list_errors 累计错误。
    返回：无；脚本错误写入 list_errors。
    """

    # scripts 根同时承载旧顶层入口探测和通用技能脚本扫描。
    scripts_root = skill_dir / "scripts"  # 技能脚本根目录

    # 自身技能的生产 Python 必须位于按任务分类的二级目录。
    scripts_python_root = scripts_root / "python"  # 分类 Python 运行时根

    # 自身技能额外执行旧入口拒绝和任务登记表完整性检查。
    if bool_self_skill:

        # 顶层 Python 入口已退役，任何残留都表示迁移未闭合。
        for script in sorted(scripts_root.glob("*.py")):

            # 错误记录具体旧入口路径。
            list_errors.append(
                f"{script.relative_to(skill_dir).as_posix()} is a removed legacy top-level script entry"
            )

        # 任务登记表中的每个 CLI 都必须落在声明的任务目录。
        for script_name, task_name in sorted(script_task_by_name.items()):

            # 组合权威任务名与脚本名得到预期生产路径。
            expected_script = (  # 当前登记脚本预期路径
                scripts_python_root / task_name / script_name  # 任务分类后的生产入口
            )

            # 缺失入口会破坏包装器和文档声明的命令合同。
            if not expected_script.is_file():

                # 错误保留任务目录和脚本名，便于直接定位。
                list_errors.append(
                    f"missing task-classified script: scripts/python/{task_name}/{script_name}"
                )

        # 自身技能仅把生产 Python 任务树纳入源码检查。
        list_scripts_to_check = sorted(  # 自身技能待检查脚本
            scripts_python_root.rglob("*.py")  # 生产 Python 任务树脚本
        )

    # 通用技能保留传统 scripts 下任意层级的 Python 支持。
    else:

        # 扫描完整脚本树以兼容不采用任务分类布局的技能。
        list_scripts_to_check = sorted(  # 通用技能待检查脚本
            scripts_root.rglob("*.py")  # 传统技能脚本树中的 Python 文件
        )

    # 每个发现的 Python 文件都执行登记、语法和规模治理。
    for script in list_scripts_to_check:

        # 结果载荷统一使用技能根相对 POSIX 路径。
        rel_path = script.relative_to(skill_dir).as_posix()  # 当前脚本相对路径

        # 必需文件阶段已登记的路径无需重复追加。
        if rel_path not in list_checked:

            # 保存实际扫描覆盖供调用方核验。
            list_checked.append(rel_path)

        # 容错读取允许语法编译给出稳定诊断。
        source = script.read_text(encoding="utf-8", errors="ignore")  # 当前脚本源码

        # compile 只验证语法，不执行目标模块的副作用。
        try:

            # 使用真实路径生成可定位的语法错误上下文。
            compile(source, str(script), "exec")

        # 语法错误转为审计载荷而不是终止整个技能扫描。
        except SyntaxError as exc:

            # 报告脚本路径和解析器给出的核心错误文本。
            list_errors.append(f"{rel_path} does not compile: {exc.msg}")

        # UTF-8 字节数与源码治理的规模单位保持一致。
        byte_count = len(source.encode("utf-8"))  # 当前脚本源码字节数

        # 只有受治理仓库中的超限文件需要权威分解计划。
        if byte_count > 65536 and has_repo_governance(path_project_root):

            # 源码目录位于项目内时使用项目相对路径查找计划。
            str_relative_to_project: str = (  # 分解计划索引路径
                script.relative_to(path_project_root).as_posix()  # 仓库内源码索引
                if script.is_relative_to(path_project_root)  # 仓库内外路径分支
                else rel_path  # 发布快照使用技能相对路径
            )

            # 将计划缺失或章节不完整错误并入总审计结果。
            list_errors.extend(
                validate_decomposition_plan(path_project_root, str_relative_to_project)
            )

# 文本资源审计器检查引用目录、占位符和本地路径。
def audit_text_resource(
    path: Path,
    rel_path: str,
    rel_parts: tuple[str, ...],
    text: str,
    list_errors: list[str],
    list_warnings: list[str],
) -> None:
    """审计已经读取的技能文本资源。

    参数：path 为文件，rel_path 为相对路径，rel_parts 为路径组件，text 为正文，
    list_errors 与 list_warnings 为共享结果列表。
    返回：无；文本诊断写入对应列表。
    """

    # 长引用文档需要目录帮助代理快速定位内容。
    if rel_parts and rel_parts[0] == "references" and path.suffix == ".md":

        # 物理行用于长度阈值和前部目录探测。
        lines = text.splitlines()  # 当前引用文档物理行

        # 超过一百行且无目录会降低引用检索效率。
        if len(lines) > 100 and not has_toc(lines):

            # 错误指出具体长文档和目录要求。
            list_errors.append(f"{rel_path}: reference files over 100 lines need a table of contents")

    # 主说明和代理界面中的模板语法可能是未渲染残留。
    if "{{" in text and (rel_path == "SKILL.md" or rel_path.startswith("agents/")):

        # 可疑占位符保留为警告而非直接阻断。
        list_warnings.append(f"{rel_path}: contains template placeholder syntax outside templates")

    # 正式模板只能使用渲染器声明的已知占位符。
    if rel_path.startswith("assets/templates/"):

        # 文件名选择对应模板的占位符白名单。
        str_template_name = path.name  # 当前模板文件名

        # 未登记模板拒绝所有隐式占位符。
        set_known = KNOWN_TEMPLATE_PLACEHOLDERS.get(str_template_name, set())  # 允许占位符

        # 差集逐项报告渲染器无法识别的占位符。
        for str_placeholder in sorted(set(TEMPLATE_PLACEHOLDER_RE.findall(text)) - set_known):

            # 错误携带模板名和未知字段名。
            list_errors.append(
                f"{str_template_name}: contains unknown template placeholder: {str_placeholder}"
            )

    # 任何分发文本都不得依赖开发机本地绝对路径。
    if contains_local_reference(text):

        # 路径泄漏作为发布阻断错误记录。
        list_errors.append(f"{rel_path}: references local-only development material")

# 单资源审计器筛选缓存、目录和可读文本类型。
def audit_resource_path(
    path: Path,
    skill_dir: Path,
    list_errors: list[str],
    list_warnings: list[str],
) -> None:
    """审计技能树中的单个文件系统成员。

    参数：path 为资源，skill_dir 为技能根，list_errors 累计错误，
    list_warnings 累计警告。
    返回：无；当前资源诊断写入对应严重度列表。
    """

    # POSIX 相对路径用于稳定跨平台诊断文本。
    rel_path = path.relative_to(skill_dir).as_posix()  # 当前资源相对路径

    # 路径组件便于识别缓存和版本控制目录。
    rel_parts = path.relative_to(skill_dir).parts  # 当前资源路径组件

    # 嵌套 Git 元数据不属于技能分发审计范围。
    if ".git" in rel_parts:

        # Git 内部成员不产生审计结果。
        return

    # Python 缓存目录和字节码文件都不得进入技能包。
    if "__pycache__" in rel_parts or path.suffix in DISALLOWED_CACHE_SUFFIXES:

        # 缓存路径作为阻断错误写入报告。
        list_errors.append(f"disallowed generated cache artifact: {rel_path}")

        # 缓存内容无需继续做文本检查。
        return

    # 目录和非文本资源没有内容合同。
    if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".py"}:

        # 无文本合同的成员结束当前审计。
        return

    # 容错读取保持一次审计可覆盖完整资源树。
    text = path.read_text(encoding="utf-8", errors="ignore")  # 当前资源文本

    # 文本 helper 继续执行引用、模板和路径检查。
    audit_text_resource(path, rel_path, rel_parts, text, list_errors, list_warnings)

# 资源树检查缓存、目录、模板占位符和本地路径泄漏。
def audit_resource_tree(
    skill_dir: Path, list_errors: list[str], list_warnings: list[str]
) -> None:
    """扫描技能资源树中的生成物和内容边界问题。

    参数：skill_dir 为技能根，list_errors 与 list_warnings 累计结果。
    返回：无；发现写入对应严重度列表。
    """

    # 外层只保持稳定遍历顺序，单资源 helper 负责分类。
    for path in skill_dir.rglob("*"):

        # 每个成员独立追加诊断并保持 rglob 顺序。
        audit_resource_path(path, skill_dir, list_errors, list_warnings)

# 总审计编排结构、引用、产品合同和仓库治理检查。
def audit(skill_dir: Path) -> dict:
    """执行技能包完整静态审计并生成机器可读载荷。

    参数：skill_dir 为待审计技能目录。
    返回：包含 checked、errors、warnings 和目标路径的结果映射。
    异常：不可恢复的文件系统错误由调用环境传播。
    """

    # 仅在真实审计入口加载跨任务依赖，保持模块导入无副作用。
    load_runtime_dependencies()

    # 错误列表承载阻断发布或运行合同的问题。
    list_errors: list[str] = []  # 审计阻断错误

    # 警告列表承载需要复核但不直接拒绝技能的情况。
    list_warnings: list[str] = []  # 审计警告

    # 检查清单证明本次审计实际覆盖的文件集合。
    list_checked: list[str] = []  # 已检查技能相对路径

    # 项目根用于读取仓库级规模和分解计划治理事实。
    path_project_root = skill_project_root(skill_dir)  # 技能所属项目根

    # SKILL.md 是通用技能身份与触发描述的权威入口。
    skill_path = skill_dir / "SKILL.md"  # 技能主说明路径

    # 文件存在时解析受支持 frontmatter，否则保持空映射供缺失门禁使用。
    dict_frontmatter: dict[str, str] = (  # 技能元数据映射
        parse_frontmatter(  # 解析存在的技能主说明元数据
            skill_path.read_text(encoding="utf-8", errors="ignore")  # 技能主说明正文
        )
        if skill_path.exists()  # 仅解析实际存在的主说明
        else {}  # 主说明缺失时的空元数据
    )

    # 自身技能身份启用产品、治理和运行时专属合同。
    bool_self_skill = is_agents_md_generator_skill(  # 是否审计自身技能
        skill_dir, dict_frontmatter  # 目录与声明共同决定自身身份
    )  # 是否审计 agents-md-generator 自身

    # 第一阶段核对文件布局和技能根边界。
    audit_required_layout(skill_dir, bool_self_skill, list_checked, list_errors)

    # 自身技能必须通过活动平台路径硬编码门禁并记录清单摘要。
    if bool_self_skill:

        # 平台硬编码门禁需要读取当前活动平台的投影结果。
        from agent_platform_gate import active_platform_hardcoding_gate

        # 执行平台路径检查并保存其机器可读结果。
        dict_platform_gate: dict[str, list[str]] = active_platform_hardcoding_gate((skill_dir,))  # 平台硬编码门禁结果

        # 把门禁实际覆盖的文件并入总检查清单。
        list_checked.extend(dict_platform_gate["checked_files"])

        # 把门禁发现的硬编码错误并入总错误集合。
        list_errors.extend(str_error for str_error in dict_platform_gate["errors"])

    # 第二阶段验证技能入口元数据与内部引用。
    audit_skill_document(
        skill_dir,
        skill_path,
        dict_frontmatter,
        bool_self_skill,
        list_checked,
        list_errors,
    )

    # 第三阶段执行版本、产品界面、eval 和引用对齐合同。
    audit_self_contracts(skill_dir, bool_self_skill, list_errors)

    # 自身技能同时是公开发布包，必须通过双语 README 与元数据合同。
    if bool_self_skill:

        # 公开产品文件事实与通用审计结果合并保存。
        dict_public_report = validate_public_skill_files(skill_dir)  # 公开产品文件事实

        # 把公开合同实际检查的路径加入审计证据。
        list_checked.extend(dict_public_report["checked"])

        # 公开合同错误直接阻断自身技能审计。
        list_errors.extend(dict_public_report["errors"])

    # 第四阶段验证生产脚本布局、语法和规模治理。
    audit_script_sources(
        skill_dir,
        path_project_root,
        bool_self_skill,
        list_checked,
        list_errors,
    )

    # 第五阶段扫描完整资源树中的缓存、占位符和本地路径。
    audit_resource_tree(skill_dir, list_errors, list_warnings)

    # 结果保留稳定字段和排序去重后的检查路径。
    return {
        "skill_dir": str(skill_dir),  # 被审计技能目录
        "checked": sorted(set(list_checked)),  # 实际检查路径集合
        "errors": list_errors,  # 阻断错误列表
        "warnings": list_warnings,  # 非阻断警告列表
    }

# CLI 保持 JSON 标准输出协议，并以错误列表决定退出码。
def main() -> int:
    """解析命令行、执行技能审计并输出 JSON 结果。

    参数：无；参数由命令行解析器读取。
    返回：审计无错误时为零，否则为一。
    """

    # CLI 进入运行阶段后再加载仓库依赖，保持模块导入无副作用。
    load_runtime_dependencies()

    # 参数解析器只暴露可选技能目录，默认审计当前工作目录。
    parser = argparse.ArgumentParser(  # 技能审计命令行解析器
        description="Audit agents-md-generator skill structure and scripts."  # CLI 帮助摘要
    )

    # 注册唯一位置参数，保持既有 CLI 兼容。
    parser.add_argument("skill_dir", nargs="?", default=".")

    # 解析结果是后续目标目录规范化的唯一输入。
    args = parser.parse_args()  # 已解析命令行参数

    # 保存技能审计载荷，确保输出内容与退出码依据同一结果。
    dict_audit_result = audit(func_resolve_project(args.skill_dir))  # 当前技能审计的机器可读结果

    # 输出既有 JSON 协议，供上层治理工具继续解析。
    func_emit_json(dict_audit_result)

    # 根据权威错误列表返回进程状态，阻止失败载荷伪装成成功。
    return 1 if dict_audit_result["errors"] else 0

# 仅直接执行时启动 CLI，模块导入保持无副作用。
if __name__ == "__main__":

    # 把审计结果状态传递给调用进程。
    raise SystemExit(main())
