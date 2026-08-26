#!/usr/bin/env bash
set -euo pipefail

# 当前脚本目录是 projection、manifest 和源 Skill 的可信入口根。
path_script_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

    # manifest 缺失时不能猜测平台、路径或运行时命令；入口可通过环境变量绑定文件。
    str_manifest_env_path="${AGENT_INSTALLER_MANIFEST_ENV_PATH:-}"

    # 环境变量非空时沿用调用者绑定，空值才允许进入 bundle 扫描分支。
if [[ -n "${str_manifest_env_path}" ]]; then

    # 将显式 env 路径规范化为本次入口唯一的 manifest 文件目标。
    path_manifest="$(realpath -m -- "${str_manifest_env_path}")"
    
    # 环境变量为空时确保 bundle 扫描成为唯一 manifest 候选来源。
else

    # 仅在没有外部绑定时扫描 bundle，避免静默选择旁路配置。
    readarray -t list_manifest_candidates < <(find -P "${path_script_root}" -maxdepth 1 -type f -name '*.manifest.env' -print)

    # 候选数量决定 manifest 身份是否唯一，异常时直接返回配置错误。
    [[ "${#list_manifest_candidates[@]}" -eq 1 ]] || {

        # 输出候选合同错误，调用方可据此修复 installer bundle。
        printf '%s\n' "> ERR: [Shell] exactly one manifest env candidate is required in the installer bundle." >&2

        # 退出码 2 表示 backend 尚未启动且入口配置无效。
        exit 2
    }

    # 固定唯一候选的绝对路径，后续所有 containment 检查围绕此文件进行。
    path_manifest="$(realpath -m -- "${list_manifest_candidates[0]}")"
fi

