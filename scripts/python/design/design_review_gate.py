"""验证设计评审记录，并把评审绑定到确定的答案与画像。"""

# 标准库提供稳定摘要、JSON 规范化、路径和通用类型。
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

# 评审记录在问答合同中的字段名保持稳定。
DESIGN_REVIEW_KEY = "design_review"  # 设计评审问答字段名。

# 附加要求在哈希前需要使用问答模块统一规范化。
EXTRA_REQUIREMENTS_KEY = "extra_requirements"  # 附加要求问答字段名。

# 完整评审必须包含执行者、结论、发现、确认项、双哈希和摘要。
DESIGN_REVIEW_REQUIRED_FIELDS = [  # 设计评审必填字段。
    "reviewer_type",  # 评审执行者类型。
    "verdict",  # 批准或拒绝结论。
    "findings",  # 评审发现列表。
    "required_user_confirmations",  # 尚需用户确认的事项。
    "reviewed_answers_hash",  # 被评审答案的稳定摘要。
    "reviewed_profile_hash",  # 被评审画像的稳定摘要。
    "review_summary",  # 评审过程与结论摘要。
]

# 文件级加载兼容不预先登记设计目录的评测夹具。
def _load_design_module(str_module_name: str) -> ModuleType:
    """按同目录文件加载设计模块。

    参数：str_module_name 为不含扩展名的设计模块名。
    返回：执行完成并提供公开属性的模块对象。
    异常：模块文件无法建立加载规格时抛出 RuntimeError。
    """

    # 所有设计模块与本评审门禁位于同一目录。
    path_module = Path(__file__).resolve().with_name(f"{str_module_name}.py")  # 设计模块文件路径。

    # 映射容器保存加载规格，避免把动态 importlib 返回值误判为业务变量。
    dict_loader_context: dict[str, Any] = {  # 文件加载上下文。
        "spec": importlib.util.spec_from_file_location(str_module_name, path_module),  # 设计模块加载规格。
    }

    # 缺少加载器表示目标文件不能作为 Python 模块执行。
    if dict_loader_context["spec"] is None or dict_loader_context["spec"].loader is None:

        # 固定错误前缀满足项目异常输出合同。
        raise RuntimeError("> ERR: [Python] design dependency could not be loaded")

    # 新模块对象接收文件执行后生成的公开 API。
    module_type_design_dependency: ModuleType = importlib.util.module_from_spec(  # 设计依赖模块对象。
        dict_loader_context["spec"]  # 已确认包含加载器的文件规格。
    )

    # 加载器执行目标文件并填充模块命名空间。
    dict_loader_context["spec"].loader.exec_module(module_type_design_dependency)

    # 调用方只依赖模块公开函数，不修改加载器状态。
    return module_type_design_dependency

# 兼容导出保留历史状态机从本模块读取规范化函数的接口。
def normalize_extra_requirements(raw_value: Any) -> str:
    """把附加要求规范化为问答合同使用的稳定文本。

    参数：raw_value 为 CLI、JSON 或状态机提供的附加要求值。
    返回：由 design_questions 规则生成的规范化文本。
    """

    # 问答模块仍是规范化语义的唯一实现来源。
    module_type_questions: ModuleType = _load_design_module("design_questions")  # 设计问答合同模块。

    # 兼容入口只转发调用，不复制规范化规则。
    return str(module_type_questions.normalize_extra_requirements(raw_value))

