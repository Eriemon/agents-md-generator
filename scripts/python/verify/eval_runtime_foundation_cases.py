"""agents-md-generator 技能评估用例治理合同分片。"""

# 延迟类型注解，避免评估上下文尚未装载时解析共享类型。
from __future__ import annotations

# 分片显式声明使用的运行时符号，避免依赖隐式全局上下文。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
    SCRIPT_DIR,

    # 共享执行器与序列化工具支撑隔离治理场景。
    build_case_result,
    json,
    run_json_script,
    run_script,
    subprocess,
    tempfile,
)

# 评估夹具复用同一 skill 仓库相对根，避免各场景拼写漂移。
PATH_SKILL_REPOSITORY = Path("skills") / "agents-md-generator"  # 模拟 skill 仓库相对根

# 置信门禁路径用于制造需要伴随测试和文档的行为变更。
PATH_CONFIDENCE_GATE = PATH_SKILL_REPOSITORY / "scripts" / "python" / "verify" / "run_confidence_gate.py"  # 置信门禁相对路径

# 版本文件路径用于制造缺少发布文档的版本提升。
PATH_VERSION_FILE = PATH_SKILL_REPOSITORY / "VERSION"  # 技能版本文件相对路径

# 三类治理参考文档组成 CLI 与评估变更的伴随证据。
PATH_SCRIPT_GUIDE = PATH_SKILL_REPOSITORY / "references" / "script-guide.md"  # 脚本指南相对路径

# 审查清单记录发布前需要核验的治理层。
PATH_REVIEW_CHECKLIST = PATH_SKILL_REPOSITORY / "references" / "review-checklist.md"  # 审查清单相对路径

# 评估场景文档记录高风险行为回归合同。
PATH_EVALUATION_SCENARIOS = PATH_SKILL_REPOSITORY / "references" / "evaluation-scenarios.md"  # 评估场景相对路径

# 正式评估清单用于检查门禁变更是否同步更新 eval。
PATH_EVALS = PATH_SKILL_REPOSITORY / "evals" / "evals.json"  # 正式评估清单相对路径

# 仓库级测试文件代表伴随测试证据。
PATH_REVIEW_TEST = Path("tests") / "test_agents_md_scripts.py"  # 审查伴随测试相对路径

# 变更日志记录版本提升的发布说明。
PATH_CHANGELOG = Path("docs") / "git_manager" / "CHANGELOG.md"  # 变更日志相对路径

# Git 管理文档记录当前活动发布版本。
PATH_GIT_MANAGER = Path("docs") / "git_manager" / "GIT_MANAGER.md"  # Git 管理文档相对路径

# 开发文档记录版本对应的实现状态。
PATH_DEVELOPMENT = Path("docs") / "development" / "DEVELOPMENT.md"  # 开发文档相对路径

# 源码治理夹具路径集中定义，便于报告断言复用。
PATH_NORMAL_SOURCE = Path("src") / "normal.py"  # 正常 Python 源码路径

# 超过阈值的生产源码用于验证阻断行为。
PATH_BIG_SOURCE = Path("src") / "big.py"  # 超过阈值的生产源码路径

# 测试目录大文件用于验证排除边界。
PATH_BIG_TEST = Path("tests") / "big.py"  # 应从生产大小治理排除的测试路径

# 分解目标路径用于验证计划内容的可执行性。
PATH_BIG_PART = Path("src") / "big_part.py"  # 分解计划声明的目标文件

# 分解计划路径与超限源码保持一一映射。
PATH_BIG_PLAN = Path("docs") / "development" / "decomposition-plans" / "src" / "big.py.md"  # 大文件分解计划相对路径

# 超长物理行夹具验证单行字节限制。
PATH_LONG_SOURCE = Path("src") / "long_line.py"  # 超长物理行夹具路径

# 单行压缩夹具验证 minified 检测。
PATH_COMPRESSED_SOURCE = Path("src") / "compressed.js"  # 单行压缩夹具路径

# JavaScript 密集夹具验证多行压缩检测。
PATH_DENSE_SOURCE = Path("src") / "dense.js"  # JavaScript 密集行夹具路径

# 其他语言密集夹具验证跨语言治理覆盖。
PATH_DENSE_CSS = Path("src") / "dense.css"  # 单行 CSS 属性表路径

# HTML 密集夹具包含内嵌脚本片段。
PATH_DENSE_HTML = Path("src") / "dense.html"  # 内嵌密集脚本页面路径

# Python 密集夹具验证调用序列压缩检测。
PATH_DENSE_PYTHON = Path("src") / "dense.py"  # 长调用元组源码路径

# C 密集夹具验证逗号表达式压缩检测。
PATH_DENSE_C = Path("src") / "dense.c"  # 逗号表达式 C 源码路径

# C++ 密集夹具验证同类跨扩展名覆盖。
PATH_DENSE_CPP = Path("src") / "dense.cpp"  # C++ 主函数密集调用路径

