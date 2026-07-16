"""集中维护设计访谈问题、选项和答案规范化规则。"""

# 延迟注解求值，保持运行时类型引用兼容性。
from __future__ import annotations

# 标准库负责 JSON 读取、文本匹配、时间戳和路径类型。
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 设计访谈状态文件位置用于保持后续处理语义明确。
STATE_PATH = ".agents/design-interview-state.json"  # 设计访谈状态文件位置

# 设计访谈终态集合用于保持后续处理语义明确。
TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}  # 设计访谈终态集合

# 接管访谈终态集合用于保持后续处理语义明确。
TAKEOVER_TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}  # 接管访谈终态集合

# 触发接管访谈的版本差异键用于保持后续处理语义明确。
TAKEOVER_REASON_KEYS = {  # 触发接管访谈的版本差异键
    "agents_version_mismatch",  # 用于识别根规则版本与目标版本不一致；问卷第一项
    "generator_version_mismatch",  # 用于声明“generator_version_mismatch”设计合同项；问卷第二项
}

# 远程 SSH 协作技能名称用于保持后续处理语义明确。
REMOTE_SSH_SKILL_NAME = "erie-remote-ssh"  # 远程 SSH 协作技能名称

# 远程 SSH 技能仓库地址用于保持后续处理语义明确。
REMOTE_SSH_GIT_URL = "https://github.com/Eriemon/remote-ssh.git"  # 远程 SSH 技能仓库地址

# 远程 SSH 技能安装规格用于保持后续处理语义明确。
REMOTE_SSH_INSTALL_SPECS = [
    {"skill": REMOTE_SSH_SKILL_NAME, "source_path": ".", "dest_name": REMOTE_SSH_SKILL_NAME}  # 技能安装映射
]  # 远程 SSH 技能安装规格

# 远程服务器启用答案键用于保持后续处理语义明确。
USE_REMOTE_SERVER_KEY = "use_remote_server"  # 远程服务器启用答案键

# 代码知识图谱启用答案键用于强制记录用户的显式选择。
USE_CODEBASE_MEMORY_MCP_KEY = "use_codebase_memory_mcp"  # 知识图谱启用答案键

# 缺少本地依赖时由用户确认是否进入人工安装流程。
CODEBASE_MEMORY_INSTALL_CONFIRM_KEY = "install_codebase_memory_mcp"  # 人工安装确认答案键

# 远程安装确认答案键用于保持后续处理语义明确。
REMOTE_INSTALL_CONFIRM_KEY = "install_remote_ssh_dependency"  # 远程安装确认答案键

# 远程配置模式答案键用于保持后续处理语义明确。
REMOTE_CONFIGURATION_MODE_KEY = "remote_server_configuration_mode"  # 远程配置模式答案键

# 已选服务器标识答案键用于保持后续处理语义明确。
REMOTE_SELECTED_SERVER_ID_KEY = "selected_remote_server_id"  # 已选服务器标识答案键

# 已选服务器名称答案键用于保持后续处理语义明确。
REMOTE_SELECTED_SERVER_NAME_KEY = "selected_remote_server_name"  # 已选服务器名称答案键

# 已选服务器类别答案键用于保持后续处理语义明确。
REMOTE_SELECTED_SERVER_CATEGORY_KEY = "selected_remote_server_category"  # 已选服务器类别答案键

# 已选服务器能力答案键用于保持后续处理语义明确。
REMOTE_SELECTED_SERVER_FUNCTIONS_KEY = "selected_remote_server_functions"  # 已选服务器能力答案键

# 已选服务器任务答案键用于保持后续处理语义明确。
REMOTE_SELECTED_SERVER_TASKS_KEY = "selected_remote_server_tasks"  # 已选服务器任务答案键

# 远程任务路由答案键用于保持后续处理语义明确。
REMOTE_SERVER_TASK_ROUTES_KEY = "remote_server_task_routes"  # 远程任务路由答案键

# 远程选择确认答案键用于保持后续处理语义明确。
REMOTE_SELECTION_CONFIRMED_KEY = "remote_server_selection_confirmed"  # 远程选择确认答案键

# 远程验证状态答案键用于保持后续处理语义明确。
REMOTE_VALIDATION_STATUS_KEY = "remote_server_validation_status"  # 远程验证状态答案键

# 远程门禁章节标题用于保持后续处理语义明确。
REMOTE_GATE_SECTION_TITLE = "## Remote Server Contract"  # 用于定位远程合同章节；问卷第三项

# 远程门禁强制规则文本用于保持后续处理语义明确。
REMOTE_GATE_FORCE_RULE = (  # 远程门禁强制规则文本
    "When the user requests remote server validation for a registered task, "
    "you must start with that task route's primary remote server"
)

# 远程路由强制规则文本用于保持后续处理语义明确。
REMOTE_ROUTE_FORCE_RULE = (  # 远程路由强制规则文本
    "When the user requests remote server validation for a registered task, "
    "you must start with that task route's primary remote server"
)

# 历史远程任务兼容名称用于保持后续处理语义明确。
REMOTE_LEGACY_TASK_NAME = "remote-validation"  # 历史远程任务兼容名称

# 所有项目共用的设计问题用于保持后续处理语义明确。
COMMON_QUESTIONS = [  # 所有项目共用的设计问题
    {
        "question_id": "1",  # 用于稳定标识问题 1；问卷第四项
        "answer_key": "development_type",  # 用于绑定答案字段问题 1；问卷第五项
        "required": True,  # 用于声明必答状态问题 1；问卷第六项
        "branch": "all",  # 用于限定适用分支问题 1；问卷第七项
        "ask": "确认是技能开发还是工程开发？技能开发进入（2），工程开发进入（11）。",  # 用于提供交互提示问题 1；问卷第八项
    },
    {
        "question_id": "32",  # 用于稳定标识问题 32；问卷第九项
        "answer_key": "default_conversation_language",  # 用于绑定答案字段问题 32；问卷第十项
        "required": True,  # 用于声明必答状态问题 32；问卷第十一项
        "branch": "all",  # 用于限定适用分支问题 32；问卷第十二项
        "ask": "生成或重构 AGENTS.md 前，必须显式确认后续默认对话语言是什么；该语言必须写入控制档案并作为 AGENTS.md 强约束，不能依赖隐式默认值。",  # 展示问题 32 的语言确认提示；问卷第十三项
    },
    {
        "question_id": "45",  # 用于稳定标识问题 45；问卷第十四项
        "answer_key": USE_REMOTE_SERVER_KEY,  # 用于绑定答案字段问题 45；问卷第十五项
        "required": True,  # 用于声明必答状态问题 45；问卷第十六项
        "branch": "all",  # 用于限定适用分支问题 45；问卷第十七项
        "ask": "本次生成或重构 AGENTS.md 是否需要启用远程服务器链路？如果启用，后续必须完成依赖检查、服务器配置/选择、校验和锁定。",  # 展示问题 45 的远程启用提示；问卷第十八项
    },
    {
        "question_id": "55",  # 稳定知识图谱问题标识
        "answer_key": USE_CODEBASE_MEMORY_MCP_KEY,  # 绑定显式启用选择
        "required": True,  # 禁止字段缺失推断默认值
        "branch": "all",  # 所有项目类型均需回答
        "ask": (  # 知识图谱使用范围与前置条件问题
            "本次生成或更新 AGENTS.md 是否使用 codebase-memory-mcp？启用后可用知识图谱理解项目架构、"
            "追踪调用关系并优先辅助代码调试，但必须安装并配置本地 MCP、在项目根完成 full + persistence "
            "索引，且 `.codebase-memory/` 只能保留为 Git 忽略的本地产物。"
        ),
    },
]

