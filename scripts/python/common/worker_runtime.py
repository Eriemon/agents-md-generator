"""读取 worker runtime 的模型和 reasoning 配置。"""

# 保留未来导入声明在模块头部，避免运行时解析类型注解。
from __future__ import annotations

# JSON 用于读取受管 worker 协议和 runtime 配置。
import json

# Path 用于把配置引用限制在当前技能根目录内。
from pathlib import Path

# cast 只提供 JSON 结果的静态字典视图，运行时仍保留对象类型检查。
from typing import cast

# 该函数集中负责读取 worker runtime，避免角色模块各自解释配置。
def load_worker_runtime() -> tuple[str, str]:
    """从受管配置读取 worker 模型和 reasoning effort。

    参数：
        无；配置路径由当前模块位置确定。
    返回：
        模型名称和 reasoning effort 组成的二元组；配置不可用时返回两个空字符串。
    """

    # 技能根目录是所有 worker 配置引用的唯一边界。
    path_skill_root: Path = Path(__file__).resolve().parents[3]  # 当前技能根目录。

    # 协议文件声明实际 runtime 配置的相对文件名。
    path_protocol: Path = path_skill_root / "config" / "workers" / "protocol.json"  # worker 协议文件。

    # 读取协议和 runtime 配置时统一把损坏输入转换为空结果。
    try:

        # 协议 JSON 先保留原始对象，再通过运行时检查确认可读取的根类型。
        obj_protocol: object = json.loads(path_protocol.read_text(encoding="utf-8"))  # 未验证的 worker 协议对象。

        # 非对象协议不能安全提供配置字段。
        if not isinstance(obj_protocol, dict):

            # 交由上层把缺失模型解释为配置阻断。
            return "", ""

        # 运行时检查通过后建立受管协议的字典视图。
        dict_protocol: dict[str, object] = cast(dict[str, object], obj_protocol)  # 已确认的 worker 协议映射。

        # 协议字段决定 runtime 配置文件的受管相对名称。
        str_runtime_name: str = str(dict_protocol.get("worker_runtime_config", "")).strip()  # runtime 配置文件名。

        # runtime 文件必须继续位于 worker 配置目录内。
        path_runtime: Path = path_protocol.parent / str_runtime_name  # runtime 配置文件路径。

        # runtime JSON 先保留原始对象，再通过独立检查确认配置根类型。
        obj_runtime: object = json.loads(path_runtime.read_text(encoding="utf-8"))  # 未验证的 runtime 配置对象。

    # 文件、编码或 JSON 破损时不泄露内部异常内容。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 空二元组让调用方保持 fail-closed 行为。
        return "", ""

    # runtime 根类型错误时不能继续读取伪造字段。
    if not isinstance(obj_runtime, dict):

        # 保持与协议读取失败相同的安全结果。
        return "", ""

    # runtime 根类型确认后，按统一字段映射读取模型和 reasoning。
    dict_runtime: dict[str, object] = cast(dict[str, object], obj_runtime)  # 已确认的 runtime 配置映射。

    # 返回配置中的模型和 reasoning 文本，调用方负责最终合同校验。
    return (
        str(dict_runtime.get("model", "")).strip(),  # 配置声明的模型供三个角色 profile 复用。
        str(dict_runtime.get("model_reasoning_effort", "")).strip(),  # 配置声明的 reasoning 强度供角色校验复用。
    )

# 载入一次 runtime 结果，避免每个角色模块重复解析协议文件。
tuple_worker_runtime: tuple[str, str] = load_worker_runtime()  # worker runtime 二元配置。

# 暴露所有 canonical worker 共用的模型名称。
WORKER_MODEL: str = tuple_worker_runtime[0]  # 三类 canonical worker 统一使用的模型名称。

# 暴露所有 canonical worker 共用的 reasoning 强度。
WORKER_REASONING: str = tuple_worker_runtime[1]  # 三类 canonical worker 统一使用的 reasoning 强度。