# 源码治理阈值常量避免夹具中的魔法数字失去语义。
INT_SOURCE_LIMIT_BYTES = 65_536  # 配置中的生产源码字节上限

# 超长行长度略高于治理阈值以稳定触发诊断。
INT_LONG_LINE_PAYLOAD = 4_100  # 超长字符串载荷字符数

# 单行压缩重复次数确保载荷超过最小检测长度。
INT_COMPRESSED_REPEAT = 400  # JavaScript 单行压缩片段重复次数

# 密集脚本重复次数用于触发可疑语法密度规则。
INT_DENSE_SCRIPT_REPEAT = 130  # JavaScript 与 HTML 密集片段重复次数

# CSS 自定义属性数量形成不可读的单行声明表。
INT_DENSE_CSS_FIELDS = 170  # CSS 密集属性数量

# Python 调用项数量形成不可读的长元组。
INT_DENSE_PYTHON_CALLS = 260  # Python 密集调用数量

# C 系语言逗号表达式数量形成不可读函数体。
INT_DENSE_C_CALLS = 160  # C 与 C++ 密集调用数量

# 伴随审查基线助手写入完整的代码、测试、文档和版本证据。
def write_review_companion_baseline(path_project: Path) -> None:
    """写入伴随治理场景的基线仓库文件。

    Args:
        path_project: 已创建的隔离 Git 仓库根。

    Returns:
        无业务返回值，基线文件直接写入 path_project。
    """

    # 文件集合覆盖审查器识别的代码、版本和伴随文档位置。
    dict_files = {  # v0.6.3 基线仓库文件
        PATH_CONFIDENCE_GATE.as_posix(): (  # 置信门禁基线脚本
            "import argparse\nargparse.ArgumentParser()\n"  # 最小可解析脚本内容
        ),  # 置信门禁基线内容结束
        PATH_VERSION_FILE.as_posix(): "v0.6.3\n",  # 技能基线版本
        PATH_SCRIPT_GUIDE.as_posix(): "# Script Guide\n",  # CLI 伴随指南
        PATH_REVIEW_CHECKLIST.as_posix(): "# Review Checklist\n",  # 发布审查清单
        PATH_EVALUATION_SCENARIOS.as_posix(): "# Evaluation Scenarios\n",  # 行为评估场景
        PATH_EVALS.as_posix(): '{"version": 1, "cases": []}\n',  # 正式 eval 基线
        PATH_REVIEW_TEST.as_posix(): "# tests\n",  # 门禁伴随测试
        PATH_CHANGELOG.as_posix(): "# Change Log\n- Version: v0.6.3\n",  # 版本变更日志
        PATH_GIT_MANAGER.as_posix(): "# Git Manager\n## Current Version\n- Active version for this release: `v0.6.3`.\n",  # Git 发布状态
        PATH_DEVELOPMENT.as_posix(): "# Development\n- Version: v0.6.3\n",  # 开发版本状态
    }

    # 写入每个基线文件前递归创建其父目录。
    for str_relative_path, str_text in dict_files.items():

        # 基线路径由仓库根和声明的相对位置组成。
        path_file = path_project / str_relative_path  # 当前基线文件

        # 同一循环支持多层 skill 和 docs 目录布局。
        path_file.parent.mkdir(parents=True, exist_ok=True)

        # UTF-8 文本与正式仓库编码保持一致。
        path_file.write_text(str_text, encoding="utf-8")

# 伴随审查执行助手在隔离 Git 仓库制造不完整门禁变更。
def review_companion_report(helper: EvalFixtures) -> dict[str, Any]:
    """运行伴随治理审查场景。

    Args:
        helper: 提供 Git 仓库初始化和提交能力的夹具助手。

    Returns:
        不完整门禁变更的正式治理审查报告。
    """

    # 临时 Git 仓库隔离基线提交和不完整变更提交。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根包含审查器识别的完整基线文件集合。
        path_project = Path(tmp)  # 伴随治理场景仓库根

        # 专用助手建立审查前完整伴随文件基线。
        write_review_companion_baseline(path_project)

        # 初始化独立 Git 仓库并提交完整基线。
        helper.init_basic_git_repo(path_project)

        # 基线提交固定审查比较前的完整伴随文件状态。
        helper.git_commit_all(path_project, "eval: baseline")

        # Git 命令读取审查比较起点。
        completed_process_base = subprocess.run(  # Git 基线解析结果
            ["git", "rev-parse", "HEAD"],  # 读取当前提交哈希
            cwd=path_project,  # 从隔离仓库解析提交哈希
            check=True,  # Git 命令失败时立即终止夹具
            capture_output=True,  # 捕获提交哈希供后续参数使用
            text=True,  # 将 Git 输出解码为文本
        )

        # 去除终端换行后作为 review --base 参数。
        str_base = completed_process_base.stdout.strip()  # 基线提交哈希

        # 门禁新增 CLI 参数，但故意不更新伴随证据。
        path_confidence_gate = path_project / PATH_CONFIDENCE_GATE  # 待修改的置信门禁脚本

        # 新参数代表需要伴随治理证据的行为变化。
        path_confidence_gate.write_text(
            "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--new-gate')\n",
            encoding="utf-8",
        )

        # 版本提升同样故意缺少发布文档更新。
        (path_project / PATH_VERSION_FILE).write_text("v0.6.4\n", encoding="utf-8")

        # 第二次提交形成审查器可比较的不完整变更集。
        helper.git_commit_all(path_project, "eval: incomplete gate change")

        # all 模式同时执行代码、eval 和版本伴随项检查。
        return run_json_script(
            "review_governance.py",  # 变更伴随治理审查入口
            path_project,  # 包含不完整伴随变更的隔离仓库
            "--base",  # 指定审查比较起点
            str_base,  # 审查范围的起始提交
            "--head",  # 指定审查比较终点
            "HEAD",  # 使用不完整变更提交作为终点
            "--skill-dir",  # 指定受伴随治理约束的技能目录
            PATH_SKILL_REPOSITORY.as_posix(),  # 仓库内技能相对根
            "--mode",  # 指定伴随项全量审查模式
            "all",  # 同时检查代码、测试、文档与版本
            cwd=REPO_ROOT,  # 使用仓库正式伴随治理审查运行时
        )

