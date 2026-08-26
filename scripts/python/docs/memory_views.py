"""生成有界 memory 摘要与显式完整导出。"""

# 视图合同使用 JSON 标签、路径和结构化条目类型。
import json
import re
from pathlib import Path
from typing import Any

# 存储层提供契约、时间和相对路径公共能力。
from memory_store import memory_contract, now_iso, rel

# 历史非英语内容只投影为英文检索指针，SQLite/JSONL 权威记录保持不变。
NON_ENGLISH_MEMORY_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")  # 非英语字符检测器

# 检查 memory 字段是否需要英文投影。
def _contains_non_english_memory_text(*values: object) -> bool:
    """判断待投影的 memory 字段是否包含非英语文本。

    参数：values 为待检查的标题、摘要和标签文本。
    返回：任一字段命中非英语字符时返回 True。
    """

    # 汇总所有字段的非英语命中状态。
    return any(NON_ENGLISH_MEMORY_RE.search(str(value or "")) for value in values)  # 汇总字段命中状态

# 将非英语 memory 条目转换为英文检索投影。
def _project_memory_item(item: dict[str, Any]) -> dict[str, Any]:
    """将非英语 memory 字段投影为英文检索元数据。

    参数：item 为 SQLite/JSONL 读取的结构化 memory 条目。
    返回：英文条目副本或原始英文条目。
    """

    # 提取条目标题以参与语言判断。
    str_title = str(item.get("title", "Untitled memory"))  # 原始标题文本

    # 提取摘要正文以参与语言判断。
    str_summary = str(item.get("summary", ""))  # 原始摘要文本

    # 提取标签 JSON 以参与语言判断。
    str_tags = str(item.get("tags_json", ""))  # 原始标签 JSON 文本

    # 英文判断只作用于当前投影字段。
    if not _contains_non_english_memory_text(str_title, str_summary, str_tags):

        # 英文条目无需改变权威字段。
        return item

    # 用稳定序号生成英文标题。
    str_sequence = str(item.get("sequence") or 0)  # 生成投影标题序号

    # 返回含英文标题、摘要和原始元数据的投影对象。
    return {
        **item,
        "title": f"Memory item {str_sequence}",
        "summary": (
            "Historical non-English content is omitted from this current English "
            "view. Retrieve the authoritative record by sequence, source reference, "
            "or source timestamp."
        ),
        "tags_json": "[]",
    }

# 单个 memory 条目渲染为摘要文档中的固定 Markdown 分块。
def memory_summary_lines(item: dict[str, Any], int_summary_limit: int = 600) -> list[str]:
    """把 memory 条目渲染为摘要 Markdown 行。

    Args:
        item: 数据库中的结构化 memory 条目。
        int_summary_limit: 有界视图允许保留的正文字符数。

    Returns:
        包含元数据和摘要正文的 Markdown 行。
    """

    # 当前条目的英文投影。
    dict_projected_item = _project_memory_item(item)  # 读取条目的英文投影

    # 标签 JSON 转换为便于人工阅读的逗号分隔文本。
    str_tags = ", ".join(json.loads(dict_projected_item.get("tags_json") or "[]"))  # memory 标签文本

    # 单条正文遵循有界视图合同；完整内容仍保留在 SQLite/JSONL。
    str_summary = str(dict_projected_item.get("summary", "")).strip()  # 当前投影摘要正文

    # 超限正文保留前缀并明确标记截断，避免读者误认完整内容。
    if len(str_summary) > int_summary_limit:

        # 截断标记不改变权威存储，只影响检索视图。
        str_summary = str_summary[:int_summary_limit].rstrip() + "… [truncated]"  # 有界视图正文

    # 固定字段顺序保证摘要文件 diff 稳定。
    return [
        f"## {dict_projected_item.get('title', 'Untitled memory')}",
        f"- Kind: {dict_projected_item.get('kind', 'note')}",
        f"- Sequence: {dict_projected_item.get('sequence') or 0}",
        f"- Updated: {dict_projected_item.get('updated_at', '')}",
        f"- Source ref: {dict_projected_item.get('source_ref') or 'not recorded'}",
        f"- Source timestamp: {dict_projected_item.get('source_timestamp') or 'not recorded'}",
        f"- Source: {dict_projected_item.get('source_path') or 'not recorded'}",
        f"- Tags: {str_tags or 'none'}",
        "",
        str_summary,
        "",
    ]

