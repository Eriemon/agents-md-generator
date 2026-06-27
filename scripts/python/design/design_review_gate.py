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
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

# 导入 脚本治理 所需的依赖模块。
from design_profile_builder import build_profile
from design_questions import DESIGN_REVIEW_KEY, EXTRA_REQUIREMENTS_KEY, normalize_extra_requirements


# 保留 DESIGN REVIEW REQUIRED FIELDS 中间值，支撑 模块入口 的当前计算步骤。
DESIGN_REVIEW_REQUIRED_FIELDS = [  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "reviewer_type",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "verdict",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "findings",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "required_user_confirmations",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "reviewed_answers_hash",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "reviewed_profile_hash",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
    "review_summary",  # DESIGN REVIEW REQUIRED FIELDS 用于本步治理判断
]
def answers_without_design_review(answers: dict[str, Any]) -> dict[str, Any]:

    # 保留 clean 中间值，支撑 answers_without_design_review 的当前计算步骤。
    clean = {key: value for key, value in answers.items() if key != DESIGN_REVIEW_KEY}  # clean 用于本步治理判断

    # 检查 answers_without_design_review 的当前条件是否需要进入专门分支。
    if EXTRA_REQUIREMENTS_KEY in clean:

        # 保留 中间载荷 中间值，支撑 answers_without_design_review 的当前计算步骤。
        clean[EXTRA_REQUIREMENTS_KEY] = normalize_extra_requirements(clean.get(EXTRA_REQUIREMENTS_KEY))  # 中间载荷 用于本步治理判断

    # 返回 answers_without_design_review 已整理完成的调用载荷。
    return clean