# 审查伴随项场景验证门禁变更必须同步测试、文档和 eval。
def case_review_governance_companion_checks(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估置信门禁与版本变更的伴随文件治理。

    Args:
        case: 当前评估用例元数据。
        helper: 提供最小 Git 仓库初始化和提交能力的夹具助手。

    Returns:
        审查阻断与四类伴随项诊断的对比结果。
    """

    # 专用助手返回不完整门禁变更的正式审查报告。
    dict_review = review_companion_report(helper)  # 伴随治理审查报告

    # 提取机器可读 finding code，忽略任何非对象扩展成员。
    set_codes = {
        dict_finding.get("code")  # 机器可读诊断代码
        for dict_finding in dict_review.get("findings", [])  # 审查器返回的全部诊断
        if isinstance(dict_finding, dict)  # 忽略非对象扩展成员
    }  # 审查器返回的诊断代码集合

    # 有技能路径必须阻断并覆盖四类缺失伴随项。
    dict_with_checks = {  # 变更伴随治理断言
        "review_blocked": not bool(dict_review.get("ok")),  # 不完整变更是否被阻断
        "tests_required": "script-change-without-tests" in set_codes,  # 是否要求伴随测试
        "docs_required": "cli-change-without-script-guide" in set_codes,  # 是否要求脚本指南
        "evals_required": "gate-change-without-evals" in set_codes,  # 是否要求正式 eval
        "version_docs_required": "version-change-without-release-docs" in set_codes,  # 是否要求发布文档
    }

    # 无治理审查基线不会确定性要求任何伴随文件。
    dict_without_checks = {  # 缺少伴随审查的基线
        "review_blocked": False,  # 无治理审查不会阻断
        "tests_required": False,  # 基线不要求伴随测试
        "docs_required": False,  # 基线不要求脚本指南
        "evals_required": False,  # 基线不要求正式 eval
        "version_docs_required": False,  # 基线不要求发布文档
    }

    # 完整审查载荷随结果返回以定位缺失的 finding。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail=dict_review,
        without_skill_detail={
            "baseline": (
                "unguided review would not deterministically require companion "
                "tests, docs, evals, and release docs"
            )
        },
    )

# 设计复核夹具助手准备最小 skill 和未复核答案文件。
def prepare_design_review_fixture(path_project: Path, helper: EvalFixtures) -> tuple[Path, dict[str, Any]]:
    """准备设计复核场景的磁盘输入。

    Args:
        path_project: 隔离项目根目录。
        helper: 提供完整 skill 设计答案的夹具助手。

    Returns:
        答案文件路径和未复核答案映射。
    """

    # 标准 skills 布局使设计收集器识别目标 skill。
    path_skill = path_project / "skills" / "demo-skill"  # 模拟 skill 根目录

    # 主说明写入前创建完整目录层级。
    path_skill.mkdir(parents=True)

    # 最小 frontmatter 提供项目名称和触发描述。
    (path_skill / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Use when testing design review gate\n---\n# Demo\n",
        encoding="utf-8",
    )

    # 完整答案暂不包含最终复核证据。
    dict_answers = helper.skill_answers()  # 未复核的完整设计答案

    # 额外要求字段消除访谈中的最后一个非复核缺口。
    dict_answers["extra_requirements"] = "none"  # 最终额外要求回答

    # collect_design_profile 从磁盘 JSON 读取答案。
    path_answers = path_project / "answers.json"  # 当前设计答案文件

    # 输入文件模拟正式访谈持久化载荷。
    path_answers.write_text(
        json.dumps(dict_answers, ensure_ascii=False),
        encoding="utf-8",
    )

    # 调用方先验证阻断，再向同一文件追加复核证据。
    return path_answers, dict_answers

# 设计复核场景验证写入前必须具备最终复核证据。
def case_design_review_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估设计答案写入前后的复核门禁与持久化行为。

    Args:
        case: 当前评估用例元数据。
        helper: 提供 skill 答案和已复核答案写入能力的夹具助手。

    Returns:
        未复核阻断、批准写入和复核字段持久化的对比结果。
    """

    # 临时项目隔离设计画像和复核状态写入。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载答案文件、skill 和最终设计画像。
        path_project = Path(tmp)  # 设计复核场景项目根

        # 专用助手准备最小 skill 与未复核答案文件。
        tuple_fixture = prepare_design_review_fixture(path_project, helper)  # 设计复核夹具结果

        # 答案路径供两次写入命令共同使用。
        path_answers: Path = tuple_fixture[0]  # 设计答案文件路径

        # 答案映射在首次阻断后追加复核证据。
        dict_answers: dict[str, Any] = tuple_fixture[1]  # 未复核设计答案

        # 首次 --write 应因缺少 design_review 被拒绝。
        tuple_blocked_result = run_script(  # 未复核写入命令结果
            "collect_design_profile.py",  # 未复核设计写入入口
            path_project,  # 接受未复核答案的隔离项目
            "--answers",  # 指定未复核答案文件
            path_answers,  # 当前磁盘设计答案
            "--write",  # 请求持久化未复核答案
            cwd=REPO_ROOT,  # 复核通过路径复用正式设计运行时
        )

        # 分解结果字段用于阻断状态和机器错误解析。
        int_blocked_returncode, str_blocked_stdout, str_blocked_stderr = tuple_blocked_result  # 未复核命令结果字段

        # 夹具追加 subagent 复核结论与签名字段。
        helper.write_reviewed_answers(path_project, path_answers, dict_answers)

        # 第二次写入应接受已复核答案并生成设计画像。
        dict_approved = run_json_script(  # 已复核设计写入结果
            "collect_design_profile.py",  # 已复核设计写入入口
            path_project,  # 接受已复核答案的同一项目
            "--answers",  # 指定已复核答案文件
            path_answers,  # 更新后的磁盘设计答案
            "--write",  # 请求持久化已复核答案
            cwd=REPO_ROOT,  # 使用正式设计收集运行时
        )

        # 未复核命令只有在输出非空时才尝试解析 JSON 错误。
        list_blocked_errors = (
            json.loads(str_blocked_stdout).get("errors", [])  # 机器可读阻断错误
            if str_blocked_stdout.strip()  # 标准输出存在时解析机器错误
            else []  # 无机器输出时保留空错误集合
        )  # 未复核写入的机器错误列表

        # 有技能路径要求拒绝未复核写入并接受 subagent 复核写入。
        dict_with_checks = {  # 设计复核门禁断言
            "unreviewed_write_blocked": int_blocked_returncode != 0,  # 未复核写入是否失败
            "review_error_reported": "design_review must be provided before --write"  # 是否报告复核缺失
            in list_blocked_errors,  # 阻断错误是否准确指出缺失复核
            "approved_subagent_write_passed": dict_approved.get("errors") == [],  # 复核通过后是否允许写入
            "review_persisted": dict_approved.get("profile", {})  # 写入结果中的设计档案
            .get("design_review", {})  # 持久化的复核记录
            .get("reviewer_type")  # 复核记录中的执行者类型
            == "subagent",  # 是否持久化批准的子代理复核
        }

        # 旧写入路径接受未复核答案且不持久化 reviewer_type。
        dict_without_checks = {  # 缺少设计复核门禁的历史基线
            "unreviewed_write_blocked": False,  # 旧路径接受未复核答案
            "review_error_reported": False,  # 旧路径不报告复核缺失
            "approved_subagent_write_passed": True,  # 旧路径同样允许写入
            "review_persisted": False,  # 旧路径不持久化结构化复核证据
        }

        # 阻断错误和批准画像共同形成门禁前后证据。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={
                "blocked_errors": list_blocked_errors,
                "approved": dict_approved,
            },
            without_skill_detail={
                "baseline": (
                    "old write path accepted aligned answer sets without a final "
                    "extra-requirements prompt or subagent design-review evidence"
                )
            },
        )

