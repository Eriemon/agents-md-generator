"""把脚本入口参数转交给受管安装 runtime。

本模块声明 machine-readable stdout protocol：正常结果由 runtime 输出，bridge 只输出带前缀的错误摘要。
"""

# 延迟解析注解，保持 bridge 与仓库 Python 运行时兼容。
from __future__ import annotations

# bridge 只负责 bundle containment 和受控子进程调用。
import os
import subprocess
import sys
from pathlib import Path

# 入口在发布目录内运行时不得生成会被内容策略拒绝的字节码缓存。
sys.dont_write_bytecode = True  # bridge 及其导入模块都保持 release source 无缓存

# manifest 合同负责校验入口配置和 Skill 根边界。
from installer_manifest_contract import validate_manifest_projection

# 从 argv 找到 bundle 根，保留脚本入口的参数透明性。
def _bundle_from_argv(list_arguments: list[str]) -> Path:
    """读取 --bundle-root 参数并返回规范路径。

    参数：
        list_arguments: 当前进程的命令行参数列表。
    返回：
        通过规范化的 bundle 根目录。
    异常：
        ValueError: 参数缺失或根目录不可用。
    """

    # bundle 参数是 bridge 进行 containment 校验的唯一根。
    if "--bundle-root" not in list_arguments:

        # 缺失根目录时禁止猜测当前工作目录。
        raise ValueError("> ERR: [Python] --bundle-root is required")

    # 读取参数后的路径值，保持用户传入路径的原始边界。
    int_bundle_index: int = list_arguments.index("--bundle-root") + 1  # bundle 参数值在 argv 中的索引。

    # 参数索引越过 argv 末尾时拒绝空路径。
    if int_bundle_index >= len(list_arguments):

        # 空参数不能指向任何安装资源。
        raise ValueError("> ERR: [Python] --bundle-root requires a path")

    # 返回已规范化的 bundle 目录。
    path_bundle: Path = Path(list_arguments[int_bundle_index]).expanduser().resolve()  # 所有 manifest containment 检查使用的 bundle 根。

    # 将唯一边界返回给入口调用方。
    return path_bundle

# manifest env 路径由入口传入或从 bundle 内唯一候选发现，禁止复制固定文件名。
def _manifest_env_from_argv(list_arguments: list[str], path_bundle: Path) -> Path:
    """解析并校验 installer manifest env 路径。

    参数：
        list_arguments: 当前进程的命令行参数列表。
        path_bundle: 已通过 containment 规范化的 installer bundle 根。
    返回：
        bundle 内唯一且存在的 manifest env 文件路径。
    异常：
        ValueError: manifest 参数缺失、候选不唯一或路径越界。
    """

    # 环境变量提供非交互入口的显式 manifest 路径覆盖。
    str_requested: str = os.environ.get("AGENT_INSTALLER_MANIFEST_ENV_PATH", "").strip()  # 环境覆盖的 manifest 路径。

    # 命令行参数优先于环境变量，保持调用者的显式选择。
    if "--manifest-env-path" in list_arguments:

        # 读取 manifest 参数对应的路径值。
        int_manifest_index: int = list_arguments.index("--manifest-env-path") + 1  # env manifest 路径值在 argv 中的索引。

        # 缺失路径值时禁止回退到隐式候选。
        if int_manifest_index >= len(list_arguments):

            # 缺少 env 路径值时不能启动 manifest 发现流程。
            raise ValueError("> ERR: [Python] --manifest-env-path requires a path")

        # 保留调用者提供的路径文本供后续 containment 校验。
        str_requested = list_arguments[int_manifest_index]  # 显式 manifest 路径文本。

    # 显式路径需要先规范化，避免相对段绕过 bundle 边界。
    if str_requested:

        # 使用调用者指定的 manifest 文件。
        path_manifest: Path = Path(str_requested).expanduser().resolve()  # 显式 manifest 文件路径。

    # 没有显式路径时从 bundle 中解析唯一受管候选。
    else:

        # 无显式路径时只接受 bundle 内唯一 manifest 候选。
        list_candidates: list[Path] = sorted(path_bundle.glob("*.manifest.env"))  # 自动发现流程使用的 manifest 候选集合。

        # 多个或零个候选都不能安全确定安装配置。
        if len(list_candidates) != 1:

            # 候选数量不唯一时要求调用者明确绑定路径。
            raise ValueError("> ERR: [Python] exactly one manifest env candidate is required")

        # 唯一候选成为本次入口的 manifest 文件。
        path_manifest = list_candidates[0].resolve()  # 自动发现的 manifest 文件路径。

    # manifest 必须是 bundle 内的普通文件。
    if not path_manifest.is_relative_to(path_bundle) or not path_manifest.is_file():

        # 越界或缺失 manifest 不能启动 runtime。
        raise ValueError("> ERR: [Python] manifest env is missing or outside the installer bundle")

    # 返回通过边界校验的 manifest 文件。
    return path_manifest