# 定义 stable_json_hash 的脚本治理处理入口。
def stable_json_hash(value: Any) -> str:

    # 保留 payload 中间值，支撑 stable_json_hash 的当前计算步骤。
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # payload 用于本步治理判断

    # 返回 stable_json_hash 已整理完成的调用载荷。
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# 定义 profile_for_design_review 的脚本治理处理入口。
def profile_for_design_review(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:

    # 收集 clean answers 条目，保持 profile_for_design_review 的处理顺序稳定。
    dict_clean_answers = answers_without_design_review(answers)  # clean answers 用于本步治理判断

    # 收集 profile、errors 条目，保持 profile_for_design_review 的处理顺序稳定。
    profile, errors = build_profile(project, dict_clean_answers)  # profile、errors 用于本步治理判断

    # 检查 profile_for_design_review 的当前条件是否需要进入专门分支。
    if errors:

        # 返回 profile_for_design_review 已整理完成的调用载荷。
        return None, errors

    # 说明该控制语句在脚本治理流程中的分支职责。
    assert profile is not None

    # 调用 pop 完成 profile_for_design_review 的当前动作。
    profile.pop(DESIGN_REVIEW_KEY, None)

    # 返回 profile_for_design_review 已整理完成的调用载荷。
    return profile, []


# 定义 design_review_hashes 的脚本治理处理入口。
def design_review_hashes(project: Path, answers: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, str]:

    # 收集 clean answers 条目，保持 design_review_hashes 的处理顺序稳定。
    dict_clean_answers = answers_without_design_review(answers)  # clean answers 用于本步治理判断

    # 保留 profile for hash 中间值，支撑 design_review_hashes 的当前计算步骤。
    tuple_profile_for_hash = profile  # profile for hash 用于本步治理判断

    # 检查 design_review_hashes 的当前条件是否需要进入专门分支。
    if tuple_profile_for_hash is None:

        # 收集 profile for hash、errors 条目，保持 design_review_hashes 的处理顺序稳定。
        tuple_profile_for_hash, tuple_errors = profile_for_design_review(project, dict_clean_answers)  # profile for hash、errors 用于本步治理判断

        # 检查 design_review_hashes 的当前条件是否需要进入专门分支。
        if tuple_errors:

            # 抛出 design_review_hashes 已确认的阻断原因。
            raise ValueError("; ".join(tuple_errors))

    # 说明该控制语句在脚本治理流程中的分支职责。
    assert tuple_profile_for_hash is not None

    # 保留 profile for hash 中间值，支撑 design_review_hashes 的当前计算步骤。
    tuple_profile_for_hash = {key: value for key, value in tuple_profile_for_hash.items() if key != DESIGN_REVIEW_KEY}  # profile for hash 用于本步治理判断

    # 返回 design_review_hashes 已整理完成的调用载荷。
    return {
        "reviewed_answers_hash": stable_json_hash(dict_clean_answers),
        "reviewed_profile_hash": stable_json_hash(tuple_profile_for_hash),
    }


# 定义 design_review_request 的脚本治理处理入口。
def design_review_request(project: Path, answers: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:

    # 收集 hashes 条目，保持 design_review_request 的处理顺序稳定。
    dict_hashes = design_review_hashes(project, answers, profile)  # hashes 用于本步治理判断

    # 返回 design_review_request 已整理完成的调用载荷。
    return {
        "kind": "design_review",
        "required_reviewer_type": "subagent",
        "required_fields": DESIGN_REVIEW_REQUIRED_FIELDS,
        "reviewed_answers_hash": dict_hashes["reviewed_answers_hash"],
        "reviewed_profile_hash": dict_hashes["reviewed_profile_hash"],
        "instructions": [
            "Spawn a new review subagent after final alignment.",
            "Ask the subagent to review the full answers and profile for design, gate, folder, version, branch, and user-confirmation risks.",
            (
                "Submit the returned JSON as design_review; do not write "  # AGENTS 长文本片段
                ".agents/agents-control.json until it approves with matching hashes and no "  # AGENTS 长文本片段
                "pending user confirmations."  # AGENTS 长文本片段
            ),
        ],
    }


# 定义 validate_design_review 的脚本治理处理入口。
def validate_design_review(
    project: Path,
    answers: dict[str, Any],
    review: Any,
    profile: dict[str, Any] | None = None,
    require_approval: bool = True,
) -> list[str]:

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if not isinstance(review, dict):

        # 返回 validate_design_review 已整理完成的调用载荷。
        return ["design_review must be provided before --write"]

    # 收集 errors 条目，保持 validate_design_review 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 逐项推进 validate_design_review 的候选项检查。
    for field in DESIGN_REVIEW_REQUIRED_FIELDS:

        # 检查 validate_design_review 的当前条件是否需要进入专门分支。
        if field not in review:

            # 调用 append 完成 validate_design_review 的当前动作。
            list_errors.append(f"design_review.{field} is required")

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if list_errors:

        # 返回 validate_design_review 已整理完成的调用载荷。
        return list_errors

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if review.get("reviewer_type") != "subagent":

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.reviewer_type must be subagent")

    # 保留 verdict 中间值，支撑 validate_design_review 的当前计算步骤。
    verdict = str(review.get("verdict", "")).strip().lower()  # verdict 用于本步治理判断

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if verdict not in {"approve", "reject"}:

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.verdict must be approve or reject")

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if not isinstance(review.get("findings"), list):

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.findings must be a list")

    # 收集 confirmations 条目，保持 validate_design_review 的处理顺序稳定。
    list_confirmations = review.get("required_user_confirmations")  # confirmations 用于本步治理判断

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if not isinstance(list_confirmations, list):

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.required_user_confirmations must be a list")

        # 收集 confirmations 条目，保持 validate_design_review 的处理顺序稳定。
        list_confirmations = []  # confirmations 用于本步治理判断

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if not str(review.get("review_summary", "")).strip():

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.review_summary must be non-empty")

    # 保护 validate_design_review 中允许失败的外部访问。
    try:

        # 收集 hashes 条目，保持 validate_design_review 的处理顺序稳定。
        dict_hashes = design_review_hashes(project, answers, profile)  # hashes 用于本步治理判断
    except ValueError as exc:

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append(f"design_review hash could not be computed: {exc}")

        # 收集 hashes 条目，保持 validate_design_review 的处理顺序稳定。
        dict_hashes = {}  # hashes 用于本步治理判断

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if dict_hashes and review.get("reviewed_answers_hash") != dict_hashes["reviewed_answers_hash"]:

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.reviewed_answers_hash does not match current answers")

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if dict_hashes and review.get("reviewed_profile_hash") != dict_hashes["reviewed_profile_hash"]:

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.reviewed_profile_hash does not match current profile")

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if require_approval and verdict == "reject":

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review verdict reject requires rework before --write")

    # 检查 validate_design_review 的当前条件是否需要进入专门分支。
    if require_approval and list_confirmations:

        # 调用 append 完成 validate_design_review 的当前动作。
        list_errors.append("design_review.required_user_confirmations must be empty before --write")

    # 返回 validate_design_review 已整理完成的调用载荷。
    return list_errors


# 定义 design_review_requires_rework 的脚本治理处理入口。
def design_review_requires_rework(review: dict[str, Any]) -> bool:

    # 收集 confirmations 条目，保持 design_review_requires_rework 的处理顺序稳定。
    confirmations = review.get("required_user_confirmations")  # confirmations 用于本步治理判断

    # 返回 design_review_requires_rework 已整理完成的调用载荷。
    return str(review.get("verdict", "")).strip().lower() == "reject" or (isinstance(confirmations, list) and bool(confirmations))