# 源码边界场景验证正式 eval 运行时位于可安装 skill 内。
def case_source_governance_test_boundary(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    """评估正式 eval 运行时与 tests 兼容包装器的目录边界。

    Args:
        case: 当前评估用例元数据。
        _helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        运行器、夹具和兼容包装器位置合同的对比结果。
    """

    # 正式运行器必须随可安装 skill 发布。
    path_runtime_runner = SCRIPT_DIR / "run_skill_evals.py"  # 正式 eval 运行器路径

    # 运行时夹具同样属于生产验证能力而非 tests 私有实现。
    path_runtime_fixture = SCRIPT_DIR / "eval_runtime_fixtures.py"  # 正式 eval 夹具路径

    # tests 入口只保留历史命令兼容委托。
    path_wrapper_runner = REPO_ROOT / "tests" / "run_skill_evals.py"  # 测试兼容包装器路径

    # 旧 tests 夹具必须删除，避免生产和测试出现双重事实源。
    path_legacy_fixture = REPO_ROOT / "tests" / "eval_fixtures.py"  # 已退役测试夹具路径

    # 正式运行器文本用于确认夹具导入来自生产模块。
    str_runtime_text = path_runtime_runner.read_text(encoding="utf-8")  # 正式运行器源码

    # 核心分片也可能承载正式夹具导入。
    str_core_text = (SCRIPT_DIR / "eval_runtime_core.py").read_text(  # eval 核心源码
        encoding="utf-8"  # eval 核心源码固定使用 UTF-8
    )  # eval 核心分片源码

    # 包装器缺失时使用空文本，让委托标记断言稳定失败。
    str_wrapper_text = (
        path_wrapper_runner.read_text(encoding="utf-8")  # 现有包装器文本
        if path_wrapper_runner.is_file()  # 包装器存在时读取委托实现
        else ""  # 包装器缺失时使用空文本参与断言
    )  # tests 兼容包装器源码

    # 有技能路径验证生产运行时完整且 tests 只承担兼容入口。
    dict_with_checks = {  # eval 源码治理边界断言
        "runtime_runner_exists": path_runtime_runner.is_file(),  # 正式运行器是否存在
        "runtime_fixture_exists": path_runtime_fixture.is_file(),  # 正式夹具是否存在
        "tests_wrapper_exists": path_wrapper_runner.is_file(),  # tests 兼容包装器是否存在
        "legacy_tests_fixture_removed": not path_legacy_fixture.exists(),  # 旧 tests 夹具是否删除
        "runtime_uses_formal_fixture": "eval_runtime_fixtures" in str_runtime_text  # 运行器是否导入正式夹具
        or "eval_runtime_fixtures" in str_core_text,  # 核心分片是否导入正式夹具
        "wrapper_delegates_runtime": all(  # 兼容包装器是否完整委托正式运行器
            str_marker in str_wrapper_text  # 当前委托标记是否存在
            for str_marker in (  # 包装器必须保留的正式运行时标记
                "_load_runtime_module",  # 动态加载正式运行器的包装器助手
                '"verify"',  # 正式运行器所在功能目录
                '"run_skill_evals.py"',  # 正式运行器文件名
            )
        ),
    }

    # 旧布局把真实运行器或夹具留在 tests，安装后不可用。
    dict_without_checks = {  # eval 运行时未纳入安装包的历史基线
        "runtime_runner_exists": False,  # 旧包缺少正式运行器
        "runtime_fixture_exists": False,  # 旧包缺少正式夹具
        "tests_wrapper_exists": False,  # 旧包不保留兼容包装器
        "legacy_tests_fixture_removed": False,  # 旧包仍依赖 tests 夹具
        "runtime_uses_formal_fixture": False,  # 旧运行器不使用正式夹具
        "wrapper_delegates_runtime": False,  # 旧包装器不委托正式运行器
    }

    # 结果详情明确正式入口与包装器的职责关系。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "run_skill_evals": (
                "formal runner lives under scripts/python/verify/; "
                "tests/run_skill_evals.py is only a compatibility wrapper"
            )
        },
        without_skill_detail={
            "baseline": (
                "older releases kept the real eval runner outside the installable "
                "skill runtime or classified it as test-only code"
            )
        },
    )