# 读取 manifest 的 runtime 相对路径并转发全部参数。
def main() -> int:
    """运行受管安装 runtime。

    参数：
        无；参数由当前进程 argv 提供。
    返回：
        runtime 的原始退出码。
    异常：
        OSError: runtime 无法启动。
    """

    # 保留入口参数列表，后续不把路径重新拼成 shell 字符串。
    list_input_arguments: list[str] = list(sys.argv[1:])  # 原始入口参数。

    # 先解析 bundle 根，确保后续 manifest 读取有可信边界。
    try:

        # 显式读取 bundle 根作为所有 runtime 路径的 containment 边界。
        path_bundle: Path = _bundle_from_argv(list_input_arguments)  # manifest 与 runtime 共用的 bundle 根。

    # 捕获参数解析异常并转为入口失败状态，避免启动 runtime。
    except ValueError as object_error:

        # 参数错误绑定到 Python 输出协议并停止子进程。
        print(f"> ERR: [Python] {object_error}", file=sys.stderr)

        # 结束 bundle 解析，阻止后续 manifest 读取。
        return 2

    # manifest 内容只允许声明 runtime 相对路径，不执行配置文本。
    try:

        # 解析调用者指定或 bundle 内唯一的 manifest 文件。
        path_manifest: Path = _manifest_env_from_argv(list_input_arguments, path_bundle)  # 通过边界校验的 manifest。

    # manifest 参数错误不能进入 runtime 启动阶段。
    except ValueError as object_error:

        # 将 manifest 失败原因转换为稳定的 stderr 摘要。
        print(f"> ERR: [Python] {object_error}", file=sys.stderr)

        # 返回 manifest 参数失败状态。
        return 2

    # 读取并验证 manifest 投影，取得 Skill 根和 runtime 路径来源。
    try:

        # 投影验证同时检查重复键、JSON 摘要和相对路径边界。
        tuple_manifest_result = validate_manifest_projection(  # 绑定安装包清单和可信根目录，后续启动仅允许受控运行时。
            path_bundle,  # 将 bundle 根作为 manifest 校验的 containment 起点。
            path_manifest,  # 使用选定的 env 文件读取 runtime 相对引用并校验摘要。
        )

    # manifest 内容错误必须在子进程启动前失败。
    except (OSError, TypeError, ValueError) as object_error:

        # 绑定 manifest 失败的稳定错误摘要。
        print(f"> ERR: [Python] manifest projection validation failed: {object_error}", file=sys.stderr)

        # 结束投影验证，阻止任何 runtime 子进程。
        return 2

    # 拆出投影验证后的环境字段。
    dict_manifest_env: dict[str, str] = tuple_manifest_result[0]  # 已验证的 manifest env 映射。

    # 单独保留 Skill 根，后续 containment 比较以此为唯一边界。
    path_skill_root: Path = tuple_manifest_result[2]  # 已验证的 Skill 根目录。

    # 读取 manifest 行，供 runtime 相对路径匹配使用。
    str_runtime_relative: str = dict_manifest_env.get("RUNTIME_RELATIVE_PATH", "")  # runtime 相对路径。

    # runtime 根必须回到 Skill 根，阻断 manifest 外部重定向。
    path_runtime: Path = (path_bundle / str_runtime_relative).resolve()  # 受管安装 runtime 文件。

    # Skill 根提供 backend 的最终 containment 边界。
    if not str_runtime_relative or not path_runtime.is_relative_to(path_skill_root) or not path_runtime.is_file():

        # 不完整 runtime 配置返回 containment 错误，不启动外部程序。
        print("> ERR: [Python] configured installer runtime is missing or outside the Skill root.", file=sys.stderr)

        # 返回 runtime containment 失败状态。
        return 2

    # 使用同一 Python 解释器和原始参数启动受管 runtime。
    list_runtime_arguments: list[str] = [sys.executable, str(path_runtime), *list_input_arguments]  # 受管 runtime 参数。

    # 子进程返回值原样传回 PowerShell、Shell 和 BAT 入口。
    completed_process_runtime: subprocess.CompletedProcess[object] = subprocess.run(  # runtime 执行结果。
        list_runtime_arguments,  # 不经 shell 解释的 runtime 参数。
        check=False,  # 由 bridge 透传 runtime 的退出码。
    )

    # 透传 runtime 的退出码，保持三类脚本入口行为一致。
    return int(completed_process_runtime.returncode)

# 直接执行模块时才启动受管 runtime。
if __name__ == "__main__":

    # 保留 runtime 退出码，便于上层判断安装是否成功。
    raise SystemExit(main())
