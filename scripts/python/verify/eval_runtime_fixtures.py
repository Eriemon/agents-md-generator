"""构造 agents-md-generator 回归评估所需的项目夹具。"""

# 延迟注解求值以兼容 Python 3.10。
from __future__ import annotations

# 哈希、动态导入和序列化服务评估夹具的数据流。
import hashlib
import importlib.util
import json
import os

# 文件复制、子进程和类型标注支撑隔离项目的生成。
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# 模块路径常量用于定位 owner 仓库内的任务脚本。
RUNTIME_DIR = Path(__file__).resolve().parent  # verify 任务目录

# Python 任务根目录包含 design、render、release 等职责目录。
SCRIPTS_PYTHON_DIR = RUNTIME_DIR.parent  # Python 任务分类根

# 评估夹具默认从技能 scripts 根目录发现实现文件。
SCRIPTS_DIR = SCRIPTS_PYTHON_DIR.parent  # 脚本资源根

# 技能根用于需要读取正式资源的评估场景。
SKILL_DIR = SCRIPTS_DIR.parent  # 正式技能根

# 子进程统一从评估启动时的仓库根执行。
REPO_ROOT = Path.cwd().resolve()  # 当前评估仓库根

# 夹具类集中维护跨评估复用的稳定测试事实。
class EvalFixtures:
    """集中生成评估脚本复用的项目答案、文件树和命令夹具。"""

    # 初始化可覆盖的脚本发现位置。
    def __init__(self, scripts_dir: Path | None = None) -> None:
        """初始化评估夹具的脚本发现根。

        参数：scripts_dir 为可选技能 scripts 目录覆盖。
        返回：无业务返回值，保存后续模块与命令定位上下文。
        """

        # 显式覆盖服务隔离测试，缺省值指向 owner 技能脚本根。
        self.scripts_dir = Path(scripts_dir) if scripts_dir is not None else SCRIPTS_DIR  # 脚本发现根

    # 构造远程目录治理答案。
    def remote_directory_answers(
        self,
        remote_directory_structure: str = "remote/workspace/demo-skill",
        include_remote_policy: bool = True,
    ) -> dict[str, Any]:
        """生成远程目录治理场景使用的访谈答案。

        参数：remote_directory_structure 为远程布局；include_remote_policy 控制运行策略字段。
        返回：可直接合并到设计访谈答案的目录合同映射。
        """

        # 基础目录合同覆盖本地、远程、功能放置和确认状态。
        dict_answers: dict[str, Any] = {  # 远程目录治理答案
            "local_directory_structure": "engineering/demo-skill/, tests/, dist/",  # 本地工程布局
            "remote_directory_structure": remote_directory_structure,  # 调用方指定的远程布局
            "feature_directory_rules": "features in src/features/<name>/ with tests nearby",  # 功能目录规则
            "directory_contract_confirmed": True,  # 模拟用户确认目录合同
        }

        # 启用远程策略时补齐环境、运行产物和归档约束。
        if include_remote_policy:

            # 四个字段共同构成可写入的远程运行合同。
            dict_answers.update(
                {
                    "remote_conda_environment_layout": ".conda/<env-name>/",  # 隔离环境相对路径
                    "remote_run_artifact_active_layout": "runs/<run-id>/",  # 活跃运行产物路径
                    "remote_run_artifact_backup_layout": "backups/runs/<run-id>/",  # 归档备份路径
                    "remote_run_archive_trigger": "after required verification passes",  # 验证通过后归档
                }
            )

        # 返回答案供 skill 或 engineering 画像继续扩展。
        return dict_answers

    # 构造技能项目完整治理答案。
    def skill_answers(
        self,
        name: str = "demo-skill",
        remote_directory_structure: str = "not configured",
        include_remote_policy: bool = False,
        use_remote_server: bool = False,
    ) -> dict[str, Any]:
        """生成 skill 项目治理场景的完整访谈答案。

        参数：name 为技能名。
        参数：remote_directory_structure 为远程目录布局。
        参数：include_remote_policy 控制是否补齐远程运行策略。
        参数：use_remote_server 表示是否启用服务器。
        返回：满足强控制写入门禁的完整技能访谈答案。
        """

        # 固定答案覆盖技能设计、内存、发布和强控制门禁。
        dict_answers: dict[str, Any] = {  # 技能设计访谈完整答案
            "development_type": "skill",  # 项目开发类型
            "default_conversation_language": "\u4e2d\u6587",  # 默认交互语言
            "use_remote_server": use_remote_server,  # 是否使用远程服务器
            "use_codebase_memory_mcp": False,  # 评估夹具明确禁用代码知识图谱
            "memory_enabled": True,  # 启用项目长期记忆
            "memory_storage_backend": "sqlite-plus-jsonl",  # 记忆存储后端
            "memory_capture_scope": (  # 长期记忆捕获范围
                "handoff summaries, user-confirmed project preferences, durable decisions, "
                "validation lessons, and release lessons"
            ),
            "memory_read_policy": "read latest handoff plus relevant docs/memory summaries before implementation",  # 记忆读取策略
            "memory_sensitivity_policy": "do not store secrets, credentials, or raw local private paths",  # 敏感信息策略
            "skill_purpose": "Create verified AGENTS.md files.",  # 技能用途
            "skill_reason": "Keep agent onboarding deterministic.",  # 创建原因
            "development_requirements": "Collect facts and render AGENTS.md with strict design-review gates.",  # 开发要求
            "expected_outcome": "Verified AGENTS.md guidance exists.",  # 预期结果
            "validation_method": "automated scripts plus user review",  # 验证方式
            "validation_granularity": "unit tests, AGENTS verification, skill audit, full evaluate chain",  # 验证粒度
            "reference_materials": ["none"],  # 参考材料
            "audience": "maintainers",  # 目标受众
            "name": name,  # 技能名称
            "design_notes": "Keep SKILL.md concise.",  # 设计说明
            "trigger_scenarios": "Use when a repo needs AGENTS.md generation or review.",  # 触发场景
            "skill_design_patterns": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],  # 设计模式
            "resource_plan": "scripts/ for deterministic checks, references/ for policy, assets/ for templates",  # 资源规划
            "progressive_disclosure_policy": "Keep SKILL.md lean and move detailed policy to references.",  # 渐进披露策略
            "validation_gates": "quick_validate.py, audit_skill.py, verify_agents.py, evaluate_skill.py",  # 验证门禁
            "forward_testing_policy": "Forward-test complex workflows.",  # 前向测试策略
            "git_management": "yes-local-only",  # Git 管理模式
            "branch_model": "master-and-dist-release",  # 分支模型
            "release_contract": f"dist/{name}-vx.x.x plus zip",  # 发布合同
            "has_existing_work": "yes",  # 已有工作状态
            "alignment_confirmed": True,  # 对齐确认状态
        }

        # 目录合同由公共构造器提供，避免远程字段场景漂移。
        dict_answers.update(
            self.remote_directory_answers(
                remote_directory_structure=remote_directory_structure,
                include_remote_policy=include_remote_policy,
            )
        )

        # skill 项目覆盖工程默认布局，限定正式技能目录。
        dict_answers["local_directory_structure"] = f"skills/{name}/, tests/, dist/"  # 技能仓库本地布局

        # 技能功能实现和详细政策分别落在 scripts 与 references。
        dict_answers["feature_directory_rules"] = "scripts in scripts/, detailed policy in references/"  # 技能资源放置规则

        # 返回可直接进入设计审查的答案快照。
        return dict_answers

    # 从文件路径动态加载待测脚本模块。
    def load_script_module(self, name: str) -> Any:
        """按文件名从当前脚本目录加载待测模块。

        参数：name 为目标 Python 脚本文件名。
        返回：执行完成且可供测试调用的模块对象。
        异常：文件无法形成 import spec 时抛出带 Python 前缀的 RuntimeError。
        """

        # spec 同时记录目标路径和后续模块加载器。
        module_spec = importlib.util.spec_from_file_location(name, self.script_path(name))  # 待测模块导入规范

        # 缺失加载器意味着脚本路径不能作为模块执行。
        if module_spec is None or module_spec.loader is None:

            # 明确报告无法加载的脚本名。
            raise RuntimeError(f"> ERR: [Python] unable to load script module: {name}")

        # 根据规范创建独立模块对象，避免污染正式包导入路径。
        module_object = importlib.util.module_from_spec(module_spec)  # 隔离加载的待测模块

        # 执行目标源码以填充模块命名空间。
        module_spec.loader.exec_module(module_object)

        # 返回模块供评估用例调用公开函数。
        return module_object

    # 解析脚本名称对应的正式文件路径。
    def script_path(self, name: str) -> Path:
        """按脚本文件名解析任务分类后的运行时路径。

        参数：name 为目标脚本文件名。
        返回：优先返回 scripts/python 任务目录内的匹配文件，否则返回旧布局路径。
        """

        # 任务目录匹配结果按路径排序以保持确定性。
        list_candidates = sorted((self.scripts_dir / "python").glob(f"*/{name}"))  # 新布局脚本候选

        # 首个任务目录候选优先，空集合时兼容旧 scripts 根布局。
        return list_candidates[0] if list_candidates else self.scripts_dir / name

    # 为答案附加与内容哈希绑定的批准审查。
    def add_approved_design_review(
        self,
        project: Path,
        answers: dict[str, Any],
        reviewer_type: str = "subagent",
        verdict: str = "approve",
        required_user_confirmations: list[Any] | None = None,
        hash_override: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """为答案快照附加可通过写入门禁的设计审查。

        参数：project 为项目根。
        参数：answers 为答案。
        参数：reviewer_type 为审查者类型。
        参数：verdict 为审查结论。
        参数：required_user_confirmations 为待确认事项。
        参数：hash_override 为故障注入使用的哈希覆盖。
        返回：包含 extra_requirements 与 design_review 的独立答案副本。
        """

        # 副本防止评估构造过程修改调用方共享答案。
        dict_reviewed_answers = dict(answers)  # 待附加审查的答案快照

        # 无补充需求是完整访谈必须显式记录的状态。
        dict_reviewed_answers.setdefault("extra_requirements", "none")

        # 正式审查模块提供与生产写入路径相同的摘要哈希。
        module_review_gate = self.load_script_module("design_review_gate.py")  # 设计审查门禁模块

        # 两个哈希绑定完整答案与最终画像预览。
        dict_review_hashes = module_review_gate.design_review_hashes(project, dict_reviewed_answers)  # 审查对象哈希

        # 篡改场景可覆盖指定哈希以验证拒绝逻辑。
        if hash_override:

            # 仅更新调用方给出的哈希字段。
            dict_review_hashes.update(hash_override)

        # 审查区块模拟 production 设计审查的稳定字段合同。
        dict_reviewed_answers["design_review"] = {  # 写入门禁读取的设计审查证据
            "reviewer_type": reviewer_type,  # 审查者必须可配置为 subagent
            "verdict": verdict,  # approve 或拒绝结论
            "findings": [] if verdict == "approve" else ["design gap requires correction"],  # 拒绝场景发现项
            "required_user_confirmations": required_user_confirmations or [],  # 待用户确认事项
            "reviewed_answers_hash": dict_review_hashes["reviewed_answers_hash"],  # 已审答案摘要
            "reviewed_profile_hash": dict_review_hashes["reviewed_profile_hash"],  # 已审画像摘要
            "review_summary": "Subagent reviewed the complete design profile and approved the plan.",  # 固定审查摘要
        }

        # 返回独立快照供写入或故障注入场景使用。
        return dict_reviewed_answers

    # 写入带批准审查证据的答案文件。
    def write_reviewed_answers(
        self,
        project: Path,
        path: Path,
        answers: dict[str, Any],
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """补齐显式治理字段、附加审查并写入答案文件。

        参数：project 为项目根；path 为输出 JSON；answers 为基础答案；env 为临时环境覆盖。
        返回：实际写入文件的已审答案映射。
        异常：审查构造或文件写入异常原样向上传播，并保证环境恢复。
        """

        # 副本承载缺省字段，避免修改测试共享输入。
        dict_explicit_answers = dict(answers)  # 即将进入审查的显式答案

        # 未声明远程服务器时明确记录禁用状态。
        dict_explicit_answers.setdefault("use_remote_server", False)

        # 正式评估夹具必须显式覆盖知识图谱选择，不能依赖生产默认值。
        dict_explicit_answers.setdefault("use_codebase_memory_mcp", False)

        # 评估项目默认启用长期记忆治理。
        dict_explicit_answers.setdefault("memory_enabled", True)

        # SQLite 与 JSONL 双存储匹配 owner 仓库默认合同。
        dict_explicit_answers.setdefault("memory_storage_backend", "sqlite-plus-jsonl")

        # 捕获范围限定为长期有价值且经过治理的信息。
        dict_explicit_answers.setdefault(
            "memory_capture_scope",
            "handoff summaries, user-confirmed project preferences, durable decisions, "
            "validation lessons, and release lessons",
        )

        # 读取策略要求实现前先恢复最近交接和相关摘要。
        dict_explicit_answers.setdefault(
            "memory_read_policy",
            "read latest handoff plus relevant docs/memory summaries before implementation",
        )

        # 敏感策略禁止凭据和原始本地私有路径进入记忆。
        dict_explicit_answers.setdefault(
            "memory_sensitivity_policy",
            "do not store secrets, credentials, or raw local private paths",
        )

        # 记录被覆盖变量的原值，确保夹具没有跨测试副作用。
        dict_old_environment = {key: os.environ.get(key) for key in (env or {})}  # 环境变量恢复快照

        # 临时环境只覆盖设计审查构造阶段。
        try:

            # 非空覆盖映射才修改当前进程环境。
            if env:

                # 环境覆盖用于测试安装目录等外部事实。
                os.environ.update(env)

            # 生成与当前显式答案哈希匹配的批准审查。
            dict_reviewed_answers = self.add_approved_design_review(project, dict_explicit_answers)  # 最终已审答案

        # 无论审查是否成功都恢复进入方法前的环境。
        finally:

            # 逐个恢复变量，区分原先缺失和原先有值。
            for str_key, str_value in dict_old_environment.items():

                # 原先不存在的变量应从环境中删除。
                if str_value is None:

                    # pop 的缺省值处理覆盖代码未创建变量的边界。
                    os.environ.pop(str_key, None)

                # 原先存在的变量恢复其精确文本值。
                else:

                    # 恢复值防止后续评估观察到本场景覆盖。
                    os.environ[str_key] = str_value  # 恢复进入夹具前的环境值

        # 紧凑 JSON 足以作为生产设计写入命令的输入。
        path.write_text(json.dumps(dict_reviewed_answers), encoding="utf-8")

        # 返回写入内容供测试继续检查或修改。
        return dict_reviewed_answers

    # 创建隔离的已安装技能版本夹具。
    def make_installed_skill_fixture(self, root: Path, version: str = "v0.4.3") -> Path:
        """创建最小已安装 agents-md-generator 技能副本。

        参数：root 为夹具根目录；version 为安装副本版本。
        返回：包含 SKILL.md 和 VERSION 的已安装技能目录。
        """

        # 安装路径遵循 Codex home 下的标准 skills 布局。
        path_installed_skill = root / "codex-home" / "skills" / "agents-md-generator"  # 已安装技能目录

        # 父目录由夹具独立创建，不依赖调用方预置结构。
        path_installed_skill.mkdir(parents=True)

        # 最小技能入口提供名称和可触发描述。
        (path_installed_skill / "SKILL.md").write_text(
            "---\nname: agents-md-generator\ndescription: Use when testing installed version\n---\n# Skill\n",
            encoding="utf-8",
        )

        # 独立版本文件支持源码与安装副本一致性检查。
        (path_installed_skill / "VERSION").write_text(version + "\n", encoding="utf-8")

        # 返回安装目录供渲染命令环境变量引用。
        return path_installed_skill

    # 写入发布流程识别所需的最小治理画像。
    def write_release_governance_profile(
        self,
        root: Path,
        kind: str = "skill",
        name: str = "agents-md-generator",
    ) -> None:
        """写入发布与目录治理测试使用的控制画像。

        参数：root 为项目根；kind 为 skill 或 engineering；name 为项目名称。
        返回：无业务返回值，写入 .agents/agents-control.json。
        """

        # 控制画像固定落在项目根的 .agents 目录。
        (root / ".agents").mkdir(exist_ok=True)

        # 项目类型决定正式源码的主目录前缀。
        str_primary_root = f"skills/{name}" if kind == "skill" else f"engineering/{name}"  # 主要项目根相对路径

        # 发布合同对 skill 启用净化，对 engineering 保持不适用。
        bool_skill_project = kind == "skill"  # 是否需要技能发布净化

        # 控制画像覆盖分支、目录和发布三个门禁域。
        dict_control_profile = {  # 发布治理控制画像
            "schema_version": 1,  # 控制画像 schema 版本
            "kind": kind,  # 控制画像项目类型
            "name": name,  # 被治理项目名称
            "git_management": "yes-local-only",  # 仅允许本地 Git 管理
            "branch_model": "master-and-dist-release",  # 主分支和发布分支模型
            "git_branch_policy": {  # 分支保护与发布准备路径
                "protected_branches": ["master", "release"],  # 禁止直接开发的分支
                "development_branches_allowed": True,  # 允许本地开发分支
                "release_prepare_allowed_paths": [  # 发布准备可修改路径
                    f"skills/{name}",  # 正式技能源码目录
                    "tests",  # 回归测试目录
                    "docs",  # 治理文档目录
                    ".agents",  # 控制画像目录
                    "AGENTS.md",  # 根级代理规则
                    "dist",  # 版本发布目录
                ],
            },
            "directory_contract": {  # 本地项目放置合同
                "confirmed": True,  # 模拟用户确认目录规则
                "local": f"{str_primary_root}/, tests/, dist/",  # 本地目录摘要
                "remote": "not configured",  # 夹具不启用远程目录
                "features": "features stay inside the governed project root",  # 功能留在项目根内
                "primary_project_root": str_primary_root,  # 正式源码根
                "feature_directory_rules": "keep new work inside the primary project root",  # 新功能放置规则
            },
            "release_contract": {  # 版本化发布与安装合同
                "current_version": "v0.4.4",  # 控制画像当前版本
                "protected_branches": ["master", "release"],  # 发布相关保护分支
                "dist_pattern": f"dist/{name}-vx.x.x",  # 版本发布目录模式
                "zip_required": True,  # 要求生成对应归档
                "receipt_file": "RELEASE_RECEIPT.json",  # 安装验证收据名
                "install_source_policy": "versioned-dist-release-only",  # 禁止源码目录安装
                "repo_install_validation_level": "strong",  # owner 仓库安装强验证
                "external_install_validation_level": "reduced_assurance",  # 外部副本降低保证
                "sanitization_required": bool_skill_project,  # skill 发布必须净化
                "sanitization_scope": "broad" if bool_skill_project else "not-applicable",  # 净化覆盖范围
                "sanitization_mode": "auto-redact-dist-copy" if bool_skill_project else "disabled",  # 净化执行模式
                "sanitization_receipt_required": bool_skill_project,  # skill 收据记录净化证据
            },
        }

        # JSON 使用稳定缩进，便于门禁读取和测试诊断。
        str_control_json = json.dumps(dict_control_profile, indent=2)  # 控制画像 JSON 文本

        # 将完整控制画像写入项目治理目录。
        (root / ".agents" / "agents-control.json").write_text(str_control_json, encoding="utf-8")

    # 创建具备发布治理事实的最小技能项目。
    def make_governed_skill_project(
        self,
        root: Path,
        name: str = "agents-md-generator",
        version: str = "v0.4.3",
    ) -> Path:
        """创建具备发布治理资料的最小 skill 项目。

        参数：root 为项目根；name 为技能名；version 为源码技能版本。
        返回：已创建的技能源码目录。
        """

        # skill 源码必须位于 skills/<name> 正式目录。
        path_skill = root / "skills" / name  # 技能源码根

        # 递归创建技能根以支持空临时项目。
        path_skill.mkdir(parents=True)

        # 受管工作区夹具默认满足唯一根 tests 目录合同。
        (root / "tests").mkdir(exist_ok=True)

        # scripts 存放可执行验证入口。
        (path_skill / "scripts").mkdir(exist_ok=True)

        # references 存放评审和覆盖说明。
        (path_skill / "references").mkdir(exist_ok=True)

        # 技能入口 frontmatter 保持名称与目录一致。
        (path_skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Use when testing\n---\n# Skill\n",
            encoding="utf-8",
        )

        # 版本文件作为发布准备的源码事实。
        (path_skill / "VERSION").write_text(version + "\n", encoding="utf-8")

        # 公开文档夹具复用正式双语用户流程，避免评估包退化为内部最小样例。
        self.write_public_package_contract(path_skill, name=name, version=version)

        # 验证脚本保留历史 skill-creator 路径以触发迁移检查。
        str_legacy_validator = (
            "from pathlib import Path\n\n\ndef quick_validate_path() -> Path:\n"
            "    return Path.home() / '.codex' / 'skills' / '.system' / "
            "'skill-creator' / 'scripts' / 'quick_validate.py'\n"
        )  # 旧路径迁移验证脚本正文

        # 脚本内容刻意保留旧路径以供迁移门禁识别。
        (path_skill / "scripts" / "quick_validate.py").write_text(
            str_legacy_validator,
            encoding="utf-8",
        )

        # 两份参考文档共享正式验证命令文本。
        str_quick_validate_command = (
            f"python skills/{name}/scripts/python/verify/quick_validate.py "
            f"skills/{name}"
        )  # 快速验证命令

        # 评审清单声明结构门禁的必要证据。
        (path_skill / "references" / "review-checklist.md").write_text(
            "\n".join(
                [
                    "# Review Checklist",
                    "",
                    "| Gate | Required evidence |",
                    "|------|-------------------|",
                    f"| Structure | `{str_quick_validate_command}` passes for this skill |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        # 设计覆盖文档列出完整验证链。
        (path_skill / "references" / "skill-design-coverage.md").write_text(
            "\n".join(
                [
                    "# Skill Design Coverage",
                    "",
                    "- Validation gates include "
                    f"`{str_quick_validate_command}`, skill audit, AGENTS.md verification, "
                    "and the full evaluate chain.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        # 项目级 docs 目录用于发布治理变更事实。
        (root / "docs").mkdir(exist_ok=True)

        # 最小文档内容保证 Git 仓库具有治理资料。
        (root / "docs" / "note.md").write_text("release governance\n", encoding="utf-8")

        # 控制画像使项目通过目录和发布合同识别。
        self.write_release_governance_profile(root, kind="skill", name=name)

        # 返回技能目录供调用方继续渲染或打包。
        return path_skill

    # 写入普通用户安装、调用、预览和交付所需的公开包资料。
    def write_public_package_contract(
        self,
        path_skill: Path,
        name: str,
        version: str,
    ) -> None:
        """把正式公开包合同写入临时技能目录。

        参数：path_skill 为技能根；name 为包名；version 为包版本。
        返回：无业务返回值，仅写入临时夹具文件和复用的 PNG 资产。
        异常：源资产或目标目录不可写时由文件系统异常直接报告。
        """

        # 版本数字同时写入 README、pyproject 和引用元数据，避免页面漂移。
        str_version_number = version.lstrip("vV")  # 不带 v 前缀的公开版本

        # 正式 README 文案已通过双语用户合同和归属合同，夹具只替换版本事实。
        str_readme_english = (  # 英文普通用户页面
            (SKILL_DIR / "README.md")  # 正式英文页面路径
            .read_text(encoding="utf-8")  # 读取正式英文页面
            .replace("v2.2.0", version)  # 将页面徽标版本同步到夹具版本
            .replace("2.2.0", str_version_number)  # 让引用元数据使用同一版本号
        )

        # 中文页面沿用同一版本替换策略，保持双语安装入口一致。
        str_readme_chinese = (  # 中文普通用户页面
            (SKILL_DIR / "README-CN.md")  # 正式中文页面路径
            .read_text(encoding="utf-8")  # 读取正式中文页面
            .replace("v2.2.0", version)  # 中文页面沿用夹具版本
            .replace("2.2.0", str_version_number)  # 中文引用同步裸版本号
        )

        # 英文页面落盘后由发布包继续读取。
        (path_skill / "README.md").write_text(str_readme_english, encoding="utf-8")

        # 中文页面落盘后与英文页面保持同一版本。
        (path_skill / "README-CN.md").write_text(str_readme_chinese, encoding="utf-8")

        # 公开包元数据使用当前临时技能名称和版本，避免复制所有者版本。
        str_pyproject = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "{str_version_number}"
description = "A Codex skill for repository instructions"
readme = "README.md"
requires-python = ">=3.10"
license = {{ file = "LICENSE" }}
"""  # 临时项目元数据文本

        # 元数据文件必须进入技能根，供发布工具检查名称与版本。
        (path_skill / "pyproject.toml").write_text(str_pyproject, encoding="utf-8")

        # 引用文件只记录当前夹具版本和公开仓库地址。
        str_citation = f"""cff-version: 1.2.0
title: "AGENTS.md Generator"
version: "{str_version_number}"
date-released: 2026-08-12
type: software
authors:
  - family-names: "Liu"
    given-names: "Jiyuan"
    affiliation: "Southeast University"
  - family-names: "Li"
    given-names: "He"
    affiliation: "Southeast University"
repository-code: "https://github.com/Eriemon/agents-md-generator"
url: "https://github.com/Eriemon/agents-md-generator"
license: "Apache-2.0"
"""  # 临时引用元数据文本

        # 引用文件随公开包分发，便于用户追踪版本来源。
        (path_skill / "CITATION.cff").write_text(str_citation, encoding="utf-8")

        # 许可正文直接复用正式 Apache 2.0 文件，避免夹具自造法律文本。
        shutil.copyfile(SKILL_DIR / "LICENSE", path_skill / "LICENSE")

        # 安全和贡献入口保持公开用户可读的最小说明。
        (path_skill / "SECURITY.md").write_text(
            "# Security\n\nReport vulnerabilities privately to the project maintainers.\n",
            encoding="utf-8",
        )

        # 贡献入口让公开包保留最小的协作说明。
        (path_skill / "CONTRIBUTING.md").write_text(
            "# Contributing\n\nDescribe the change and validation before opening a pull request.\n",
            encoding="utf-8",
        )

        # 双语 README 引用的本地 PNG 必须完整进入临时公开包。
        path_readme_assets = path_skill / "assets" / "readme"  # 临时 README 资源目录

        # 资源目录承载与页面逐一对应的本地 PNG 文件。
        path_readme_assets.mkdir(parents=True, exist_ok=True)

        # 资产名称保持与正式双语页面中的角色命名一致。
        tuple_asset_names = (
            "hero.png",  # 英文首屏图
            "hero-cn.png",  # 中文首屏图
            "project-facts.png",  # 英文事实图
            "project-facts-cn.png",  # 中文事实图
            "design-profile.png",  # 英文画像图
            "design-profile-cn.png",  # 中文画像图
            "rule-rendering.png",  # 英文规则图
            "rule-rendering-cn.png",  # 中文规则图
            "evidence-guard.png",  # 英文交付图
            "evidence-guard-cn.png",  # 中文交付图
        )

        # 按页面引用顺序复制资产，避免临时包出现缺图。
        for str_asset_name in tuple_asset_names:

            # 当前资产从正式技能目录复制到隔离夹具。
            shutil.copyfile(
                SKILL_DIR / "assets" / "readme" / str_asset_name,  # 正式资产来源
                path_readme_assets / str_asset_name,  # 临时包目标路径
            )

    # 初始化无需发布分支的基础 Git 仓库。
    def init_basic_git_repo(self, root: Path) -> None:
        """初始化仅含 master 分支的测试 Git 仓库。

        参数：root 为待初始化的临时项目根。
        返回：无业务返回值，Git 命令失败时由 subprocess 抛出异常。
        """

        # 显式指定 master，避免宿主机默认分支配置影响夹具。
        subprocess.run(
            ["git", "init", "-b", "master"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 固定作者名使测试提交不依赖全局 Git 配置。
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 无效域邮箱明确表示该身份只用于本地夹具。
        subprocess.run(
            ["git", "config", "user.email", "test-user.invalid"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    # 提交夹具仓库中的全部当前内容。
    def git_commit_all(self, root: Path, message: str, when: str | None = None) -> None:
        """提交临时仓库中的全部文件并可固定提交时间。

        参数：root 为仓库根；message 为提交说明；when 为可选 Git 时间文本。
        返回：无业务返回值，Git 命令失败时由 subprocess 抛出异常。
        """

        # 子进程环境副本允许注入时间且不修改当前测试进程。
        dict_git_environment = dict(os.environ)  # Git 提交命令环境

        # 指定时间时同时固定 author 和 committer，保证历史排序可复现。
        if when:

            # 作者时间用于历史事实和审计显示。
            dict_git_environment["GIT_AUTHOR_DATE"] = when  # 固定作者时间

            # 提交者时间防止宿主当前时间改变排序。
            dict_git_environment["GIT_COMMITTER_DATE"] = when  # 固定提交者时间

        # 夹具提交覆盖当前仓库的全部新增和修改内容。
        subprocess.run(
            ["git", "add", "."],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=dict_git_environment,
        )

        # 使用调用方消息创建单个可审计提交。
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=dict_git_environment,
        )

    # 初始化包含发布分支的受管 Git 仓库。
    def init_governed_git_repo(self, root: Path) -> None:
        """初始化包含 master 和 release 的受管 Git 仓库。

        参数：root 为已落盘治理项目根。
        返回：无业务返回值，最终保持 master 为当前分支。
        """

        # 基础仓库仍显式使用 master 主分支。
        subprocess.run(
            ["git", "init", "-b", "master"], cwd=root, check=True, capture_output=True, text=True
        )

        # 固定本地提交作者名，避免依赖用户配置。
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True
        )

        # 固定测试专用邮箱以完成提交身份配置。
        subprocess.run(
            ["git", "config", "user.email", "test-user.invalid"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 首次提交收录已生成的全部治理文件。
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)

        # 初始化提交为 release 分支创建提供共同基点。
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, text=True)

        # release 分支满足发布门禁要求的本地分支集合。
        subprocess.run(["git", "checkout", "-b", "release"], cwd=root, check=True, capture_output=True, text=True)

        # 评估从 master 开始，保持生产发布准备的入口状态。
        subprocess.run(["git", "checkout", "master"], cwd=root, check=True, capture_output=True, text=True)

    # 创建已渲染且带隔离安装副本的受管技能项目。
    def make_rendered_governed_skill_project(
        self,
        root: Path,
        name: str = "demo-skill",
        project_version: str = "v0.4.4",
        installed_version: str = "v0.4.3",
    ) -> tuple[Path, Path]:
        """创建完成设计写入、Git 初始化和 AGENTS 渲染的技能项目。

        参数：root 为项目根；name 为技能名；project_version 与 installed_version 控制版本差异。
        返回：技能源码目录和隔离的已安装技能目录。
        """

        # 首先落盘可被设计和发布流程识别的技能骨架。
        path_skill = self.make_governed_skill_project(root, name=name, version=project_version)  # 技能源码目录

        # 渲染前满足受管工作区唯一根 tests 目录契约。
        (root / "tests").mkdir(exist_ok=True)

        # 完整技能答案用于强控制设计写入。
        dict_answers = self.skill_answers(name=name)  # 技能设计访谈答案

        # 答案文件是 collect_design_profile 批处理入口输入。
        path_answers = root / "answers.json"  # 已审答案输出路径

        # 附加匹配哈希的 subagent 审查并写入答案。
        self.write_reviewed_answers(root, path_answers, dict_answers)

        # 正式设计写入命令生成根 AGENTS 和控制画像派生资产。
        subprocess.run(
            [
                sys.executable,
                str(self.script_path("collect_design_profile.py")),
                str(root),
                "--answers",
                str(path_answers),
                "--write",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        # 设计资产落盘后建立 master 与 release 的受管历史。
        self.init_governed_git_repo(root)

        # 隔离安装副本用于渲染版本对照，不修改用户真实 Codex home。
        path_installed_skill = self.make_installed_skill_fixture(  # 安装版本夹具目录
            root.parent / f"{root.name}-installed",  # 与项目并列的隔离夹具根
            version=installed_version,  # 调用方指定的安装版本
        )

        # 渲染器通过环境变量读取隔离安装副本。
        subprocess.run(
            [sys.executable, str(self.script_path("render_agents.py")), str(root), "--write"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ, AGENTS_MD_INSTALLED_SKILL_DIR=str(path_installed_skill)),
        )

        # 返回源码和安装目录供后续版本、治理和发布断言使用。
        return path_skill, path_installed_skill

    # 为发布目录生成内容完整性收据。
    def make_release_receipt(
        self,
        release_dir: Path,
        skill_name: str,
        version: str,
        validation_level: str = "reduced_assurance",
    ) -> None:
        """为现有发布目录生成可供安装器验证的最小收据。

        参数：release_dir 为发布目录；skill_name 与 version 标识技能；validation_level 控制来源保证级别。
        返回：无业务返回值，写入 RELEASE_RECEIPT.json。
        """

        # 文件表记录每个正式内容文件的相对路径和 SHA-256。
        list_receipt_files: list[dict[str, str]] = []  # 发布收据文件清单

        # 稳定排序保证收据在不同文件系统上可复现。
        for path_entry in sorted(release_dir.rglob("*")):

            # 收据本身不能进入自身哈希清单。
            if path_entry.is_file() and path_entry.name != "RELEASE_RECEIPT.json":

                # 每个条目提供安装器重算所需的路径和摘要。
                list_receipt_files.append(
                    {
                        "path": path_entry.relative_to(release_dir).as_posix(),  # 跨平台发布相对路径
                        "sha256": hashlib.sha256(path_entry.read_bytes()).hexdigest(),  # 文件内容摘要
                    }
                )

        # 强验证表示发布目录直接来自 owner 仓库流程。
        str_provenance_mode = "repository-dist" if validation_level == "strong" else "external-copy"  # 发布来源模式

        # 收据字段覆盖安装器的版本、来源、净化和文件完整性合同。
        dict_release_receipt = {  # 最小可验证发布收据
            "skill_name": skill_name,  # 发布技能名称
            "version": version,  # 发布语义版本
            "source_path": f"skills/{skill_name}",  # owner 仓库源码相对路径
            "generated_at": "2026-05-14T18:00:00",  # 固定生成时间保证夹具稳定
            "current_branch": "master",  # 打包时主分支事实
            "local_branches": ["master", "release"],  # 发布合同要求的本地分支
            "worktree_clean": True,  # 模拟打包时工作树干净
            "phase_results": {"pre": True, "post": True},  # 发布前后门禁结果
            "packaging_mode": "standalone-copy",  # 独立复制打包模式
            "validation_level": validation_level,  # 调用方指定的保证级别
            "provenance_mode": str_provenance_mode,  # 保证级别对应的来源模式
            "sanitization": {  # 发布副本净化证据
                "enabled": True,  # 净化流程已启用
                "scope": "broad",  # 扫描全部文本发布内容
                "mode": "auto-redact-dist-copy",  # 只修改 dist 副本
                "files": [],  # 当前最小夹具没有脱敏文件
                "receipt_required": True,  # 安装器必须复核净化区块
            },
            "files": list_receipt_files,  # 路径与内容摘要表
        }

        # 收据使用稳定缩进便于篡改测试读取和修改。
        (release_dir / "RELEASE_RECEIPT.json").write_text(
            json.dumps(dict_release_receipt, indent=2),
            encoding="utf-8",
        )

    # 写入可被精确 cwd 筛选的 Codex 会话夹具。
    def write_codex_session_fixture(
        self,
        codex_home: Path,
        cwd: Path,
        session_id: str,
        lines: list[tuple[str, str]],
    ) -> Path:
        """写入精确 cwd 的最小 Codex rollout JSONL 会话。

        参数：codex_home 为隔离主目录；cwd 为会话工作目录；session_id 为 ID；lines 为角色与文本序列。
        返回：已写入的 rollout JSONL 文件路径。
        """

        # 日期分层路径匹配 Codex sessions 的正式存储布局。
        path_session_file = codex_home / "sessions" / "2026" / "05" / "13" / f"rollout-{session_id}.jsonl"  # 会话夹具文件

        # 隔离 Codex home 初始为空，递归创建日期目录。
        path_session_file.parent.mkdir(parents=True, exist_ok=True)

        # 首行元数据绑定会话 ID、时间、精确 cwd 和 Codex 来源。
        list_session_rows: list[dict[str, Any]] = [  # rollout JSONL 记录序列
            {
                "timestamp": "2026-05-13T10:00:00.000Z",  # 元数据事件时间
                "type": "session_meta",  # Codex 会话元数据类型
                "payload": {  # 精确会话身份和工作目录
                    "id": session_id,  # 调用方指定会话 ID
                    "timestamp": "2026-05-13T10:00:00.000Z",  # 会话创建时间
                    "cwd": str(cwd),  # exact-cwd 筛选依据
                    "originator": "Codex Desktop",  # 会话来源产品
                },
            }
        ]

        # 按调用方顺序追加用户和 agent 消息事件。
        for str_role, str_text in lines:

            # 角色映射为 Codex event_msg 支持的 payload 类型。
            str_message_type = "user_message" if str_role == "user" else "agent_message"  # Codex 消息事件类型

            # 每条输入行生成独立 JSONL 事件。
            list_session_rows.append(
                {
                    "timestamp": "2026-05-13T10:00:01.000Z",  # 消息事件固定时间
                    "type": "event_msg",  # Codex 对话事件类型
                    "payload": {  # 消息角色和正文
                        "type": str_message_type,  # 用户或 agent 消息标识
                        "message": str_text,  # 调用方提供的消息正文
                    },
                }
            )

        # 每个对象单独占一行并保留中文正文。
        str_session_jsonl = (
            "\n".join(json.dumps(row, ensure_ascii=False) for row in list_session_rows) + "\n"  # 序列化记录
        )  # 完整会话 JSONL

        # 写入结果供 session bootstrap 和 memory 测试读取。
        path_session_file.write_text(str_session_jsonl, encoding="utf-8")

        # 返回文件路径便于调用方记录证据来源。
        return path_session_file

    # 生成包含会话复读证据的演进审查结果。
    def ai_evolution_review(
        self,
        target: dict[str, Any],
        **review_options: Any,
    ) -> dict[str, Any]:
        """生成 AI evolution review 评估使用的结构化审查证据。

        参数：target 为候选演进目标。
        参数：review_options 接受结论、目标快照、会话证据和完整说明关键字。
        返回：满足 evolution review 校验器合同的审查映射。
        """

        # 选项键保持旧公共调用的关键字名称和缺省行为。
        verdict = review_options.get("verdict", "approve")  # 审查结论

        # 批准目标允许测试覆盖候选演进结果。
        approved_target = review_options.get("approved_target")  # 批准后目标

        # 原始目标允许测试构造审查前后差异。
        original_target = review_options.get("original_target")  # 原始目标

        # 会话标识记录复读证据对应的逻辑 ID。
        session_ids = review_options.get("session_ids")  # 已复读会话 ID

        # 会话路径记录复读证据的物理来源。
        session_paths = review_options.get("session_paths")  # 已复读会话路径

        # 状态位区分是否真正执行过历史复读。
        session_reread_performed = review_options.get("session_reread_performed", False)  # 复读状态

        # 原因文本解释为什么需要或不需要复读。
        session_reread_reason = review_options.get("session_reread_reason", "")  # 复读原因

        # 调用方说明可以覆盖五个默认审查维度。
        full_explanation = review_options.get("full_explanation")  # 调用方完整说明

        # 缺省说明覆盖开发、设计、问题、分类和发布五个审查维度。
        dict_default_explanation = {  # 演进审查完整说明
            "development_flow": (  # 开发事实链
                "Read repository facts, updated scripts, ran focused tests, "
                "and verified docs governance."
            ),  # 开发流程说明
            "design_flow": (  # 设计控制链
                "Kept deterministic scripts responsible for contracts and blocked template "
                "writes until review matched the target."
            ),  # 模板写入控制说明
            "problem_analysis": (  # 核心风险分析
                "The risk was allowing a plausible summary to evolve templates without "
                "matching repository evidence."
            ),  # 模板演进风险说明
            "classification_rationale": (  # 分类依据
                "The approved target matches repository kind, governance vocabulary, "
                "and current docs evidence."
            ),  # 仓库事实匹配说明
            "release_alignment": "The summary aligns with handoff, changelog, development, and release evidence.",  # 发布证据一致性
        }

        # 返回结构模拟已读取仓库证据的完整 subagent 审查。
        return {
            "verdict": verdict,  # approve 或 reject 审查结论
            "approved_target": approved_target or target,  # 审查批准的最终目标
            "original_target": original_target or target,  # 审查前的原始目标
            "evidence_read": {  # 审查者实际读取的证据路径
                "conversation_snapshot_paths": [".agents/conversation-snapshots/example-handoff-10.json"],  # 对话快照证据
                "handoff_paths": ["docs/handoff/HANDOFF.md"],  # 当前交接证据
                "docs_paths": ["docs/git_manager/CHANGELOG.md", "docs/development/DEVELOPMENT.md"],  # 开发文档证据
                "release_evidence_paths": [],  # 默认场景没有独立发布证据
                "session_ids": session_ids or [],  # 审查证据会话标识
                "session_paths": session_paths or [],  # 已复读会话文件
            },
            "session_reread_performed": session_reread_performed,  # 是否实际复读历史会话
            "session_reread_reason": session_reread_reason,  # 执行或跳过复读的原因
            "full_explanation": full_explanation or dict_default_explanation,  # 调用方覆盖或完整缺省说明
        }

