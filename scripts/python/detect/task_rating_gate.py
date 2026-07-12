"""根据任务文本推断难度与规模，并决定是否需要用户确认。"""

# 延迟解析类型注解，保持脚本兼容 Python 3.10+。
from __future__ import annotations

# 标准库负责 CLI、JSON、正则、模块路径和类型表达。
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

# 直接执行分类脚本时需要显式暴露 common 等兄弟任务模块。
def extend_task_module_search_path() -> None:
    """把 scripts/python 的任务目录加入模块搜索路径。

    参数:
        无。

    返回:
        无，直接更新当前解释器的 ``sys.path``。
    """

    # 当前文件的父级任务目录统一位于 scripts/python 根下。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # Python 任务脚本根目录

    # 仅直接子目录可能成为兄弟任务模块的导入根。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 普通文件不能作为顶层模块搜索目录。
        if not path_task_directory.is_dir():

            # 跳过 scripts/python 根下的非目录条目。
            continue

        # sys.path 使用字符串保存搜索目录。
        str_task_directory = str(path_task_directory)  # 当前兄弟任务目录字符串

        # 已存在路径保持原有优先级，避免重复插入。
        if str_task_directory in sys.path:

            # 当前任务目录已经可导入，无需修改解释器状态。
            continue

        # 仓库任务目录优先于解释器默认搜索位置。
        sys.path.insert(0, str_task_directory)

# 完成兄弟任务模块引导后再导入项目共享能力。
extend_task_module_search_path()

# 共享路径策略验证并规范化用户传入的项目根。
from agents_common import resolve_project

# 难度顺序用于比较启发式候选是否需要升级。
DIFFICULTY_ORDER = [  # 难度等级从低到高
    "simple",  # 简单任务
    "normal",  # 普通任务
    "hard",  # 困难任务
    "hell",  # 地狱级任务
    "nightmare",  # 噩梦级任务
]

# 规模顺序用于比较任务影响范围是否需要升级。
SCALE_ORDER = [  # 任务规模从小到大
    "micro",  # 微型改动
    "small",  # 小型改动
    "medium",  # 中型改动
    "large",  # 大型改动
    "project",  # 项目级改动
]

# 难度别名覆盖英文、简体中文和繁体中文表达。
DIFFICULTY_ALIASES = {  # 规范难度到用户表达别名
    "simple": ["simple", "easy", "trivial", "简单", "輕量", "轻量"],  # 简单难度别名
    "normal": ["normal", "ordinary", "standard", "普通", "一般"],  # 普通难度别名
    "hard": ["hard", "difficult", "困难", "困難"],  # 困难难度别名
    "hell": ["hell", "地狱", "地獄"],  # 地狱难度别名
    "nightmare": ["nightmare", "噩梦", "噩夢"],  # 噩梦难度别名
}

# 规模别名覆盖常见工程表达和中英文变体。
SCALE_ALIASES = {  # 规范规模到用户表达别名
    "micro": ["micro", "tiny", "one-line", "微型", "极小", "很小"],  # 微型规模别名
    "small": ["small", "小型", "小"],  # 小型规模别名
    "medium": ["medium", "中型", "中等"],  # 中型规模别名
    "large": ["large", "big", "大型", "大"],  # 大型规模别名
    "project": ["project", "program", "项目级", "專案級", "工程级"],  # 项目级规模别名
}

# 复杂任务关键词覆盖架构、迁移、发布、远程和跨模块变更。
COMPLEX_KEYWORDS = {  # 触发复杂度升级的文本信号
    "architecture", "架构", "架構", "migration", "migrate", "迁移",  # 架构与迁移信号
    "release", "发布", "remote", "远程", "debugging", "debug", "调试",  # 发布远程调试信号
    "complex", "复杂", "多模块", "multi-module", "multiple modules",  # 显式复杂与多模块信号
    "multiple services", "多阶段", "multi-stage", "refactor", "重构", "重構",  # 多服务阶段与重构信号
    "breaking change", "public api", "schema", "database", "deployment", "部署",  # 接口数据部署信号
}

# 不确定性关键词表示任务范围仍可能需要用户确认。
UNCLEAR_KEYWORDS = {  # 需求不清晰文本信号
    "unclear", "unknown", "not sure", "maybe", "不确定", "不明", "需求不清", "看情况",  # 模糊需求表达
}