# 隔离项目 helper 把源码与分解计划写入磁盘后运行正式治理检查。
def source_governance_fixture_report(
    dict_files: dict[str, str],
    dict_plans: dict[str, str] | None = None,
) -> dict[str, Any]:
    """为一组内存源码构造临时项目并返回源码治理报告。

    Args:
        dict_files: 相对路径到源码文本的映射。
        dict_plans: 可选的相对路径到分解计划文本映射。

    Returns:
        ``check_source_governance.py`` 的 JSON 结果。
    """

    # 每个场景使用独立项目，避免文件集合互相影响。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根统一容纳待检源码和可选分解计划。
        path_project = Path(tmp)  # 源码治理夹具根

        # 写入场景声明的全部源码文件。
        for str_relative_path, str_text in dict_files.items():

            # 相对路径保持检查器报告中的仓库定位信息。
            path_file = path_project / str_relative_path  # 当前夹具源码

            # 支持 src/tests 等任意多层相对目录。
            path_file.parent.mkdir(parents=True, exist_ok=True)

            # UTF-8 写入保证字节阈值计算与正式仓库一致。
            path_file.write_text(str_text, encoding="utf-8")

        # 分解计划使用同一写入流程，但允许调用方省略。
        for str_relative_path, str_text in (dict_plans or {}).items():

            # 计划路径与生产检查器约定的目录结构一致。
            path_plan = path_project / str_relative_path  # 当前分解计划

            # 计划目录通常位于 docs/development/decomposition-plans。
            path_plan.parent.mkdir(parents=True, exist_ok=True)

            # 计划内容参与 oversized 例外合同验证。
            path_plan.write_text(str_text, encoding="utf-8")

        # 正式检查器返回大小、可读性和分解计划综合结论。
        return run_json_script(
            "check_source_governance.py",
            path_project,
            cwd=REPO_ROOT,
        )