# manifest 必须留在脚本目录内，确保外部路径不能重定向入口资源。
[[ "${path_manifest}" == "${path_script_root}"/* ]] || {

    # 路径边界失败时保留明确的错误输出并停止解析。
    printf '%s\n' "> ERR: [Shell] manifest env escapes the installer bundle." >&2

    # containment 错误以 2 返回，保持 backend 零副作用。
    exit 2
}

    # manifest 缺失会使后续路径失去来源证明，错误必须在事务创建前返回。
if [[ ! -f "${path_manifest}" ]]; then

    # 输出缺失文件的准确位置，避免后续命令产生泛化异常。
    printf '%s\n' "> ERR: [Shell] installer manifest is missing: ${path_manifest}" >&2

    # 文件身份缺失时不进入任何 backend 或写入阶段。
    exit 2
fi

# 读取单行 manifest 值，避免把配置文本当作 shell 代码执行。
manifest_value() {

    # 将调用者给出的键名限定为单字段查询，防止 manifest 文本被解释为 shell 代码。
    local str_key="$1"

    # awk 的输出作为键值查询结果，确保 projection 与摘要检查读取同一字段。
    awk -F '=' -v key="${str_key}" '$1 == key { print substr($0, index($0, "=") + 1); exit }' "${path_manifest}"
}

# env manifest 的键必须唯一，避免首个重复键掩盖后续篡改。
validate_manifest_keys() {

    # 使用 awk 在原始文本层检查键名、空值和重复项，避免解析器先覆盖旧值。
    awk '
        /^[[:space:]]*$/ { next }
        index($0, "=") == 0 { invalid = 1; next }
        {
            str_key = substr($0, 1, index($0, "=") - 1)
            str_value = substr($0, index($0, "=") + 1)
            if (str_key !~ /^[A-Z][A-Z0-9_]*$/ || str_value == "") invalid = 1
            count[str_key] += 1
        }
        END {
            for (str_key in count) if (count[str_key] != 1) invalid = 1
            exit invalid
        }
    ' "${path_manifest}"
}

# 选择配置声明的哈希命令，并统一输出小写摘要。
hash_file() {

    # 文件和命令候选均来自受管 manifest，保持摘要计算不执行拼接文本。
    local path_file="$1"

    # 将 manifest 命令候选保存为受控输入，确保摘要选择不引入额外命令。
    local command_candidates="$2"

    # 记录当前摘要命令的可执行名称，便于保持候选顺序。
    local command_hash

    # 保存 command -v 的真实路径，确保后续摘要调用不依赖重新解析。
    local path_hash

    # 将逗号列表展开为命令边界，确保每个候选仍按 manifest 顺序处理。
    command_candidates="${command_candidates//,/ }"

    # 按 manifest 顺序筛选摘要命令，首个可用命令决定输出算法。
    for command_hash in ${command_candidates}; do

        # 解析候选真实路径，失败时继续尝试而不回退到环境默认命令。
        if ! path_hash="$(command -v "${command_hash}" 2>/dev/null)"; then

            # 当前候选解析失败，保持已知状态不变并继续寻找下一项。
            continue
        fi

        # 根据命令类型选择兼容的摘要参数，保证返回值只包含 SHA-256。
        case "${command_hash}" in

            # shasum 分支携带显式算法参数，确保摘要算法不会隐式变化。
            shasum)

                # shasum 需要显式 -a 256，输出首列即文件摘要。
                "${path_hash}" -a 256 "${path_file}" | awk '{print $1}'

                # shasum 摘要已成功输出，返回 0 结束该算法分支。
                return 0
                ;;
            # 其他选项不在白名单，输入合同失败且不得传播到后续阶段。
            *)

                # 其他候选使用其标准单文件摘要接口并截取首列。
                "${path_hash}" "${path_file}" | awk '{print $1}'

                # 通用摘要命令已成功输出，返回 0 结束该算法分支。
                return 0
                ;;
        esac
    done

    # 所有声明候选均失败时摘要身份无法建立，必须返回错误并跳过安装。
    printf '%s\n' "> ERR: [Shell] no configured hash command is available." >&2

    # 退出码 2 保持“配置缺失且未写入”的错误语义。
    return 2
}

# 将用户参数映射为 shell 变量，未知参数直接失败。
parse_arguments() {

    # 保存平台输入的初始空值，确保选择阶段只能绑定 projection 记录。
    path_selected_platform_label=""

    # 保存源目录覆盖的初始空值，确保空值仍回退到 manifest 根。
    path_source_override=""

    # 保存目标根覆盖的初始空值，确保空值仍由平台 projection 决定边界。
    path_target_root=""

    # 继承调用者声明的项目类型，后续合同会阻断未许可的类型。
    str_project_kind="${AGENT_PROJECT_KIND:-}"

    # 使用谓词命名替换开关，显式控制目标冲突时是否允许覆盖。
    is_replace=false

    # 使用谓词命名确认开关，显式控制是否跳过交互确认。
    is_yes=false

    # 使用谓词命名预演开关，显式控制是否禁止写入事务。
    is_dry_run=false

    # 保存输出类别的初始空值，确保空值采用 manifest 的 shell 合同。
    str_output_kind=""

    # 顺序扫描参数并确保未知输入不会穿过受控变量边界。
    while [[ $# -gt 0 ]]; do

        # 使用 case 固定可接受的命令行选项，未知输入走失败分支。
        case "$1" in

            # 平台选项进入独立分支，值缺失时立即走错误合同。
            --platform)

                # 缺失平台值属于参数错误，不能让空输入进入 projection 查询。
                [[ $# -ge 2 ]] || { printf '%s\n' "> ERR: [Shell] --platform requires a value." >&2; return 2; }

                # 保存调用者的显式平台身份，后续只在投影中查找该值。
                path_selected_platform_label="$2"

                # 消费选项和值，确保下一轮从下一个参数位置开始。
                shift 2
                ;;

            # 源目录选项进入独立分支，后续仍由 containment 重新验证。
            --skill-source)

                # 源目录选项必须携带值，避免空值触发错误的默认路径。
                [[ $# -ge 2 ]] || { printf '%s\n' "> ERR: [Shell] --skill-source requires a value." >&2; return 2; }

                # 保存源目录覆盖值，resolve_paths 会重新执行 containment 校验。
                path_source_override="$2"

                # 一次消费选项和值，避免同一参数被重复解析。
                shift 2
                ;;

            # 目标根选项进入独立分支，写入边界由 resolve_paths 最终确认。
            --target-root)

                # 目标根选项必须携带值，后续事务只允许在此边界内写入。
                [[ $# -ge 2 ]] || { printf '%s\n' "> ERR: [Shell] --target-root requires a value." >&2; return 2; }

                # 保存目标根覆盖值，resolve_paths 会验证其存在与 containment。
                path_target_root="$2"

                # 一次消费选项和值，保持调用者输入的顺序语义。
                shift 2
                ;;

            # 项目类型分支确保许可值来自 manifest，未授权值不会进入事务。
            --project-kind)

                # 缺失项目类型属于参数错误，不能猜测安装资格。
                [[ $# -ge 2 ]] || { printf '%s\n' "> ERR: [Shell] --project-kind requires a value." >&2; return 2; }

                # 将项目类型保存为后续许可比较的唯一输入，防止绕过 manifest。
                str_project_kind="$2"

                # 一次消费选项和值，防止类型值再次被当作独立参数。
                shift 2
                ;;

            # 替换开关只改变确认合同，不直接执行文件操作。
            --replace)

                # 打开替换谓词，后续冲突检查才允许移动旧目标。
                is_replace=true

                # 只消费开关本身，不从后续参数读取隐式值。
                shift
                ;;

            # 非交互开关只改变确认合同，不直接执行文件操作。
            --yes)

                # 打开非交互确认谓词，调用者承担显式写入确认责任。
                is_yes=true

                # 消费开关后确保参数游标继续单调前进。
                shift
                ;;

            # 预演开关只改变事务路径，不创建目标文件。
            --dry-run)

                # 打开预演谓词，后续确认阶段必须保持零副作用。
                is_dry_run=true

                # 消费预演开关后确保其他选项仍按原位置解析。
                shift
                ;;

            # 输出类别选项进入独立分支，值稍后与 manifest 比较。
            --output-kind)

                # 输出类别选项必须携带值，后续与 manifest 输出合同比较。
                [[ $# -ge 2 ]] || { printf '%s\n' "> ERR: [Shell] --output-kind requires a value." >&2; return 2; }

                # 保存调用者输出类别，入口不自行扩展 manifest 的允许集合。
                str_output_kind="$2"

                # 一次消费选项和值，避免输出值被误判为未知参数。
                shift 2
                ;;

            # 帮助选项只输出使用说明，不触发配置或写入流程。
            --help|-h)

                # 帮助路径只写入固定说明，不读取配置也不触发安装事务。
                printf '%s\n' "> INFO: [Shell] Usage: install.sh [--platform <id>] [--skill-source <path>] [--target-root <path>] [--project-kind <kind>] [--dry-run] [--replace] [--yes]"

                # 帮助请求正常结束且没有文件副作用。
                return 0
                ;;

            # 未知选项进入统一错误分支，确保没有未声明参数继续传播。
            *)

                # 未知选项不能被静默忽略，避免调用者误以为参数已生效。
                printf '%s\n' "> ERR: [Shell] unknown installer argument: $1" >&2

                # 返回配置错误，后续阶段不应继续运行。
                return 2
                ;;
        esac
    done
}

# 读取并校验 projection 的源摘要、记录类别和列结构。
load_projection() {

    # manifest 的源根字段决定后续所有资源的 containment 边界，先保存这项绑定事实。
    str_source_root_relative="$(manifest_value SOURCE_ROOT_RELATIVE)"

    # 源根字段为空时无法证明 bundle 归属，立即返回配置错误。
    [[ -n "${str_source_root_relative}" ]] || { printf '%s\n' "> ERR: [Shell] SOURCE_ROOT_RELATIVE is missing from the manifest." >&2; return 2; }

    # 将源根相对路径解析为绝对目录，后续资源均从该根派生。
    path_skill_root="$(realpath -m -- "${path_script_root}/${str_source_root_relative}")"

    # bundle 必须位于 Skill 根内，确保入口不会从外部目录加载资源。
    [[ "${path_script_root}" == "${path_skill_root}"/* ]] || { printf '%s\n' "> ERR: [Shell] installer bundle is outside the configured Skill root." >&2; return 2; }

    # 记录 projection 文件位置，后续摘要和平台选择都读取该生成物。
    path_projection="$(realpath -m -- "${path_script_root}/$(manifest_value PROJECTION_RELATIVE_PATH)")"

    # 记录平台 catalog 位置，后续摘要核对使用同一受管文件。
    path_catalog="$(realpath -m -- "${path_script_root}/$(manifest_value CATALOG_RELATIVE_PATH)")"

    # 记录 projection schema 位置，列合同校验只接受此声明文件。
    path_projection_schema="$(realpath -m -- "${path_script_root}/$(manifest_value PROJECTION_SCHEMA_RELATIVE_PATH)")"

    # 记录 projection generator 位置，确保生成来源仍在 Skill 根内。
    path_projection_generator="$(realpath -m -- "${path_script_root}/$(manifest_value PROJECTION_GENERATOR_RELATIVE_PATH)")"

    # 记录 JSON manifest 位置，摘要校验将它与 env 身份字段绑定。
    path_manifest_json="$(realpath -m -- "${path_skill_root}/$(manifest_value MANIFEST_JSON_RELATIVE_PATH)")"

    # 记录 manifest projection 位置，后续只从 bundle 内的 TSV 读取字段。
    path_manifest_projection="$(realpath -m -- "${path_script_root}/$(manifest_value MANIFEST_PROJECTION_RELATIVE_PATH)")"

    # 保存 projection 摘要，防止平台表被替换后继续安装。
    str_projection_hash="$(manifest_value PROJECTION_SHA256)"

    # 保存 catalog 摘要，确保平台事实来自 generator 产物。
    str_catalog_hash="$(manifest_value CATALOG_SHA256)"

    # 将 JSON 摘要固定为 env 与文件内容比较的基准，防止读取过期 manifest。
    str_manifest_hash="$(manifest_value MANIFEST_SHA256)"

    # 保存 projection 摘要值，防止 env 与 TSV 文件脱钩。
    str_manifest_projection_hash="$(manifest_value MANIFEST_PROJECTION_SHA256)"

    # 将摘要命令列表固定为 manifest 事实，确保 hash_file 不回退到环境默认值。
    str_hash_commands="$(manifest_value HASH_COMMANDS)"

    # 保存 shell 工具列表，后续验证确保运行环境满足脚本合同。
    path_shell_commands="$(manifest_value SHELL_UTILITIES)"

    # 保存 env 文件名，后续比较它与实际 launcher 资源的身份。
    str_manifest_env_relative="$(manifest_value MANIFEST_ENV_RELATIVE_PATH)"

    # 将 generator 记录类别保存为校验输入，确保 projection 元数据完整。
    record_class_names="$(manifest_value PROJECTION_RECORD_CLASSES)"

    # 将 schema 必需列保存为表头校验输入，防止字段错位进入安装。
    required_columns="$(manifest_value PROJECTION_REQUIRED_COLUMNS)"

    # projection 文件必须属于 Skill 根且为普通文件。
    [[ "${path_projection}" == "${path_skill_root}"/* && -f "${path_projection}" ]] || { printf '%s\n' "> ERR: [Shell] configured projection is missing or outside the Skill root." >&2; return 2; }

    # catalog 文件必须属于 Skill 根且为普通文件。
    [[ "${path_catalog}" == "${path_skill_root}"/* && -f "${path_catalog}" ]] || { printf '%s\n' "> ERR: [Shell] configured catalog is missing or outside the Skill root." >&2; return 2; }

    # schema 文件必须属于 Skill 根，避免使用外部列合同。
    [[ "${path_projection_schema}" == "${path_skill_root}"/* && -f "${path_projection_schema}" ]] || { printf '%s\n' "> ERR: [Shell] configured projection schema is missing or outside the Skill root." >&2; return 2; }

    # generator 文件必须属于 Skill 根，避免生成来源被旁路替换。
    [[ "${path_projection_generator}" == "${path_skill_root}"/* && -f "${path_projection_generator}" ]] || { printf '%s\n' "> ERR: [Shell] configured projection generator is missing or outside the Skill root." >&2; return 2; }

    # JSON manifest 必须属于 Skill 根，确保摘要绑定到当前 Skill。
    [[ "${path_manifest_json}" == "${path_skill_root}"/* && -f "${path_manifest_json}" ]] || { printf '%s\n' "> ERR: [Shell] configured manifest JSON is missing or outside the Skill root." >&2; return 2; }

    # TSV projection 必须属于 installer bundle，避免读取外部菜单数据。
    [[ "${path_manifest_projection}" == "${path_script_root}"/* && -f "${path_manifest_projection}" ]] || { printf '%s\n' "> ERR: [Shell] configured manifest projection is missing or outside the installer bundle." >&2; return 2; }

    # 摘要命令列表缺失时不能建立任何文件身份。
    [[ -n "${str_hash_commands}" ]] || { printf '%s\n' "> ERR: [Shell] HASH_COMMANDS is missing from the manifest." >&2; return 2; }

    # 先验证 env 键合同，防止重复键在后续读取时覆盖事实。
    validate_manifest_keys || { printf '%s\n' "> ERR: [Shell] manifest env contains duplicate keys." >&2; return 2; }

    # env 文件名必须与实际 manifest basename 相同，确保入口身份稳定。
    [[ "${str_manifest_env_relative}" == "$(basename -- "${path_manifest}")" ]] || { printf '%s\n' "> ERR: [Shell] configured manifest env path does not match the launcher resource." >&2; return 2; }

    # JSON 摘要字段缺失属于配置错误，不能核对 manifest 内容。
    [[ -n "${str_manifest_hash}" ]] || { printf '%s\n' "> ERR: [Shell] MANIFEST_SHA256 is missing from the manifest." >&2; return 2; }

    # projection 摘要缺失属于配置错误，不能核对菜单表内容。
    [[ -n "${str_manifest_projection_hash}" ]] || { printf '%s\n' "> ERR: [Shell] MANIFEST_PROJECTION_SHA256 is missing from the manifest." >&2; return 2; }

    # shell 工具列表缺失属于环境错误，运行环境的确定性无法保证。
    [[ -n "${path_shell_commands}" ]] || { printf '%s\n' "> ERR: [Shell] SHELL_UTILITIES is missing from the manifest." >&2; return 2; }

    # 记录类别或必需列缺失时不能验证 projection 结构。
    [[ -n "${record_class_names}" && -n "${required_columns}" ]] || { printf '%s\n' "> ERR: [Shell] projection schema columns or record classes are missing." >&2; return 2; }

    # 将工具列表转成循环输入，仍保留 manifest 的候选顺序。
    path_shell_commands="${path_shell_commands//,/ }"

    # 每个声明工具都必须能在当前 shell 解析，避免运行到事务中才失败。
    for command_required in ${path_shell_commands}; do

        # 当前工具解析失败时返回环境错误，阻断后续摘要和写入。
        command -v "${command_required}" >/dev/null 2>&1 || { printf '%s\n' "> ERR: [Shell] configured shell utility is unavailable: ${command_required}" >&2; return 2; }
    done

    # 先核对 JSON manifest 摘要，确保 env 身份没有指向过期内容。
    [[ "$(hash_file "${path_manifest_json}" "${str_hash_commands}")" == "${str_manifest_hash}" ]] || { printf '%s\n' "> ERR: [Shell] installer JSON manifest hash mismatch." >&2; return 2; }

    # 再核对 TSV projection 摘要，阻断菜单文件单独替换。
    [[ "$(hash_file "${path_manifest_projection}" "${str_hash_commands}")" == "${str_manifest_projection_hash}" ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection hash mismatch." >&2; return 2; }

    # TSV 第二行必须绑定同一 JSON 摘要，避免跨版本拼接资源。
    [[ "$(sed -n '2p' "${path_manifest_projection}")" == "# manifest_json_sha256=${str_manifest_hash}" ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection JSON binding mismatch." >&2; return 2; }

    # 使用关联数组记录已见投影键，重复项必须在写入前被拒绝。
    declare -A dict_projection_keys=()

    # 以整数零起始 projection 行计数，确保后续可与 env 字段数做合同比较。
    count_projection_rows=0+0

    # 逐行读取 TSV 的键、来源和投影值，保持列合同可追溯。
    while IFS=$'\t' read -r str_projection_key str_projection_source str_projection_value; do

        # 行字段格式错误会破坏键名、来源路径和值的投影合同。
        [[ "${str_projection_key}" =~ ^[A-Z][A-Z0-9_]*$ && -n "${str_projection_source}" && "${str_projection_source}" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$ ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection row is invalid." >&2; return 2; }

        # 已见键不能再次出现，避免后一行覆盖前一行的投影事实。
        [[ -z "${dict_projection_keys[${str_projection_key}]+present}" ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection contains duplicate keys: ${str_projection_key}" >&2; return 2; }

        # 记录键存在性，关联数组的值只作为 presence 标记使用。
        dict_projection_keys[${str_projection_key}]=present

        # 每确认一条合法 projection 行就递增计数，确保行数证据与实际 TSV 一致。
        count_projection_rows=$((count_projection_rows + 1))

        # 当前 projection 值不一致属于输入错误，必须阻断单列篡改。
        [[ "$(manifest_value "${str_projection_key}")" == "${str_projection_value}" ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection mismatch: ${str_projection_key}" >&2; return 2; }

    # 结束 projection TSV 逐行读取，后续数量比较使用已验证的完整行集。
    done < <(awk 'NR > 3 { print }' "${path_manifest_projection}")

    # 从 manifest 行数独立计算 env 投影数量，确保 TSV 行数不是自证。
    is_projection_env_total="$(awk -F '=' '$1 != "MANIFEST_SHA256" && $1 != "MANIFEST_PROJECTION_SHA256" && NF { count += 1 } END { print count + 0 }' "${path_manifest}")"

    # 行数不一致是 projection 与 env 漂移错误，不能继续安装。
    [[ "${count_projection_rows}" == "${is_projection_env_total}" ]] || { printf '%s\n' "> ERR: [Shell] installer manifest projection row count does not match env projection count." >&2; return 2; }

    # catalog 摘要不匹配是平台来源错误，必须阻断替换后的菜单。
    [[ "$(hash_file "${path_catalog}" "${str_hash_commands}")" == "${str_catalog_hash}" ]] || { printf '%s\n' "> ERR: [Shell] platform catalog hash mismatch." >&2; return 2; }

    # projection 摘要不匹配是生成物错误，必须阻断替换后的平台行。
    [[ "$(hash_file "${path_projection}" "${str_hash_commands}")" == "${str_projection_hash}" ]] || { printf '%s\n' "> ERR: [Shell] platform projection hash mismatch." >&2; return 2; }

    # 将记录类别列表转成循环输入，逐项确认 generator 元数据。
    path_record_class_names="${record_class_names//,/ }"

    # 每个声明类别都必须出现在 projection 元数据中，确保菜单来源完整。
    for str_record in ${path_record_class_names}; do

        # 缺失类别说明 projection 不是当前 generator 生成的完整产物。
        grep -q "^# ${str_record} " "${path_projection}" || { printf '%s\n' "> ERR: [Shell] projection record class is missing: ${str_record}" >&2; return 2; }
    done

    # 过滤元数据行，保留唯一表头和平台记录供选择阶段消费。
    is_platform_table="$(awk 'BEGIN { found=0 } !/^#/ && NF { if(!found){ print; found=1; next } print }' "${path_projection}")"

    # 平台表为空属于 projection 错误，不能解析选择或计算目标路径。
    [[ -n "${is_platform_table}" ]] || { printf '%s\n' "> ERR: [Shell] projection has no platform table." >&2; return 2; }

    # 将列清单展开为循环输入，确保每个 schema 字段都被单独核验。
    path_required_columns="${required_columns//,/ }"

    # 每个必需列都必须存在，避免字段错位后继续安装。
    for str_column in ${path_required_columns}; do

        # 当前列缺失时返回结构错误，保持目标路径尚未解析。
        awk -F '\t' -v wanted="${str_column}" 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == wanted) found=1 } END { exit(found ? 0 : 1) }' <(printf '%s\n' "${is_platform_table}") || { printf '%s\n' "> ERR: [Shell] projection column is missing: ${str_column}" >&2; return 2; }
    done
}

# 只从已验证 projection 表按平台和列名取值，确保目标路径不依赖硬编码案例。
platform_field() {

    # 保存平台 ID，awk 只允许从该记录提取字段。
    local str_platform_id="$1"

    # 保存列名，调用者后续用它读取 projection 的结构化字段。
    local str_column_name="$2"

    # 由 TSV 表头建立列索引，再输出唯一平台记录对应的字段值。
    awk -F '\t' -v wanted="${str_platform_id}" -v column="${str_column_name}" '
        BEGIN { is_header_ready = 0 }
        is_header_ready == 0 {
            count_field_total = split($0, field_value, "\t")
            for (i = 1; i <= count_field_total; i++) header[field_value[i]] = i
            is_header_ready = 1
            next
        }
        $1 == wanted {
            count_field_total = split($0, field_value, "\t")
            print field_value[header[column]]
            exit
        }
    ' <(printf '%s\n' "${is_platform_table}")
}

# 构造不跟随链接的源树清单，确保复制事务拥有节点类型、字节数和 SHA-256 证据。
build_tree_manifest() {

    # 保存可信源根，目录遍历和路径裁剪都以此边界为准。
    local path_tree_root="$1"

    # 保存本次事务的清单输出文件，所有成员记录写入该目标。
    local path_manifest_output="$2"

        # 保存当前成员绝对路径，确保节点类型和安全边界判断引用同一对象。
    local path_member

    # 当前成员相对于源根的路径，写入清单而不暴露源根前缀。
    local path_relative

    # 普通文件的字节数，和摘要一起构成成员身份。
    local int_bytes

    # 普通文件的内容摘要，确保 staging 前后可以逐项比较。
    local str_digest

    # 清单输出先截断为本次运行的唯一事实文件，避免混入上次事务残留。
    : > "${path_manifest_output}"

    # 递归读取源树成员，保留隐藏项并拒绝跟随符号链接。
    while IFS= read -r -d '' path_member; do

        # 计算成员相对路径，清单不记录源根本身。
        path_relative="${path_member#"${path_tree_root}/"}"

        # 控制字符会破坏 TSV 记录边界，先阻断该成员。
        if [[ "${path_relative}" == *$'\t'* || "${path_relative}" == *$'\r'* || "${path_relative}" == *$'\n'* ]]; then

            # 输出无法安全编码的成员路径并终止清单生成。
            printf '%s\n' "> ERR: [Shell] source tree contains a control-character path: ${path_relative}" >&2

            # 清单证据不完整属于源树错误，不允许复制事务继续。
            return 2
        fi

        # 符号链接越出源根会破坏清单身份，错误必须在 staging 前拒绝。
        if [[ -L "${path_member}" ]]; then

            # 输出链接成员，保持拒绝原因可定位。
            printf '%s\n' "> ERR: [Shell] source tree contains a symbolic link: ${path_relative}" >&2

            # 源树身份失败时不生成可安装清单。
            return 2
        fi

        # 目录节点写入零字节记录，保留空目录和隐藏目录事实。
        if [[ -d "${path_member}" ]]; then

            # 目录记录写入清单，确保空目录事实不会在复制时丢失。
            printf 'directory\t%s\t0\t-\n' "${path_relative}" >> "${path_manifest_output}"

            # 目录已完成记录，不再执行文件摘要分支。
            continue
        fi

        # 普通文件需要同时记录字节数和内容摘要。
        if [[ -f "${path_member}" ]]; then

            # 读取文件字节数，供清单复核大小一致性。
            int_bytes="$(wc -c < "${path_member}")"

            # 使用受管摘要命令记录文件内容身份。
            str_digest="$(hash_file "${path_member}" "${str_hash_commands}")"

            # 将普通文件成员写入清单，保持类型、路径、大小、摘要列顺序。
            printf 'file\t%s\t%s\t%s\n' "${path_relative}" "${int_bytes}" "${str_digest}" >> "${path_manifest_output}"

            # 文件已完成记录，不再落入特殊节点分支。
            continue
        fi

        # 设备、管道等特殊节点无法形成稳定清单身份，属于源树错误。
        printf '%s\n' "> ERR: [Shell] source tree contains a special node: ${path_relative}" >&2

        # 特殊节点使复制证据不完整，返回错误而不继续事务。
        return 2

    # 结束不跟随链接的源树遍历，清单此时已覆盖全部成员节点。
    done < <(find -P "${path_tree_root}" -mindepth 1 -print0 | sort -z)
}

# 选择平台并确认 projection 中存在且唯一的记录，确保目标根解析有单一来源。
select_platform() {

    # 只在调用者未给出平台时显示 projection 菜单，不内置平台案例。
    if [[ -z "${path_selected_platform_label}" ]]; then

        # 菜单只遍历 generator 输出的平台行，避免展示未验证选项。
        printf '%s\n' "> INFO: [Shell] Available platforms:"

        # 输出行号与平台标签，用户选择值稍后仍由 projection 反查。
        awk -F '\t' 'NR > 1 { printf "> INFO: [Shell]   %d) %s (%s)\n", NR - 1, $2, $1 }' <(printf '%s\n' "${is_platform_table}")

        # 读取用户菜单编号，保持交互输入只影响当前平台选择。
        read -r -p "Select a platform number: " str_menu_choice

        # 将菜单编号映射回唯一平台 ID，避免把编号直接当路径使用。
        path_selected_platform_label="$(awk -F '\t' -v choice="${str_menu_choice}" 'NR == choice + 1 { print $1; exit }' <(printf '%s\n' "${is_platform_table}"))"
    fi

    # 平台 ID 为空时没有可验证目标，返回选择错误。
    [[ -n "${path_selected_platform_label}" ]] || { printf '%s\n' "> ERR: [Shell] platform selection is invalid." >&2; return 2; }

    # 先独立统计平台 ID 出现次数，避免长条件中的命令替换隐藏错误边界。
    count_platform_match_total="$(awk -F '\t' -v wanted="${path_selected_platform_label}" '$1 == wanted { count++ } END { print count + 0 }' <(printf '%s\n' "${is_platform_table}"))"

    # 平台 ID 必须在 projection 中恰好出现一次，防止目标根产生歧义。
    if [[ "${count_platform_match_total}" != "1" ]]; then

        # 重复或缺失平台记录属于 projection 合同错误。
        printf '%s\n' "> ERR: [Shell] projection record cardinality is invalid: ${path_selected_platform_label}" >&2

        # 记录错误码并阻断目标路径解析。
        return 2
    fi
}

# 解析源目录、平台根和目标目录，并完成 containment 诊断。
resolve_paths() {

    # 源目录优先使用显式覆盖，否则回到 manifest 根，确保输入来源可追溯。
    path_source="${path_source_override:-$(realpath -m -- "${path_script_root}/$(manifest_value SOURCE_ROOT_RELATIVE)")}"

    # 再次规范化源目录，确保后续 containment 比较不受相对段影响。
    path_source="$(realpath -m -- "${path_source}")"

    # 源目录必须位于 Skill 根且真实存在，阻断外部目录进入事务。
    [[ ("${path_source}" == "${path_skill_root}" || "${path_source}" == "${path_skill_root}/"*) && -d "${path_source}" ]] || { printf '%s\n' "> ERR: [Shell] Skill source is missing or outside the Skill root." >&2; return 2; }

    # Skill 身份文件必须存在，确保复制目标不是任意目录。
    [[ -f "${path_source}/SKILL.md" && -f "${path_source}/VERSION" ]] || { printf '%s\n' "> ERR: [Shell] Skill source must contain SKILL.md and VERSION." >&2; return 2; }

    # 提取 Skill 名称，目标目录将以此叶节点建立。
    str_skill_name="$(basename -- "${path_source}")"

    # 名称必须是有效叶节点，避免目标路径回退到根目录或当前目录。
    [[ -n "${str_skill_name}" && "${str_skill_name}" != "." && "${str_skill_name}" != ".." ]] || { printf '%s\n' "> ERR: [Shell] Skill source name is invalid." >&2; return 2; }

    # 目标边界优先使用显式根，否则读取 projection 的平台 home 声明。
    if [[ -n "${path_target_root}" ]]; then

        # 规范化调用者目标根，所有后续写入都限制在该目录下。
        path_boundary="$(realpath -m -- "${path_target_root}")"

        # 自定义目标根必须预先存在，入口不隐式创建根目录。
        [[ -d "${path_boundary}" ]] || { printf '%s\n' "> ERR: [Shell] target root does not exist." >&2; return 2; }

        # 自定义根同时作为平台 home，避免后续分支读取未声明环境变量。
        path_platform_home="${path_boundary}"

        # 未提供自定义根时确保平台 home 分支继续受 projection 控制。
    else

        # 记录 projection 指定的 home 环境变量名，确保平台根来源可追溯。
        str_home_env="$(platform_field "${path_selected_platform_label}" home_env)"

        # 读取 home 模式，决定使用 platform_root 还是用户 home 分支。
        str_home_mode="$(platform_field "${path_selected_platform_label}" home_env_mode)"

        # 读取用户 home 子目录，供非 platform_root 模式构造目标边界。
        str_user_home="$(platform_field "${path_selected_platform_label}" user_home_dir)"

        # platform_root 模式通过动态环境名取得平台根，并保留存在性校验边界。
        if [[ "${str_home_mode}" == "platform_root" ]]; then

            # 通过 awk 的 ENVIRON 按声明名称读取平台根，避免动态展开越过脚本边界。
            path_platform_home="$(awk -v name="${str_home_env}" 'BEGIN { print ENVIRON[name] }')"

            # 动态平台根必须存在且为目录，防止写入未解析位置。
            [[ -n "${path_platform_home}" && -d "${path_platform_home}" ]] || { printf '%s\n' "> ERR: [Shell] configured platform root is unavailable." >&2; return 2; }

            # 规范化平台根，确保跨平台路径比较使用绝对形式。
            path_platform_home="$(realpath -m -- "${path_platform_home}")"

            # 已解析平台根作为 containment 根，确保后续目标不越界。
            path_boundary="${path_platform_home}"

            # 非 platform_root 模式改用用户 home 子目录作为平台根。
        else

            # 非 platform_root 模式以当前用户 home 作为 containment 根，限制写入范围。
            path_boundary="$(realpath -m -- "${HOME}")"

            # 将 projection 的用户子目录解析为平台安装根。
            path_platform_home="$(realpath -m -- "${path_boundary}/${str_user_home}")"

            # 用户平台根必须存在，避免创建跨边界目录。
            [[ -d "${path_platform_home}" ]] || { printf '%s\n' "> ERR: [Shell] configured user platform root is unavailable." >&2; return 2; }
        fi
    fi

    # 读取 projection 声明的安装子目录，目标必须位于平台根下一层。
    str_skill_install_dir="$(platform_field "${path_selected_platform_label}" skill_install_dir)"

    # 构造安装父目录并保留平台根的直接子目录约束。
    path_install_parent="$(realpath -m -- "${path_platform_home}/${str_skill_install_dir}")"

    # 安装父目录越出平台根时拒绝继续解析目标。
    [[ "${path_install_parent}" == "${path_platform_home}"/* && "$(dirname -- "${path_install_parent}")" == "${path_platform_home}" ]] || { printf '%s\n' "> ERR: [Shell] projection install directory escapes the platform root." >&2; return 2; }

    # 将 Skill 名称拼接到受控安装父目录，形成逻辑目标路径。
    path_destination_logical="${path_install_parent}/${str_skill_name}"

    # 逻辑目标不能是符号链接，防止替换动作跟随外部目标。
    [[ ! -L "${path_destination_logical}" ]] || { printf '%s\n' "> ERR: [Shell] destination symbolic links are not replaceable." >&2; return 2; }

    # 规范化最终目标路径，后续事务只在该绝对目录切换。
    path_destination="$(realpath -m -- "${path_destination_logical}")"

    # 最终目标越出 containment 根属于路径错误，必须阻断事务。
    [[ "${path_destination}" == "${path_boundary}"/* ]] || { printf '%s\n' "> ERR: [Shell] destination escapes the selected target root." >&2; return 2; }

    # 目标不能位于源目录内，避免安装动作覆盖正在读取的 Skill。
    [[ "${path_destination}" != "${path_source}" && "${path_destination}" != "${path_source}/"* ]] || { printf '%s\n' "> ERR: [Shell] destination is inside the Skill source." >&2; return 2; }
}

# 确认目标冲突和真实写入意图。
confirm_install() {

    # 目标存在时先要求替换谓词，再决定是否接受交互确认。
    if [[ -e "${path_destination}" || -L "${path_destination}" ]]; then

        # 已有目标没有替换许可时，事务不得移动或覆盖任何目录。
        [[ "${is_replace}" == true ]] || { printf '%s\n' "> ERR: [Shell] destination already exists; use --replace." >&2; return 2; }

        # 非交互确认关闭时，要求调用者明确同意替换。
        if [[ "${is_yes}" != true ]]; then

            # 读取替换确认回答，默认拒绝已有目标覆盖。
            read -r -p "Destination exists. Replace it? [y/N] " path_replace_confirmation

            # 非确认回答属于写入授权错误，必须阻断替换事务。
            [[ "${path_replace_confirmation,,}" == "y" || "${path_replace_confirmation,,}" == "yes" ]] || { printf '%s\n' "> ERR: [Shell] replace confirmation was not granted." >&2; return 2; }
        fi
    fi

    # 输出当前平台和目标，给调用者在真实写入前检查边界。
    printf '%s\n' "> INFO: [Shell] Platform: ${path_selected_platform_label}; destination: ${path_destination}"

    # 预演模式到此结束，确保不创建父目录、锁或 staging。
    if [[ "${is_dry_run}" == true ]]; then

        # 明确报告没有发生文件写入，保持机器外可读的零副作用证据。
        printf '%s\n' "> INFO: [Shell] Dry-run complete; no files were written"

        # 预演成功返回，调用者不会进入安装事务。
        return 0
    fi

    # 非预演调用在没有 yes 开关时必须再次确认真实写入。
    if [[ "${is_yes}" != true ]]; then

        # 读取最终写入确认，默认拒绝创建或替换目标。
        read -r -p "Proceed with installation? [y/N] " path_install_confirmation

        # 只有明确 y/yes 才能把控制流交给事务函数。
        [[ "${path_install_confirmation,,}" == "y" || "${path_install_confirmation,,}" == "yes" ]] || { printf '%s\n' "> ERR: [Shell] installation confirmation was not granted." >&2; return 2; }
    fi
}

# 执行同卷 staging、备份、交换和失败隔离事务。
install_transaction() {

    # 记录独占锁路径，后续所有失败证据都引用同一锁文件。
    path_lock="${path_boundary}/$(manifest_value LOCK_FILE_NAME)"

    # 记录同卷 staging 路径，临时副本只在目标根内生成。
    path_staging="${path_boundary}/$(manifest_value STAGING_PREFIX)${BASHPID}"

    # 记录源清单路径，复制前先建立不可变的源身份证据。
    path_source_manifest="${path_boundary}/$(manifest_value SOURCE_MANIFEST_PREFIX)${BASHPID}.tsv"

    # 记录隔离目录根，失败时把不完整目标移出正式路径。
    path_quarantine_root="${path_boundary}/$(manifest_value QUARANTINE_DIRECTORY_NAME)"

    # 记录备份目录根，替换模式下旧目标只能移动到该受控位置。
    path_backup_root="${path_boundary}/$(manifest_value BACKUP_DIRECTORY_NAME)"

    # 备份路径初始为空，表示当前事务尚未移动旧目标。
    path_backup=""

    # 源清单摘要初始为空，只有清单成功生成后才写入证据。
    str_source_manifest_hash=""

    # staging 清单摘要初始为空，供失败收据区分未执行阶段。
    str_staging_manifest_hash=""

    # 最终清单摘要初始为空，确保只有目标切换后才产生该事实。
    str_final_manifest_hash=""

    # lock 使用 noclobber 独占创建，避免两个事务同时修改同一目标。
    ( set -o noclobber; : > "${path_lock}" ) 2>/dev/null || { printf '%s\n' "> ERR: [Shell] installer transaction lock already exists." >&2; return 2; }

    # 失败处理保留 staging/destination 现场并恢复旧目标。
    recover_failure() {

        # 记录待隔离的失败对象，收据会保留它的实际路径。
        local path_failed=""

        # 累积恢复阶段错误，决定是否保留锁供人工处理。
        local str_recovery_errors=""

        # 记录恢复收据路径，供后续诊断读取事务现场。
        local path_recovery_receipt=""

        # 先确保隔离根存在，失败时仍保留原锁和错误证据。
        if ! mkdir -p "${path_quarantine_root}"; then

            # 追加隔离根错误，恢复流程继续收集其他失败。
            str_recovery_errors="${str_recovery_errors}quarantine_root;"
        fi

        # staging 是首要恢复现场；缺失时才检查 destination，避免误隔离旧目标。
        if [[ -e "${path_staging}" || -L "${path_staging}" ]]; then

            # staging 包含当前最可能的不完整副本，先保存它的恢复现场。
            path_failed="${path_staging}"

        # staging 不存在时确保只隔离已切换且尚未验证的 destination 现场。
        elif [[ -e "${path_destination}" || -L "${path_destination}" ]]; then

            # destination 是切换后校验失败时需要隔离的现场。
            path_failed="${path_destination}"
        fi

        # 只有发现失败对象时才执行隔离移动，避免误移动旧目标。
        if [[ -n "${path_failed}" ]]; then

            # 使用进程号生成隔离目录，保证同一 boundary 内名字唯一。
            path_quarantine="${path_quarantine_root}/${BASHPID}"

            # 隔离移动失败时保留错误标记，禁止伪造恢复成功。
            if ! mv -- "${path_failed}" "${path_quarantine}"; then

                # 记录隔离动作失败，后续收据会暴露该状态。
                str_recovery_errors="${str_recovery_errors}quarantine;"
            fi
        fi

        # 只有备份存在且正式目标为空时才尝试恢复旧目标。
        if [[ -n "${path_backup}" && -e "${path_backup}" && ! -e "${path_destination}" ]]; then

            # 移回旧目标，恢复 replace 事务开始前的可用状态。
            if ! mv -- "${path_backup}" "${path_destination}"; then

                # 恢复失败时保留锁，避免下一次运行误判状态。
                str_recovery_errors="${str_recovery_errors}restore;"
            fi
        fi

        # 优先把恢复收据写入隔离根，隔离根不存在时退回 boundary。
        if [[ -d "${path_quarantine_root}" ]]; then

            # 隔离根存在时收据与失败现场放在同一目录。
            path_recovery_receipt="${path_quarantine_root}/${BASHPID}$(manifest_value RECOVERY_RECEIPT_SUFFIX)"

            # 隔离根不可用时把收据退回 boundary，保持失败事实可落盘。
        else

            # 隔离根创建失败时仍在 boundary 保留收据。
            path_recovery_receipt="${path_boundary}/${BASHPID}$(manifest_value RECOVERY_RECEIPT_SUFFIX)"
        fi

        # 记录所有恢复阶段摘要和路径，形成可追溯失败收据。
        if ! printf 'recovery_errors=%s\nquarantine=%s\nbackup=%s\ndestination=%s\nsource_manifest=%s\nstaging_manifest=%s\nfinal_manifest=%s\nlock=%s\n' "${str_recovery_errors:-none}" "${path_quarantine:-}" "${path_backup:-}" "${path_destination}" "${str_source_manifest_hash:-}" "${str_staging_manifest_hash:-}" "${str_final_manifest_hash:-}" "${path_lock}" > "${path_recovery_receipt}"; then

            # 收据落盘失败也属于恢复失败，不能清理锁。
            str_recovery_errors="${str_recovery_errors}receipt;"
        fi

        # 恢复错误非空时保留锁，等待人工核对隔离现场。
        if [[ -n "${str_recovery_errors}" ]]; then

            # 不完整恢复时保留锁，避免下一次运行误判为已完成。
            return 1
        fi

        # 恢复完整时尝试释放锁，释放失败仍必须保留收据。
        if ! rm -f -- "${path_lock}"; then

            # 锁清理失败时补写收据，明确记录残留锁风险。
            if ! printf 'recovery_errors=lock_cleanup\nquarantine=%s\nbackup=%s\ndestination=%s\nsource_manifest=%s\nstaging_manifest=%s\nfinal_manifest=%s\nlock=%s\n' "${path_quarantine:-}" "${path_backup:-}" "${path_destination}" "${str_source_manifest_hash:-}" "${str_staging_manifest_hash:-}" "${str_final_manifest_hash:-}" "${path_lock}" > "${path_recovery_receipt}"; then

                # 收据也无法写入时保留原失败返回。
                return 1
            fi

            # 锁仍存在，调用者必须按收据处理残留事务。
            return 1
        fi

        # 恢复成功且锁已删除，允许调用者收到零错误结果。
        return 0
    }

    # 只允许在已存在平台根下创建一层缺失的 skills 子目录，防止扩大写入范围。
    if [[ ! -d "${path_install_parent}" ]]; then

        # 父目录缺失时只创建 projection 指定的一层目录。
        if ! mkdir "${path_install_parent}"; then

            # 创建失败先进入统一恢复，保留锁和失败证据。
            recover_failure

            # 输出父目录创建错误，调用者可定位 boundary 权限问题。
            printf '%s\n' "> ERR: [Shell] install parent directory could not be created." >&2

            # 父目录未建立时事务以失败结束。
            return 1
        fi
    fi

    # 同卷检查确保后续 move 保持原子边界，而不是跨设备复制。
    if [[ "$(stat -c '%d' "${path_platform_home}")" != "$(stat -c '%d' "${path_install_parent}")" ]]; then

        # 跨设备时先恢复现场，再报告不能保证原子切换。
        recover_failure

        # 输出文件系统边界错误，避免伪造原子安装结论。
        printf '%s\n' "> ERR: [Shell] target crosses a filesystem boundary." >&2

        # 事务在复制前结束，确保正式目标尚未被切换。
        return 1
    fi

    # 复制前先生成源树清单，链接和特殊节点在 staging 前被拒绝。
    if ! build_tree_manifest "${path_source}" "${path_source_manifest}"; then

        # 清单失败时恢复锁与临时现场。
        recover_failure

        # 输出源树身份错误，保持失败阶段可定位。
        printf '%s\n' "> ERR: [Shell] source tree manifest validation failed." >&2

        # 未生成完整源清单时不继续复制。
        return 1
    fi

    # 计算源清单摘要，确保 staging 和最终目标共享同一比较基准。
    str_source_manifest_hash="$(hash_file "${path_source_manifest}" "${str_hash_commands}")"

    # 显式创建 staging 根，避免 cp 对尾随斜杠产生不确定目录语义。
    if ! mkdir "${path_staging}"; then

        # staging 创建失败时先保留恢复证据。
        recover_failure

        # 输出 staging 创建错误。
        printf '%s\n' "> ERR: [Shell] staging directory could not be created." >&2

        # staging 创建失败时不触发复制，避免把文件写入未知目录。
        return 1
    fi

    # 复制前所有失败均转入统一恢复分支，避免留下未收据化副本。
    if ! cp -a -- "${path_source}/." "${path_staging}/" 2>/dev/null; then

        # 复制失败先隔离 staging 并恢复旧目标。
        recover_failure

        # 输出源 staging 复制错误。
        printf '%s\n' "> ERR: [Shell] source staging copy failed." >&2

        # 复制失败时不继续读取 staging 清单。
        return 1
    fi

    # staging 必须保留 Skill 身份文件，确保复制目标仍是同一 Skill。
    [[ -f "${path_staging}/SKILL.md" && -f "${path_staging}/VERSION" ]] || { recover_failure; printf '%s\n' "> ERR: [Shell] staged Skill identity is incomplete." >&2; return 1; }

    # 为 staging 生成独立清单，比较复制后的每个节点事实。
    path_staging_manifest="${path_staging}.manifest.tsv"

    # staging 清单失败时不允许把不完整副本切换到正式目录。
    build_tree_manifest "${path_staging}" "${path_staging_manifest}" || { recover_failure; printf '%s\n' "> ERR: [Shell] staged source manifest validation failed." >&2; return 1; }

    # 计算 staging 摘要，后续必须与源清单完全一致。
    str_staging_manifest_hash="$(hash_file "${path_staging_manifest}" "${str_hash_commands}")"

    # 源与 staging 清单不一致属于复制错误，必须阻断目标切换。
    cmp -s "${path_source_manifest}" "${path_staging_manifest}" || { recover_failure; printf '%s\n' "> ERR: [Shell] source and staging manifests differ." >&2; return 1; }

    # 替换安装先把旧目标移动到受控 backup 根，确保失败可恢复。
    if [[ -e "${path_destination}" || -L "${path_destination}" ]]; then

        # backup 根缺失时先创建它，确保旧目标移动前仍可恢复。
        mkdir -p -- "${path_backup_root}"

        # 以 Skill 名称和进程号构造唯一旧目标备份路径。
        path_backup="${path_backup_root}/${str_skill_name}-${BASHPID}"

        # 旧目标移动失败时恢复 staging 与锁状态。
        mv -- "${path_destination}" "${path_backup}" || { recover_failure; return 1; }
    fi

    # staging 已通过清单核对后移动到正式目录，保持同卷原子切换。
    if ! mv -- "${path_staging}" "${path_destination}"; then

        # 切换失败时先隔离现场并尝试恢复旧目标。
        recover_failure

        # 输出正式切换错误，防止误报安装成功。
        printf '%s\n' "> ERR: [Shell] staged Skill switch failed." >&2

        # 目标切换失败时事务保持非零结果。
        return 1
    fi

    # 切换后再次确认 Skill 身份文件，防止目标目录内容异常。
    [[ -f "${path_destination}/SKILL.md" && -f "${path_destination}/VERSION" ]] || { recover_failure; printf '%s\n' "> ERR: [Shell] post-switch Skill identity is incomplete." >&2; return 1; }

    # 为正式目标生成最终清单，比较切换后的完整目录事实。
    path_final_manifest="${path_destination}.final.manifest.tsv"

    # 最终清单失败时隔离目标并保留恢复证据。
    build_tree_manifest "${path_destination}" "${path_final_manifest}" || { recover_failure; printf '%s\n' "> ERR: [Shell] final source manifest validation failed." >&2; return 1; }

    # 计算最终目标摘要，后续必须与源清单保持一致。
    str_final_manifest_hash="$(hash_file "${path_final_manifest}" "${str_hash_commands}")"

    # 最终目标与源清单不一致属于切换错误，必须拒绝释放事务锁。
    cmp -s "${path_source_manifest}" "${path_final_manifest}" || { recover_failure; printf '%s\n' "> ERR: [Shell] final destination manifest differs from source." >&2; return 1; }

    # 只有源、staging、最终清单均核对完成后才清理中间证据。
    if ! rm -f -- "${path_source_manifest}" "${path_staging_manifest}" "${path_final_manifest}"; then

        # 清单清理失败时先建立隔离根，锁必须继续保留。
        if ! mkdir -p -- "${path_quarantine_root}"; then

            # 隔离根也无法创建时输出锁残留风险。
            printf '%s\n' "> ERR: [Shell] manifest cleanup failed and recovery receipt root could not be created; lock preserved: ${path_lock}" >&2

            # 清理失败以非零结果结束。
            return 1
        fi

        # 记录清单清理失败的恢复收据路径。
        path_recovery_receipt="${path_quarantine_root}/${BASHPID}$(manifest_value RECOVERY_RECEIPT_SUFFIX)"

        # 将三份清单摘要和锁路径写入恢复收据。
        if ! printf 'recovery_errors=manifest_cleanup\nsource_manifest=%s\nstaging_manifest=%s\nfinal_manifest=%s\nlock=%s\n' "${str_source_manifest_hash}" "${str_staging_manifest_hash}" "${str_final_manifest_hash}" "${path_lock}" > "${path_recovery_receipt}"; then

            # 收据写入失败时明确报告锁仍被保留。
            printf '%s\n' "> ERR: [Shell] manifest cleanup recovery receipt could not be written; lock preserved: ${path_lock}" >&2

            # 保留非零结果，不伪造清理成功。
            return 1
        fi

        # 清单清理失败但收据已落盘，仍保留锁供人工恢复。
        printf '%s\n' "> ERR: [Shell] installation completed but manifest cleanup failed; lock preserved: ${path_lock}" >&2

        # 事务已经切换但收尾失败，返回非零以触发治理诊断。
        return 1
    fi

    # 清理所有中间清单后再释放事务锁，避免中途状态被误判为完成。
    if ! rm -f -- "${path_lock}"; then

        # 锁清理失败时先确保恢复收据根可用。
        if ! mkdir -p -- "${path_quarantine_root}"; then

            # 无法创建收据根时直接报告锁残留风险。
            printf '%s\n' "> ERR: [Shell] lock cleanup failed and recovery receipt root could not be created; lock preserved: ${path_lock}" >&2

            # 锁仍存在，返回失败让调用者阻止下一次事务。
            return 1
        fi

        # 记录锁清理失败的恢复收据位置。
        path_recovery_receipt="${path_quarantine_root}/${BASHPID}$(manifest_value RECOVERY_RECEIPT_SUFFIX)"

        # 将最终摘要与锁路径落盘，保留事务已切换事实。
        if ! printf 'recovery_errors=lock_cleanup\nsource_manifest=%s\nstaging_manifest=%s\nfinal_manifest=%s\nlock=%s\n' "${str_source_manifest_hash}" "${str_staging_manifest_hash}" "${str_final_manifest_hash}" "${path_lock}" > "${path_recovery_receipt}"; then

            # 收据无法写入时输出不可恢复风险并保留锁。
            printf '%s\n' "> ERR: [Shell] lock cleanup recovery receipt could not be written; lock preserved: ${path_lock}" >&2

            # 锁清理失败保持非零结果。
            return 1
        fi

        # 收据已写入但锁仍残留，调用者必须先处理该锁。
        printf '%s\n' "> ERR: [Shell] installation completed but lock cleanup failed; lock preserved: ${path_lock}" >&2

        # 锁残留属于事务失败，不能返回成功。
        return 1
    fi

    # 源、staging、最终摘要全部一致且锁已清除，输出可验证成功事实。
    printf '%s\n' "> INFO: [Shell] Installation completed successfully; source_manifest=${str_source_manifest_hash}; staging_manifest=${str_staging_manifest_hash}; final_manifest=${str_final_manifest_hash}"
}

# 入口检查确保参数、manifest、平台和路径全部通过后才允许写入。
main() {

    # 先解析调用者参数，后续所有路径和开关都来自受控变量。
    parse_arguments "$@"

    # 项目类型必须与 manifest 许可值一致，避免把 installer 用于未授权项目。
    [[ "${str_project_kind}" == "$(manifest_value ALLOWED_PROJECT_KIND)" ]] || { printf '%s\n' "> ERR: [Shell] project kind is not eligible for the Skill installer." >&2; return 2; }

    # 读取并验证 projection、catalog、manifest 和 schema 的摘要合同。
    load_projection

    # 读取 manifest 的 shell 输出类别，保持控制台消息使用统一 Kind。
    str_shell_output_format="$(manifest_value SHELL_OUTPUT_FORMAT)"

    # 未显式指定输出类别时沿用 manifest，显式值稍后严格比较。
    str_output_kind="${str_output_kind:-${str_shell_output_format}}"

    # 输出类别偏离 manifest 时阻断入口，避免产生未治理日志格式。
    [[ "${str_output_kind}" == "${str_shell_output_format}" ]] || { printf '%s\n' "> ERR: [Shell] output-kind is not permitted by the manifest." >&2; return 2; }

    # 选择并核验唯一平台记录，目标根尚未解析前不进入事务。
    select_platform

    # 解析源根、平台根和目标路径，确保 containment 检查完成后才写入。
    resolve_paths

    # 处理替换确认和 dry-run 边界，未获确认时不创建文件。
    confirm_install

    # 预演模式跳过事务，真实写入只在谓词关闭时发生。
    [[ "${is_dry_run}" == true ]] || install_transaction
}

# 启动入口，任何非零返回都由 shell 传播给调用者。
main "$@"