# 低风险关键词用于识别单一文档或措辞类微型任务。
SIMPLE_KEYWORDS = {  # 低风险文本信号
    "readme", "docs", "documentation", "wording", "typo", "comment", "rename",  # 英文文档措辞信号
    "文档", "说明", "错别字",  # 中文文档措辞信号
}

# 文本比较统一使用 Unicode 感知的大小写折叠。
def norm_text(value: str) -> str:
    """归一化评分匹配文本。

    参数:
        value: 用户任务文本或上下文摘要。

    返回:
        经过 Unicode 大小写折叠的文本。
    """

    # casefold 比 lower 更适合跨语言大小写匹配。
    return value.casefold()

# 英文别名使用单词边界，中文别名保持直接字面匹配。
def alias_pattern(alias: str) -> str:
    """构造单个评分别名的安全正则片段。

    参数:
        alias: 用户可能使用的难度或规模表达。

    返回:
        已转义并带适用边界的正则片段。
    """

    # 含拉丁字符的别名需要避免命中更长单词内部。
    if re.search(r"[A-Za-z0-9_-]", alias):

        # 单词边界保持 easy 与 uneasy 等文本相互隔离。
        return rf"\b{re.escape(alias.casefold())}\b"

    # 中文表达直接转义，不添加不可靠的单词边界。
    return re.escape(alias.casefold())