# 技能项目专用设计问题用于保持后续处理语义明确。
SKILL_QUESTIONS = [  # 技能项目专用设计问题
    ("2", "skill_purpose", "这个技能是干什么的？"),  # 用于采集技能用途；问卷第十九项
    ("3", "skill_reason", "为什么要开发这个技能？"),  # 用于采集“skill_reason”对应的设计答案；问卷第二十项
    ("4", "reference_materials", "这个技能有无参考资料？这些资料只是临时输入，开发完成后需要用户手动删除。"),  # 用于采集“reference_materials”对应的设计答案；问卷第二十一项
    ("5", "audience", "这个技能面向目标人群是什么？科研、商业、个人用户还是其他？"),  # 用于采集“audience”对应的设计答案；问卷第二十二项
    ("6", "name", "这个技能的名称是什么？"),  # 用于采集“name”对应的设计答案；问卷第二十三项
    ("7", "design_notes", "这个技能的设计有无注意事项或者已有的经验？"),  # 用于采集“design_notes”对应的设计答案；问卷第二十四项
    ("8", "git_management", "这个技能的设计是否要进行 git 管理，不提交远端？"),  # 用于采集“git_management”对应的设计答案；问卷第二十五项
    ("9", "branch_model", "这个技能所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),  # 用于采集“branch_model”对应的设计答案；问卷第二十六项
    (
        "10",  # 技能发布问题编号
        "release_contract",  # 技能发布合同字段
        "dist 文件夹中释放可安装版本文件夹是否命名为【技能名】-vx.x.x，并同步生成 zip 压缩包？",  # 技能发布提示
    ),  # 用于采集“release_contract”对应的设计答案；问卷第二十七项
    ("22", "trigger_scenarios", "这个技能应该在什么用户请求、文件类型、项目状态或任务场景下触发？"),  # 用于采集“trigger_scenarios”对应的设计答案；问卷第二十八项
    (
        "23",  # 默认语言问题编号
        "skill_design_patterns",  # 技能设计模式答案字段
        "这个技能采用哪些设计模式：Tool Wrapper、Generator、Reviewer、Inversion、Pipeline，或其他？",  # 技能模式访谈提示
    ),  # 用于采集“skill_design_patterns”对应的设计答案；问卷第二十九项
    (
        "24",  # 第三百五题编号
        "resource_plan",  # 第三百十题答案字段
        "这个技能的资源边界是什么？哪些内容进入 SKILL.md、references/、scripts/、assets/、agents/openai.yaml？",  # 第三百十五题访谈提示
    ),  # 用于采集“resource_plan”对应的设计答案；问卷第三十项
    (
        "25",  # 第三百十九题编号
        "progressive_disclosure_policy",  # 第三百二十三题答案字段
        "这个技能如何保持渐进式披露，例如 SKILL.md 精简、详细规则进入 references/、资源按需加载？",  # 第三百二十七题访谈提示
    ),  # 用于采集“progressive_disclosure_policy”对应的设计答案；问卷第三十一项
    (
        "26",  # 第三百三十题编号
        "validation_gates",  # 第三百三十三题答案字段
        "这个技能完成前必须运行哪些验证门禁，例如 quick_validate.py、audit、verify、evaluate 或前端/端到端检查？",  # 第三百三十六题访谈提示
    ),  # 用于采集“validation_gates”对应的设计答案；问卷第三十二项
    (
        "27",  # 第三百三十八题编号
        "forward_testing_policy",  # 前向测试策略答案字段
        "复杂或高风险技能是否需要前向测试？如果需要，触发条件和测试方式是什么？",  # 第三百四十题访谈提示
    ),  # 用于采集“forward_testing_policy”对应的设计答案；问卷第三十三项
    ("28", "development_requirements", "这个技能的详细开发需求是什么？"),  # 用于采集“development_requirements”对应的设计答案；问卷第三十四项
    ("29", "expected_outcome", "这个技能开发完成后的预期结果是什么？"),  # 用于采集“expected_outcome”对应的设计答案；问卷第三十五项
    ("30", "validation_method", "这个技能开发完成后如何验证？"),  # 用于采集“validation_method”对应的设计答案；问卷第三十六项
    ("31", "validation_granularity", "验证方式需要达到什么颗粒度？"),  # 用于采集“validation_granularity”对应的设计答案；问卷第三十七项
]

# 工程项目专用设计问题用于保持后续处理语义明确。
ENGINEERING_QUESTIONS = [  # 工程项目专用设计问题
    ("11", "project_purpose", "这个工程是干什么的？"),  # 用于采集工程用途；问卷第三十八项
    ("12", "project_reason", "为什么要干这个工程？"),  # 用于采集“project_reason”对应的设计答案；问卷第三十九项
    ("13", "expected_outcome", "这个工程的预期效果和目标是什么？"),  # 用于采集“expected_outcome”对应的设计答案；问卷第四十项
    ("14", "environment", "这个工程是在远程服务器、WSL 或者本地开发？"),  # 用于采集“environment”对应的设计答案；问卷第四十一项
    ("15", "reusable_experience", "这个工程有无经验可以借鉴？"),  # 用于采集“reusable_experience”对应的设计答案；问卷第四十二项
    ("16", "name", "这个工程开发的名称是什么？"),  # 用于采集“name”对应的设计答案；问卷第四十三项
    ("17", "git_management", "这个工程开发是否要进行 git 管理，不提交远端？"),  # 用于采集“git_management”对应的设计答案；问卷第四十四项
    ("18", "branch_model", "这个工程所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),  # 用于采集“branch_model”对应的设计答案；问卷第四十五项
    (
        "19",  # 工程发布问题编号
        "release_contract",  # 工程发布合同字段
        "dist 文件夹中释放可安装版本文件夹是否命名为【工程名】-vx.x.x，并同步生成 zip 压缩包？",  # 工程发布提示
    ),  # 用于采集“release_contract”对应的设计答案；问卷第四十六项
    ("33", "development_requirements", "这个工程的详细开发需求是什么？"),  # 用于采集“development_requirements”对应的设计答案；问卷第四十七项
    ("34", "resource_plan", "这个工程的资源边界是什么？源码、脚本、测试、文档、部署和发布产物分别放在哪里？"),  # 用于采集“resource_plan”对应的设计答案；问卷第四十八项
    ("35", "validation_method", "这个工程开发完成后如何验证？"),  # 用于采集“validation_method”对应的设计答案；问卷第四十九项
    ("36", "validation_granularity", "这个工程的验证方式需要达到什么颗粒度？"),  # 用于采集“validation_granularity”对应的设计答案；问卷第五十项
    (
        "37",  # 工程语言问题编号
        "forward_testing_policy",  # 工程前向测试答案字段
        "复杂或高风险工程改动是否需要前向测试？如果需要，触发条件和测试方式是什么？",  # 工程前向测试提示
    ),  # 用于采集“forward_testing_policy”对应的设计答案；问卷第五十一项
    (
        "38",  # 第三百四题编号
        "engineering_rule_primary",  # 第三百九题答案字段
        "这个工程是否启用书籍化工程规则集？如果启用，选择哪一个主规则集？",  # 第三百十四题访谈提示
    ),  # 用于采集“engineering_rule_primary”对应的设计答案；问卷第五十二项
    ("39", "engineering_rule_mode", "工程规则集使用 mini、nano，还是不启用？"),  # 用于采集“engineering_rule_mode”对应的设计答案；问卷第五十三项
    ("40", "engineering_rule_scope", "工程规则集作用于整个工程、局部目录，还是按需启用？"),  # 用于采集“engineering_rule_scope”对应的设计答案；问卷第五十四项
    ("41", "engineering_rule_notes", "工程规则集还有哪些本地经验或注意事项需要记录？"),  # 用于采集“engineering_rule_notes”对应的设计答案；问卷第五十五项
]

# 目录治理设计问题用于保持后续处理语义明确。
DIRECTORY_QUESTIONS = [  # 目录治理设计问题
    ("42", "local_directory_structure", "请明确本地目录结构约定，包含主目录、tests、dist、docs 等位置。"),  # 用于采集本地目录合同；问卷第五十六项
    (
        "43",  # 远程目录问题编号
        "remote_directory_structure",  # 远程目录合同字段
        "请明确远程目录结构或远程部署边界；如果没有远程环境，也要明确写出没有配置。",  # 远程目录提示
    ),  # 用于采集“remote_directory_structure”对应的设计答案；问卷第五十七项
    ("44", "feature_directory_rules", "请明确新增功能、脚本、文档、测试等后续内容应该进入哪些目录。"),  # 用于采集“feature_directory_rules”对应的设计答案；问卷第五十八项
    (
        "46",  # 远程环境问题编号
        "remote_conda_environment_layout",  # 远程环境布局答案字段
        "如果远端工作区需要 conda 环境，请明确该前缀环境固定放在哪里；推荐 `.conda/<env-name>/`。如果远端未配置，可保持 disabled。",  # 远程环境布局提示
    ),  # 远程环境布局
    (
        "47",  # 第三百三题编号
        "remote_run_artifact_active_layout",  # 第三百八题答案字段
        "如果远端会产生运行产物，请明确活动运行目录结构；推荐 `runs/<run-id>/`。如果远端未配置，可保持 disabled。",  # 第三百十三题访谈提示
    ),  # 用于采集“remote_run_artifact_active_layout”对应的设计答案；问卷第六十项
    (
        "48",  # 第三百十八题编号
        "remote_run_artifact_backup_layout",  # 第三百二十二题答案字段
        "如果远端会归档运行产物，请明确归档目录结构；推荐 `backups/runs/<run-id>/`。如果远端未配置，可保持 disabled。",  # 第三百二十六题访谈提示
    ),  # 远程归档布局
    (
        "49",  # 第三百二十九题编号
        "remote_run_archive_trigger",  # 第三百三十二题答案字段
        "请明确远端运行产物何时必须从活动目录归档到 backups；推荐 `after required verification passes`。如果远端未配置，可保持 disabled。",  # 第三百三十五题访谈提示
    ),  # 远程归档时机
]

# 项目记忆设计问题用于保持后续处理语义明确。
MEMORY_QUESTIONS = [  # 项目记忆设计问题
    ("50", "memory_enabled", "是否启用 `docs/memory/` 记忆治理层？默认推荐启用；如关闭，AGENTS.md 只保留 handoff 指针。"),  # 用于确认记忆治理开关；问卷第六十三项
    (
        "51",  # 记忆后端问题编号
        "memory_storage_backend",  # 记忆后端答案字段
        "记忆层使用什么存储后端？默认 `sqlite-plus-jsonl`：SQLite 负责查询索引，JSONL/Markdown 保留可审计原文和摘要。",  # 记忆后端提示
    ),  # 用于采集“memory_storage_backend”对应的设计答案；问卷第六十四项
    (
        "52",  # 记忆范围问题编号
        "memory_capture_scope",  # 记忆采集范围答案字段
        "哪些内容可以进入长期记忆？默认保存 handoff 摘要、用户确认的项目偏好、长期决策、验证/发布教训。",  # 记忆采集范围提示
    ),  # 用于采集“memory_capture_scope”对应的设计答案；问卷第六十五项
    (
        "53",  # 第三百二题编号
        "memory_read_policy",  # 第三百七题答案字段
        "任务开始和恢复时如何读取记忆？默认读取最新 handoff 和相关 `docs/memory` 摘要。",  # 第三百十二题访谈提示
    ),  # 用于采集“memory_read_policy”对应的设计答案；问卷第六十六项
    (
        "54",  # 第三百十七题编号
        "memory_sensitivity_policy",  # 第三百二十一题答案字段
        "记忆层的敏感信息边界是什么？默认不保存 secrets、凭据、本地私密路径原文。",  # 第三百二十五题访谈提示
    ),  # 用于采集“memory_sensitivity_policy”对应的设计答案；问卷第六十七项
]

# 既有工作接管问题用于保持后续处理语义明确。
EXISTING_WORK_QUESTIONS = [  # 既有工作接管问题
    ("20", "has_existing_work", "当前工作文件夹是否已经存在工程或者技能？"),  # 用于识别既有项目接管场景；问卷第六十八项
    (
        "21",  # 目录确认问题编号
        "directory_contract_confirmed",  # 目录确认答案字段
        "是否确认本地目录结构、远程目录结构和新增功能目录规则已经明确并固定为强控制契约？",  # 目录确认提示
    ),  # 用于采集“directory_contract_confirmed”对应的设计答案；问卷第六十九项
]

# 目录合同答案键集合用于保持后续处理语义明确。
DIRECTORY_KEYS = [  # 目录合同答案键集合
    "local_directory_structure",  # 用于校验本地目录合同是否齐备；问卷第七十项
    "remote_directory_structure",  # 用于声明“remote_directory_structure”设计合同项；问卷第七十一项
    "feature_directory_rules",  # 用于声明“feature_directory_rules”设计合同项；问卷第七十二项
]

# 远程目录策略答案键集合用于保持后续处理语义明确。
REMOTE_DIRECTORY_POLICY_KEYS = [  # 远程目录策略答案键集合
    "remote_conda_environment_layout",  # 用于校验远程环境目录策略；问卷第七十三项
    "remote_run_artifact_active_layout",  # 用于声明“remote_run_artifact_active_layout”设计合同项；问卷第七十四项
    "remote_run_artifact_backup_layout",  # 用于声明“remote_run_artifact_backup_layout”设计合同项；问卷第七十五项
    "remote_run_archive_trigger",  # 用于声明“remote_run_archive_trigger”设计合同项；问卷第七十六项
]

# 允许留空的答案键集合用于保持后续处理语义明确。
OPTIONAL_EMPTY_KEYS = {"engineering_rule_notes"}  # 允许留空的答案键集合

# 设计对齐确认答案键用于保持后续处理语义明确。
ALIGNMENT_KEY = "alignment_confirmed"  # 设计对齐确认答案键

# 问题分组确认答案键用于保持后续处理语义明确。
GROUP_CONFIRMATION_KEY = "group_confirmed"  # 问题分组确认答案键

# 额外需求答案键用于保持后续处理语义明确。
EXTRA_REQUIREMENTS_KEY = "extra_requirements"  # 额外需求答案键

# 设计复核结论答案键用于保持后续处理语义明确。
DESIGN_REVIEW_KEY = "design_review"  # 设计复核结论答案键

# 设计返工确认答案键用于保持后续处理语义明确。
REVIEW_REWORK_CONFIRMATION_KEY = "review_rework_confirmed"  # 设计返工确认答案键

# 技能名称合法格式匹配器用于保持后续处理语义明确。
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # 技能名称合法格式匹配器

# 无额外需求的等价表达用于保持后续处理语义明确。
NO_EXTRA_REQUIREMENTS = {"", "none", "no", "no extra", "n/a", "无", "没有", "无补充", "无额外补充", "不补充", "无需补充"}  # 无额外需求的等价表达

# 工程规则集可选值用于保持后续处理语义明确。
ENGINEERING_RULE_SETS = {  # 工程规则集可选值
    "a-philosophy-of-software-design",  # 用于允许软件设计哲学规则集；问卷第七十七项
    "clean-architecture",  # 用于声明“clean-architecture”设计合同项；问卷第七十八项
    "clean-code",  # 用于声明“clean-code”设计合同项；问卷第七十九项
    "code-complete",  # 用于声明“code-complete”设计合同项；问卷第八十项
    "designing-data-intensive-applications",  # 用于声明“designing-data-intensive-applicat...”设计合同项；问卷第八十一项
    "domain-driven-design",  # 用于声明“domain-driven-design”设计合同项；问卷第八十二项
    "domain-driven-design-distilled",  # 用于声明“domain-driven-design-distilled”设计合同项；问卷第八十三项
    "implementing-domain-driven-design",  # 用于声明“implementing-domain-driven-design”设计合同项；问卷第八十四项
    "patterns-of-enterprise-application-architecture",  # 用于声明“patterns-of-enterprise-applicatio...”设计合同项；问卷第八十五项
    "refactoring",  # 用于声明“refactoring”设计合同项；问卷第八十六项
    "refactoring-guru",  # 用于声明“refactoring-guru”设计合同项；问卷第八十七项
    "release-it",  # 用于声明“release-it”设计合同项；问卷第八十八项
    "the-pragmatic-programmer",  # 用于声明“the-pragmatic-programmer”设计合同项；问卷第八十九项
    "working-effectively-with-legacy-code",  # 用于声明“working-effectively-with-legacy-code”设计合同项；问卷第九十项
}

# 工程规则模式可选值用于保持后续处理语义明确。
ENGINEERING_RULE_MODES = {"none", "mini", "nano"}  # 工程规则模式可选值

# 工程规则作用域可选值用于保持后续处理语义明确。
ENGINEERING_RULE_SCOPES = {"project-baseline", "scoped", "on-demand"}  # 工程规则作用域可选值

# 项目记忆问题分组用于保持后续处理语义明确。
MEMORY_GROUPS = [["50", "51", "52", "53", "54"]]  # 项目记忆问题分组

# 公共设计问题分组用于保持后续处理语义明确。
COMMON_GROUPS = [["1", "32", "45", "55"], ["50", "51", "52", "53", "54"]]  # 公共设计问题分组

# 技能设计问题分组用于保持后续处理语义明确。
SKILL_GROUPS = [  # 技能设计问题分组
    ["2", "3", "4"],  # 用于先确认技能目的与参考材料；问卷第九十一项
    ["5", "6", "7"],  # 用于安排问题 5 起始的访谈顺序；问卷第九十二项
    ["8", "9", "10"],  # 用于安排问题 8 起始的访谈顺序；问卷第九十三项
    ["22", "23", "24"],  # 用于安排问题 22 起始的访谈顺序；问卷第九十四项
    ["25", "26", "27"],  # 用于安排问题 25 起始的访谈顺序；问卷第九十五项
    ["28", "29", "30"],  # 用于安排问题 28 起始的访谈顺序；问卷第九十六项
    ["31"],  # 用于安排问题 31 起始的访谈顺序；问卷第九十七项
    ["42", "43", "44", "46", "47", "48", "49"],  # 用于安排问题 42 起始的访谈顺序；问卷第九十八项
    ["20", "21"],  # 用于安排问题 20 起始的访谈顺序；问卷第九十九项
]

# 工程设计问题分组用于保持后续处理语义明确。
ENGINEERING_GROUPS = [  # 工程设计问题分组
    ["11", "12", "13"],  # 用于先确认工程目的与预期目标；问卷第一百项
    ["14", "15", "16"],  # 用于安排问题 14 起始的访谈顺序；问卷第一百一项
    ["17", "18", "19"],  # 用于安排问题 17 起始的访谈顺序；问卷第一百二项
    ["33", "34", "35"],  # 用于安排问题 33 起始的访谈顺序；问卷第一百三项
    ["36", "37", "38"],  # 用于安排问题 36 起始的访谈顺序；问卷第一百四项
    ["39", "40", "41"],  # 用于安排问题 39 起始的访谈顺序；问卷第一百五项
    ["42", "43", "44", "46", "47", "48", "49"],  # 用于安排问题 42 起始的访谈顺序；问卷第一百六项
    ["20", "21"],  # 用于安排问题 20 起始的访谈顺序；问卷第一百七项
]

# 接管流程公共问题分组用于保持后续处理语义明确。
TAKEOVER_COMMON_GROUPS = [["1", "32", "45", "55"], ["50", "51", "52", "53", "54"]]  # 接管流程公共问题分组

# 接管技能项目问题分组用于保持后续处理语义明确。
TAKEOVER_SKILL_GROUPS = [["6"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]  # 接管技能项目问题分组

# 接管工程项目问题分组用于保持后续处理语义明确。
TAKEOVER_ENGINEERING_GROUPS = [["16"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]  # 接管工程项目问题分组

# 答案字段对应的结构化选项用于保持后续处理语义明确。
QUESTION_OPTIONS: dict[str, list[dict[str, Any]]] = {  # 答案字段对应的结构化选项
    "development_type": [  # 用于提供开发类型候选答案；问卷第一百八项
        {
            "label": "技能开发",  # 技能开发展示标签
            "value": "skill",  # 技能开发提交值
            "description": "为 Codex skill 收集设计、目录和验证契约。",  # 技能开发用途说明
            "recommended": True,  # 技能开发推荐状态
        },  # 用于定义“技能开发”回答选项的提交合同；问卷第一百九项
        {
            "label": "工程开发",  # 第三百一项展示标签
            "value": "engineering",  # 第三百六项提交值
            "description": "为普通工程仓库收集 AGENTS.md 控制档案。",  # 第三百十一项选择说明
            "recommended": False,  # 第三百十六项推荐状态
        },  # 用于定义“工程开发”回答选项的提交合同；问卷第一百十项
    ],
    "git_management": [  # 用于声明“git_management”设计合同项；问卷第一百十一项
        {
            "label": "启用 git 管理",  # 第三百二十项展示标签
            "value": "yes-local-only",  # 第三百二十四项提交值
            "description": "允许本地分支和提交，默认不推送远端。",  # 第三百二十八项选择说明
            "recommended": True,  # 第三百三十一项推荐状态
        },  # 用于定义“启用 git 管理”回答选项的提交合同；问卷第一百十二项
        {
            "label": "不启用 git 管理",  # 第三百三十四项展示标签
            "value": "no-git-management",  # 第三百三十七项提交值
            "description": "不把 git 作为当前技能开发流程的一部分。",  # 第三百三十九项选择说明
            "recommended": False,  # 第三百四十一项推荐状态
        },  # 禁用 Git 管理
        {
            "label": "其他",  # 第三百四十二项展示标签
            "value": "__user_input__",  # 第三百四十三项提交值
            "description": "由用户输入自定义 git 管理规则。",  # 第三百四十四项选择说明
            "recommended": False,  # 第三百四十五项推荐状态
        },  # 用于定义“其他”回答选项的提交合同；问卷第一百十四项
    ],
    "branch_model": [  # 用于声明“branch_model”设计合同项；问卷第一百十五项
        {
            "label": "master + dist release",  # 第三百四十六项展示标签
            "value": "master-and-dist-release",  # 第三百四十七项提交值
            "description": "源码在 master，发布产物在 dist。",  # 第三百四十八项选择说明
            "recommended": True,  # 第三百四十九项推荐状态
        },  # 主线发布布局
        {
            "label": "当前分支为准",  # 第三百五十项展示标签
            "value": "current-branch",  # 第三百五十一项提交值
            "description": "不固定 master，先检查当前分支。",  # 第三百五十二项选择说明
            "recommended": False,  # 第三百五十三项推荐状态
        },  # 用于定义“当前分支为准”回答选项的提交合同；问卷第一百十七项
    ],
    "release_contract": [  # 用于声明“release_contract”设计合同项；问卷第一百十八项
        {
            "label": "目录和 zip 同步",  # 第三百五十四项展示标签
            "value": "dist/<name>-vx.x.x plus zip",  # 第三百五十五项提交值
            "description": "生成同名 release 目录和 zip 包。",  # 第三百五十六项选择说明
            "recommended": True,  # 第三百五十七项推荐状态
        },  # 双发布载体
        {
            "label": "暂不发布",  # 第三百五十八项展示标签
            "value": "no-release",  # 第三百五十九项提交值
            "description": "当前阶段不定义安装包产物。",  # 第三百六十项选择说明
            "recommended": False,  # 第三百六十一项推荐状态
        },  # 用于定义“暂不发布”回答选项的提交合同；问卷第一百二十项
    ],
    "has_existing_work": [  # 用于声明“has_existing_work”设计合同项；问卷第一百二十一项
        {
            "label": "已有项目/技能",  # 第三百六十二项展示标签
            "value": "yes",  # 第三百六十三项提交值
            "description": "从当前文件内容生成目录和控制契约。",  # 第三百六十四项选择说明
            "recommended": True,  # 第三百六十五项推荐状态
        },  # 用于定义“已有项目/技能”回答选项的提交合同；问卷第一百二十二项
        {
            "label": "新项目/技能",  # 第三百六十六项展示标签
            "value": "no",  # 第三百六十七项提交值
            "description": "先按计划创建结构，再生成契约。",  # 第三百六十八项选择说明
            "recommended": False,  # 第三百六十九项推荐状态
        },  # 用于定义“新项目/技能”回答选项的提交合同；问卷第一百二十三项
    ],
    "directory_contract_confirmed": [  # 用于声明“directory_contract_confirmed”设计合同项；问卷第一百二十四项
        {
            "label": "确认目录契约",  # 第三百七十项展示标签
            "value": True,  # 第三百七十一项提交值
            "description": "允许写入本地、远程、新功能目录规则。",  # 第三百七十二项选择说明
            "recommended": True,  # 第三百七十三项推荐状态
        },  # 用于定义“确认目录契约”回答选项的提交合同；问卷第一百二十五项
        {
            "label": "暂不确认",  # 第三百七十四项展示标签
            "value": False,  # 第三百七十五项提交值
            "description": "只输出待确认摘要，不写强控制档案。",  # 第三百七十六项选择说明
            "recommended": False,  # 第三百七十七项推荐状态
        },  # 用于定义“暂不确认”回答选项的提交合同；问卷第一百二十六项
    ],
    "remote_conda_environment_layout": [  # 用于声明“remote_conda_environment_layout”设计合同项；问卷第一百二十七项
        {
            "label": ".conda/<env-name>/",  # 第三百七十八项展示标签
            "value": ".conda/<env-name>/",  # 第三百七十九项提交值
            "description": "远端 conda 前缀环境固定放在对应工作区根下。",  # 第三百八十项选择说明
            "recommended": True,  # 第三百八十一项推荐状态
        },  # Conda 环境目录
        {
            "label": "disabled",  # 第三百八十二项展示标签
            "value": "disabled",  # 第三百八十三项提交值
            "description": "远端未配置或不在本次目录治理范围内。",  # 第三百八十四项选择说明
            "recommended": False,  # 第三百八十五项推荐状态
        },  # 用于定义“disabled”回答选项的提交合同；问卷第一百二十九项
        {
            "label": "用户自定义",  # 第三百八十六项展示标签
            "value": "__user_input__",  # 第三百八十七项提交值
            "description": "由用户输入其他远端 conda 前缀目录规则。",  # 第三百八十八项选择说明
            "recommended": False,  # 第三百八十九项推荐状态
        },  # 用于定义“用户自定义”回答选项的提交合同；问卷第一百三十项
    ],
    "remote_run_artifact_active_layout": [  # 用于声明“remote_run_artifact_active_layout”设计合同项；问卷第一百三十一项
        {
            "label": "runs/<run-id>/",  # 第三百九十项展示标签
            "value": "runs/<run-id>/",  # 第三百九十一项提交值
            "description": "远端运行中的活动产物按运行编号进入 runs 目录。",  # 第三百九十二项选择说明
            "recommended": True,  # 第三百九十三项推荐状态
        },  # 活动运行目录
        {
            "label": "disabled",  # 第三百九十四项展示标签
            "value": "disabled",  # 第三百九十五项提交值
            "description": "远端未配置或本次不治理运行产物。",  # 第三百九十六项选择说明
            "recommended": False,  # 第三百九十七项推荐状态
        },  # 用于定义“disabled”回答选项的提交合同；问卷第一百三十三项
        {
            "label": "用户自定义",  # 第三百九十八项展示标签
            "value": "__user_input__",  # 第三百九十九项提交值
            "description": "由用户输入其他远端活动运行目录规则。",  # 第四百项选择说明
            "recommended": False,  # 第四百一项推荐状态
        },  # 用于定义“用户自定义”回答选项的提交合同；问卷第一百三十四项
    ],
    "remote_run_artifact_backup_layout": [  # 用于声明“remote_run_artifact_backup_layout”设计合同项；问卷第一百三十五项
        {
            "label": "backups/runs/<run-id>/",  # 第四百二项展示标签
            "value": "backups/runs/<run-id>/",  # 第四百三项提交值
            "description": "验证完成后的远端运行产物归档到 backups/runs。",  # 第四百四项选择说明
            "recommended": True,  # 第四百五项推荐状态
        },  # 备份运行目录
        {
            "label": "disabled",  # 第四百六项展示标签
            "value": "disabled",  # 第四百七项提交值
            "description": "远端未配置或本次不治理运行归档。",  # 第四百八项选择说明
            "recommended": False,  # 第四百九项推荐状态
        },  # 用于定义“disabled”回答选项的提交合同；问卷第一百三十七项
        {
            "label": "用户自定义",  # 第四百十项展示标签
            "value": "__user_input__",  # 第四百十一项提交值
            "description": "由用户输入其他远端运行归档目录规则。",  # 第四百十二项选择说明
            "recommended": False,  # 第四百十三项推荐状态
        },  # 用于定义“用户自定义”回答选项的提交合同；问卷第一百三十八项
    ],
    "remote_run_archive_trigger": [  # 用于声明“remote_run_archive_trigger”设计合同项；问卷第一百三十九项
        {
            "label": "after required verification passes",  # 用于展示选项名称remote_run_archive_trigger 的“after required verification passes”选项；问卷第一百四十项
            "value": "after required verification passes",  # 用于提交机器值remote_run_archive_trigger 的“after required verification passes”选项；问卷第一百四十一项
            "description": "该仓库要求的验证门禁通过后，活动运行目录必须归档。",  # 用于解释选择影响remote_run_archive_trigger 的“after required verification passes”选项；问卷第一百四十二项
            "recommended": True,  # 用于标记推荐优先级remote_run_archive_trigger 的“after required verification passes”选项；问卷第一百四十三项
        },
        {
            "label": "disabled",  # 第四百十四项展示标签
            "value": "disabled",  # 第四百十五项提交值
            "description": "远端未配置或本次不治理运行归档触发时机。",  # 第四百十六项选择说明
            "recommended": False,  # 第四百十七项推荐状态
        },  # 用于定义“disabled”回答选项的提交合同；问卷第一百四十四项
        {
            "label": "用户自定义",  # 第四百十八项展示标签
            "value": "__user_input__",  # 第四百十九项提交值
            "description": "由用户输入其他远端归档触发规则。",  # 第四百二十项选择说明
            "recommended": False,  # 第四百二十一项推荐状态
        },  # 用于定义“用户自定义”回答选项的提交合同；问卷第一百四十五项
    ],
    "alignment_confirmed": [  # 用于声明“alignment_confirmed”设计合同项；问卷第一百四十六项
        {  # 理解一致确认选项
            "label": "是，理解一致",  # 第四百二十二项展示标签
            "value": True,  # 第四百二十三项提交值
            "description": "允许写入强控制档案。",  # 第四百二十四项选择说明
            "recommended": True,  # 第四百二十五项推荐状态
        },  # 用于定义“是，理解一致”回答选项的提交合同；问卷第一百四十七项
        {
            "label": "否，需要修正",  # 第四百二十六项展示标签
            "value": False,  # 第四百二十七项提交值
            "description": "继续修正并重新确认。",  # 第四百二十八项选择说明
            "recommended": False,  # 第四百二十九项推荐状态
        },  # 用于定义“否，需要修正”回答选项的提交合同；问卷第一百四十八项
    ],
    "default_conversation_language": [  # 用于声明“default_conversation_language”设计合同项；问卷第一百四十九项
        {"label": "中文", "value": "中文", "description": "默认后续对话使用中文。", "recommended": True},  # 用于定义“中文”回答选项的提交合同；问卷第一百五十项
        {
            "label": "English",  # 第五百一项展示标签
            "value": "English",  # 第五百二项提交值
            "description": "默认后续对话使用英文。",  # 第五百三项选择说明
            "recommended": False,  # 第五百四项推荐状态
        },  # 用于定义“English”回答选项的提交合同；问卷第一百五十一项
        {
            "label": "用户自定义",  # 第五百五项展示标签
            "value": "__user_input__",  # 第五百六项提交值
            "description": "由用户输入其他默认语言。",  # 第五百七项选择说明
            "recommended": False,  # 第五百八项推荐状态
        },  # 用于定义“用户自定义”回答选项的提交合同；问卷第一百五十二项
    ],
    USE_REMOTE_SERVER_KEY: [  # 用于构建设计访谈的结构化合同项；问卷第一百五十三项
        {
            "label": "不使用远程",  # 第五百九项展示标签
            "value": False,  # 第五百十项提交值
            "description": "本次 AGENTS 生成不锁定远程服务器，未来如需远程验证必须先更新 AGENTS。",  # 第五百十一项选择说明
            "recommended": True,  # 第五百十二项推荐状态
        },  # 本地生成模式
        {
            "label": "使用远程",  # 第五百十三项展示标签
            "value": True,  # 第五百十四项提交值
            "description": "本次必须完成 erie-remote-ssh 依赖检查、服务器配置/选择、校验和锁定。",  # 第五百十五项选择说明
            "recommended": False,  # 第五百十六项推荐状态
        },  # 远程生成模式
    ],
    USE_CODEBASE_MEMORY_MCP_KEY: [  # 知识图谱启用选择的交互选项
        {
            "label": "使用知识图谱",  # 启用选项标签
            "value": True,  # 启用知识图谱的提交值
            "description": "调试时优先查询项目知识图谱，并强制完成根级持久化索引门禁。",  # 启用后的治理义务
            "recommended": True,  # 完整架构分析场景默认推荐启用
        },
        {
            "label": "不使用知识图谱",  # 禁用选项标签
            "value": False,  # 禁用知识图谱的提交值
            "description": "不检测或调用 MCP，但仍保持 `.codebase-memory/` 被忽略且不受 Git 跟踪。",  # 禁用后的仓库边界
            "recommended": False,  # 完整架构分析场景不推荐禁用
        },
    ],
    "memory_enabled": [  # 用于声明“memory_enabled”设计合同项；问卷第一百五十六项
        {
            "label": "启用记忆",  # 第五百十七项展示标签
            "value": True,  # 第五百十八项提交值
            "description": "创建 `docs/memory/`，保存可审计摘要和可查询索引。",  # 第五百十九项选择说明
            "recommended": True,  # 第五百二十项推荐状态
        },  # 用于定义“启用记忆”回答选项的提交合同；问卷第一百五十七项
        {
            "label": "关闭记忆",  # 第五百二十一项展示标签
            "value": False,  # 第五百二十二项提交值
            "description": "仅保留 handoff 和 AGENTS 指针，不写入记忆库。",  # 第五百二十三项选择说明
            "recommended": False,  # 第五百二十四项推荐状态
        },  # 用于定义“关闭记忆”回答选项的提交合同；问卷第一百五十八项
    ],
    "memory_storage_backend": [  # 用于声明“memory_storage_backend”设计合同项；问卷第一百五十九项
        {
            "label": "sqlite-plus-jsonl",  # 第五百二十五项展示标签
            "value": "sqlite-plus-jsonl",  # 第五百二十六项提交值
            "description": "SQLite 查询索引 + JSONL 追加事件 + Markdown 压缩摘要。",  # 第五百二十七项选择说明
            "recommended": True,  # 第五百二十八项推荐状态
        },  # 混合记忆后端
    ],
    "memory_capture_scope": [  # 用于声明“memory_capture_scope”设计合同项；问卷第一百六十一项
        {
            "label": "默认长期范围",  # 用于展示选项名称memory_capture_scope 的“默认长期范围”选项；问卷第一百六十二项
            "value": (  # 默认记忆范围
                "handoff summaries, user-confirmed project preferences, durable decisions, "
                "validation lessons, and release lessons"
            ),
            "description": "保存交接摘要、用户确认偏好、长期决策、验证和发布教训。",  # 用于解释选择影响memory_capture_scope 的“默认长期范围”选项；问卷第一百六十四项
            "recommended": True,  # 用于标记推荐优先级memory_capture_scope 的“默认长期范围”选项；问卷第一百六十五项
        },
        {
            "label": "仅 handoff 摘要",  # 第五百二十九项展示标签
            "value": "handoff summaries only",  # 第五百三十项提交值
            "description": "降低长期记忆写入范围。",  # 第五百三十一项选择说明
            "recommended": False,  # 第五百三十二项推荐状态
        },  # 交接摘要范围
        {
            "label": "用户自定义",  # 第五百三十三项展示标签
            "value": "__user_input__",  # 第五百三十四项提交值
            "description": "由用户输入更具体的捕获范围。",  # 第五百三十五项选择说明
            "recommended": False,  # 第五百三十六项推荐状态
        },  # “用户自定义”对应的问卷合同；问卷第二百一项
    ],
    "memory_read_policy": [  # “memory_read_policy”对应的问卷合同；问卷第二百二项
        {
            "label": "handoff + 相关摘要",  # “handoff + 相关摘要”对应的问卷合同；问卷第二百三项
            "value": "read latest handoff plus relevant docs/memory summaries before implementation",  # “value”对应的问卷合同；问卷第二百四项
            "description": "每次任务开始读取最新 handoff，并按任务查询相关记忆摘要。",  # “description”对应的问卷合同；问卷第二百五项
            "recommended": True,  # “recommended”对应的问卷合同；问卷第二百六项
        },
        {
            "label": "仅恢复时读取",  # 第五百三十七项展示标签
            "value": "read memory during resume or takeover only",  # 第五百三十八项提交值
            "description": "减少日常上下文加载。",  # 第五百三十九项选择说明
            "recommended": False,  # 第五百四十项推荐状态
        },  # 恢复期读取
        {
            "label": "用户自定义",  # 第五百四十一项展示标签
            "value": "__user_input__",  # 第五百四十二项提交值
            "description": "由用户输入读取策略。",  # 第五百四十三项选择说明
            "recommended": False,  # 第五百四十四项推荐状态
        },  # “用户自定义”对应的问卷合同；问卷第二百八项
    ],
    "memory_sensitivity_policy": [  # “memory_sensitivity_policy”对应的问卷合同；问卷第二百九项
        {
            "label": "不存敏感原文",  # “不存敏感原文”对应的问卷合同；问卷第二百十项
            "value": "do not store secrets, credentials, or raw local private paths",  # “value”对应的问卷合同；问卷第二百十一项
            "description": "禁止保存 secrets、凭据、本地私密路径原文。",  # “description”对应的问卷合同；问卷第二百十二项
            "recommended": True,  # “recommended”对应的问卷合同；问卷第二百十三项
        },
        {
            "label": "仅占位摘要",  # 第五百四十五项展示标签
            "value": "store only redacted placeholders for sensitive facts",  # 第五百四十六项提交值
            "description": "敏感事实只允许以脱敏占位符描述。",  # 第五百四十七项选择说明
            "recommended": False,  # 第五百四十八项推荐状态
        },  # 脱敏占位存储
        {
            "label": "用户自定义",  # 第五百四十九项展示标签
            "value": "__user_input__",  # 第五百五十项提交值
            "description": "由用户输入敏感信息边界。",  # 第五百五十一项选择说明
            "recommended": False,  # 第五百五十二项推荐状态
        },  # “用户自定义”对应的问卷合同；问卷第二百十五项
    ],
    "skill_design_patterns": [  # “skill_design_patterns”对应的问卷合同；问卷第二百十六项
        {
            "label": "五模式组合",  # “五模式组合”对应的问卷合同；问卷第二百十七项
            "value": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],  # “value”对应的问卷合同；问卷第二百十八项
            "description": "脚本、模板、审查、反问和流水线都启用。",  # “description”对应的问卷合同；问卷第二百十九项
            "recommended": True,  # “recommended”对应的问卷合同；问卷第二百二十项
        },
        {
            "label": "生成器为主",  # 第五百五十三项展示标签
            "value": ["Tool Wrapper", "Generator"],  # 第五百五十四项提交值
            "description": "强调稳定输出和可执行脚本。",  # 第五百五十五项选择说明
            "recommended": False,  # 第五百五十六项推荐状态
        },  # 生成器角色组合
        {
            "label": "审查器为主",  # 第五百五十七项展示标签
            "value": ["Reviewer", "Pipeline"],  # 第五百五十八项提交值
            "description": "强调验证、审查和顺序门禁。",  # 第五百五十九项选择说明
            "recommended": False,  # 第五百六十项推荐状态
        },  # “审查器为主”对应的问卷合同；问卷第二百二十二项
    ],
    "validation_method": [  # “validation_method”对应的问卷合同；问卷第二百二十三项
        {
            "label": "自动化 + 人工验收",  # 第五百六十一项展示标签
            "value": "automated scripts plus user review",  # 第五百六十二项提交值
            "description": "脚本验证后由用户确认结果是否符合预期。",  # 第五百六十三项选择说明
            "recommended": True,  # 第五百六十四项推荐状态
        },  # 双重验收方式
        {
            "label": "仅自动化",  # 第五百六十五项展示标签
            "value": "automated scripts",  # 第五百六十六项提交值
            "description": "以测试、审计、evaluate 链为准。",  # 第五百六十七项选择说明
            "recommended": False,  # 第五百六十八项推荐状态
        },  # “仅自动化”对应的问卷合同；问卷第二百二十五项
        {
            "label": "前向测试",  # 第五百六十九项展示标签
            "value": "forward testing",  # 第五百七十项提交值
            "description": "用真实任务或新 fixture 验证行为。",  # 第五百七十一项选择说明
            "recommended": False,  # 第五百七十二项推荐状态
        },  # “前向测试”对应的问卷合同；问卷第二百二十六项
    ],
    "validation_granularity": [  # “validation_granularity”对应的问卷合同；问卷第二百二十七项
        {
            "label": "完整验证链",  # “完整验证链”对应的问卷合同；问卷第二百二十八项
            "value": "unit tests, AGENTS verification, skill audit, full evaluate chain",  # “value”对应的问卷合同；问卷第二百二十九项
            "description": "覆盖单测、AGENTS 校验、skill audit 和 evaluate。",  # “description”对应的问卷合同；问卷第二百三十项
            "recommended": True,  # “recommended”对应的问卷合同；问卷第二百三十一项
        },
        {  # 最小相关验证选项
            "label": "最小相关验证",  # 第五百七十三项展示标签
            "value": "narrow tests plus changed-script verification",  # 第五百七十四项提交值
            "description": "只运行与改动相关的最小验证。",  # 第五百七十五项选择说明
            "recommended": False,  # 第五百七十六项推荐状态
        },  # 窄域验证策略
    ],
    "engineering_rule_primary": [  # “engineering_rule_primary”对应的问卷合同；问卷第二百三十三项
        {
            "label": "不启用规则集",  # 第五百七十七项展示标签
            "value": "none",  # 第五百七十八项提交值
            "description": "不启用书籍化工程规则集。",  # 第五百七十九项选择说明
            "recommended": True,  # 第五百八十项推荐状态
        },  # “不启用规则集”对应的问卷合同；问卷第二百三十四项
        {
            "label": "refactoring",  # 第五百八十一项展示标签
            "value": "refactoring",  # 第五百八十二项提交值
            "description": "适合重构和设计整洁性。",  # 第五百八十三项选择说明
            "recommended": False,  # 第五百八十四项推荐状态
        },  # “refactoring”对应的问卷合同；问卷第二百三十五项
        {
            "label": "legacy-code",  # 第五百八十五项展示标签
            "value": "working-effectively-with-legacy-code",  # 第五百八十六项提交值
            "description": "适合遗留工程改造。",  # 第五百八十七项选择说明
            "recommended": False,  # 第五百八十八项推荐状态
        },  # 遗留代码规则集
        {
            "label": "release-it",  # 第五百八十九项展示标签
            "value": "release-it",  # 第五百九十项提交值
            "description": "适合发布可靠性和交付纪律。",  # 第五百九十一项选择说明
            "recommended": False,  # 第五百九十二项推荐状态
        },  # “release-it”对应的问卷合同；问卷第二百三十七项
    ],
    "engineering_rule_mode": [  # “engineering_rule_mode”对应的问卷合同；问卷第二百三十八项
        {"label": "none", "value": "none", "description": "不启用规则集模式。", "recommended": True},  # “none”对应的问卷合同；问卷第二百三十九项
        {"label": "mini", "value": "mini", "description": "保留关键决策规则。", "recommended": False},  # “mini”对应的问卷合同；问卷第二百四十项
        {"label": "nano", "value": "nano", "description": "保留最小常驻规则。", "recommended": False},  # “nano”对应的问卷合同；问卷第二百四十一项
    ],
    "engineering_rule_scope": [  # “engineering_rule_scope”对应的问卷合同；问卷第二百四十二项
        {
            "label": "on-demand",  # 第五百九十三项展示标签
            "value": "on-demand",  # 第五百九十四项提交值
            "description": "按需启用规则集。",  # 第五百九十五项选择说明
            "recommended": True,  # 第五百九十六项推荐状态
        },  # “on-demand”对应的问卷合同；问卷第二百四十三项
        {
            "label": "project-baseline",  # 第五百九十七项展示标签
            "value": "project-baseline",  # 第五百九十八项提交值
            "description": "对整个工程提供基线约束。",  # 第五百九十九项选择说明
            "recommended": False,  # 第六百项推荐状态
        },  # “project-baseline”对应的问卷合同；问卷第二百四十四项
        {
            "label": "scoped",  # 第六百一项展示标签
            "value": "scoped",  # 第六百二项提交值
            "description": "仅作用于特定目录或场景。",  # 第六百三项选择说明
            "recommended": False,  # 第六百四项推荐状态
        },  # “scoped”对应的问卷合同；问卷第二百四十五项
    ],
}

# 需要区分项目类型的问题集合用于保持后续处理语义明确。
_branched_questions = SKILL_QUESTIONS + ENGINEERING_QUESTIONS  # 需要区分项目类型的问题集合

# 跨项目类型共享的问题集合用于保持后续处理语义明确。
_shared_questions = DIRECTORY_QUESTIONS + MEMORY_QUESTIONS + EXISTING_WORK_QUESTIONS  # 跨项目类型共享的问题集合

# 问题标识到完整问题记录的索引用于保持后续处理语义明确。
QUESTION_MAP: dict[str, dict[str, Any]] = {  # 问题标识到完整问题记录的索引
    **{item["question_id"]: item for item in COMMON_QUESTIONS},  # 用于索引公共问题；问卷第一百六十六项
    **{  # 用于合并分支问题记录到统一索引；问卷第一百六十七项
        question_id: {  # 用于构建设计访谈的结构化合同项；问卷第一百六十八项
            "question_id": question_id,  # 用于稳定标识engineering_rule_scope 的“未命名”选项；问卷第一百六十九项
            "answer_key": answer_key,  # 用于绑定答案字段engineering_rule_scope 的“未命名”选项；问卷第一百七十项
            "required": True,  # 用于声明必答状态engineering_rule_scope 的“未命名”选项；问卷第一百七十一项
            "branch": "skill"  # 技能分支映射起点
            if question in SKILL_QUESTIONS  # 技能问题选择技能分支
            else "engineering",  # 用于限定适用分支engineering_rule_scope 的“未命名”选项；问卷第一百七十二项
            "ask": prompt,  # 用于提供交互提示engineering_rule_scope 的“未命名”选项；问卷第一百七十三项
        }
        for question in _branched_questions  # 用于构建设计访谈的结构化合同项；问卷第一百七十四项
        for question_id, answer_key, prompt in (question,)  # 用于构建设计访谈的结构化合同项；问卷第一百七十五项
    },
    **{  # 用于合并分支问题记录到统一索引；问卷第一百七十六项
        question_id: {  # 用于构建设计访谈的结构化合同项；问卷第一百七十七项
            "question_id": question_id,  # 用于稳定标识engineering_rule_scope 的“未命名”选项；问卷第一百七十八项
            "answer_key": answer_key,  # 用于绑定答案字段engineering_rule_scope 的“未命名”选项；问卷第一百七十九项
            "required": True,  # 用于声明必答状态engineering_rule_scope 的“未命名”选项；问卷第一百八十项
            "branch": "all",  # 用于限定适用分支engineering_rule_scope 的“未命名”选项；问卷第一百八十一项
            "ask": prompt,  # 展示共享问题的交互提示；问卷第一百八十二项
        }
        for question_id, answer_key, prompt in _shared_questions  # 用于构建设计访谈的结构化合同项；问卷第一百八十三项
    },
}

# 生成设计访谈状态文件使用的稳定时间戳。
def now_iso() -> str:
    """返回无微秒的 UTC ISO 时间戳。

    参数：无。
    返回：以 ``Z`` 结尾的 UTC ISO 时间文本。
    """

    # 统一使用秒精度和 Z 后缀，避免不同调用方产生格式漂移。
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# 为自由文本问题提供一致的默认回答入口。
def default_options(answer_key: str) -> list[dict[str, Any]]:
    """为没有专用选项的问题生成通用回答选项。

    参数：answer_key 为需要填写的答案字段名。
    返回：用户输入和仓库事实两种通用选项。
    """

    # 保留人工输入优先、仓库事实兜底的固定顺序。
    return [
        {
            "label": "用户输入",
            "value": "__user_input__",
            "description": f"由用户提供 `{answer_key}` 的具体内容。",
            "recommended": True,
        },
        {
            "label": "沿用仓库事实",
            "value": "__repo_fact__",
            "description": "如果仓库事实足够明确，使用探测结果作为答案。",
            "recommended": False,
        },
    ]

# 在不修改共享问题定义的前提下补齐选项。
def with_options(item: dict[str, Any]) -> dict[str, Any]:
    """复制问题记录并补齐对应的回答选项。

    参数：item 为原始问题记录。
    返回：包含 options 字段且不修改原对象的问题记录。
    """

    # 避免修改输入对象的问题记录副本用于保持后续处理语义明确。
    dict_row = dict(item)  # 避免修改输入对象的问题记录副本

    # 当前问题使用的答案字段名用于保持后续处理语义明确。
    str_answer_key = str(dict_row.get("answer_key", ""))  # 当前问题使用的答案字段名

    # 专用选项优先，缺失时按答案字段生成通用选项。
    dict_row.setdefault(
        "options",
        QUESTION_OPTIONS.get(str_answer_key, default_options(str_answer_key)),
    )

    # 返回独立记录，防止调用方污染模块级问题合同。
    return dict_row

# 按项目类型组合首次设计访谈的问题分组。
def groups_for(kind: str) -> list[list[str]]:
    """返回指定项目类型的完整访谈问题分组。

    参数：kind 为 ``skill`` 或 ``engineering``。
    返回：公共分组与对应类型分组组成的有序列表。
    异常：kind 未受支持时抛出 ValueError。
    """

    # 技能项目追加技能目的、资料和交付合同问题。
    if kind == "skill":

        # 公共问题必须先于技能专用问题出现。
        return COMMON_GROUPS + SKILL_GROUPS

    # 工程项目追加工程目标、技术边界和规则问题。
    if kind == "engineering":

        # 公共问题必须先于工程专用问题出现。
        return COMMON_GROUPS + ENGINEERING_GROUPS

    # 未知类型无法生成可靠问题序列，立即向调用方报告。
    raise ValueError(f"> ERR: [Python] unknown project kind: {kind}")

# 按项目类型组合接管既有工作时的问题分组。
def takeover_groups_for(kind: str) -> list[list[str]]:
    """返回接管既有项目时使用的访谈问题分组。

    参数：kind 为 ``skill`` 或 ``engineering``。
    返回：接管流程需要重新确认的有序问题分组。
    异常：kind 未受支持时抛出 ValueError。
    """

    # 技能接管只重新确认会影响既有技能合同的关键问题。
    if kind == "skill":

        # 接管公共问题与技能增量问题共同构成最小复核集。
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_SKILL_GROUPS

    # 工程接管只重新确认会影响既有工程合同的关键问题。
    if kind == "engineering":

        # 接管公共问题与工程增量问题共同构成最小复核集。
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_ENGINEERING_GROUPS

    # 未知类型无法选择接管合同，立即向调用方报告。
    raise ValueError(f"> ERR: [Python] unknown takeover project kind: {kind}")

# 展开项目类型对应的完整问题记录。
def questions_for(kind: str) -> list[dict[str, Any]]:
    """返回指定项目类型的有序问题记录。

    参数：kind 为需要构建设计访谈的问题类型。
    返回：按访谈分组顺序展开且带回答选项的问题记录。
    """

    # 分组顺序就是交互顺序，展开时同步补齐回答选项。
    return [with_options(QUESTION_MAP[qid]) for group in groups_for(kind) for qid in group]

# 将问题标识序列映射为答案字段序列。
def question_ids_to_keys(question_ids: list[str]) -> list[str]:
    """把问题标识转换为对应的答案字段名。

    参数：question_ids 为待转换的问题标识列表。
    返回：与输入顺序一致的答案字段名列表。
    """

    # 保持输入顺序，供缺失字段校验准确回报问题位置。
    return [str(QUESTION_MAP[qid]["answer_key"]) for qid in question_ids]

# 将问题标识序列映射为可展示的问题记录。
def question_rows(question_ids: list[str]) -> list[dict[str, Any]]:
    """按问题标识返回带回答选项的问题记录。

    参数：question_ids 为需要读取的问题标识列表。
    返回：与输入顺序一致且包含回答选项的问题记录。
    """

    # 每条记录都复制并补齐选项，避免共享状态被交互层修改。
    return [with_options(QUESTION_MAP[qid]) for qid in question_ids]

# 从磁盘读取设计答案 JSON 对象。
def read_json_object(path: Path) -> dict[str, Any]:
    """从文件读取 JSON 对象，格式错误时终止命令。

    参数：path 为答案 JSON 文件路径。
    返回：解析得到的 JSON 对象。
    异常：文件不可读、JSON 无效或根值不是对象时抛出 SystemExit。
    """

    # 文件读取和 JSON 解析使用同一命令级错误出口。
    try:

        # 解析结果承载答案文件的 JSON 根对象。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # 从答案文件解析出的 JSON 根对象

    # 保留底层异常文本，帮助用户定位路径、编码或语法错误。
    except Exception as exc:

        # 命令以稳定 JSON 错误载荷终止，便于机器调用方解析。
        raise SystemExit(json.dumps({"errors": [f"could not read answers: {exc}"]}, indent=2))

    # 根值必须是答案键值对象，数组或标量无法参与合同校验。
    if not isinstance(dict_data, dict):

        # 使用与读取失败一致的 JSON 错误载荷终止命令。
        raise SystemExit(json.dumps({"errors": ["answers must be a JSON object"]}, indent=2))

    # 类型检查通过后向调用方返回确定的答案对象。
    return dict_data

# 判断设计答案是否缺少有效内容。
def empty(value: Any) -> bool:
    """判断访谈答案是否为空。

    参数：value 为待检查的答案值。
    返回：值为 None、空字符串或空列表时返回 True。
    """

    # 仅合同明确允许的三种空值参与缺失答案判断。
    return value is None or value == "" or value == []

# 将额外需求的多种输入形态归一为单行文本。
def normalize_extra_requirements(raw_value: Any) -> str:
    """把额外需求规范为稳定的单行文本。

    参数：raw_value 为字符串、列表或其他可文本化的答案。
    返回：规范化需求文本；无额外需求时返回 ``none``。
    """

    # 多选或批量输入先去除空白项，再按稳定分隔符合并。
    if isinstance(raw_value, list):

        # 条目列表只保留去除两端空白后仍非空的需求。
        parts = [str(item).strip() for item in raw_value if str(item).strip()]  # 清理空白后的额外需求条目

        # 准备规范化或判断的原始文本用于保持后续处理语义明确。
        raw_value = "; ".join(parts)  # 准备规范化或判断的原始文本

    # 大小写判断前的规范化需求文本用于保持后续处理语义明确。
    normalized = str(raw_value if raw_value is not None else "").strip()  # 大小写判断前的规范化需求文本

    # 所有无需求同义词统一写成 none，稳定后续哈希与复核。
    return "none" if normalized.casefold() in NO_EXTRA_REQUIREMENTS else normalized

# 判断远程目录答案是否表达了真实配置。
def remote_directory_configured(raw: Any) -> bool:
    """判断答案是否描述了已配置的远程目录。

    参数：raw 为远程目录结构的原始答案。
    返回：答案表达有效远程目录配置时返回 True。
    """

    # 去除远程目录答案两端空白，避免空格被误判为有效配置。
    raw_value = str(raw).strip()  # 远程目录配置判定使用的清洁文本

    # 空文本明确表示没有可用远程目录配置。
    if not raw_value:

        # 空答案不触发远程目录策略追问。
        return False

    # 远程目录答案的小写形式用于保持后续处理语义明确。
    lowered = raw_value.lower()  # 远程目录答案的小写形式

    # 标准禁用词明确声明远程目录未配置。
    if lowered in {"none", "not configured", "disabled"}:

        # 显式禁用答案不触发远程目录策略追问。
        return False

    # 历史完整句式同样表示没有远程工作区。
    if "no remote workspace is configured" in lowered:

        # 兼容历史答案并维持旧项目接管行为。
        return False

    # 其他非空内容视为调用方提供的远程目录配置。
    return True

# 判断当前设计答案是否需要完整远程目录策略。
def remote_directory_policy_required(answers: dict[str, Any] | None) -> bool:
    """判断当前答案是否要求收集远程目录策略。

    参数：answers 为当前已收集的设计答案，可为 None。
    返回：启用远程服务器或配置远程目录时返回 True。
    """

    # 空值归一后的设计答案对象用于保持后续处理语义明确。
    answers = answers or {}  # 空值归一后的设计答案对象

    # 是否明确启用远程服务器用于保持后续处理语义明确。
    bool_uses_remote_server = bool(answers.get(USE_REMOTE_SERVER_KEY))  # 是否明确启用远程服务器

    # 是否存在有效远程目录配置用于保持后续处理语义明确。
    bool_has_remote_directory = remote_directory_configured(  # 是否存在有效远程目录配置
        answers.get("remote_directory_structure", "")  # 用于读取远程目录答案
    )

    # 任一远程信号成立都必须继续收集远程目录治理合同。
    return bool_uses_remote_server or bool_has_remote_directory