# 哈希计算必须排除评审自身，避免循环依赖。
def answers_without_design_review(answers: dict[str, Any]) -> dict[str, Any]:
    """返回移除设计评审并规范化附加要求的答案副本。

    参数：answers 为完整设计问答映射。
    返回：适合画像构建和稳定哈希的独立答案映射。
    """

    # 字典推导创建副本，不修改调用方提供的答案。
    dict_clean_answers = {  # 不含评审记录的答案副本。
        str_key: value  # 保留原字段和值。
        for str_key, value in answers.items()  # 遍历全部设计答案。
        if str_key != DESIGN_REVIEW_KEY  # 排除会引用哈希的评审记录。
    }

    # 附加要求的等价写法必须映射到同一哈希输入。
    if EXTRA_REQUIREMENTS_KEY in dict_clean_answers:

        # 规范化结果覆盖副本中的原始表达。
        dict_clean_answers[EXTRA_REQUIREMENTS_KEY] = normalize_extra_requirements(  # 规范化附加要求。
            dict_clean_answers.get(EXTRA_REQUIREMENTS_KEY)  # 当前附加要求输入。
        )

    # 调用方可安全修改这份副本而不污染原始问答。
    return dict_clean_answers

# 稳定 JSON 编码确保字段顺序不影响评审摘要。
def stable_json_hash(value: Any) -> str:
    """计算 JSON 可序列化值的稳定 SHA-256 摘要。

    参数：value 为需要绑定到评审的答案或画像载荷。
    返回：小写十六进制 SHA-256 摘要。
    """

    # 紧凑排序编码同时保留中文原文。
    str_payload = json.dumps(  # 规范化 JSON 文本。
        value,  # 待摘要的结构化载荷。
        ensure_ascii=False,  # 中文保持原字符编码。
        sort_keys=True,  # 映射字段按键排序。
        separators=(",", ":"),  # 删除无语义空白。
    )

    # UTF-8 字节摘要在不同平台保持一致。
    return hashlib.sha256(str_payload.encode("utf-8")).hexdigest()