# 多语言密集载荷助手生成六种扩展名的正式治理报告。
def dense_source_governance_report() -> tuple[dict[str, Any], set[str], set[str]]:
    """运行跨语言密集源码治理场景。

    Args:
        无外部业务参数。

    Returns:
        治理报告、实际违规路径和期望违规路径。
    """

    # JavaScript 样本保留正常声明后追加密集调用片段。
    str_dense_javascript = (
        "const ok = true;\n"  # 保留一行正常声明用于避免单行文件特例
        + "{a(),b();}" * INT_DENSE_SCRIPT_REPEAT  # 制造连续密集调用片段
        + "\n"  # 以换行结束源码文本
    )  # JavaScript 语句密度检测载荷

    # CSS 样本使用大量自定义属性形成单行声明表。
    str_dense_css = (
        ".a{"  # 打开密集自定义属性规则
        + ";".join(f"--v{index}:{index}" for index in range(INT_DENSE_CSS_FIELDS))  # 生成大量属性声明
        + "}\n.short{color:red}\n"  # 添加正常短规则形成对照
    )  # CSS 单行属性表检测载荷

    # HTML 样本通过内嵌脚本形成页面中的密集语句。
    str_dense_html = (
        "<main>\n<script>"  # 打开页面和内嵌脚本边界
        + "{a(),b();}" * INT_DENSE_SCRIPT_REPEAT  # 在脚本中生成密集调用
        + "</script>\n</main>\n"  # 关闭脚本和页面边界
    )  # HTML 内嵌脚本检测载荷

    # Python 样本通过长调用元组触发密度诊断。
    str_dense_python = (
        "ok = True\nvalues = ("  # 正常声明后打开长调用元组
        + ",".join("fn()" for _ in range(INT_DENSE_PYTHON_CALLS))  # 生成密集函数调用项
        + ")\n"  # 关闭调用元组并结束文件
    )  # Python 长调用元组检测载荷

    # C 与 C++ 样本使用相同密度、不同函数签名验证扩展名覆盖。
    str_dense_c = "int ok;\nint main(void){" + "a(),b();" * INT_DENSE_C_CALLS + "return 0;}\n"  # C 函数体载荷

    # C++ 样本采用无参数 main 入口。
    str_dense_cpp = "int ok;\nint main(){" + "a(),b();" * INT_DENSE_C_CALLS + "return 0;}\n"  # C++ 无参入口逗号调用样本

    # 文件映射覆盖治理配置声明的六种代表性扩展名。
    dict_dense_files = {  # 跨语言密集源码夹具映射
        PATH_DENSE_SOURCE.as_posix(): str_dense_javascript,  # 脚本语句密度样本
        PATH_DENSE_CSS.as_posix(): str_dense_css,  # 样式属性密度样本
        PATH_DENSE_HTML.as_posix(): str_dense_html,  # 页面内嵌脚本样本
        PATH_DENSE_PYTHON.as_posix(): str_dense_python,  # 调用元组密度样本
        PATH_DENSE_C.as_posix(): str_dense_c,  # C 逗号表达式样本
        PATH_DENSE_CPP.as_posix(): str_dense_cpp,  # C++ 调用表达式样本
    }

    # 正式检查器应为每个扩展名生成密集行违规。
    dict_report = source_governance_fixture_report(dict_dense_files)  # 多语言密集源码报告

    # 仅收集命中密集行规则的相对路径。
    set_actual_paths = {  # 实际密集行违规路径
        dict_item.get("path")  # 当前可读性违规路径
        for dict_item in dict_report.get("readability_violations", [])  # 跨语言可读性违规
        if "minified or obfuscated dense line" in dict_item.get("message", "")  # 只收集密集行诊断
    }

    # 期望集合直接来自输入映射，避免重复维护扩展名清单。
    set_expected_paths = set(dict_dense_files)  # 应命中密集行规则的路径

    # 调用方同时使用报告详情和集合等价断言。
    return dict_report, set_actual_paths, set_expected_paths