# 旧条目仅渲染稳定索引，不复制完整元数据和正文。
def memory_index_line(item: dict[str, Any]) -> str:
    """把旧 memory 条目压缩为一行检索索引。

    Args:
        item: 数据库中的结构化 memory 条目。

    Returns:
        包含序号、标题和来源引用的 Markdown 列表项。
    """

    # 当前索引条目的英文投影。
    dict_projected_item = _project_memory_item(item)  # 读取索引条目的英文投影

    # 来源引用优先于路径，二者都缺失时不生成空占位字段。
    str_source_ref = dict_projected_item.get("source_ref")  # 来源引用文本

    # 缺少引用时回退到来源路径。
    str_source_path = dict_projected_item.get("source_path")  # 来源路径文本

    # 合并来源并去除外围空白。
    str_source = str(str_source_ref or str_source_path or "").strip()  # 规范化来源文本

    # 后缀只承载真实来源，避免生成无信息的破折号。
    str_suffix = f" — {str_source}" if str_source else ""  # 仅在有信息时添加来源。

    # 序号让调用者可通过 memory-read 精确回查。
    int_sequence = int(dict_projected_item.get("sequence") or 0)  # 稳定序号

    # 返回序号、标题和来源组成的稳定索引行。
    return f"- {int_sequence}: {dict_projected_item.get('title', 'Untitled memory')}{str_suffix}"

# 完整导出路径必须留在 memory 根内且不能覆盖默认摘要。
def resolve_full_memory_output(
    project: Path,
    dict_paths: dict[str, Path],
    str_full_output: str,
) -> tuple[Path | None, list[str]]:
    """解析并校验显式完整导出目标。

    Args:
        project: 项目根目录。
        dict_paths: 归一化后的 memory 文件路径。
        str_full_output: 用户提供的完整导出相对路径。

    Returns:
        合法目标路径与错误列表；非法时目标为 None。
    """

    # 相对路径锚定 memory 根；绝对路径和父目录穿越均被拒绝。
    path_memory_root = (project / memory_contract(project)["folder"]).resolve()  # 完整导出边界

    # 用户路径在解析后仍必须位于上述边界内。
    path_full_output = (path_memory_root / str_full_output).resolve()  # 完整视图目标

    # relative_to 按路径组件判断归属，可防止同名前缀目录逃逸。
    try:

        # 能够相对化说明目标没有越过 memory 根。
        path_full_output.relative_to(path_memory_root)

    # 无法相对化时返回统一的导出边界错误。
    except ValueError:

        # 越界目标不能创建任何父目录或文件。
        return None, ["--full-output must stay under the memory root and must not overwrite summaries.md"]

    # 默认有界摘要绝不能被完整导出覆盖。
    if path_full_output == dict_paths["summaries"].resolve():

        # 覆盖请求与路径越界共享稳定的用户诊断。
        return None, ["--full-output must stay under the memory root and must not overwrite summaries.md"]

    # 合法目标交给写入函数创建父目录和正文。
    return path_full_output, []