# 显式评分要求标签、赋值连接词和别名连续出现。
def find_explicit_value(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:
    """查找带 difficulty 或 scale 标签的显式评分。

    参数:
        text: 待检查的任务与上下文文本。
        aliases: 规范值到可接受别名的映射。
        labels: 当前评分维度的中英文标签。

    返回:
        命中的规范评分值；未命中时返回空字符串。
    """

    # 所有评分比较都在归一化文本上执行。
    str_lowered = norm_text(text)  # 大小写折叠后的任务文本

    # 标签通过转义后合并，防止特殊字符改变正则结构。
    str_label_pattern = "|".join(re.escape(label.casefold()) for label in labels)  # 评分维度标签正则

    # 规范值顺序决定多个显式评分并存时的稳定首选项。
    for str_canonical, list_names in aliases.items():

        # 每个用户表达都复用同一标签与连接词合同。
        for str_name in list_names:

            # 显式形式支持冒号、等号及中英文“是/为”。
            str_pattern = (  # 当前显式评分正则
                rf"(?:{str_label_pattern})\s*(?:[:=：]|是|为|為)\s*{alias_pattern(str_name)}"  # 标签赋值形式
            )

            # 第一个命中值按别名声明顺序返回。
            if re.search(str_pattern, str_lowered):

                # 返回规范值而不是用户输入变体。
                return str_canonical

    # 没有显式标签评分时交给上下文匹配入口。
    return ""

# 上下文评分允许“困难级”或“任务是 hard”等自然语言形式。
def find_contextual_rating(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:
    """从自然语言上下文中查找难度或规模评分。

    参数:
        text: 待检查的任务与上下文文本。
        aliases: 规范值到可接受别名的映射。
        labels: 当前评分维度的中英文标签。

    返回:
        命中的规范评分值；未命中时返回空字符串。
    """

    # 上下文语句先归一化，确保英文难度别名匹配不区分大小写。
    str_lowered = norm_text(text)  # 上下文评分匹配文本

    # 维度标签用于识别“hard difficulty”等形式。
    str_label_pattern = "|".join(re.escape(label.casefold()) for label in labels)  # 上下文评分标签正则

    # 别名声明顺序提供确定性匹配优先级。
    for str_canonical, list_names in aliases.items():

        # 每个别名生成等级后缀与任务主语两类模式。
        for str_name in list_names:

            # 当前别名先应用中英文边界策略。
            str_alias = alias_pattern(str_name)  # 当前评分别名正则

            # 两种自然语言结构覆盖等级后缀和任务判断句。
            tuple_patterns = (  # 当前别名的上下文正则集合
                rf"{str_alias}\s*(?:级|級|等级|等級|{str_label_pattern})",  # 等级后缀形式
                rf"(?:任务|task|问题|problem)\s*(?:是|为|為|属于|屬於|算)?\s*{str_alias}",  # 任务判断形式
            )

            # 任一结构命中即可返回对应规范值。
            if any(re.search(str_pattern, str_lowered) for str_pattern in tuple_patterns):

                # 返回规范值保证下游顺序比较稳定。
                return str_canonical

    # 没有上下文评分时由启发式关键词决定默认值。
    return ""

# 关键词计数按集合成员去重，同一词多次出现只贡献一次信号。
def count_matches(text: str, keywords: set[str]) -> int:
    """统计文本中命中的不同关键词数量。

    参数:
        text: 待评分的任务文本。
        keywords: 当前信号类别的去重关键词集合。

    返回:
        至少出现一次的不同关键词数量。
    """

    # 风险信号计数前统一折叠大小写，避免同一英文词出现两种结果。
    str_lowered = norm_text(text)  # 关键词信号匹配文本

    # 集合迭代只统计不同关键词是否出现，不累计重复次数。
    return sum(1 for str_keyword in keywords if str_keyword.casefold() in str_lowered)

# 等级升级只允许向顺序表中更高风险的候选移动。
def max_level(current: str, candidate: str, order: list[str]) -> str:
    """返回两个等级中顺序更高的值。

    参数:
        current: 当前已选等级。
        candidate: 新的候选等级。
        order: 从低到高排列的合法等级表。

    返回:
        风险顺序较高的等级。

    异常:
        ValueError: 任一等级不在顺序表中。
    """

    # index 比较同时验证输入等级均属于合法集合。
    return candidate if order.index(candidate) > order.index(current) else current

# 用户评分解析集中处理显式值与自然语言上下文的优先级。
def find_user_ratings(text: str) -> tuple[str, str, bool]:
    """解析用户提供的难度和规模。

    参数:
        text: 合并后的任务与上下文文本。

    返回:
        用户难度、用户规模以及是否存在显式评分。
    """

    # 带标签的显式评分优先于任何上下文表达。
    str_explicit_difficulty = find_explicit_value(  # 用户显式难度
        text,  # 评分输入文本
        DIFFICULTY_ALIASES,  # 难度别名集合
        ("difficulty", "难度", "難度"),  # 难度标签集合
    )

    # 规模维度允许独立于难度维度提供。
    str_explicit_scale = find_explicit_value(  # 用户显式规模
        text,  # 规模扫描文本
        SCALE_ALIASES,  # 规模别名集合
        ("scale", "规模", "規模"),  # 规模标签集合
    )

    # 只有缺失的维度才允许从自然语言上下文回退解析。
    str_contextual_difficulty = "" if str_explicit_difficulty else find_contextual_rating(  # 上下文难度
        text,  # 上下文扫描文本
        DIFFICULTY_ALIASES,  # 上下文难度别名
        ("difficulty", "难度", "難度"),  # 上下文难度标签
    )

    # 规模上下文仅补充用户尚未显式提供的维度。
    str_contextual_scale = "" if str_explicit_scale else find_contextual_rating(  # 上下文规模
        text,  # 规模上下文扫描文本
        SCALE_ALIASES,  # 上下文规模别名
        ("scale", "规模", "規模"),  # 上下文规模标签
    )

    # 三元组保留每个维度的最终来源和显式评分状态。
    return (
        str_explicit_difficulty or str_contextual_difficulty,
        str_explicit_scale or str_contextual_scale,
        bool(str_explicit_difficulty or str_explicit_scale),
    )

# 后续动作只依赖最终评分，不参与评分本身的计算。
def build_recommended_actions(
    ask_user_rating: bool,
    difficulty: str,
    scale: str,
) -> list[str]:
    """根据最终评级构造稳定顺序的治理动作。

    参数:
        ask_user_rating: 是否需要请求用户确认评级。
        difficulty: 最终难度等级。
        scale: 最终规模等级。

    返回:
        按执行顺序排列的治理动作。
    """

    # 任何任务都先检查仓库中已有的实现模式。
    list_actions = ["inspect existing patterns before editing"]  # 建议执行动作

    # 未评级的高风险任务需要先确认难度和规模。
    if ask_user_rating:

        # 确认动作在复用研究之前执行。
        list_actions.append("ask user to confirm difficulty and scale")

    # 最高风险任务需要先研究可复用资产并留下审计记录。
    if difficulty in {"hell", "nightmare"} or scale == "project":

        # 两项研究动作保持固定相邻顺序。
        list_actions.extend(
            [
                "reuse-first research",
                "record candidate tools, libraries, templates, open-source projects, fit, risks, and rejection reasons",
            ]
        )

    # 项目级任务还需要可调整的阶段计划。
    if difficulty == "nightmare" or scale == "project":

        # 阶段拆分与变更响应要求作为一组输出。
        list_actions.extend(
            [
                "split into multi-stage project plan",
                "keep the project plan adjustable when the user changes requirements",
            ]
        )

    # 调用方按此顺序执行治理动作。
    return list_actions

# 关键词阈值只调整用户未明确指定的评分维度。
def apply_keyword_rating(
    tuple_current_rating: tuple[str, str],
    tuple_user_rating: tuple[str, str],
    tuple_signal_hits: tuple[int, int, int],
) -> tuple[str, str, str]:
    """应用复杂、简单关键词阈值并返回对应原因。

    参数:
        tuple_current_rating: 当前难度和规模。
        tuple_user_rating: 用户提供的难度和规模。
        tuple_signal_hits: 复杂、不清晰和简单信号数量。

    返回:
        调整后的难度、规模和可选原因文本。

    形状:
        输入和输出均为固定长度元组，不包含数组维度。

    数据类型:
        评分为字符串，信号计数为整数。

    单位:
        信号值是关键词命中个数，无物理单位。
    """

    # 输入元组按稳定位置拆分为评分规则所需字段。
    str_difficulty = tuple_current_rating[0]  # 当前难度

    # 当前规模与难度保持独立升级。
    str_scale = tuple_current_rating[1]  # 当前规模

    # 用户难度用于锁定对应维度。
    str_user_difficulty = tuple_user_rating[0]  # 用户难度

    # 用户规模用于锁定对应维度。
    str_user_scale = tuple_user_rating[1]  # 用户规模

    # 信号元组顺序与三个关键词集合一致。
    int_complex_hits = tuple_signal_hits[0]  # 复杂信号数

    # 不清晰信号参与简单任务排除判断。
    int_unclear_hits = tuple_signal_hits[1]  # 不清晰信号数

    # 简单信号仅在其他风险信号为空时生效。
    int_simple_hits = tuple_signal_hits[2]  # 简单信号数

    # 六个以上复杂信号提升到最高自动推断等级。
    if int_complex_hits >= 6:

        # 用户没有锁定难度时才应用最高阈值。
        if not str_user_difficulty:

            # 当前难度只向更高风险等级移动。
            str_difficulty = max_level(str_difficulty, "hell", DIFFICULTY_ORDER)  # 高复杂度难度

        # 用户没有锁定规模时才提升到项目级。
        if not str_user_scale:

            # 当前规模只向更高风险等级移动。
            str_scale = max_level(str_scale, "project", SCALE_ORDER)  # 高复杂度规模

        # 最高阈值使用独立原因，便于审计触发来源。
        return str_difficulty, str_scale, "many complex-task signals detected"

    # 三到五个复杂信号至少提升到困难、大型。
    if int_complex_hits >= 3:

        # 用户难度存在时保持原值。
        if not str_user_difficulty:

            # 中等复杂密度至少提升到 hard。
            str_difficulty = max_level(str_difficulty, "hard", DIFFICULTY_ORDER)  # 中复杂度难度

        # 用户规模存在时保持原值。
        if not str_user_scale:

            # 多个复杂信号至少提升到 large。
            str_scale = max_level(str_scale, "large", SCALE_ORDER)  # 中复杂度规模

        # 中等级阈值保留自己的原因文本。
        return str_difficulty, str_scale, "multiple complex-task signals detected"

    # 仅有简单信号时允许降为简单微型任务。
    if int_simple_hits and int_complex_hits == 0 and int_unclear_hits == 0:

        # 用户值仍覆盖简单关键词推断。
        return (
            str_user_difficulty or "simple",
            str_user_scale or "micro",
            "single low-risk documentation or wording task",
        )

    # 未触发关键词阈值时保持当前评分。
    return str_difficulty, str_scale, ""

# 评分主入口先尊重用户显式值，再使用启发式信号补足缺失维度。
def infer_from_text(task_text: str, context_summary: str = "") -> dict[str, Any]:
    """推断任务难度、规模、置信度和建议动作。

    参数:
        task_text: 用户当前任务文本。
        context_summary: 可选的已知任务上下文摘要。

    返回:
        包含确认需求、推断值、原因和建议动作的评分载荷。
    """

    # 空文本片段不进入组合结果，避免产生多余分隔符。
    str_combined = " ".join(part for part in [task_text, context_summary] if part)  # 合并后的判定语料

    # 用户评级解析保持显式表达优先，并允许只提供一个维度。
    tuple_user_ratings = find_user_ratings(str_combined)  # 用户评分解析结果

    # 分项读取避免把多目标赋值误判为同一容器类型。
    str_user_difficulty = tuple_user_ratings[0]  # 用户提供的难度

    # 规模维度可独立为空。
    str_user_scale = tuple_user_ratings[1]  # 用户提供的规模

    # 显式标志用于区分原因文本。
    bool_explicit_rating = tuple_user_ratings[2]  # 是否存在显式评分

    # 未提供难度时从普通任务起步。
    str_difficulty = str_user_difficulty or "normal"  # 当前推断难度

    # 未提供规模时从小型任务起步。
    str_scale = str_user_scale or "small"  # 当前推断规模

    # 原因列表按评分决策顺序解释最终结果。
    list_reasons: list[str] = []  # 评分原因列表

    # 显式评分存在时不得再次询问同一信息。
    if bool_explicit_rating:

        # 原因文本成为机器可读评分载荷的一部分。
        list_reasons.append("explicit user rating found; do not ask again")

    # 上下文评分同样代表用户已表达等级。
    elif str_user_difficulty or str_user_scale:

        # 上下文来源与显式来源分开记录，便于审计。
        list_reasons.append("contextual user rating found; do not ask again")

    # 三类关键词信号分别计数，供阈值规则组合判断。
    int_complex_hits = count_matches(str_combined, COMPLEX_KEYWORDS)  # 复杂任务信号数

    # 不确定信号会降低置信度并可能要求用户确认。
    int_unclear_hits = count_matches(str_combined, UNCLEAR_KEYWORDS)  # 不清晰需求信号数

    # 简单信号仅在没有复杂或不确定信号时降级任务。
    int_simple_hits = count_matches(str_combined, SIMPLE_KEYWORDS)  # 低风险任务信号数

    # 阈值升级集中处理，并返回本轮决策原因。
    tuple_keyword_rating = apply_keyword_rating(  # 关键词评分结果
        (str_difficulty, str_scale),  # 当前评分
        (str_user_difficulty, str_user_scale),  # 用户评分
        (int_complex_hits, int_unclear_hits, int_simple_hits),  # 关键词命中数
    )

    # 三元组首项是阈值调整后的难度。
    str_difficulty = tuple_keyword_rating[0]  # 阈值调整后的难度

    # 三元组第二项是阈值调整后的规模。
    str_scale = tuple_keyword_rating[1]  # 阈值调整后的规模

    # 可选原因为空时表示没有触发关键词阈值。
    str_keyword_reason = tuple_keyword_rating[2]  # 关键词评分原因

    # 仅在阈值确实触发时追加原因。
    if str_keyword_reason:

        # 原因列表维持评分决策发生顺序。
        list_reasons.append(str_keyword_reason)

    # 任何不确定关键词都进入原因列表。
    if int_unclear_hits:

        # 调用方可据此解释为什么需要确认。
        list_reasons.append("unclear requirement signal detected")

    # 没有其他信号时记录普通默认判断。
    if not list_reasons:

        # 默认原因明确表示未发现高风险信号。
        list_reasons.append("no high-risk task signals detected")

    # 任一用户评分维度存在即视为用户已参与评级。
    bool_user_rating = bool(str_user_difficulty or str_user_scale)  # 用户是否已给出评级

    # 高风险或不清晰任务在用户未评级时建议确认。
    bool_ask_user_rating = not bool_user_rating and (  # 是否需要用户确认评级
        int_unclear_hits > 0  # 需求不清时需要确认
        or int_complex_hits >= 3  # 多个复杂信号需要确认
        or str_difficulty in {"hard", "hell", "nightmare"}  # 高难度需要确认
        or str_scale in {"large", "project"}  # 大范围需要确认
    )

    # 用户评分或纯低风险信号提供高置信度，其余默认中等。
    str_confidence = (  # 当前评分置信度
        "high"  # 用户评级或纯低风险任务的置信度
        if bool_user_rating or (int_simple_hits and int_complex_hits == 0 and int_unclear_hits == 0)  # 高置信条件
        else "medium"  # 无明确评级的普通任务置信度
    )

    # 需求不清且需要确认时置信度降为低。
    if bool_ask_user_rating and int_unclear_hits:

        # 低置信度提示调用方不要直接据此扩大执行范围。
        str_confidence = "low"  # 不清晰且需确认时的置信度

    # 动作构造与评分计算分离，保证输出顺序稳定。
    list_actions = build_recommended_actions(  # 最终治理动作序列
        bool_ask_user_rating,  # 是否先确认评级
        str_difficulty,  # 最终难度
        str_scale,  # 最终规模
    )

    # 返回稳定字段集合供 CLI 和其他治理入口消费。
    return {
        "ask_user_rating": bool_ask_user_rating,  # 是否建议询问用户评级
        "inferred_difficulty": str_difficulty,  # 最终难度等级
        "inferred_scale": str_scale,  # 最终规模等级
        "confidence": str_confidence,  # 评分置信度
        "reasons": list_reasons,  # 最终评分决策原因
        "recommended_actions": list_actions,  # 后续治理动作列表
    }

# CLI 参数保持任务文本必填，项目根和上下文摘要可选。
def parse_args() -> argparse.Namespace:
    """解析 task rating CLI 参数。

    参数:
        无。

    返回:
        包含项目根、任务文本、上下文和输出选项的命名空间。
    """

    # 解析器描述说明本工具只提供启发式建议。
    argument_parser = argparse.ArgumentParser(  # task rating 参数解析器
        description="Heuristically decide whether a task needs user difficulty/scale rating."  # CLI 帮助摘要
    )

    # 项目根用于路径验证和未来上下文扩展。
    argument_parser.add_argument(
        "--project",
        default=".",
        help="Current project root. Used for path validation and future context hooks.",
    )

    # 当前任务文本是评分的唯一必填输入。
    argument_parser.add_argument("--task-text", required=True, help="User task text to classify.")

    # 已知上下文可补充任务文本中未重复的事实。
    argument_parser.add_argument(
        "--context-summary",
        default="",
        help="Optional concise known context for the task.",
    )

    # 保留 json 开关兼容旧调用方，文本模式仍输出稳定 JSON。
    argument_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON. Text mode also emits JSON for stable automation.",
    )

    # 返回 argparse 完成校验后的参数对象。
    return argument_parser.parse_args()

# CLI 主入口验证项目根、计算评分并输出稳定 JSON。
def main() -> None:
    """执行 task rating CLI。

    参数:
        无。

    返回:
        无，评分载荷写入标准输出。
    """

    # 参数解析由 argparse 负责必填项和帮助输出。
    namespace_arguments = parse_args()  # 已解析 CLI 参数

    # 项目根必须通过共享路径安全策略。
    path_project = resolve_project(namespace_arguments.project)  # 规范化项目根

    # 推断函数保持纯文本输入，便于单元测试覆盖。
    dict_payload = infer_from_text(  # 任务评分载荷
        namespace_arguments.task_text,  # 用户任务正文
        namespace_arguments.context_summary,  # 已知上下文摘要
    )

    # 项目路径作为审计上下文追加到机器可读结果。
    dict_payload["project"] = str(path_project)  # 追加规范化项目根

    # stdout 固定输出 JSON，保持现有自动化消费合同。
    sys.stdout.write(json.dumps(dict_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

# 直接执行脚本时才启动 CLI，导入模块不会触发评分。
if __name__ == "__main__":

    # 主入口负责所有控制台副作用。
    main()