# 源码治理断言助手把八类真实报告转换为稳定能力检查。
def source_governance_contract_checks(
    dict_reports: dict[str, dict[str, Any]],
    set_actual_dense_paths: set[str],
    set_expected_dense_paths: set[str],
) -> dict[str, bool]:
    """构造源码大小与可读性合同断言。

    Args:
        dict_reports: 正常、超限、计划和可读性报告映射。
        set_actual_dense_paths: 实际命中跨语言密集行规则的路径。
        set_expected_dense_paths: 应命中跨语言密集行规则的路径。

    Returns:
        八类源码治理能力检查映射。
    """

    # 首个超限项应是生产文件，而非已排除的 tests 文件。
    dict_oversized_item = (dict_reports["oversized"].get("oversized_source_files") or [{}])[0]  # 首个大文件诊断

    # 每项断言对应一个独立的大小、例外或可读性合同。
    return {  # 源码大小与可读性合同断言
        "normal_under_64kb_passes": bool(dict_reports["normal"].get("ok")),  # 正常源码是否通过
        "oversized_reports_bytes": dict_oversized_item.get("path") == PATH_BIG_SOURCE.as_posix()  # 是否定位生产大文件
        and dict_oversized_item.get("byte_count", 0)  # 实际字节数是否超过报告阈值
        > dict_oversized_item.get("max_bytes", 0)  # 报告中记录的配置阈值
        == INT_SOURCE_LIMIT_BYTES,  # 阈值是否与治理配置一致
        "excluded_tests_skipped": all(  # 测试目录大文件是否全部排除
            dict_item.get("path") != PATH_BIG_TEST.as_posix()  # 当前超限项是否位于生产目录
            for dict_item in dict_reports["oversized"].get("oversized_source_files", [])  # 治理报告中的全部超限项
        ),
        "decomposition_plan_allows_oversize": bool(dict_reports["planned"].get("ok")),  # 有效计划是否放行
        "overlong_physical_line_blocked": any(  # 超长物理行是否触发可读性阻断
            "physical line" in dict_item.get("message", "")  # 当前诊断是否属于物理行上限
            for dict_item in dict_reports["overlong"].get("readability_violations", [])  # 超长行场景诊断
        ),
        "one_line_compressed_blocked": any(  # 单行压缩源码是否被阻断
            "one-line compressed source" in dict_item.get("message", "")  # 当前诊断是否属于单行压缩
            for dict_item in dict_reports["compressed"].get("readability_violations", [])  # 单行压缩场景诊断
        ),
        "minified_dense_line_blocked": any(  # 高密度源码行是否被阻断
            "minified or obfuscated dense line" in dict_item.get("message", "")  # 当前诊断是否属于密集行
            for dict_item in dict_reports["dense"].get("readability_violations", [])  # JavaScript 密集场景诊断
        ),
        "minified_dense_line_requested_styles_blocked": set_actual_dense_paths == set_expected_dense_paths,  # 六种扩展名是否全部命中
    }

# 基础源码治理报告助手运行大小、计划和三类可读性场景。
def basic_source_governance_reports() -> dict[str, dict[str, Any]]:
    """运行六类基础源码治理夹具。

    Args:
        无外部业务参数。

    Returns:
        正常、超限、计划、超长行、压缩和密集行报告映射。
    """

    # 正常 Python 文件证明阈值以下源码不会被误阻断。
    str_normal_text = "\n".join(  # 低于阈值的多行 Python 源码
        f"VALUE_{int_index} = {int_index}"  # 当前正常源码赋值行
        for int_index in range(40)  # 足够形成多行但保持低于阈值
    ) + "\n"  # 低于 64 KiB 的正常源码

    # 正常场景只包含一个简短生产文件。
    dict_normal = source_governance_fixture_report(  # 正常源码治理报告
        {PATH_NORMAL_SOURCE.as_posix(): str_normal_text}  # 单个正常生产文件
    )

    # 大文件文本超过 64 KiB，同时用于验证 tests 排除边界。
    str_oversized_text = "".join(  # 超过 64 KiB 的 Python 源码
        f"VALUE_{int_index} = '{'a' * 120}'\n"  # 当前超限源码赋值行
        for int_index in range(600)  # 稳定超过 64 KiB 的行数
    )  # 超过字节阈值的 Python 源码

    # 生产与 tests 各放一份，只允许生产文件进入 oversized 报告。
    dict_oversized = source_governance_fixture_report(  # 未提供分解计划的大文件报告
        {
            PATH_BIG_SOURCE.as_posix(): str_oversized_text,  # 应报告的生产大文件
            PATH_BIG_TEST.as_posix(): str_oversized_text,  # 应被排除的测试大文件
        }
    )

    # 合法分解计划包含四个必需章节和具体拆分目标。
    str_plan = "\n".join(  # 覆盖大文件的四段式分解计划
        [
            "## Current Size",  # 分解计划当前尺寸章节
            "src/big.py exceeds the configured size limit.",  # 超限事实说明
            "## Split Boundaries",  # 分解边界章节
            "Move generated tables into data modules.",  # 具体拆分策略
            "## Target Files",  # 分解目标章节
            PATH_BIG_PART.as_posix(),  # 拆分后目标模块路径
            "## Exit Criteria",  # 分解退出标准章节
            "src/big.py returns below 64KB.",  # 大文件完成拆分的验收条件
            "",  # 分解计划末尾保留标准换行
        ]
    )  # oversized 源码的治理分解计划

    # 同一大文件在有效计划覆盖下应允许继续分解工作。
    dict_planned = source_governance_fixture_report(  # 有效分解计划覆盖后的报告
        {PATH_BIG_SOURCE.as_posix(): str_oversized_text},  # 计划覆盖的生产大文件
        {PATH_BIG_PLAN.as_posix(): str_plan},  # 对应源码的有效分解计划
    )

    # 三种可读性夹具分别触发超长行、单行压缩和密集行诊断。
    dict_overlong = source_governance_fixture_report(  # 超长 Python 物理行报告
        {PATH_LONG_SOURCE.as_posix(): f"VALUE = '{'a' * INT_LONG_LINE_PAYLOAD}'\nOTHER = 1\n"}  # 超长物理行夹具
    )

    # 单行 JavaScript 重复语句验证压缩源码启发式。
    dict_compressed = source_governance_fixture_report(  # 单行压缩 JavaScript 报告
        {PATH_COMPRESSED_SOURCE.as_posix(): "var x=1;" + "x=x+1;" * INT_COMPRESSED_REPEAT + "\n"}  # 单行压缩夹具
    )

    # 第二行高密度调用验证 minified dense line 诊断。
    dict_dense = source_governance_fixture_report(  # JavaScript 密集行报告
        {PATH_DENSE_SOURCE.as_posix(): "const ok = true;\n" + "{a(),b();}" * INT_DENSE_SCRIPT_REPEAT + "\n"}  # 密集行夹具
    )

    # 调用方将六类报告交给统一断言助手。
    return {  # 基础源码治理场景报告
        "normal": dict_normal,  # 正常源码报告
        "oversized": dict_oversized,  # 未计划超限源码报告
        "planned": dict_planned,  # 有效分解计划报告
        "overlong": dict_overlong,  # 物理行字节上限检查结果
        "compressed": dict_compressed,  # 单文件压缩启发式检查结果
        "dense": dict_dense,  # 第二行高密度调用检查结果
    }

