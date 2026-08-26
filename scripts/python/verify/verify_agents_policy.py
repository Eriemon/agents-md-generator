"""AGENTS 校验策略常量。"""

# 导入 AGENTS 校验策略 所需的依赖声明。
from __future__ import annotations

# 导入 AGENTS 校验策略 所需的依赖模块。
import re

# 导入 AGENTS 双技能路由契约常量。
from routing_contract import (
    PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,
    SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,
    SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS,
)

# 收集 AGENTS 里的反引号命令片段，供命令校验复用。
COMMAND_RE = re.compile(r"`([^`\n]+)`")  # 提取反引号中的命令候选片段

# 收集 AGENTS 里的路径片段，供路径存在性与路径格式校验复用。
PATH_RE = re.compile(  # 识别带常见文件后缀的反引号路径片段
    r"`([^`\n]+(?:/|\\|\.md|\.json|\.toml|\.yml|\.yaml|\.py|\.ts|\.tsx|\.go|\.php)[^`\n]*)`"  # 匹配后续需要校验存在性的路径文本
)

# 保留根 AGENTS 大小上限，供 verify_agents.py 报错与提示复用。
ROOT_AGENTS_MAX_KB = 20  # 根 AGENTS 的体积上限，单位 KB

# 保留根 AGENTS 字节上限，避免运行时重复计算。
ROOT_AGENTS_MAX_BYTES = ROOT_AGENTS_MAX_KB * 1024  # 根 AGENTS 的字节级体积上限

# 收集默认语言锁定规则，供根 AGENTS 元数据校验复用。
LANGUAGE_LOCK_RE = re.compile(  # 匹配普通自然语言回复的默认语言锁
    r"(?:All natural-language responses must use|Natural-language replies.*?use)\s+"  # 支持旧版和精炼版前缀
    r"(.+?)\s+unless the user (?:explicitly )?switches language(?:s)?[.;]",  # 捕获默认语言与切换条件
    flags=re.IGNORECASE,  # 兼容手写标题的大小写差异
)

# 单独锁定 Plan Mode 中的 `<proposed_plan>` 语言，避免计划内容悄悄切回英文。
PLAN_LANGUAGE_LOCK_RE = re.compile(  # 匹配 Plan Mode 专用的默认语言锁
    r"(?:In Plan Mode,\s+any content inside\s+`<proposed_plan>`\s+must use|"  # 旧版计划锁前缀
    r"Natural-language replies, including\s+`<proposed_plan>`\s+content, use)\s+"  # 精炼版计划锁前缀
    r"(.+?)\s+unless the user (?:explicitly )?switches language(?:s)?[.;]",  # 默认语言与切换条件
    flags=re.IGNORECASE,  # 兼容 `<proposed_plan>` 段落的大小写差异
)

# 收集编码行为段落必须保留的基础短语，供根 AGENTS 校验复用。
CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS = (  # 编码行为基础短语用于本步校验判断
    "Coding behavior source: `.agents/global-rule-overrides.json`",  # 配置来源指针
    "Comment quality: Comments must explain",  # 注释规则保留语义边界
    "preserve line and blank-line separation",  # 代码排版保持分隔
    "must not start with digits or underscores",  # 文件命名边界
    "File naming semantics:",  # 文件语义复核边界
)

# 复用共同门禁强制短语，确保跨语言前置要求只由 shared 行承载。
CODING_BEHAVIOR_LANGUAGE_ROUTING_SHARED_REQUIRED_SNIPPETS = SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 共同门禁强制短语

# 复用 Python 路由强制短语，保持渲染、校验和测试的精确短语一致。
CODING_BEHAVIOR_LANGUAGE_ROUTING_PYTHON_REQUIRED_SNIPPETS = PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # Python 路由强制短语用于本步校验判断

# 把脚本侧强制短语单独暴露给 verifier，防止与 Python 侧职责边界混淆。
CODING_BEHAVIOR_LANGUAGE_ROUTING_SCRIPT_REQUIRED_SNIPPETS = SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 脚本路由强制短语用于本步校验判断

# 收集脚本输出策略必须保留的短语，供根 AGENTS 校验复用。
SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS = (  # 脚本输出策略短语用于本步校验判断
    "Configuration source:",  # 脚本输出配置来源
    "the `Kind` catalog is read from this JSON",  # Kind 来源必须绑定到 JSON 配置
    "must not be embedded in code",  # 禁止把 Kind 列表硬编码进源码
    "`> INFO: [{kind}]`",  # INFO 模板必须继续存在
    "`> WARNING: [{kind}]`",  # WARNING 行模板必须继续覆盖警告输出
    "`> ERR: [{kind}]`",  # ERR 行模板必须继续覆盖错误输出
    "Python process INFO is enabled by default",  # Python 默认输出规则必须保留
    "`--quiet`",  # quiet 开关语义必须继续存在
    "WARNING and ERR remain visible",  # 安静模式下仍需保留警告与错误
    "machine-readable output has no prefix",  # 机器可读输出豁免必须继续存在
)

# 用源码运行时命令特征拦截 non-owner 仓库复制 owner 侧开发命令。
PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE = re.compile(  # 命中 owner 仓库专属的 repo-local runtime 命令
    r"`python\s+"
    r"(?:scripts/|skills/[^/\s]+/scripts/)"
    r"(?:manage_docs|manage_dirs|verify_agents|evaluate_skill|review_governance|"
    r"run_confidence_gate|collect_design_profile|render_agents)"
    r"\.py\b[^`]*`"
)
