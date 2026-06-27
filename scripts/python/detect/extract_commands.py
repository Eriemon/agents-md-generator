# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)
import sys

# 关闭字节码写入，避免命令抽取时在技能源码目录留下缓存文件。
sys.dont_write_bytecode = True  # CLI 运行期间不落地 pycache

# 复用共享项目扫描函数，保持抽取逻辑和渲染阶段一致。
from agents_common import emit_json, extract_commands, parse_args, resolve_project


# CLI 入口只负责参数解析、项目定位和 JSON 输出，实际扫描逻辑留在共享模块。
def main() -> None:

    # 构造当前命令的参数解析器，描述文本会出现在 --help 中。
    parser = parse_args("Extract AGENTS.md command candidates from project files.")  # 命令抽取参数解析器

    # 读取用户传入的项目路径，后续只把解析后的路径交给共享扫描函数。
    args = parser.parse_args()  # 命令行参数命名空间

    # 以稳定 JSON 形式输出发现到的命令候选，供渲染和测试复用。
    emit_json(extract_commands(resolve_project(args.project)))


# 仅在文件作为脚本执行时启动 CLI，测试导入时不触发输出。
if __name__ == "__main__":

    # 进入命令抽取流程。
    main()


