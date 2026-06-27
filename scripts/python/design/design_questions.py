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
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# 分隔当前密集代码块，保留原有执行顺序。
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import emit_json, inspect_project, resolve_project
from manage_docs import scaffold as scaffold_docs


# 保留 STATE PATH 中间值，支撑 模块入口 的当前计算步骤。
STATE_PATH = ".agents/design-interview-state.json"  # STATE PATH 用于本步治理判断

# 保留 TERMINAL STATUSES 中间值，支撑 模块入口 的当前计算步骤。
TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}  # TERMINAL STATUSES 用于本步治理判断

# 保留 TAKEOVER TERMINAL STATUSES 中间值，支撑 模块入口 的当前计算步骤。
TAKEOVER_TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}  # TAKEOVER TERMINAL STATUSES 用于本步治理判断

# 保留 TAKEOVER REASON KEYS 中间值，支撑 模块入口 的当前计算步骤。
TAKEOVER_REASON_KEYS = {  # TAKEOVER REASON KEYS 用于本步治理判断
    "agents_version_mismatch",  # TAKEOVER REASON KEYS 用于本步治理判断
    "generator_version_mismatch",  # TAKEOVER REASON KEYS 用于本步治理判断
}

# 保留 REMOTE SSH SKILL NAME 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SSH_SKILL_NAME = "erie-remote-ssh"  # REMOTE SSH SKILL NAME 用于本步治理判断

# 保留 REMOTE SSH GIT URL 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SSH_GIT_URL = "https://github.com/Eriemon/remote-ssh.git"  # REMOTE SSH GIT URL 用于本步治理判断

# 保留 REMOTE SSH INSTALL SPECS 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SSH_INSTALL_SPECS = [{"skill": REMOTE_SSH_SKILL_NAME, "source_path": ".", "dest_name": REMOTE_SSH_SKILL_NAME}]  # REMOTE SSH INSTALL SPECS 用于本步治理判断

# 保留 USE REMOTE SERVER KEY 中间值，支撑 模块入口 的当前计算步骤。
USE_REMOTE_SERVER_KEY = "use_remote_server"  # USE REMOTE SERVER KEY 用于本步治理判断

# 保留 REMOTE INSTALL CONFIRM KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_INSTALL_CONFIRM_KEY = "install_remote_ssh_dependency"  # REMOTE INSTALL CONFIRM KEY 用于本步治理判断

# 保留 REMOTE CONFIGURATION MODE KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_CONFIGURATION_MODE_KEY = "remote_server_configuration_mode"  # REMOTE CONFIGURATION MODE KEY 用于本步治理判断

# 保留 REMOTE SELECTED SERVER ID KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTED_SERVER_ID_KEY = "selected_remote_server_id"  # REMOTE SELECTED SERVER ID KEY 用于本步治理判断

# 保留 REMOTE SELECTED SERVER NAME KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTED_SERVER_NAME_KEY = "selected_remote_server_name"  # REMOTE SELECTED SERVER NAME KEY 用于本步治理判断

# 保留 REMOTE SELECTED SERVER CATEGORY KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTED_SERVER_CATEGORY_KEY = "selected_remote_server_category"  # REMOTE SELECTED SERVER CATEGORY KEY 用于本步治理判断

# 保留 REMOTE SELECTED SERVER FUNCTIONS KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTED_SERVER_FUNCTIONS_KEY = "selected_remote_server_functions"  # REMOTE SELECTED SERVER FUNCTIONS KEY 用于本步治理判断

# 保留 REMOTE SELECTED SERVER TASKS KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTED_SERVER_TASKS_KEY = "selected_remote_server_tasks"  # REMOTE SELECTED SERVER TASKS KEY 用于本步治理判断

# 保留 REMOTE SERVER TASK ROUTES KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SERVER_TASK_ROUTES_KEY = "remote_server_task_routes"  # REMOTE SERVER TASK ROUTES KEY 用于本步治理判断

# 保留 REMOTE SELECTION CONFIRMED KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SELECTION_CONFIRMED_KEY = "remote_server_selection_confirmed"  # REMOTE SELECTION CONFIRMED KEY 用于本步治理判断

# 保留 REMOTE VALIDATION STATUS KEY 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_VALIDATION_STATUS_KEY = "remote_server_validation_status"  # REMOTE VALIDATION STATUS KEY 用于本步治理判断

# 保留 REMOTE GATE SECTION TITLE 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_GATE_SECTION_TITLE = "## Remote Server Contract"  # 远程契约段落标题

# 保留 REMOTE GATE FORCE RULE 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_GATE_FORCE_RULE = "When the user requests remote server validation for a registered task, you must start with that task route's primary remote server"  # REMOTE GATE FORCE RULE 用于本步治理判断

# 保留 REMOTE ROUTE FORCE RULE 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_ROUTE_FORCE_RULE = "When the user requests remote server validation for a registered task, you must start with that task route's primary remote server"  # REMOTE ROUTE FORCE RULE 用于本步治理判断

# 保留 REMOTE LEGACY TASK NAME 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_LEGACY_TASK_NAME = "remote-validation"  # REMOTE LEGACY TASK NAME 用于本步治理判断

