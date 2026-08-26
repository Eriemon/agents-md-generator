"""校验强控制画像的语言和 Worker 授权字段。"""

# 延迟类型解析，保持验证入口与 Python 3.10 兼容。
from __future__ import annotations

# 语言 helper 在函数调用时才加载，避免验证模块导入产生路径副作用。
import sys
from pathlib import Path

# 延迟返回当前工作树的 canonical language helper。
def _load_canonical_language():
    """返回当前工作树的 canonical language helper。

    参数：无。
    返回：可调用的 canonical_language 函数。
    异常：ImportError 表示 helper 入口不可用。
    """

    # 当前 verify 目录的上一级是 scripts/python 根目录。
    path_common_directory = Path(__file__).resolve().parents[1] / "common"  # helper 导入所需的共享目录

    # 仅在实际验证调用期间加入共享模块路径。
    if str(path_common_directory) not in sys.path:

        # 将 helper 目录登记到当前进程的临时搜索边界。
        sys.path.insert(0, str(path_common_directory))

    # 延迟导入 helper，避免模块导入阶段执行环境修改。
    from language_contract import canonical_language

    # 返回当前工作树实现供 profile 校验复用。
    return canonical_language

# 对单个 profile 执行语言和授权字段校验。
def validate_language_profile(
    str_file: str,
    dict_profile: dict[str, object],
    list_errors: list[str],
) -> None:
    """追加语言和 canonical worker 授权字段错误。

    参数：
        str_file：当前 AGENTS 文件标识。
        dict_profile：项目治理配置对象。
        list_errors：接收诊断的可变列表。
    返回：无；错误直接追加到 list_errors。
    异常：ValueError 由 helper 捕获并转换为字段级诊断。
    """

    # 读取当前工作树的 canonicalization 函数。
    func_canonical_language = _load_canonical_language()  # 当前验证使用的 canonicalization 函数

    # 会话语言必须是 catalog canonical ID，旧 alias 只允许迁移输入。
    try:

        # 归一化语言值以验证 catalog 绑定。
        func_canonical_language(
            str(dict_profile.get("default_conversation_language", "")),
            "conversation",
        )

    # 语言值未知或为空时记录配置错误。
    except ValueError:

        # 不回显配置正文，只报告字段级根因。
        list_errors.append(f"{str_file}: default_conversation_language is not a catalog language")

    # 当前文档语言必须显式且得到 documentation catalog 允许。
    try:

        # 空字段不能由渲染器猜测默认值。
        str_documentation_language = str(dict_profile.get("documentation_language", "")).strip()  # 当前文档语言

        # 缺少显式文档语言时必须阻断当前 profile。
        if not str_documentation_language:

            # 缺失文档语言直接进入统一错误分支。
            raise ValueError("> ERR: [Python] documentation language is empty")

        # 验证文档语言是否被 catalog 标记为允许。
        func_canonical_language(str_documentation_language, "documentation")

    # 文档语言未知、缺失或不允许时阻断当前根验证。
    except ValueError:

        # 保留与会话语言一致的字段级诊断。
        list_errors.append(f"{str_file}: documentation_language must be an allowed catalog language")

    # canonical worker authorization 必须显式声明且默认 disabled。
    obj_canonical_workers = dict_profile.get("canonical_workers")  # canonical worker 授权节点

    # 授权节点缺失时只能进入全拒绝错误分支。
    if not isinstance(obj_canonical_workers, dict):

        # 缺失节点不能授予任何 Worker 权限。
        list_errors.append(f"{str_file}: canonical_workers must be an explicit object")

        # 返回前不再读取不存在的授权字段。
        return

    # 默认状态必须明确为 disabled，防止平台能力隐式开启角色。
    if obj_canonical_workers.get("default_state") != "disabled":

        # 仅允许 schema v2 的安全默认状态。
        list_errors.append(f"{str_file}: canonical_workers.default_state must be disabled")

