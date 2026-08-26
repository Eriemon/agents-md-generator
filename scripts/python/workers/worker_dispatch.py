"""保持 worker dispatch 公共 API 和 CLI 导入路径稳定的 facade。"""

# 延迟解析类型注解，保持 facade 与 Python 3.10 运行时兼容。
from __future__ import annotations

# facade 只转出公共入口，内部职责由各 shard 分别负责。
try:

    # 包内入口使用相对导入，保持安装包模块身份稳定。
    from .worker_dispatch_contracts import dispatch_contracts
    from .worker_dispatch_events import check_dispatch_event, start_dispatch_session
    from .worker_dispatch_receipts import record_dispatch_result
    from .worker_dispatch_repair import dispatch_repair
    from .worker_dispatch_shared import build_event_id

# 脚本入口由调用方登记 worker 目录后回退到同目录导入。
except ImportError:

    # 同目录入口保留兼容导入路径，不在导入阶段修改 sys.path。
    from worker_dispatch_contracts import dispatch_contracts
    from worker_dispatch_events import check_dispatch_event, start_dispatch_session
    from worker_dispatch_receipts import record_dispatch_result
    from worker_dispatch_repair import dispatch_repair
    from worker_dispatch_shared import build_event_id

# 将结构化 dispatch 结果映射到 CLI 退出码。
def dispatch_exit_code(
    dict_result: dict[str, object],
    bool_input_error: bool = False,
) -> int:
    """映射 dispatch CLI 退出码。

    参数：
        dict_result 为结构化 dispatch 结果；bool_input_error 表示调用方输入错误。
    返回：0、1、2 或 3。
    """

    # 输入格式错误优先返回 2。
    if bool_input_error:

        # 调用方输入错误不代表 worker 运行失败。
        return 2

    # 提取结构化错误列表供 session 错误分类。
    list_errors = dict_result.get("errors", [])  # dispatch 错误列表

    # session 绑定错误使用最高优先级的 3。
    if any("session" in str(str_error).lower() for str_error in list_errors):

        # session 错误要求先修复治理或状态绑定。
        return 3

    # 其他 blocking 结果映射为普通失败码。
    if dict_result.get("blocking"):

        # worker 合同阻断返回 1。
        return 1

    # 无输入或运行阻断的有效结果返回成功码。
    return 0

# 声明 facade 对外稳定导出的入口集合。
__all__ = (
    "dispatch_contracts",  # 固定合同查询入口
    "build_event_id",  # 事件摘要构造入口
    "start_dispatch_session",  # session 启动入口
    "check_dispatch_event",  # 事件派发决策入口
    "record_dispatch_result",  # receipt 记录入口
    "dispatch_exit_code",  # CLI 退出码映射入口
    "dispatch_repair",  # 同 target 修复 follow-up 入口
)