# 保留 COMMON QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
COMMON_QUESTIONS = [  # COMMON QUESTIONS 用于本步治理判断
    {  # COMMON QUESTIONS 用于本步治理判断
        "question_id": "1",  # COMMON QUESTIONS 用于本步治理判断
        "answer_key": "development_type",  # COMMON QUESTIONS 用于本步治理判断
        "required": True,  # COMMON QUESTIONS 用于本步治理判断
        "branch": "all",  # COMMON QUESTIONS 用于本步治理判断
        "ask": "确认是技能开发还是工程开发？技能开发进入（2），工程开发进入（11）。",  # COMMON QUESTIONS 用于本步治理判断
    },  # COMMON QUESTIONS 用于本步治理判断
    {  # COMMON QUESTIONS 用于本步治理判断
        "question_id": "32",  # COMMON QUESTIONS 用于本步治理判断
        "answer_key": "default_conversation_language",  # COMMON QUESTIONS 用于本步治理判断
        "required": True,  # COMMON QUESTIONS 用于本步治理判断
        "branch": "all",  # COMMON QUESTIONS 用于本步治理判断
        "ask": "生成或重构 AGENTS.md 前，必须显式确认后续默认对话语言是什么；该语言必须写入控制档案并作为 AGENTS.md 强约束，不能依赖隐式默认值。",  # COMMON QUESTIONS 用于本步治理判断
    },  # COMMON QUESTIONS 用于本步治理判断
    {  # COMMON QUESTIONS 用于本步治理判断
        "question_id": "45",  # COMMON QUESTIONS 用于本步治理判断
        "answer_key": USE_REMOTE_SERVER_KEY,  # COMMON QUESTIONS 用于本步治理判断
        "required": True,  # COMMON QUESTIONS 用于本步治理判断
        "branch": "all",  # COMMON QUESTIONS 用于本步治理判断
        "ask": "本次生成或重构 AGENTS.md 是否需要启用远程服务器链路？如果启用，后续必须完成依赖检查、服务器配置/选择、校验和锁定。",  # COMMON QUESTIONS 用于本步治理判断
    },  # COMMON QUESTIONS 用于本步治理判断
]