# 评审画像不包含评审记录本身。
def profile_for_design_review(
    project: Path,
    answers: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """构建供设计评审使用的无评审画像。

    参数：project 为项目根目录；answers 为当前设计问答。
    返回：成功时返回画像和空诊断，失败时返回空画像和构建诊断。
    """

    # 清理后的答案避免旧评审影响新画像。
    dict_clean_answers = answers_without_design_review(answers)  # 无评审设计答案。

    # 画像构建器按文件加载，兼容隔离评测环境。
    module_type_profile_builder: ModuleType = _load_design_module("design_profile_builder")  # 设计画像构建模块。

    # 画像构建结果同时包含可选画像和错误列表。
    tuple_profile_result = module_type_profile_builder.build_profile(project, dict_clean_answers)  # 画像构建结果。

    # 首项是成功时的设计画像。
    dict_profile: dict[str, Any] | None = tuple_profile_result[0]  # 待评审画像。

    # 第二项收集设计问答或合同错误。
    list_profile_errors: list[str] = tuple_profile_result[1]  # 画像构建诊断。

    # 构建失败时保持原诊断顺序。
    if list_profile_errors:

        # 空画像防止调用方误用部分结果。
        return None, list_profile_errors

    # 构建器合同要求无错误时必须提供画像。
    if dict_profile is None:

        # 防御性诊断替代生产代码中的断言。
        return None, ["design profile builder returned no profile"]

    # 即使上游未来附加评审字段，此处也强制移除。
    dict_profile.pop(DESIGN_REVIEW_KEY, None)

    # 空诊断表示画像可进入哈希与评审流程。
    return dict_profile, []

# 双哈希把评审结论绑定到答案和派生画像。
def design_review_hashes(
    project: Path,
    answers: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, str]:
    """计算设计评审所需的答案和画像摘要。

    参数：project 为项目根；answers 为问答；profile 可提供已构建画像。
    返回：包含 reviewed_answers_hash 和 reviewed_profile_hash 的映射。
    异常：无法从答案构建合法画像时抛出 ValueError。
    """

    # 答案摘要始终排除可能存在的旧评审记录。
    dict_clean_answers = answers_without_design_review(answers)  # 规范化评审答案。

    # 调用方未提供画像时按当前答案重新构建。
    if profile is None:

        # 构建结果用于计算画像摘要或报告问答错误。
        tuple_profile_result = profile_for_design_review(project, dict_clean_answers)  # 待摘要画像结果。

        # 首项保存成功构建的画像。
        dict_profile_for_hash: dict[str, Any] | None = tuple_profile_result[0]  # 哈希输入画像。

        # 第二项保存无法构建画像的原因。
        list_profile_errors: list[str] = tuple_profile_result[1]  # 画像哈希前置诊断。

        # 哈希不得掩盖画像合同错误。
        if list_profile_errors:

            # ValueError 表示调用数据无法形成可评审画像。
            raise ValueError("> ERR: [Python] design profile contains invalid answers")

    # 已提供画像时复制载荷，隔离后续字段清理。
    else:

        # 调用方提供的画像先复制，避免移除字段时修改原对象。
        dict_profile_for_hash = dict(profile)  # 外部画像的独立副本。

    # 防御上游合同异常，避免对空画像计算误导摘要。
    if dict_profile_for_hash is None:

        # 明确异常比生产断言更适合 CLI 捕获。
        raise ValueError("> ERR: [Python] design profile is unavailable for review hashing")

    # 评审字段不属于被评审画像内容。
    dict_profile_for_hash.pop(DESIGN_REVIEW_KEY, None)

    # 两个摘要字段名是评审合同的稳定公共接口。
    return {
        "reviewed_answers_hash": stable_json_hash(dict_clean_answers),  # 当前答案摘要。
        "reviewed_profile_hash": stable_json_hash(dict_profile_for_hash),  # 当前画像摘要。
    }

# 请求载荷指导上层启动独立设计评审。
def design_review_request(
    project: Path,
    answers: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """构造绑定当前设计内容的评审请求。

    参数：project 为项目根；answers 为问答；profile 为待评审画像。
    返回：包含执行者要求、必填字段、双哈希和评审说明的请求映射。
    """

    # 双哈希确保返回的评审不能应用到后续变更。
    dict_hashes = design_review_hashes(project, answers, profile)  # 当前设计双哈希。

    # 指令保持既有英文协议，供外部评审智能体直接消费。
    return {
        "kind": "design_review",  # 请求类型标识。
        "required_reviewer_type": "subagent",  # 强制独立子智能体评审。
        "required_fields": DESIGN_REVIEW_REQUIRED_FIELDS,  # 评审响应必填字段。
        "reviewed_answers_hash": dict_hashes["reviewed_answers_hash"],  # 待评审答案摘要。
        "reviewed_profile_hash": dict_hashes["reviewed_profile_hash"],  # 待评审画像摘要。
        "instructions": [  # 外部评审执行说明。
            "Spawn a new review subagent after final alignment.",  # 对齐完成后启动独立评审。
            (
                "Ask the subagent to review the full answers and profile for design, gate, "  # 评审设计与门禁。
                "folder, version, branch, and user-confirmation risks."  # 评审目录、版本与确认风险。
            ),
            (
                "Submit the returned JSON as design_review; do not write "  # 评审结果提交方式。
                ".agents/agents-control.json until it approves with matching hashes and no "  # 画像写入前置条件。
                "pending user confirmations."  # 用户确认项必须清空。
            ),
        ],
    }

# 基础结构验证先阻断缺字段或类型错误。
def _review_structure_errors(review: Any) -> tuple[list[str], dict[str, Any] | None]:
    """验证评审载荷的必填字段和基础类型。

    参数：review 为调用方提供的任意评审载荷。
    返回：诊断列表以及类型有效时的评审映射。
    """

    # 非映射载荷无法承载评审合同字段。
    if not isinstance(review, dict):

        # 稳定诊断由写入门禁和测试共同依赖。
        return ["design_review must be provided before --write"], None

    # 缺失字段按合同定义顺序报告。
    list_errors = [  # 评审结构诊断。
        f"design_review.{str_field} is required"  # 单个缺失字段诊断。
        for str_field in DESIGN_REVIEW_REQUIRED_FIELDS  # 遍历全部必填字段。
        if str_field not in review  # 只登记缺失项。
    ]

    # 缺字段时暂不执行依赖字段值的检查。
    if list_errors:

        # 返回原映射便于调用方保持统一解包方式。
        return list_errors, review

    # 字段完整的映射进入语义和哈希验证。
    return [], review

# 字段语义验证与当前项目状态无关，可独立执行。
def _review_value_errors(dict_review: dict[str, Any]) -> tuple[list[str], str, list[Any]]:
    """验证评审执行者、结论、列表字段和摘要。

    参数：dict_review 为字段完整的评审映射。
    返回：诊断、规范化结论以及类型安全的用户确认列表。
    """

    # 所有字段问题累计报告，减少重复提交次数。
    list_errors: list[str] = []  # 评审字段语义诊断。

    # 设计评审必须由独立子智能体执行。
    if dict_review.get("reviewer_type") != "subagent":

        # 执行者错误不影响后续字段检查。
        list_errors.append("design_review.reviewer_type must be subagent")

    # 结论统一为小写文本后判断支持范围。
    str_verdict = str(dict_review.get("verdict", "")).strip().lower()  # 规范化评审结论。

    # 评审协议只允许批准或拒绝。
    if str_verdict not in {"approve", "reject"}:

        # 未知结论不能参与写入批准判断。
        list_errors.append("design_review.verdict must be approve or reject")

    # 发现必须使用列表，以便保留多条独立问题。
    if not isinstance(dict_review.get("findings"), list):

        # 类型诊断保持原有公共错误正文。
        list_errors.append("design_review.findings must be a list")

    # 用户确认项需要在批准写入前单独检查。
    value_confirmations = dict_review.get("required_user_confirmations")  # 原始用户确认项。

    # 非列表确认项既是类型错误，也不能参与布尔判断。
    if not isinstance(value_confirmations, list):

        # 登记类型错误后使用空列表继续验证。
        list_errors.append("design_review.required_user_confirmations must be a list")

        # 空列表是错误场景下的安全内部替代值。
        list_confirmations: list[Any] = []  # 类型安全的确认项替代值。

    # 合法确认列表保持原始事项供批准门禁判断。
    else:

        # 已验证列表可直接用于批准条件检查。
        list_confirmations = value_confirmations  # 用户确认事项列表。

    # 摘要不能为空，确保评审留下可审查依据。
    if not str(dict_review.get("review_summary", "")).strip():

        # 空摘要无法证明评审实际覆盖内容。
        list_errors.append("design_review.review_summary must be non-empty")

    # 调用方继续执行哈希和批准状态验证。
    return list_errors, str_verdict, list_confirmations

# 哈希验证确认评审针对当前答案和画像。
def _review_hash_errors(
    path_project: Path,
    dict_answers: dict[str, Any],
    dict_review: dict[str, Any],
    dict_profile: dict[str, Any] | None,
) -> list[str]:
    """比较评审摘要与当前设计内容。

    参数：path_project 为项目根；dict_answers 为问答；dict_review 为评审；dict_profile 为可选画像。
    返回：哈希计算或不匹配诊断列表。
    """

    # 哈希计算可能因画像问答不完整而失败。
    try:

        # 当前摘要对照用于识别评审后的内容漂移。
        dict_hashes = design_review_hashes(path_project, dict_answers, dict_profile)  # 实时设计摘要对照。

    # 画像无法构建时转换成普通门禁诊断。
    except ValueError as error:

        # 画像错误转换为评审门禁诊断而非中断调用方。
        return [f"design_review hash could not be computed: {error}"]

    # 两类不匹配分别报告，便于定位答案或画像漂移。
    list_errors: list[str] = []  # 评审哈希诊断。

    # 答案变化会使旧评审立即失效。
    if dict_review.get("reviewed_answers_hash") != dict_hashes["reviewed_answers_hash"]:

        # 调用方需要重新评审当前答案。
        list_errors.append("design_review.reviewed_answers_hash does not match current answers")

    # 派生画像变化同样要求重新评审。
    if dict_review.get("reviewed_profile_hash") != dict_hashes["reviewed_profile_hash"]:

        # 防止答案等价但治理画像已变化时误用旧批准。
        list_errors.append("design_review.reviewed_profile_hash does not match current profile")

    # 空列表表示评审确实绑定当前设计。
    return list_errors

# 公开门禁组合结构、字段、哈希和批准状态检查。
def validate_design_review(
    project: Path,
    answers: dict[str, Any],
    review: Any,
    profile: dict[str, Any] | None = None,
    require_approval: bool = True,
) -> list[str]:
    """验证设计评审是否允许画像写入。

    参数：project 为项目根；answers 为问答；review 为评审载荷；profile 为可选画像；require_approval 控制是否强制批准。
    返回：所有阻断诊断；空列表表示评审有效。
    """

    # 第一阶段确认映射类型和必填字段。
    tuple_structure_result = _review_structure_errors(review)  # 评审结构验证结果。

    # 首项决定能否继续读取评审字段。
    list_structure_errors: list[str] = tuple_structure_result[0]  # 缺失或类型诊断。

    # 第二项是类型有效时的评审映射。
    dict_review: dict[str, Any] | None = tuple_structure_result[1]  # 已确认评审映射。

    # 结构不完整时不能安全读取后续字段。
    if list_structure_errors:

        # 保持缺失字段诊断的合同顺序。
        return list_structure_errors

    # 防御结构助手违反内部返回合同。
    if dict_review is None:

        # 与非映射输入保持相同稳定诊断。
        return ["design_review must be provided before --write"]

    # 第二阶段验证字段值并提取批准判断所需状态。
    tuple_value_result = _review_value_errors(dict_review)  # 评审字段验证结果。

    # 字段诊断允许与哈希问题共同返回。
    list_errors: list[str] = tuple_value_result[0]  # 累计评审诊断。

    # 规范化结论用于批准状态判断。
    str_verdict: str = tuple_value_result[1]  # 评审批准或拒绝结论。

    # 类型安全的列表用于检查待确认事项。
    list_confirmations: list[Any] = tuple_value_result[2]  # 待用户确认事项。

    # 当前设计哈希必须与评审记录完全一致。
    list_errors.extend(_review_hash_errors(project, answers, dict_review, profile))

    # 强制批准模式拒绝明确返工结论。
    if require_approval and str_verdict == "reject":

        # 写入前必须先修复评审发现的问题。
        list_errors.append("design_review verdict reject requires rework before --write")

    # 尚有用户决策时不能把评审视为最终批准。
    if require_approval and list_confirmations:

        # 所有确认项清空后才能重新提交评审。
        list_errors.append("design_review.required_user_confirmations must be empty before --write")

    # 空列表是画像写入门禁通过的唯一状态。
    return list_errors

# 状态机通过该轻量判断决定进入返工还是写入阶段。
def design_review_requires_rework(review: dict[str, Any]) -> bool:
    """判断评审是否要求返工或补充用户确认。

    参数：review 为字段已解析的设计评审映射。
    返回：结论为拒绝或确认项为非空列表时为真。
    """

    # 轻量状态判断同样忽略结论文本首尾空白和大小写。
    str_verdict = str(review.get("verdict", "")).strip().lower()  # 返工判断使用的结论。

    # 只有真实列表才能代表待用户确认事项。
    value_confirmations = review.get("required_user_confirmations")  # 原始用户确认字段。

    # 拒绝结论或非空确认列表都会阻断画像写入。
    return str_verdict == "reject" or (isinstance(value_confirmations, list) and bool(value_confirmations))