# 完整导出只在显式请求后写入全部数据库摘要正文。
def write_full_memory_output(
    project: Path,
    path_full_output: Path,
    list_sorted_items: list[dict[str, Any]],
) -> str:
    """写入完整 memory Markdown 导出并返回相对路径。

    Args:
        project: 项目根目录。
        path_full_output: 已通过边界检查的导出目标。
        list_sorted_items: 按历史顺序排列的全部 memory 条目。

    Returns:
        仓库相对的完整导出路径。
    """

    # 标题明确完整导出的非权威、按需生成属性。
    list_full_lines = [  # 完整导出的标题和权威性声明
        "# Full Memory Export",  # 导出文档标题
        "",  # 标题与声明之间的空行
        "Generated on explicit request; SQLite and JSONL remain authoritative.",  # 权威存储边界
        "",  # 声明与条目之间的空行
    ]  # 完整导出正文容器

    # 完整导出逐条保留数据库中的全部摘要正文。
    for item in list_sorted_items:

        # 传入超过当前正文的限制以复用同一渲染合同。
        list_full_lines.extend(memory_summary_lines(item, len(str(item.get("summary", ""))) + 1))

    # 父目录只在显式导出路径下创建。
    path_full_output.parent.mkdir(parents=True, exist_ok=True)

    # 一次写入完整 Markdown，避免部分导出文件。
    path_full_output.write_text("\n".join(list_full_lines).rstrip() + "\n", encoding="utf-8")

    # 返回仓库相对路径作为可移植证据。
    return rel(project, path_full_output)

# 条目分区集中计算稳定顺序、详情窗口和历史索引窗口。
def partition_memory_items(
    list_items: list[dict[str, Any]],
    dict_summary_policy: dict[str, Any],
) -> dict[str, Any]:
    """按有界摘要策略划分 memory 条目。

    Args:
        list_items: 数据库中的全部 memory 条目。
        dict_summary_policy: 已归一化的有界摘要策略。

    Returns:
        排序全集、最近详情、旧索引和省略数量。
    """

    # 序号优先、更新时间次优先，保持摘要顺序稳定。
    list_sorted_items = sorted(  # 依据序号和更新时间生成稳定展示顺序
        list_items,  # 数据库中的全部 memory 条目
        key=lambda row: (  # 先按历史序号、再按更新时间排列
            int(row.get("sequence") or 0),  # 首要历史顺序键
            str(row.get("updated_at", "")),  # 次要更新时间键
        ),
    )

    # 两个窗口上限来自同一份摘要策略。
    int_recent_limit = int(dict_summary_policy["recent_detail_limit"])  # 最近详情条数

    # 历史标题窗口独立限制索引规模。
    int_older_limit = int(dict_summary_policy["older_index_limit"])  # 旧索引条数

    # 最近条目保留有限详情正文。
    list_recent_items = list_sorted_items[-int_recent_limit:] if int_recent_limit else []  # 最近详情

    # 详情窗口之前的条目均进入历史索引候选集合。
    list_older_items = list_sorted_items[:-int_recent_limit] if int_recent_limit else list_sorted_items  # 历史候选

    # 旧索引只保留距离当前最近的有限标题。
    list_indexed_older = list_older_items[-int_older_limit:] if int_older_limit else []  # 保留的历史索引条目

    # 省略计数让读者知道有界视图不代表完整历史。
    int_omitted = max(0, len(list_older_items) - len(list_indexed_older))  # 未展示条目数

    # 调用方复用同一分区生成有界视图和可选完整导出。
    return {
        "sorted": list_sorted_items,  # 完整稳定顺序
        "recent": list_recent_items,  # 最近详情窗口
        "indexed": list_indexed_older,  # 历史索引窗口
        "omitted": int_omitted,  # 窗口外条目数量
    }