# 大小与可读性场景验证字节阈值、计划例外和压缩源码阻断。
def case_source_governance_size_readability_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    """评估源码大小、物理行和多语言压缩检测合同。

    Args:
        case: 当前评估用例元数据。
        _helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        八项源码治理能力的结构化对比结果。
    """

    # 基础助手运行大小、计划和三类可读性场景。
    dict_reports = basic_source_governance_reports()  # 六类基础源码治理报告

    # 各报告使用独立变量保留清晰的最终诊断映射。
    dict_normal = dict_reports["normal"]  # 最终详情中的低于阈值证据

    # 超限报告同时用于生产路径和 tests 排除断言。
    dict_oversized = dict_reports["oversized"]  # 最终详情中的生产超限证据

    # 有效计划报告证明受控分解期间可以继续工作。
    dict_planned = dict_reports["planned"]  # 最终详情中的计划放行证据

    # 三类可读性报告分别保留具体违规列表。
    dict_overlong = dict_reports["overlong"]  # 最终详情中的物理行违规

    # 单行压缩报告验证完整文件压缩启发式。
    dict_compressed = dict_reports["compressed"]  # 单行压缩源码报告

    # 密集行报告验证多行文件中的局部压缩。
    dict_dense = dict_reports["dense"]  # 最终详情中的局部密集行违规

    # 跨语言助手返回报告和实际、期望路径集合。
    tuple_dense_evidence = dense_source_governance_report()  # 跨语言密集源码证据

    # 报告详情用于最终失败诊断。
    dict_dense_by_extension: dict[str, Any] = tuple_dense_evidence[0]  # 六种扩展名联合检查结果

    # 实际路径集合反映正式检查器的命中范围。
    set_actual_dense_paths: set[str] = tuple_dense_evidence[1]  # 检查器真实命中的文件集合

    # 期望路径集合来自六种扩展名输入边界。
    set_expected_dense_paths: set[str] = tuple_dense_evidence[2]  # 期望密集行违规路径

    # 有技能路径验证八项大小、计划和可读性治理能力。
    dict_with_checks = source_governance_contract_checks(  # 源码治理能力断言
        dict_reports,  # 六类基础治理报告
        set_actual_dense_paths,  # 实际跨语言命中路径
        set_expected_dense_paths,  # 期望跨语言命中路径
    )

    # 无源码治理基线不具备上述任何确定性阻断能力。
    dict_without_checks = {
        str_key: False  # 基线不具备当前治理能力
        for str_key in dict_with_checks  # 当前场景的全部治理能力名称
    }  # 全部能力关闭的历史基线

    # 各场景原始报告随结果返回用于精确定位规则误判。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "normal": {"ok": dict_normal.get("ok")},
            "oversized": dict_oversized,
            "planned": {"ok": dict_planned.get("ok")},
            "overlong": dict_overlong.get("readability_violations", []),
            "compressed": dict_compressed.get("readability_violations", []),
            "dense": dict_dense.get("readability_violations", []),
            "dense_by_extension": dict_dense_by_extension.get(
                "readability_violations",
                [],
            ),
        },
        without_skill_detail={
            "baseline": (
                "line-count governance did not measure UTF-8 byte size or block "
                "one-line/minified readable-source regressions"
            )
        },
    )
