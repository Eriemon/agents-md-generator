"""聚合文档发布策略、打包与门禁实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 标准库按明确文件位置加载验证器，并定位当前模块同目录的实现分片。
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

# 验证器按文件加载，避免独立导入本分片时依赖聚合入口修改 sys.path。
def _load_test_evidence_module() -> ModuleType:
    """加载不透明测试证据验证模块。

    参数：无。
    返回：从当前源码树明确加载的验证模块。
    异常：验证器文件不能形成可执行模块规格时抛出 RuntimeError。
    """

    # 明确文件路径不受调用方模块搜索顺序影响。
    path_evidence_module = Path(__file__).resolve().parents[1] / "verify" / "test_evidence.py"  # 验证模块路径。

    # 独立模块名避免复用环境中可能存在的同名验证器。
    module_spec = importlib.util.spec_from_file_location(  # 验证模块加载规格。
        "agents_test_evidence",  # 当前源码验证器的隔离模块名。
        path_evidence_module,  # 当前源码验证器的明确位置。
    )

    # 缺失加载器表示源码布局或解释器导入机制已损坏。
    if module_spec is None or module_spec.loader is None:

        # 发布证据验证器不可用时必须阻断发布流程。
        raise RuntimeError("> ERR: [Python] test evidence validator could not be loaded")

    # 模块对象承载验证器执行后公开的稳定 API。
    module_evidence = importlib.util.module_from_spec(module_spec)  # 隔离验证模块。

    # 延迟执行避免导入本发布分片时产生跨目录副作用。
    module_spec.loader.exec_module(module_evidence)

    # 调用方只读取模块公开验证函数。
    return module_evidence

# 公共包装器保持发布分片既有调用签名。
def validate_project_test_evidence(
    path_project: Path,
    str_receipt_raw: str,
    int_freshness_seconds: int = 24 * 60 * 60,
    bool_required: bool = False,
) -> dict[str, Any]:
    """调用不透明测试证据验证器而不依赖导入顺序。

    参数：path_project 为仓库根，str_receipt_raw 为收据路径。
    参数：int_freshness_seconds 为最大证据年龄，bool_required 控制缺失收据策略。
    返回：验证器生成的脱敏结构化报告。
    """

    # 每次调用从当前源码树解析验证器，避免环境同名模块污染。
    module_type_evidence = _load_test_evidence_module()  # 当前源码验证模块。

    # 公开函数由固定产品模块提供，缺失时让 AttributeError 明确暴露合同损坏。
    return module_type_evidence.validate_project_test_evidence(
        path_project,  # 待验证项目根。
        str_receipt_raw,  # 调用方提供的收据路径。
        int_freshness_seconds,  # 证据新鲜度上限。
        bool_required,  # 发布态收据必需策略。
    )

# 分片加载器保持文档发布 API 的单模块入口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载文档发布流程的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录包含策略、打包和门禁三个分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 固定加载顺序保留策略、打包和门禁之间的符号依赖。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径用于读取源码和保留错误来源。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译对象绑定真实文件名以支持发布故障定位。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享当前模块命名空间以维持既有调用合同。
        exec(code_shard, globals())

# 策略定义先于打包和门禁实现加载。
_load_module_shards(
    (
        "release_policy.py",
        "release_package.py",
        "release_gate.py",
    )
)