# 有界 Markdown 渲染只消费已分区条目，不再重复窗口决策。
def bounded_memory_markdown(
    dict_partition: dict[str, Any],
    int_summary_limit: int,
) -> str:
    """渲染有界 memory 摘要 Markdown。

    Args:
        dict_partition: 已按摘要策略划分的条目集合。
        int_summary_limit: 单条摘要允许保留的字符数。

    Returns:
        具有稳定尾换行的有界 Markdown 文本。
    """

    # 文档头声明权威存储边界和精确回查入口。
    list_lines = [  # 摘要标题、更新时间和正文行的累计容器
        "# Memory Summaries",  # 摘要文档标题
        "",  # 标题与元数据之间的空行
        f"- Updated at: {now_iso()}",  # 本次压缩更新时间
        "- View: bounded; SQLite and JSONL remain authoritative.",  # 视图与权威存储边界
        '- Retrieve: `python skills/agents-md-generator/scripts/python/docs/manage_docs.py '
        'memory-read <project> --query "<text>" --limit 5`',  # 按需回查完整条目的命令
        "",  # 元数据与条目正文之间的空行
    ]

    # 空数据库仍生成可解释的摘要文件。
    if not dict_partition["sorted"]:

        # 占位文本区分空库与压缩失败。
        list_lines.append("No memory items recorded yet.")

    # 非空旧集合先输出紧凑索引和省略说明。
    if dict_partition["indexed"]:

        # 索引保持单行，并在尾部记录未展示数量。
        list_lines.extend(["## Older index", ""])

        # 每条历史索引保持单行，便于浏览和检索。
        list_lines.extend(memory_index_line(item) for item in dict_partition["indexed"])

        # 索引尾部记录未展示数量并恢复段落边界。
        list_lines.extend(["", f"Older items omitted: {dict_partition['omitted']}.", ""])

    # 最近条目仍以独立 Markdown 分块展示。
    for item in dict_partition["recent"]:

        # extend 保留渲染函数提供的行边界。
        list_lines.extend(memory_summary_lines(item, int_summary_limit))

    # 尾部统一保留一个换行，便于版本控制 diff。
    return "\n".join(list_lines).rstrip() + "\n"

# 可选完整导出把路径校验与写入结果统一为无副作用报告。
def export_full_memory_if_requested(
    project: Path,
    dict_paths: dict[str, Path],
    dict_partition: dict[str, Any],
    str_full_output: str | None,
) -> tuple[str | None, list[str]]:
    """按显式请求生成完整 memory 导出。

    Args:
        project: 项目根目录。
        dict_paths: 归一化后的 memory 文件路径。
        dict_partition: 已按摘要策略划分的条目集合。
        str_full_output: 可选的完整导出相对路径。

    Returns:
        已写入的相对路径和错误列表。
    """

    # 未显式请求时不创建完整导出文件。
    if not str_full_output:

        # None 证明默认压缩路径只写入有界摘要。
        return None, []

    # 专用解析器统一检查根目录穿越和默认摘要覆盖。
    tuple_full_resolution = resolve_full_memory_output(  # 完整导出路径校验结果
        project,  # 当前项目根目录
        dict_paths,  # 默认有界摘要路径用于防覆盖
        str_full_output,  # 用户提供的导出相对路径
    )

    # 校验结果拆出可选目标和稳定诊断。
    path_full_output = tuple_full_resolution[0]  # 已校验完整导出路径

    # 错误列表保持解析器给出的边界或覆盖诊断。
    list_full_errors = tuple_full_resolution[1]  # 完整导出路径错误

    # 路径错误时不能创建任何导出父目录或文件。
    if list_full_errors:

        # 原样返回解析器诊断，供压缩报告合并。
        return None, list_full_errors

    # 防御性分支处理解析器合同漂移。
    if path_full_output is None:

        # 理论不可达分支仍提供可操作错误。
        return None, ["full memory output path resolution failed"]

    # 合法路径使用完整稳定顺序写入全部摘要正文。
    str_full_written = write_full_memory_output(  # 完整导出的相对路径
        project,  # 导出路径相对化所用项目根
        path_full_output,  # 已通过边界检查的目标
        dict_partition["sorted"],  # 全部条目的稳定顺序
    )

    # 空错误列表证明完整导出成功完成。
    return str_full_written, []