# 保留 SKILL QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
SKILL_QUESTIONS = [  # SKILL QUESTIONS 用于本步治理判断
    ("2", "skill_purpose", "这个技能是干什么的？"),  # SKILL QUESTIONS 用于本步治理判断
    ("3", "skill_reason", "为什么要开发这个技能？"),  # SKILL QUESTIONS 用于本步治理判断
    ("4", "reference_materials", "这个技能有无参考资料？这些资料只是临时输入，开发完成后需要用户手动删除。"),  # SKILL QUESTIONS 用于本步治理判断
    ("5", "audience", "这个技能面向目标人群是什么？科研、商业、个人用户还是其他？"),  # SKILL QUESTIONS 用于本步治理判断
    ("6", "name", "这个技能的名称是什么？"),  # SKILL QUESTIONS 用于本步治理判断
    ("7", "design_notes", "这个技能的设计有无注意事项或者已有的经验？"),  # SKILL QUESTIONS 用于本步治理判断
    ("8", "git_management", "这个技能的设计是否要进行 git 管理，不提交远端？"),  # SKILL QUESTIONS 用于本步治理判断
    ("9", "branch_model", "这个技能所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),  # SKILL QUESTIONS 用于本步治理判断
    ("10", "release_contract", "dist 文件夹中释放可安装版本文件夹是否命名为【技能名】-vx.x.x，并同步生成 zip 压缩包？"),  # SKILL QUESTIONS 用于本步治理判断
    ("22", "trigger_scenarios", "这个技能应该在什么用户请求、文件类型、项目状态或任务场景下触发？"),  # SKILL QUESTIONS 用于本步治理判断
    ("23", "skill_design_patterns", "这个技能采用哪些设计模式：Tool Wrapper、Generator、Reviewer、Inversion、Pipeline，或其他？"),  # SKILL QUESTIONS 用于本步治理判断
    ("24", "resource_plan", "这个技能的资源边界是什么？哪些内容进入 SKILL.md、references/、scripts/、assets/、agents/openai.yaml？"),  # SKILL QUESTIONS 用于本步治理判断
    ("25", "progressive_disclosure_policy", "这个技能如何保持渐进式披露，例如 SKILL.md 精简、详细规则进入 references/、资源按需加载？"),  # SKILL QUESTIONS 用于本步治理判断
    ("26", "validation_gates", "这个技能完成前必须运行哪些验证门禁，例如 quick_validate.py、audit、verify、evaluate 或前端/端到端检查？"),  # SKILL QUESTIONS 用于本步治理判断
    ("27", "forward_testing_policy", "复杂或高风险技能是否需要前向测试？如果需要，触发条件和测试方式是什么？"),  # SKILL QUESTIONS 用于本步治理判断
    ("28", "development_requirements", "这个技能的详细开发需求是什么？"),  # SKILL QUESTIONS 用于本步治理判断
    ("29", "expected_outcome", "这个技能开发完成后的预期结果是什么？"),  # SKILL QUESTIONS 用于本步治理判断
    ("30", "validation_method", "这个技能开发完成后如何验证？"),  # SKILL QUESTIONS 用于本步治理判断
    ("31", "validation_granularity", "验证方式需要达到什么颗粒度？"),  # SKILL QUESTIONS 用于本步治理判断
]

# 保留 ENGINEERING QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
ENGINEERING_QUESTIONS = [  # ENGINEERING QUESTIONS 用于本步治理判断
    ("11", "project_purpose", "这个工程是干什么的？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("12", "project_reason", "为什么要干这个工程？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("13", "expected_outcome", "这个工程的预期效果和目标是什么？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("14", "environment", "这个工程是在远程服务器、WSL 或者本地开发？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("15", "reusable_experience", "这个工程有无经验可以借鉴？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("16", "name", "这个工程开发的名称是什么？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("17", "git_management", "这个工程开发是否要进行 git 管理，不提交远端？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("18", "branch_model", "这个工程所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("19", "release_contract", "dist 文件夹中释放可安装版本文件夹是否命名为【工程名】-vx.x.x，并同步生成 zip 压缩包？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("33", "development_requirements", "这个工程的详细开发需求是什么？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("34", "resource_plan", "这个工程的资源边界是什么？源码、脚本、测试、文档、部署和发布产物分别放在哪里？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("35", "validation_method", "这个工程开发完成后如何验证？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("36", "validation_granularity", "这个工程的验证方式需要达到什么颗粒度？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("37", "forward_testing_policy", "复杂或高风险工程改动是否需要前向测试？如果需要，触发条件和测试方式是什么？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("38", "engineering_rule_primary", "这个工程是否启用书籍化工程规则集？如果启用，选择哪一个主规则集？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("39", "engineering_rule_mode", "工程规则集使用 mini、nano，还是不启用？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("40", "engineering_rule_scope", "工程规则集作用于整个工程、局部目录，还是按需启用？"),  # ENGINEERING QUESTIONS 用于本步治理判断
    ("41", "engineering_rule_notes", "工程规则集还有哪些本地经验或注意事项需要记录？"),  # ENGINEERING QUESTIONS 用于本步治理判断
]

# 保留 DIRECTORY QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
DIRECTORY_QUESTIONS = [  # DIRECTORY QUESTIONS 用于本步治理判断
    ("42", "local_directory_structure", "请明确本地目录结构约定，包含主目录、tests、dist、docs 等位置。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("43", "remote_directory_structure", "请明确远程目录结构或远程部署边界；如果没有远程环境，也要明确写出没有配置。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("44", "feature_directory_rules", "请明确新增功能、脚本、文档、测试等后续内容应该进入哪些目录。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("46", "remote_conda_environment_layout", "如果远端工作区需要 conda 环境，请明确该前缀环境固定放在哪里；推荐 `.conda/<env-name>/`。如果远端未配置，可保持 disabled。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("47", "remote_run_artifact_active_layout", "如果远端会产生运行产物，请明确活动运行目录结构；推荐 `runs/<run-id>/`。如果远端未配置，可保持 disabled。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("48", "remote_run_artifact_backup_layout", "如果远端会归档运行产物，请明确归档目录结构；推荐 `backups/runs/<run-id>/`。如果远端未配置，可保持 disabled。"),  # DIRECTORY QUESTIONS 用于本步治理判断
    ("49", "remote_run_archive_trigger", "请明确远端运行产物何时必须从活动目录归档到 backups；推荐 `after required verification passes`。如果远端未配置，可保持 disabled。"),  # DIRECTORY QUESTIONS 用于本步治理判断
]

# 保留 MEMORY QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
MEMORY_QUESTIONS = [  # MEMORY QUESTIONS 用于本步治理判断
    ("50", "memory_enabled", "是否启用 `docs/memory/` 记忆治理层？默认推荐启用；如关闭，AGENTS.md 只保留 handoff 指针。"),  # MEMORY QUESTIONS 用于本步治理判断
    ("51", "memory_storage_backend", "记忆层使用什么存储后端？默认 `sqlite-plus-jsonl`：SQLite 负责查询索引，JSONL/Markdown 保留可审计原文和摘要。"),  # MEMORY QUESTIONS 用于本步治理判断
    ("52", "memory_capture_scope", "哪些内容可以进入长期记忆？默认保存 handoff 摘要、用户确认的项目偏好、长期决策、验证/发布教训。"),  # MEMORY QUESTIONS 用于本步治理判断
    ("53", "memory_read_policy", "任务开始和恢复时如何读取记忆？默认读取最新 handoff 和相关 `docs/memory` 摘要。"),  # MEMORY QUESTIONS 用于本步治理判断
    ("54", "memory_sensitivity_policy", "记忆层的敏感信息边界是什么？默认不保存 secrets、凭据、本地私密路径原文。"),  # MEMORY QUESTIONS 用于本步治理判断
]

# 保留 EXISTING WORK QUESTIONS 中间值，支撑 模块入口 的当前计算步骤。
EXISTING_WORK_QUESTIONS = [  # EXISTING WORK QUESTIONS 用于本步治理判断
    ("20", "has_existing_work", "当前工作文件夹是否已经存在工程或者技能？"),  # EXISTING WORK QUESTIONS 用于本步治理判断
    ("21", "directory_contract_confirmed", "是否确认本地目录结构、远程目录结构和新增功能目录规则已经明确并固定为强控制契约？"),  # EXISTING WORK QUESTIONS 用于本步治理判断
]

# 保留 DIRECTORY KEYS 中间值，支撑 模块入口 的当前计算步骤。
DIRECTORY_KEYS = [  # DIRECTORY KEYS 用于本步治理判断
    "local_directory_structure",  # DIRECTORY KEYS 用于本步治理判断
    "remote_directory_structure",  # DIRECTORY KEYS 用于本步治理判断
    "feature_directory_rules",  # DIRECTORY KEYS 用于本步治理判断
]

# 保留 REMOTE DIRECTORY POLICY KEYS 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_DIRECTORY_POLICY_KEYS = [  # REMOTE DIRECTORY POLICY KEYS 用于本步治理判断
    "remote_conda_environment_layout",  # REMOTE DIRECTORY POLICY KEYS 用于本步治理判断
    "remote_run_artifact_active_layout",  # REMOTE DIRECTORY POLICY KEYS 用于本步治理判断
    "remote_run_artifact_backup_layout",  # REMOTE DIRECTORY POLICY KEYS 用于本步治理判断
    "remote_run_archive_trigger",  # REMOTE DIRECTORY POLICY KEYS 用于本步治理判断
]

# 保留 OPTIONAL EMPTY KEYS 中间值，支撑 模块入口 的当前计算步骤。
OPTIONAL_EMPTY_KEYS = {"engineering_rule_notes"}  # OPTIONAL EMPTY KEYS 用于本步治理判断

# 保留 ALIGNMENT KEY 中间值，支撑 模块入口 的当前计算步骤。
ALIGNMENT_KEY = "alignment_confirmed"  # ALIGNMENT KEY 用于本步治理判断

# 保留 GROUP CONFIRMATION KEY 中间值，支撑 模块入口 的当前计算步骤。
GROUP_CONFIRMATION_KEY = "group_confirmed"  # GROUP CONFIRMATION KEY 用于本步治理判断

# 保留 EXTRA REQUIREMENTS KEY 中间值，支撑 模块入口 的当前计算步骤。
EXTRA_REQUIREMENTS_KEY = "extra_requirements"  # EXTRA REQUIREMENTS KEY 用于本步治理判断

# 保留 DESIGN REVIEW KEY 中间值，支撑 模块入口 的当前计算步骤。
DESIGN_REVIEW_KEY = "design_review"  # DESIGN REVIEW KEY 用于本步治理判断

# 保留 REVIEW REWORK CONFIRMATION KEY 中间值，支撑 模块入口 的当前计算步骤。
REVIEW_REWORK_CONFIRMATION_KEY = "review_rework_confirmed"  # REVIEW REWORK CONFIRMATION KEY 用于本步治理判断

# 保留 SKILL NAME RE 中间值，支撑 模块入口 的当前计算步骤。
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # SKILL NAME RE 用于本步治理判断

# 保留 NO EXTRA REQUIREMENTS 中间值，支撑 模块入口 的当前计算步骤。
NO_EXTRA_REQUIREMENTS = {"", "none", "no", "no extra", "n/a", "无", "没有", "无补充", "无额外补充", "不补充", "无需补充"}  # NO EXTRA REQUIREMENTS 用于本步治理判断

# 保留 ENGINEERING RULE SETS 中间值，支撑 模块入口 的当前计算步骤。
ENGINEERING_RULE_SETS = {  # ENGINEERING RULE SETS 用于本步治理判断
    "a-philosophy-of-software-design",  # ENGINEERING RULE SETS 用于本步治理判断
    "clean-architecture",  # ENGINEERING RULE SETS 用于本步治理判断
    "clean-code",  # ENGINEERING RULE SETS 用于本步治理判断
    "code-complete",  # ENGINEERING RULE SETS 用于本步治理判断
    "designing-data-intensive-applications",  # ENGINEERING RULE SETS 用于本步治理判断
    "domain-driven-design",  # ENGINEERING RULE SETS 用于本步治理判断
    "domain-driven-design-distilled",  # ENGINEERING RULE SETS 用于本步治理判断
    "implementing-domain-driven-design",  # ENGINEERING RULE SETS 用于本步治理判断
    "patterns-of-enterprise-application-architecture",  # ENGINEERING RULE SETS 用于本步治理判断
    "refactoring",  # ENGINEERING RULE SETS 用于本步治理判断
    "refactoring-guru",  # ENGINEERING RULE SETS 用于本步治理判断
    "release-it",  # ENGINEERING RULE SETS 用于本步治理判断
    "the-pragmatic-programmer",  # ENGINEERING RULE SETS 用于本步治理判断
    "working-effectively-with-legacy-code",  # ENGINEERING RULE SETS 用于本步治理判断
}

# 保留 ENGINEERING RULE MODES 中间值，支撑 模块入口 的当前计算步骤。
ENGINEERING_RULE_MODES = {"none", "mini", "nano"}  # ENGINEERING RULE MODES 用于本步治理判断

# 保留 ENGINEERING RULE SCOPES 中间值，支撑 模块入口 的当前计算步骤。
ENGINEERING_RULE_SCOPES = {"project-baseline", "scoped", "on-demand"}  # ENGINEERING RULE SCOPES 用于本步治理判断

# 保留 MEMORY GROUPS 中间值，支撑 模块入口 的当前计算步骤。
MEMORY_GROUPS = [["50", "51", "52", "53", "54"]]  # MEMORY GROUPS 用于本步治理判断

# 保留 COMMON GROUPS 中间值，支撑 模块入口 的当前计算步骤。
COMMON_GROUPS = [["1", "32", "45"], ["50", "51", "52", "53", "54"]]  # COMMON GROUPS 用于本步治理判断

# 保留 SKILL GROUPS 中间值，支撑 模块入口 的当前计算步骤。
SKILL_GROUPS = [  # SKILL GROUPS 用于本步治理判断
    ["2", "3", "4"],  # SKILL GROUPS 用于本步治理判断
    ["5", "6", "7"],  # SKILL GROUPS 用于本步治理判断
    ["8", "9", "10"],  # SKILL GROUPS 用于本步治理判断
    ["22", "23", "24"],  # SKILL GROUPS 用于本步治理判断
    ["25", "26", "27"],  # SKILL GROUPS 用于本步治理判断
    ["28", "29", "30"],  # SKILL GROUPS 用于本步治理判断
    ["31"],  # SKILL GROUPS 用于本步治理判断
    ["42", "43", "44", "46", "47", "48", "49"],  # SKILL GROUPS 用于本步治理判断
    ["20", "21"],  # SKILL GROUPS 用于本步治理判断
]

# 保留 ENGINEERING GROUPS 中间值，支撑 模块入口 的当前计算步骤。
ENGINEERING_GROUPS = [  # ENGINEERING GROUPS 用于本步治理判断
    ["11", "12", "13"],  # ENGINEERING GROUPS 用于本步治理判断
    ["14", "15", "16"],  # ENGINEERING GROUPS 用于本步治理判断
    ["17", "18", "19"],  # ENGINEERING GROUPS 用于本步治理判断
    ["33", "34", "35"],  # ENGINEERING GROUPS 用于本步治理判断
    ["36", "37", "38"],  # ENGINEERING GROUPS 用于本步治理判断
    ["39", "40", "41"],  # ENGINEERING GROUPS 用于本步治理判断
    ["42", "43", "44", "46", "47", "48", "49"],  # ENGINEERING GROUPS 用于本步治理判断
    ["20", "21"],  # ENGINEERING GROUPS 用于本步治理判断
]

# 保留 TAKEOVER COMMON GROUPS 中间值，支撑 模块入口 的当前计算步骤。
TAKEOVER_COMMON_GROUPS = [["1", "32", "45"], ["50", "51", "52", "53", "54"]]  # TAKEOVER COMMON GROUPS 用于本步治理判断

# 保留 TAKEOVER SKILL GROUPS 中间值，支撑 模块入口 的当前计算步骤。
TAKEOVER_SKILL_GROUPS = [["6"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]  # TAKEOVER SKILL GROUPS 用于本步治理判断

# 保留 TAKEOVER ENGINEERING GROUPS 中间值，支撑 模块入口 的当前计算步骤。
TAKEOVER_ENGINEERING_GROUPS = [["16"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]  # TAKEOVER ENGINEERING GROUPS 用于本步治理判断


# 保留 QUESTION OPTIONS 中间值，支撑 模块入口 的当前计算步骤。
QUESTION_OPTIONS: dict[str, list[dict[str, Any]]] = {  # QUESTION OPTIONS 用于本步治理判断
    "development_type": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "技能开发", "value": "skill", "description": "为 Codex skill 收集设计、目录和验证契约。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "工程开发", "value": "engineering", "description": "为普通工程仓库收集 AGENTS.md 控制档案。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "git_management": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "启用 git 管理", "value": "yes-local-only", "description": "允许本地分支和提交，默认不推送远端。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "不启用 git 管理", "value": "no-git-management", "description": "不把 git 作为当前技能开发流程的一部分。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "其他", "value": "__user_input__", "description": "由用户输入自定义 git 管理规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "branch_model": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "master + dist release", "value": "master-and-dist-release", "description": "源码在 master，发布产物在 dist。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "当前分支为准", "value": "current-branch", "description": "不固定 master，先检查当前分支。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "release_contract": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "目录和 zip 同步", "value": "dist/<name>-vx.x.x plus zip", "description": "生成同名 release 目录和 zip 包。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "暂不发布", "value": "no-release", "description": "当前阶段不定义安装包产物。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "has_existing_work": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "已有项目/技能", "value": "yes", "description": "从当前文件内容生成目录和控制契约。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "新项目/技能", "value": "no", "description": "先按计划创建结构，再生成契约。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "directory_contract_confirmed": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "确认目录契约", "value": True, "description": "允许写入本地、远程、新功能目录规则。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "暂不确认", "value": False, "description": "只输出待确认摘要，不写强控制档案。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "remote_conda_environment_layout": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": ".conda/<env-name>/", "value": ".conda/<env-name>/", "description": "远端 conda 前缀环境固定放在对应工作区根下。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "disabled", "value": "disabled", "description": "远端未配置或不在本次目录治理范围内。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端 conda 前缀目录规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "remote_run_artifact_active_layout": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "runs/<run-id>/", "value": "runs/<run-id>/", "description": "远端运行中的活动产物按运行编号进入 runs 目录。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行产物。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端活动运行目录规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "remote_run_artifact_backup_layout": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "backups/runs/<run-id>/", "value": "backups/runs/<run-id>/", "description": "验证完成后的远端运行产物归档到 backups/runs。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行归档。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端运行归档目录规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "remote_run_archive_trigger": [  # QUESTION OPTIONS 用于本步治理判断
        {
            "label": "after required verification passes",  # 交互选项字段
            "value": "after required verification passes",  # 交互选项字段
            "description": "该仓库要求的验证门禁通过后，活动运行目录必须归档。",  # 交互选项字段
            "recommended": True,  # 交互选项字段
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行归档触发时机。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端归档触发规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "alignment_confirmed": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "是，理解一致", "value": True, "description": "允许写入强控制档案。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "否，需要修正", "value": False, "description": "继续修正并重新确认。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "default_conversation_language": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "中文", "value": "中文", "description": "默认后续对话使用中文。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "English", "value": "English", "description": "默认后续对话使用英文。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他默认语言。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    USE_REMOTE_SERVER_KEY: [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "不使用远程", "value": False, "description": "本次 AGENTS 生成不锁定远程服务器，未来如需远程验证必须先更新 AGENTS。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "使用远程", "value": True, "description": "本次必须完成 erie-remote-ssh 依赖检查、服务器配置/选择、校验和锁定。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "memory_enabled": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "启用记忆", "value": True, "description": "创建 `docs/memory/`，保存可审计摘要和可查询索引。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "关闭记忆", "value": False, "description": "仅保留 handoff 和 AGENTS 指针，不写入记忆库。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "memory_storage_backend": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "sqlite-plus-jsonl", "value": "sqlite-plus-jsonl", "description": "SQLite 查询索引 + JSONL 追加事件 + Markdown 压缩摘要。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "memory_capture_scope": [  # QUESTION OPTIONS 用于本步治理判断
        {  # QUESTION OPTIONS 用于本步治理判断
            "label": "默认长期范围",  # QUESTION OPTIONS 用于本步治理判断
            "value": "handoff summaries, user-confirmed project preferences, durable decisions, validation lessons, and release lessons",  # QUESTION OPTIONS 用于本步治理判断
            "description": "保存交接摘要、用户确认偏好、长期决策、验证和发布教训。",  # QUESTION OPTIONS 用于本步治理判断
            "recommended": True,  # QUESTION OPTIONS 用于本步治理判断
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "仅 handoff 摘要", "value": "handoff summaries only", "description": "降低长期记忆写入范围。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入更具体的捕获范围。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "memory_read_policy": [  # QUESTION OPTIONS 用于本步治理判断
        {  # QUESTION OPTIONS 用于本步治理判断
            "label": "handoff + 相关摘要",  # QUESTION OPTIONS 用于本步治理判断
            "value": "read latest handoff plus relevant docs/memory summaries before implementation",  # QUESTION OPTIONS 用于本步治理判断
            "description": "每次任务开始读取最新 handoff，并按任务查询相关记忆摘要。",  # QUESTION OPTIONS 用于本步治理判断
            "recommended": True,  # QUESTION OPTIONS 用于本步治理判断
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "仅恢复时读取", "value": "read memory during resume or takeover only", "description": "减少日常上下文加载。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入读取策略。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "memory_sensitivity_policy": [  # QUESTION OPTIONS 用于本步治理判断
        {  # QUESTION OPTIONS 用于本步治理判断
            "label": "不存敏感原文",  # QUESTION OPTIONS 用于本步治理判断
            "value": "do not store secrets, credentials, or raw local private paths",  # QUESTION OPTIONS 用于本步治理判断
            "description": "禁止保存 secrets、凭据、本地私密路径原文。",  # QUESTION OPTIONS 用于本步治理判断
            "recommended": True,  # QUESTION OPTIONS 用于本步治理判断
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "仅占位摘要", "value": "store only redacted placeholders for sensitive facts", "description": "敏感事实只允许以脱敏占位符描述。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入敏感信息边界。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "skill_design_patterns": [  # QUESTION OPTIONS 用于本步治理判断
        {
            "label": "五模式组合",  # 交互选项字段
            "value": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],  # 交互选项字段
            "description": "脚本、模板、审查、反问和流水线都启用。",  # 交互选项字段
            "recommended": True,  # 交互选项字段
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "生成器为主", "value": ["Tool Wrapper", "Generator"], "description": "强调稳定输出和可执行脚本。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "审查器为主", "value": ["Reviewer", "Pipeline"], "description": "强调验证、审查和顺序门禁。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "validation_method": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "自动化 + 人工验收", "value": "automated scripts plus user review", "description": "脚本验证后由用户确认结果是否符合预期。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "仅自动化", "value": "automated scripts", "description": "以测试、审计、evaluate 链为准。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "前向测试", "value": "forward testing", "description": "用真实任务或新 fixture 验证行为。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "validation_granularity": [  # QUESTION OPTIONS 用于本步治理判断
        {
            "label": "完整验证链",  # 交互选项字段
            "value": "unit tests, AGENTS verification, skill audit, full evaluate chain",  # 交互选项字段
            "description": "覆盖单测、AGENTS 校验、skill audit 和 evaluate。",  # 交互选项字段
            "recommended": True,  # 交互选项字段
        },  # QUESTION OPTIONS 用于本步治理判断
        {"label": "最小相关验证", "value": "narrow tests plus changed-script verification", "description": "只运行与改动相关的最小验证。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "engineering_rule_primary": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "不启用规则集", "value": "none", "description": "不启用书籍化工程规则集。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "refactoring", "value": "refactoring", "description": "适合重构和设计整洁性。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "legacy-code", "value": "working-effectively-with-legacy-code", "description": "适合遗留工程改造。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "release-it", "value": "release-it", "description": "适合发布可靠性和交付纪律。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "engineering_rule_mode": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "none", "value": "none", "description": "不启用规则集模式。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "mini", "value": "mini", "description": "保留关键决策规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "nano", "value": "nano", "description": "保留最小常驻规则。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
    "engineering_rule_scope": [  # QUESTION OPTIONS 用于本步治理判断
        {"label": "on-demand", "value": "on-demand", "description": "按需启用规则集。", "recommended": True},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "project-baseline", "value": "project-baseline", "description": "对整个工程提供基线约束。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
        {"label": "scoped", "value": "scoped", "description": "仅作用于特定目录或场景。", "recommended": False},  # QUESTION OPTIONS 用于本步治理判断
    ],  # QUESTION OPTIONS 用于本步治理判断
}

# 保留 QUESTION MAP 中间值，支撑 模块入口 的当前计算步骤。
QUESTION_MAP: dict[str, dict[str, Any]] = {}  # QUESTION MAP 用于本步治理判断

# 逐项推进 模块入口 的候选项检查。
for item in COMMON_QUESTIONS:

    # 保留 中间载荷 中间值，支撑 模块入口 的当前计算步骤。
    QUESTION_MAP[item["question_id"]] = item  # 中间载荷 用于本步治理判断

# 逐项推进 模块入口 的候选项检查。
for qid, key, ask in SKILL_QUESTIONS + ENGINEERING_QUESTIONS + DIRECTORY_QUESTIONS + MEMORY_QUESTIONS + EXISTING_WORK_QUESTIONS:

    # 保留 branch 中间值，支撑 模块入口 的当前计算步骤。
    branch = "skill" if (qid, key, ask) in SKILL_QUESTIONS else "engineering" if (qid, key, ask) in ENGINEERING_QUESTIONS else "all"  # branch 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 模块入口 的当前计算步骤。
    QUESTION_MAP[qid] = {  # 中间载荷 用于本步治理判断
        "question_id": qid,  # 中间载荷 用于本步治理判断
        "answer_key": key,  # 中间载荷 用于本步治理判断
        "required": True,  # 中间载荷 用于本步治理判断
        "branch": branch,  # 中间载荷 用于本步治理判断
        "ask": ask,  # 中间载荷 用于本步治理判断
    }




# 定义 now_iso 的脚本治理处理入口。
def now_iso() -> str:

    # 返回 now_iso 已整理完成的调用载荷。
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# 定义 default_options 的脚本治理处理入口。
def default_options(answer_key: str) -> list[dict[str, Any]]:

    # 返回 default_options 已整理完成的调用载荷。
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

# 定义 with_options 的脚本治理处理入口。
def with_options(item: dict[str, Any]) -> dict[str, Any]:

    # 保留 row 中间值，支撑 with_options 的当前计算步骤。
    dict_row = dict(item)  # row 用于本步治理判断

    # 调用 setdefault 完成 with_options 的当前动作。
    dict_row.setdefault("options", QUESTION_OPTIONS.get(str(dict_row.get("answer_key", "")), default_options(str(dict_row.get("answer_key", "")))))

    # 返回 with_options 已整理完成的调用载荷。
    return dict_row

# 定义 groups_for 的脚本治理处理入口。
def groups_for(kind: str) -> list[list[str]]:

    # 检查 groups_for 的当前条件是否需要进入专门分支。
    if kind == "skill":

        # 返回 groups_for 已整理完成的调用载荷。
        return COMMON_GROUPS + SKILL_GROUPS

    # 检查 groups_for 的当前条件是否需要进入专门分支。
    if kind == "engineering":

        # 返回 groups_for 已整理完成的调用载荷。
        return COMMON_GROUPS + ENGINEERING_GROUPS

    # 抛出 groups_for 已确认的阻断原因。
    raise ValueError(f"unknown kind: {kind}")

# 定义 takeover_groups_for 的脚本治理处理入口。
def takeover_groups_for(kind: str) -> list[list[str]]:

    # 检查 takeover_groups_for 的当前条件是否需要进入专门分支。
    if kind == "skill":

        # 返回 takeover_groups_for 已整理完成的调用载荷。
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_SKILL_GROUPS

    # 检查 takeover_groups_for 的当前条件是否需要进入专门分支。
    if kind == "engineering":

        # 返回 takeover_groups_for 已整理完成的调用载荷。
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_ENGINEERING_GROUPS

    # 抛出 takeover_groups_for 已确认的阻断原因。
    raise ValueError(f"unknown kind for takeover: {kind}")

# 定义 questions_for 的脚本治理处理入口。
def questions_for(kind: str) -> list[dict[str, Any]]:

    # 返回 questions_for 已整理完成的调用载荷。
    return [with_options(QUESTION_MAP[qid]) for group in groups_for(kind) for qid in group]

# 定义 question_ids_to_keys 的脚本治理处理入口。
def question_ids_to_keys(question_ids: list[str]) -> list[str]:

    # 返回 question_ids_to_keys 已整理完成的调用载荷。
    return [str(QUESTION_MAP[qid]["answer_key"]) for qid in question_ids]

# 定义 question_rows 的脚本治理处理入口。
def question_rows(question_ids: list[str]) -> list[dict[str, Any]]:

    # 返回 question_rows 已整理完成的调用载荷。
    return [with_options(QUESTION_MAP[qid]) for qid in question_ids]


# 定义 read_json_object 的脚本治理处理入口。
def read_json_object(path: Path) -> dict[str, Any]:

    # 保护 read_json_object 中允许失败的外部访问。
    try:

        # 保留 data 中间值，支撑 read_json_object 的当前计算步骤。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # data 用于本步治理判断
    except Exception as exc:

        # 抛出 read_json_object 已确认的阻断原因。
        raise SystemExit(json.dumps({"errors": [f"could not read answers: {exc}"]}, indent=2))

    # 检查 read_json_object 的当前条件是否需要进入专门分支。
    if not isinstance(dict_data, dict):

        # 抛出 read_json_object 已确认的阻断原因。
        raise SystemExit(json.dumps({"errors": ["answers must be a JSON object"]}, indent=2))

    # 返回 read_json_object 已整理完成的调用载荷。
    return dict_data


# 定义 empty 的脚本治理处理入口。
def empty(value: Any) -> bool:

    # 返回 empty 已整理完成的调用载荷。
    return value is None or value == "" or value == []


# 定义 normalize_extra_requirements 的脚本治理处理入口。
def normalize_extra_requirements(raw_value: Any) -> str:

    # 检查 normalize_extra_requirements 的当前条件是否需要进入专门分支。
    if isinstance(raw_value, list):

        # 收集 parts 条目，保持 normalize_extra_requirements 的处理顺序稳定。
        parts = [str(item).strip() for item in raw_value if str(item).strip()]  # parts 用于本步治理判断

        # 保留 value 中间值，支撑 normalize_extra_requirements 的当前计算步骤。
        raw_value = "; ".join(parts)  # value 用于本步治理判断

    # 保留 normalized 中间值，支撑 normalize_extra_requirements 的当前计算步骤。
    normalized = str(raw_value if raw_value is not None else "").strip()  # normalized 用于本步治理判断

    # 返回 normalize_extra_requirements 已整理完成的调用载荷。
    return "none" if normalized.casefold() in NO_EXTRA_REQUIREMENTS else normalized


# 定义 remote_directory_configured 的脚本治理处理入口。
def remote_directory_configured(raw: Any) -> bool:

    # 保留 value 中间值，支撑 remote_directory_configured 的当前计算步骤。
    raw_value = str(raw).strip()  # value 用于本步治理判断

    # 检查 remote_directory_configured 的当前条件是否需要进入专门分支。
    if not raw_value:

        # 返回 remote_directory_configured 已整理完成的调用载荷。
        return False

    # 保留 lowered 中间值，支撑 remote_directory_configured 的当前计算步骤。
    lowered = raw_value.lower()  # lowered 用于本步治理判断

    # 检查 remote_directory_configured 的当前条件是否需要进入专门分支。
    if lowered in {"none", "not configured", "disabled"}:

        # 返回 remote_directory_configured 已整理完成的调用载荷。
        return False

    # 检查 remote_directory_configured 的当前条件是否需要进入专门分支。
    if "no remote workspace is configured" in lowered:

        # 返回 remote_directory_configured 已整理完成的调用载荷。
        return False

    # 返回 remote_directory_configured 已整理完成的调用载荷。
    return True


# 定义 remote_directory_policy_required 的脚本治理处理入口。
def remote_directory_policy_required(answers: dict[str, Any] | None) -> bool:

    # 收集 answers 条目，保持 remote_directory_policy_required 的处理顺序稳定。
    answers = answers or {}  # answers 用于本步治理判断

    # 返回 remote_directory_policy_required 已整理完成的调用载荷。
    return bool(answers.get(USE_REMOTE_SERVER_KEY) is True or remote_directory_configured(answers.get("remote_directory_structure", "")))


