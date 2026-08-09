"""实现设计访谈的远程路由、最终对齐、审查及写入前完成态。"""

# 远程路由处理器验证服务器选择并保存可执行的任务映射。
def answer_remote_server_route_mapping(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """验证并保存访谈提交的远程任务服务器路由。

    参数：project 为项目根，state 为访谈状态，payload 为远程启用标志和任务路由。
    返回：远程门禁完成后的下一阶段交互载荷。
    异常：路由缺失、依赖未安装或解析失败时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由任务路由和服务器数决定，dtype 为 JSON 兼容映射，unit 不适用。
    """

    # 保留原始选择以区分显式 false、缺失字段和其他非法类型。
    remote_enabled = payload.get(USE_REMOTE_SERVER_KEY)  # 用户提交的远程服务器启用标志。

    # 只有布尔 false 触发禁用分支，其他值继续由路由合同验证。
    if isinstance(remote_enabled, bool) and not remote_enabled:

        # 禁用路径不需要解析服务器注册表。
        return disable_remote_gate_and_continue(project, state)

    # 保留原始路由输入供规范化器处理字符串和映射变体。
    raw_routes = payload.get(REMOTE_SERVER_TASK_ROUTES_KEY, [])  # 用户提交的远程任务路由。

    # 规范化后每个条目都遵循稳定的任务路由 schema。
    routes = normalize_remote_task_routes(raw_routes)  # 规范化任务路由列表。

    # 启用远程执行时至少需要一条明确路由。
    if not routes:

        # 返回缺失字段诊断而不改变现有门禁状态。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=[f"missing required answer: {REMOTE_SERVER_TASK_ROUTES_KEY}"],
            )
        )

        # 缺失路由阻止访谈进入后续阶段。
        raise SystemExit(1)

    # 当前门禁载荷包含发现阶段保存的服务器候选。
    gate = remote_gate_payload(state)  # 当前远程服务器门禁状态。

    # 依赖摘要提供已安装状态和 skill 目录位置。
    dependency = remote_dependency_summary()  # erie-remote-ssh 依赖事实。

    # 未安装远程技能时无法验证服务器身份和任务能力。
    if not dependency["installed"]:

        # 返回依赖缺失诊断，避免把未验证路由标记为成功。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["remote server routes cannot be validated because erie-remote-ssh is not installed"],
            )
        )

        # 依赖缺失是当前提交的阻断条件。
        raise SystemExit(1)

    # 服务器候选来自前序发现门禁的 choices 字段。
    list_records = gate.get("choices", {}).get("servers", [])  # 原始服务器注册记录。

    # 畸形 choices 不应传入注册表规范化器。
    if not isinstance(list_records, list):

        # 空列表使后续校验产生明确的未知服务器诊断。
        list_records = []  # 无可用服务器候选。

    # 远程技能目录用于解析服务器注册表和执行策略。
    path_skill_dir = Path(str(dependency["skill_dir"]))  # 已安装远程技能根目录。

    # 规范化注册记录以统一服务器 ID、账号、端口和能力字段。
    registry = normalize_remote_server_registry(list_records)  # 标准服务器注册表。

    # ID 索引支持快速验证主服务器与回退服务器引用。
    registry_map = server_registry_map(registry)  # 服务器 ID 到注册记录的映射。

    # 汇总全部路由诊断，避免用户逐条修复后重复提交。
    list_errors: list[str] = []  # 远程路由验证错误集合。

    # 只把成功解析的标准路由写回最终答案。
    list_resolved_routes: list[dict[str, Any]] = []  # 已验证任务路由集合。

    # 解析证据保留实际选中服务器和回退决策。
    list_validation_results: list[dict[str, Any]] = []  # 每条路由的解析结果。

    # 每条任务路由独立验证引用并执行服务器选择解析。
    for route in routes:

        # 先验证路由引用的所有服务器 ID 均存在于注册表。
        list_errors.extend(validate_route_server_ids(route, registry_map))

        # 单路由门禁配置复用运行时解析器验证真实选择行为。
        resolution = resolve_remote_server_for_task(  # 当前任务的服务器解析证据。
            {
                "enabled": True,  # 本分支已确认启用远程执行。
                "server_registry": registry,  # 使用本轮规范化注册表。
                "task_routes": [route],  # 每次仅验证当前路由。
                "unmatched_task_policy": "block-and-update-agents",  # 未匹配任务必须补规则。
                "failover_policy": "auto-fallback",  # 主服务器不可用时允许声明式回退。
            },
            str(route.get("task_name", "")),  # 解析当前路由声明的任务名。
            path_skill_dir,  # 使用已安装远程技能的运行时合同。
        )

        # 解析失败时保留失败明细并跳过标准路由构建。
        if not resolution.get("ok"):

            # 优先返回结构化 failures，缺失时使用解析器消息。
            list_errors.extend(
                resolution.get("failures", [])
                or [str(resolution.get("message", "remote route validation failed"))]
            )

            # 当前失败路由不应进入已验证结果集合。
            continue

        # 主服务器能力用于补全未显式给出的任务和功能范围。
        primary_server = registry_map.get(  # 当前路由引用的主服务器记录。
            str(route.get("primary_server_id", "")).strip(),  # 规范化主服务器 ID。
            {},  # 未知 ID 使用空记录并由前序诊断报告。
        )

        # 仅映射类型服务器记录能够公开 functions 字段。
        primary_functions = (  # 主服务器规范化能力列表。
            normalize_remote_task_list(primary_server.get("functions", []))  # 规范化声明能力。
            if isinstance(primary_server, dict)  # 服务器记录必须是映射。
            else []  # 畸形记录不提供能力回填。
        )

        # 复制路由避免在遍历时修改规范化输入集合。
        dict_normalized_route = dict(route)  # 待补全并写回状态的路由。

        # 未声明 route_tasks 时使用服务器能力或当前任务名回填。
        if not dict_normalized_route.get("route_tasks"):

            # 回填值保证最终规则明确该路由覆盖的任务集合。
            dict_normalized_route["route_tasks"] = (  # 路由覆盖的任务名称。
                primary_functions  # 优先继承主服务器声明的能力范围。
                or [str(route.get("task_name", "")).strip()]  # 无能力声明时限定为当前任务。
            )

        # 未声明 route_functions 时继承主服务器能力。
        if not dict_normalized_route.get("route_functions"):

            # 功能范围用于后续运行时匹配具体远程能力。
            dict_normalized_route["route_functions"] = primary_functions  # 路由允许的服务器功能。

        # 用户提交并通过解析后，路由选择才可标记为已确认。
        dict_normalized_route["selection_confirmed"] = True  # 服务器选择确认标志。

        # 验证状态供生成器和运行时拒绝未核验路由。
        dict_normalized_route["validation_status"] = "verified"  # 路由验证结论。

        # 保存完整标准路由供最终答案和门禁状态复用。
        list_resolved_routes.append(dict_normalized_route)

        # 保存解析器证据用于审计实际服务器选择。
        list_validation_results.append(resolution)

    # 任一路由失败都会阻止整批配置写入，避免部分成功状态。
    if list_errors:

        # 一次性返回全部路由诊断供用户统一修正。
        emit_json(interactive_payload(project, state, errors=list_errors))

        # 错误批次不更新答案或门禁载荷。
        raise SystemExit(1)

    # 最终答案映射承载生成 AGENTS 远程策略所需字段。
    answers = state.setdefault("answers", {})  # 当前访谈累计答案。

    # 写回全部通过验证的标准任务路由。
    answers[REMOTE_SERVER_TASK_ROUTES_KEY] = list_resolved_routes  # 最终远程任务路由。

    # 总体验证状态证明本轮路由已通过真实解析器。
    answers[REMOTE_VALIDATION_STATUS_KEY] = "verified"  # 最终远程验证结论。

    # 门禁状态保留规范化注册表供后续恢复与展示。
    gate["server_registry"] = registry  # 已验证路由使用的服务器注册表。

    # 门禁状态与最终答案共享同一标准路由集合。
    gate["task_routes"] = list_resolved_routes  # 门禁确认的任务路由。

    # 每条解析证据支持审计主服务器和回退选择。
    gate["route_validation_results"] = list_validation_results  # 路由解析证据集合。

    # 门禁自身进入已验证状态，允许访谈继续。
    gate["validation_status"] = "verified"  # 远程门禁验证状态。

    # 将完整远程门禁载荷写回访谈状态。
    set_remote_gate_payload(state, gate)

    # 远程门禁闭合后由统一推进器选择下一访谈阶段。
    return advance_after_remote_gate(project, state)

# 已确认分组推进器记录确认状态并选择下一访谈阶段。
def confirm_regular_group(
    project: Path,
    state: dict[str, Any],
    list_correction_keys: list[str],
) -> dict[str, Any]:
    """处理纯确认提交并推进分组、远程门禁或附加需求。

    参数：project 为项目根，state 为访谈状态，list_correction_keys 为额外修正键。
    数据合同：list_correction_keys 的 shape=(n,)，dtype=str，unit=无量纲；
    state 是字段到访谈值的映射，不适用数值 shape、dtype 或 unit。
    返回：下一问题组、远程门禁、附加需求或 takeover 完成载荷。
    异常：确认提交混入修正字段时抛出 SystemExit(1)。
    """

    # 修正与确认混合会让确认对象产生歧义。
    if list_correction_keys:

        # 返回可操作诊断，要求先修正再单独确认。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["confirmed groups cannot carry extra correction fields in the same submission"],
            )
        )

        # 混合动作不推进状态机。
        raise SystemExit(1)

    # 当前索引决定确认记录和后续组位置。
    int_index = int(state.get("current_group_index", 0))  # 当前问题组零基索引。

    # 集合去除历史状态中可能存在的重复确认索引。
    set_confirmed = {int(item) for item in state.get("confirmed_group_indices", [])}  # 已确认组索引集合。

    # 将当前组加入确认集合并稳定排序。
    set_confirmed.add(int_index)

    # 持久化表示使用稳定升序，避免重复索引和无意义差异。
    state["confirmed_group_indices"] = sorted(set_confirmed)  # 更新完整确认进度。

    # 公共组首次确认后才能确定项目类型和分支问题组。
    if int_index == 0 and state.get("kind") is None:

        # 根据公共答案重建后续 skill 或 engineering 分组。
        update_groups_after_common_confirmation(state)

        # 启用知识图谱时先完成本地依赖与 Codex MCP 配置问询。
        command_result = refresh_codebase_memory_gate(project, state)  # 可选知识图谱门禁响应

        # 依赖未就绪时返回人工安装或完成等待交互载荷。
        if command_result is not None:

            # 当前门禁必须完成后才能进入远程服务器选择。
            return command_result

        # 启用远程服务器时刷新服务器选择门禁。
        if use_remote_server_enabled(state.get("answers", {})):

            # 门禁可能直接返回需要用户交互的服务器载荷。
            command_result = refresh_remote_gate(project, state)  # 可选远程门禁响应。

            # 非空响应表示状态机应暂停在远程服务器确认。
            if command_result is not None:

                # 将远程门禁载荷直接交给调用方。
                return command_result

    # takeover 模式完成最后一组后走专用接管收口。
    if str(state.get("mode", "interactive")) == "takeover" and int_index + 1 >= len(state.get("groups", [])):

        # 接管完成器负责生成缺失治理文件的后续动作。
        return complete_takeover(project, state, move_to_extra_requirements)

    # 当前组已经是最后一组时改走附加需求阶段。
    if int_index + 1 >= len(state.get("groups", [])):

        # 标准访谈全部分组完成后进入附加需求问题。
        return move_to_extra_requirements(project, state)

    # 下一组索引紧随当前已确认组。
    state["current_group_index"] = int_index + 1  # 更新问题组游标。

    # 新问题组从收集答案状态开始。
    state["status"] = "collecting_group"  # 等待下一组答案。

    # 持久化确认进度和下一组游标。
    write_state(project, state)

    # 返回下一组对应的交互载荷。
    return interactive_payload(project, state)

# 否认确认处理器校验可选修正并返回当前问题组。
def revise_regular_group(
    project: Path,
    state: dict[str, Any],
    payload: dict[str, Any],
    list_correction_keys: list[str],
) -> dict[str, Any]:
    """处理否认确认后的本组修正或重新作答请求。

    参数：project 为项目根，state 为访谈状态，payload 为提交载荷，
    list_correction_keys 为本组修正键。
    数据合同：list_correction_keys 的 shape=(n,)，dtype=str，unit=无量纲；
    state 与 payload 是字段映射，不适用数值 shape、dtype 或 unit。
    返回：更新后的当前问题组交互载荷。
    异常：修正值不符合问题合同时抛出 SystemExit(1)。
    """

    # 同次提交包含修正时先执行字段值验证。
    if list_correction_keys:

        # 使用当前组字段合同校验修正后的值。
        list_errors = validate_group_answers(  # 当前组修正值的验证诊断。
            {key: payload[key] for key in list_correction_keys},  # 本次提交的修正字段值。
            list_correction_keys,  # 需要逐项验证的字段顺序。
        )

        # 任一字段错误都会保留原答案和状态。
        if list_errors:

            # 将全部字段诊断一次性返回给交互客户端。
            emit_json(interactive_payload(project, state, errors=list_errors))

            # 验证失败时终止本次状态转换。
            raise SystemExit(1)

        # 合法修正覆盖当前组的对应答案字段。
        state.setdefault("answers", {}).update({key: payload[key] for key in list_correction_keys})

        # 修正完成后再次请求用户确认当前组。
        state["status"] = "awaiting_group_confirmation"  # 等待修正后的组确认。

    # 没有修正字段时回到当前问题组重新收集答案。
    else:

        # 未提供修正表示需要重新进入当前组答案收集。
        state["status"] = "collecting_group"  # 返回当前问题组重新作答。

    # 持久化当前分组确认结果和下一交互状态。
    write_state(project, state)

    # 返回分组确认后的交互载荷供调用方继续访谈。
    return interactive_payload(project, state)

# 分组确认处理器校验本组修正，并推进到下一问题组或附加需求。
def confirm_group(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """处理当前问题组的确认、修正与状态推进。

    参数：project 为项目根，state 为访谈状态，payload 为确认标志及可选修正。
    返回：下一问题组、远程门禁、附加需求或 takeover 完成载荷。
    异常：确认字段无效或修正越界时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由当前问题组字段数决定，dtype 为 JSON 兼容答案，unit 不适用。
    """

    # 确认标志必须显式为布尔值，避免把缺失和否认混为一类。
    if GROUP_CONFIRMATION_KEY not in payload or not isinstance(payload[GROUP_CONFIRMATION_KEY], bool):

        # 标准交互错误说明调用方需要提交 true 或 false。
        emit_json(interactive_payload(
            project,
            state,
            errors=[f"{GROUP_CONFIRMATION_KEY} must be provided as true or false"],
        ))

        # 无效确认不得改变持久化状态。
        raise SystemExit(1)

    # 除确认标志外的字段都视为对当前组答案的修正。
    list_correction_keys = [key for key in payload if key != GROUP_CONFIRMATION_KEY]  # 本次提交的修正字段。

    # 当前组答案字段限定修正范围。
    list_expected_keys = question_ids_to_keys(current_group_ids(state))  # 当前组允许修改的答案字段。

    # 跨组修正会破坏逐组确认顺序，因此直接阻断。
    if any(key not in list_expected_keys for key in list_correction_keys):

        # 错误载荷指出修正必须限制在当前问题组。
        emit_json(interactive_payload(project, state, errors=["group corrections must stay within the current group"]))

        # 越界修正不写入任何答案。
        raise SystemExit(1)

    # 确认与否认分别交给单一职责推进器。
    if payload[GROUP_CONFIRMATION_KEY]:

        # 纯确认路径推进到下一门禁或问题组。
        return confirm_regular_group(project, state, list_correction_keys)

    # 否认路径保留在当前组并应用可选修正。
    return revise_regular_group(project, state, payload, list_correction_keys)

# 问题索引器把答案字段映射回标准设计问题组。
def group_index_for_key(kind: str, answer_key: str) -> int | None:
    """查找答案字段在指定开发类型问题组中的位置。

    参数：kind 为 skill 或 engineering，answer_key 为答案字段名。
    返回：首个匹配组的零基索引；未找到时返回 None。
    """

    # 按展示顺序扫描问题组，确保返工定位稳定。
    for index, group in enumerate(groups_for(kind)):

        # 问题标识先转换为答案字段再进行成员判断。
        if answer_key in question_ids_to_keys(group):

            # 首个命中组就是交互流程需要返回的位置。
            return index

    # 未知字段不属于该开发类型的标准问题组。
    return None

# 状态索引器优先使用持久化分组，兼容问题定义升级后的会话。
def group_index_for_key_in_state(state: dict[str, Any], answer_key: str) -> int | None:
    """从访谈状态中的实际分组定位答案字段。

    参数：state 为持久化访谈状态，answer_key 为待定位答案字段。
    返回：匹配问题组索引；状态不足且标准分组也不匹配时返回 None。
    数组契约：shape 为状态内问题组的一维序列，dtype 为字符串问题标识，unit 不适用。
    """

    # 历史会话保存的分组是恢复交互位置的第一证据。
    groups = state.get("groups", [])  # 会话创建时固化的问题组列表。

    # 非列表分组按空集合处理，避免畸形状态中断返工诊断。
    for index, group in enumerate(groups if isinstance(groups, list) else []):

        # 只接受列表组，并将持久化问题标识统一转换为字符串。
        if isinstance(group, list) and answer_key in question_ids_to_keys([str(item) for item in group]):

            # 返回会话实际使用的组索引而非当前定义索引。
            return index

    # 会话未保存匹配组时，从类型字段选择当前标准问题定义。
    kind = str(state.get("kind") or state.get("answers", {}).get("development_type", "")).strip()  # 访谈开发类型。

    # 只有受支持类型才能安全调用标准问题组查找器。
    if kind in {"skill", "engineering"}:

        # 标准定义为旧会话或缺失分组提供兼容回退。
        return group_index_for_key(kind, answer_key)

    # 无有效类型时无法推导字段所属问题组。
    return None

# 答案字段汇总器限定最终对齐阶段允许修正的键集合。
def all_answer_keys_for_state(state: dict[str, Any]) -> set[str]:
    """收集当前访谈允许出现在对齐修正中的全部答案字段。

    参数：state 为持久化访谈状态。
    返回：标准问题答案字段与附加需求字段组成的集合。
    数组契约：shape 为一维答案字段集合，dtype 为 str，unit 不适用。
    """

    # 开发类型决定需要加载 skill 还是 engineering 问题定义。
    kind = str(state.get("kind") or state.get("answers", {}).get("development_type", "")).strip()  # 当前访谈类型。

    # 未知类型不加载问题，防止把非法字段误判为可修正字段。
    set_keys = (
        {item["answer_key"] for item in questions_for(kind)}  # 标准问题声明的答案字段。
        if kind in {"skill", "engineering"}  # 仅支持两个受管开发分支。
        else set()  # 缺失类型时从空集合开始。
    )

    # 附加需求是独立于标准问题组的最终开放字段。
    set_keys.add(EXTRA_REQUIREMENTS_KEY)

    # 集合用于拒绝最终对齐中的未知修正键。
    return set_keys

# 附加需求处理器保存最后一个开放问题并进入最终对齐状态。
def answer_extra_requirements(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """接受附加需求答案并使访谈进入最终对齐阶段。

    参数：project 为项目根，state 为访谈状态，payload 为本次回答。
    返回：包含最终对齐提示的最新交互载荷。
    异常：字段缺失时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 取决于附加需求条目数，dtype 为字符串需求，unit 不适用。
    """

    # 字段必须显式存在，空值仍代表用户确认没有附加需求。
    if EXTRA_REQUIREMENTS_KEY not in payload:

        # 缺失答案通过标准交互载荷返回给调用端。
        emit_json(interactive_payload(project, state, errors=[f"missing required answer: {EXTRA_REQUIREMENTS_KEY}"]))

        # 非零退出阻止状态在答案缺失时前进。
        raise SystemExit(1)

    # 将字符串或列表输入规范为稳定的附加需求结构。
    extra = normalize_extra_requirements(payload.get(EXTRA_REQUIREMENTS_KEY))  # 规范化附加需求答案。

    # 保存开放问题答案以参与最终画像构建。
    state.setdefault("answers", {})[EXTRA_REQUIREMENTS_KEY] = extra  # 更新最终开放问题答案。

    # 所有问题完成后等待用户确认完整答案摘要。
    state["status"] = "awaiting_final_alignment"  # 将状态机推进到对齐确认节点。

    # 答案变化使旧画像预览失效。
    state.pop("profile_preview", None)

    # 答案变化也使旧设计审查请求失效。
    state.pop("design_review_request", None)

    # 移除旧审查结论，确保修正后的画像重新审查。
    state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)

    # 原子持久化更新后的答案与状态。
    write_state(project, state)

    # 返回最终对齐阶段的交互载荷。
    return interactive_payload(project, state)

# 写入意图审查入口保存画像预览并生成设计审查请求。
def enter_design_review(
    project: Path,
    state: dict[str, Any],
    final_answers: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """将已对齐答案转换为等待设计审查的写入状态。

    参数：project 为项目根，state 为访谈状态，final_answers 为对齐答案，profile 为画像预览。
    返回：包含画像预览和审查请求的交互载荷。
    数组契约：shape 由答案与画像字段决定，dtype 为 JSON 兼容业务值，unit 不适用。
    """

    # 新审查开始前删除可能来自旧轮次的审查结论。
    final_answers.pop(DESIGN_REVIEW_KEY, None)

    # 对齐答案成为本轮审查的权威输入。
    state["answers"] = final_answers  # 固化本轮审查使用的最终答案。

    # 写入意图要求设计审查通过后才能完成。
    state["intent"] = "write"  # 标记审查通过后将执行受管写入。

    # 状态机停在审查节点等待外部审阅结果。
    state["status"] = "awaiting_design_review"  # 将状态机停在设计审查节点。

    # 保存可审阅的完整项目画像。
    state["profile_preview"] = profile  # 保存供审阅者核对的项目画像。

    # 请求载荷包含审阅者需要的事实和检查项。
    state["design_review_request"] = design_review_request(  # 构造本轮结构化审查请求。
        project,  # 将审查请求绑定到当前项目根。
        final_answers,  # 提供本轮最终对齐答案。
        profile,  # 附带需要审阅的项目画像。
    )

    # 持久化审查状态以支持跨进程恢复。
    write_state(project, state)

    # 基础交互载荷描述下一步审查动作。
    dict_payload_out = interactive_payload(project, state)  # 等待审查的响应载荷。

    # 画像预览单独公开，便于客户端展示完整设计结果。
    dict_payload_out["profile_preview"] = profile  # 在响应中公开可审阅画像。

    # 返回审查请求及其项目画像。
    return dict_payload_out

# 只读完成入口跳过写入审查但保留可检查的画像预览。
def complete_read_only(
    project: Path,
    state: dict[str, Any],
    final_answers: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """完成只读访谈并返回画像预览，不创建写入批准状态。

    参数：project 为项目根，state 为访谈状态，final_answers 为对齐答案，profile 为画像预览。
    返回：标记只读完成且包含画像预览的交互载荷。
    数组契约：shape 由答案与画像字段决定，dtype 为 JSON 兼容业务值，unit 不适用。
    """

    # 只读结果不携带任何旧写入审查结论。
    final_answers.pop(DESIGN_REVIEW_KEY, None)

    # 保存最终答案供结果展示和后续重新进入写入流程。
    state["answers"] = final_answers  # 保存只读结果对应的最终答案。

    # 显式记录只读意图，避免调用方误解为已批准写入。
    state["intent"] = "read_only"  # 明确禁止把完成态解释为写入批准。

    # 专用完成态区分只读交付与受管写入完成。
    state["status"] = "completed_read_only"  # 记录只读访谈已经完整结束。

    # 只读模式仍公开完整画像供审阅。
    state["profile_preview"] = profile  # 保留只读交付的项目画像。

    # 清除写入模式遗留的审查请求。
    state.pop("design_review_request", None)

    # 清除尚未提交的审查结果，避免跨意图泄漏。
    state.pop("pending_design_review", None)

    # 持久化只读完成证据和画像预览。
    write_state(project, state)

    # 基础响应包含只读完成状态与对齐摘要。
    dict_payload_out = interactive_payload(project, state)  # 只读完成响应载荷。

    # 将画像预览直接附加到外部响应。
    dict_payload_out["profile_preview"] = profile  # 将画像附加到只读响应。

    # 返回无需进一步审查的只读结果。
    return dict_payload_out

# 默认写入完成器在用户未请求方案审查时直接关闭访谈。
def complete_without_review(
    project: Path,
    state: dict[str, Any],
    final_answers: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """完成默认写入访谈，不创建方案审查智能体请求。

    参数：project 为项目根，state 为访谈状态，final_answers 为对齐答案，profile 为待写入画像。
    返回：标记写入访谈完成且包含画像预览的交互载荷。
    数组契约：shape 由答案与画像字段决定，dtype 为 JSON 兼容业务值，unit 不适用。
    """

    # 默认流程移除旧审查证据，防止历史请求被误当作本轮授权。
    final_answers.pop(DESIGN_REVIEW_KEY, None)

    # 保存用户已经完成最终对齐的写入答案。
    state["answers"] = final_answers  # 当前写入访谈的最终答案。

    # 写入意图保持不变，供后续受管生成流程识别。
    state["intent"] = "write"  # 当前访谈允许执行受管写入。

    # 完成态表示无需等待任何方案审查智能体。
    state["status"] = "completed"  # 默认无审查写入访谈已完成。

    # 保留最终画像供写入命令和用户核对。
    state["profile_preview"] = profile  # 已确认的项目画像预览。

    # 清除旧方案审查请求，避免默认流程继续提示派发智能体。
    state.pop("design_review_request", None)

    # 清除尚未提交的审查结果，避免跨任务继承授权。
    state.pop("pending_design_review", None)

    # 持久化无需方案审查的完成状态。
    write_state(project, state)

    # 构建包含完成状态和对齐摘要的响应。
    dict_payload_out = interactive_payload(project, state)  # 默认写入完成响应。

    # 将已确认画像直接附加到外部响应。
    dict_payload_out["profile_preview"] = profile  # 供调用方继续受管写入。

    # 返回不含审查派发请求的完成结果。
    return dict_payload_out

# 最终对齐处理器接受纯确认或将修正路由回对应问题组。
def finalize_alignment(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """处理最终答案摘要的确认或字段修正。

    参数：project 为项目根，state 为访谈状态，payload 为对齐标志和可选修正。
    返回：只读完成、设计审查或重新确认问题组的交互载荷。
    异常：标志无效、修正未知或必填值为空时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由修正字段数决定，dtype 为 JSON 兼容答案，unit 不适用。
    """

    # 对齐标志必须显式为布尔值以区分确认、否认和缺失。
    if ALIGNMENT_KEY not in payload or not isinstance(payload[ALIGNMENT_KEY], bool):

        # 返回字段合同诊断而不改变访谈状态。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=[f"{ALIGNMENT_KEY} must be provided as true or false"],
            )
        )

        # 无效对齐标志不能触发画像构建或返工。
        raise SystemExit(1)

    # 从最终对齐提交中分离需要重新验证的答案字段。
    correction_keys = [key for key in payload if key != ALIGNMENT_KEY]  # 对齐阶段修正字段。

    # 当前访谈问题定义限定允许修改的答案字段。
    set_all_keys = all_answer_keys_for_state(state)  # 合法最终答案字段集合。

    # 未知字段不能写入画像或用于定位返工问题组。
    if any(key not in set_all_keys for key in correction_keys):

        # 返回未知字段范围诊断，要求调用方仅提交已定义答案。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["alignment corrections must reference known design-answer fields"],
            )
        )

        # 越界修正不写入持久化答案。
        raise SystemExit(1)

    # 确认路径构建最终画像并按访谈意图完成或进入审查。
    if payload[ALIGNMENT_KEY]:

        # 最终确认必须是纯动作，不能与字段修正混合。
        if correction_keys:

            # 最终确认不能和修正内容混合提交，需返回明确阻断原因。
            list_errors = [  # 最终确认混入修正字段的阻断原因。
                "final alignment confirmation cannot include extra correction fields "  # 描述禁止混合的动作。
                "in the same submission"  # 要求调用方拆分两次提交。
            ]

            # 将阻断原因写入交互响应，避免误写未确认的设计档案。
            emit_json(interactive_payload(project, state, errors=list_errors))

            # 混合提交不能标记最终对齐成功。
            raise SystemExit(1)

        # 使用副本追加确认标志，构建失败时不污染持久化状态。
        dict_final_answers = dict(state.get("answers", {}))  # 待构建画像的最终答案副本。

        # 显式记录用户已经确认完整答案摘要。
        dict_final_answers[ALIGNMENT_KEY] = True  # 最终对齐完成证据。

        # 画像构建器执行全部设计字段和项目事实合同。
        profile, errors = build_profile(project, dict_final_answers)  # 最终画像及构建诊断。

        # 构建错误必须在切换完成态或审查态前返回。
        if errors:

            # 一次性公开全部画像合同错误。
            emit_json(interactive_payload(project, state, errors=errors))

            # 无有效画像时保留最终对齐等待状态。
            raise SystemExit(1)

        # 只读意图不要求写入批准审查，直接完成并展示画像。
        if normalize_intent(state.get("intent")) == "read_only":

            # 专用完成器持久化只读完成证据。
            return complete_read_only(project, state, dict_final_answers, profile)

        # 默认写入不创建方案审查智能体，显式审查仍由专用入口触发。
        return complete_without_review(project, state, dict_final_answers, profile)

    # 否认最终对齐时必须说明至少一个需要修正的字段。
    if not correction_keys:

        # 返回可操作诊断，提示提交修正或重置访谈。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["alignment rejection requires correction fields or --reset-interview"],
            )
        )

        # 空修正不能决定状态机应返回哪个问题组。
        raise SystemExit(1)

    # 只复制已经通过字段名白名单的修正值。
    corrections = {key: payload[key] for key in correction_keys}  # 合法最终对齐修正映射。

    # 逐项拒绝非可选字段的空值，保留原答案直至全部通过。
    for key, raw_value in corrections.items():

        # 可选字段允许显式清空，因此跳过必填检查。
        if key in OPTIONAL_EMPTY_KEYS:

            # 继续检查其余必填修正字段。
            continue

        # 其余字段使用统一空值语义判断。
        if empty(raw_value):

            # 指出具体缺失字段，便于调用方只修复该答案。
            emit_json(interactive_payload(project, state, errors=[f"missing required answer: {key}"]))

            # 空必填值不能覆盖原有有效答案。
            raise SystemExit(1)

    # 附加需求支持字符串或列表输入，需要恢复为标准结构。
    if EXTRA_REQUIREMENTS_KEY in corrections:

        # 规范化后再写入，保证最终画像结构稳定。
        corrections[EXTRA_REQUIREMENTS_KEY] = normalize_extra_requirements(  # 标准附加需求列表。
            corrections[EXTRA_REQUIREMENTS_KEY]  # 用户提交的原始附加需求值。
        )

    # 全部修正合法后一次性覆盖对应答案。
    state.setdefault("answers", {}).update(corrections)

    # 任何答案修正都会使先前设计审查结论失效。
    state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)

    # 标准问题字段映射回其问题组，附加需求没有组索引。
    indices = [  # 受修正影响的标准问题组索引。
        group_index_for_key_in_state(state, key)  # 根据会话实际分组定位字段。
        for key in correction_keys  # 遍历本次全部修正字段。
        if key != EXTRA_REQUIREMENTS_KEY  # 附加需求属于最终开放问题。
    ]

    # 仅修正附加需求时仍停留在最终对齐阶段。
    if not indices:

        # 新摘要需要用户再次确认。
        state["status"] = "awaiting_final_alignment"  # 等待修正后最终确认。

        # 持久化附加需求修正和等待状态。
        write_state(project, state)

        # 返回更新后的最终摘要交互载荷。
        return interactive_payload(project, state)

    # 最早受影响组是重新确认流程的起点。
    target_index = min(index for index in indices if index is not None)  # 首个返工问题组索引。

    # 将问题组游标回退到最早修正位置。
    state["current_group_index"] = target_index  # 当前返工问题组。

    # 修正值已写入，因此先要求确认该组而非重新收集。
    state["status"] = "awaiting_group_confirmation"  # 等待返工组确认。

    # 返工组及其后续组的旧确认均不再有效。
    state["confirmed_group_indices"] = [  # 仍有效的早期组确认索引。
        index  # 保留位于返工起点之前的确认记录。
        for index in state.get("confirmed_group_indices", [])  # 遍历原确认进度。
        if int(index) < target_index  # 丢弃返工起点及后续确认。
    ]

    # 持久化修正答案、回退游标和确认集合。
    write_state(project, state)

    # 返回返工组确认所需的交互载荷。
    return interactive_payload(project, state)

# 审查提交处理器验证审阅结果，并路由到返工或写入完成态。
def submit_design_review(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """处理设计审查结果并更新访谈状态。

    参数：project 为项目根，state 为等待审查状态，payload 为审查结果。
    返回：返工提示或包含最终画像的完成载荷。
    异常：审查或最终画像无效时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由审查发现项数量决定，dtype 为 JSON 兼容映射，unit 不适用。
    """

    # 审查对象由稳定字段名从本次提交中提取。
    review = payload.get(DESIGN_REVIEW_KEY)  # 待验证的设计审查结果。

    # 使用副本合并审查结论，避免验证失败污染持久化答案。
    dict_answers = dict(state.get("answers", {}))  # 当前最终答案副本。

    # 画像预览必须是映射；缺失时交由验证器报告。
    profile = (  # 审查所针对的项目画像预览。
        state.get("profile_preview")  # 读取最终对齐阶段保存的画像。
        if isinstance(state.get("profile_preview"), dict)  # 仅接受映射画像。
        else None  # 缺失或畸形画像交给验证器报告。
    )

    # 首轮验证允许返工结论，因此不强制 approved。
    errors = validate_design_review(  # 审查结构与项目一致性诊断。
        project,  # 绑定审查结果所属项目。
        dict_answers,  # 提供审查所依据的最终答案。
        review,  # 校验本次提交的审查载荷。
        profile,  # 对照当前画像检查审查一致性。
        require_approval=False,  # 首轮提交允许审查要求返工。
    )

    # 无效审查不得改变等待审查状态。
    if errors:

        # 一次性返回全部审查结构和一致性错误。
        emit_json(interactive_payload(project, state, errors=errors))

        # 终止当前提交并保留原画像预览。
        raise SystemExit(1)

    # 验证器成功后审查对象必须满足映射合同。
    if not isinstance(review, dict):

        # 防御验证器合同回退，避免非映射对象进入审查状态机。
        raise TypeError("> ERR: [Python] validated design review must be a mapping")

    # 需要返工的审查保存待处理结论并进入修正状态。
    if design_review_requires_rework(review):

        # 待处理审查为后续修正字段和审阅意见提供来源。
        state["pending_design_review"] = review  # 当前要求返工的审查结果。

        # 返工完成前不能把审查结论写入最终答案。
        state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)

        # 专用状态提示客户端提交修正字段或重新作答。
        state["status"] = "awaiting_review_rework"  # 等待设计审查返工。

        # 持久化审查意见以支持跨进程恢复返工。
        write_state(project, state)

        # 返回包含审查意见和下一动作的交互载荷。
        return interactive_payload(project, state)

    # 通过审查的结论成为最终答案的一部分。
    dict_answers[DESIGN_REVIEW_KEY] = review  # 已批准设计审查证据。

    # 把批准审查合并进答案后重新构建可写入画像。
    profile, profile_errors = build_profile(project, dict_answers)  # 审查完成画像及诊断。

    # 合并审查后产生的画像错误仍然阻止完成态。
    if profile_errors:

        # 将最终构建诊断返回审阅者处理。
        emit_json(interactive_payload(project, state, errors=profile_errors))

        # 无有效最终画像时不持久化批准结果。
        raise SystemExit(1)

    # 保存包含批准审查证据的最终答案。
    state["answers"] = dict_answers  # 可用于受管写入的完整答案。

    # 预览替换为重新构建后的最终画像。
    state["profile_preview"] = profile  # 审查通过后的最终项目画像。

    # completed 表明访谈、对齐和设计审查均已闭合。
    state["status"] = "completed"  # 允许进入受管写入的完成态。

    # 清除已处理的返工审查，避免旧意见残留。
    state.pop("pending_design_review", None)

    # 持久化完整答案、最终画像和完成状态。
    write_state(project, state)

    # 基础完成载荷包含对齐摘要和状态证据。
    dict_payload_out = interactive_payload(project, state)  # 设计审查完成响应。

    # 将最终画像直接公开给调用方进行写入或展示。
    dict_payload_out["profile_preview"] = profile  # 审查通过的画像预览。

    # 返回可进入写入流程的完整响应。
    return dict_payload_out

# 写入升级入口把已完成的只读访谈重新送入设计审查。
def enter_write_review(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    """将只读完成态升级为等待设计审查的写入态。

    参数：project 为项目根，state 为已完成只读访谈状态。
    返回：包含画像预览和审查请求的交互载荷。
    异常：状态不合法或画像构建失败时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由答案和画像字段决定，dtype 为 JSON 兼容映射，unit 不适用。
    """

    # 只有完整只读结果拥有足够答案重新进入写入审查。
    if str(state.get("status", "")) != "completed_read_only":

        # 返回专用状态诊断，避免从中间访谈节点跳过确认。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["write-review escalation requires a completed_read_only interview state"],
            )
        )

        # 非只读完成态不得创建写入审查请求。
        raise SystemExit(1)

    # 复制最终答案，避免审查入口删除旧审查键时原地修改状态。
    dict_answers = dict(state.get("answers", {}))  # 只读访谈最终答案副本。

    # 优先复用只读完成时已经构建并展示的画像。
    profile = (  # 可复用的项目画像预览。
        state.get("profile_preview")  # 读取只读完成时固化的画像。
        if isinstance(state.get("profile_preview"), dict)  # 仅复用合法映射画像。
        else None  # 缺失或畸形时触发重新构建。
    )

    # 历史只读状态缺失画像时从最终答案重新构建。
    if profile is None:

        # 构建器同时返回画像和全部合同诊断。
        profile, errors = build_profile(project, dict_answers)  # 重建画像及错误集合。

        # 构建错误必须在进入审查前反馈。
        if errors:

            # 复用交互载荷格式返回完整画像构建诊断。
            emit_json(interactive_payload(project, state, errors=errors))

            # 无有效画像时不能生成设计审查请求。
            raise SystemExit(1)

    # 统一审查入口负责持久化写入意图和审查请求。
    return enter_design_review(project, state, dict_answers, profile)

# 审查返工处理器应用修正并回退到最早受影响的问题组。
def answer_review_rework(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """接受设计审查返工修正并重置后续确认状态。

    参数：project 为项目根，state 为等待返工状态，payload 为确认标志和修正字段。
    返回：重新确认问题组或最终对齐阶段的交互载荷。
    异常：确认无效、修正缺失或字段非法时输出诊断并抛出 SystemExit(1)。
    数组契约：shape 由返工字段数决定，dtype 为 JSON 兼容答案，unit 不适用。
    """

    # 保存原始返工确认值以同时验证类型和值。
    rework_confirmed = payload.get(REVIEW_REWORK_CONFIRMATION_KEY)  # 审查返工确认标志。

    # 只有显式布尔 true 才允许覆盖已经审查的答案。
    if not isinstance(rework_confirmed, bool) or not rework_confirmed:

        # 返回明确门禁诊断，要求调用方确认接受返工。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=[
                    f"{REVIEW_REWORK_CONFIRMATION_KEY} must be true "
                    "before rework corrections are accepted"
                ],
            )
        )

        # 未确认返工时不修改任何答案或审查状态。
        raise SystemExit(1)

    # 除确认标志外的字段均视为设计答案修正。
    correction_keys = [  # 本次审查返工提交的答案字段。
        key  # 保留需要重新验证并写回的设计字段。
        for key in payload  # 遍历返工提交的全部字段。
        if key != REVIEW_REWORK_CONFIRMATION_KEY  # 排除控制标志。
    ]

    # 返工提交必须包含至少一个实际修正字段。
    if not correction_keys:

        # 空返工无法消除审查发现项，因此返回阻断诊断。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["design review rework requires at least one correction field"],
            )
        )

        # 保留等待返工状态供用户重新提交。
        raise SystemExit(1)

    # 当前访谈问题定义限定审查返工可修改的字段。
    set_all_keys = all_answer_keys_for_state(state)  # 合法设计答案字段集合。

    # 未知字段不能进入画像或问题组定位逻辑。
    if any(key not in set_all_keys for key in correction_keys):

        # 返回字段范围诊断，避免静默接收拼写错误。
        emit_json(
            interactive_payload(
                project,
                state,
                errors=["review rework corrections must reference known design-answer fields"],
            )
        )

        # 越界返工不清除原设计审查意见。
        raise SystemExit(1)

    # 复制白名单内的返工值，全部验证成功后再写入状态。
    corrections = {key: payload[key] for key in correction_keys}  # 待应用的审查返工映射。

    # 逐项规范化可选字段并拒绝空的必填答案。
    for key, raw_value in corrections.items():

        # 普通可选字段允许显式清空。
        if key in OPTIONAL_EMPTY_KEYS:

            # 继续检查剩余返工字段。
            continue

        # 附加需求需要接受多种输入形式并规范为列表。
        if key == EXTRA_REQUIREMENTS_KEY:

            # 将审查返工中的开放需求恢复为画像要求的列表结构。
            corrections[key] = normalize_extra_requirements(raw_value)  # 返工后的附加需求列表。

            # 已完成专用规范化，无需执行普通空值检查。
            continue

        # 非可选标准字段不能用空值消除原答案。
        if empty(raw_value):

            # 指出具体必填字段，方便审阅者修正提交。
            emit_json(interactive_payload(project, state, errors=[f"missing required answer: {key}"]))

            # 空必填值不能关闭待处理审查。
            raise SystemExit(1)

    # 获取持久化答案映射，后续一次性应用已验证修正。
    answers = state.setdefault("answers", {})  # 当前访谈最终答案映射。

    # 全部字段合法后覆盖对应答案。
    answers.update(corrections)

    # 旧审查结论针对修正前画像，必须移除。
    answers.pop(DESIGN_REVIEW_KEY, None)

    # 已处理的待返工审查不再作为活动状态保留。
    state.pop("pending_design_review", None)

    # 修正后的画像需要生成新的设计审查请求。
    state.pop("design_review_request", None)

    # 旧画像预览同样因答案变化失效。
    state.pop("profile_preview", None)

    # 将标准答案字段映射回问题组，附加需求没有组索引。
    indices = [  # 返工影响的标准问题组索引。
        group_index_for_key_in_state(state, key)  # 使用会话固化分组定位字段。
        for key in correction_keys  # 遍历本次审查返工字段。
        if key != EXTRA_REQUIREMENTS_KEY  # 附加需求在最终对齐阶段确认。
    ]

    # 标准问题字段修正需要回退到最早受影响组。
    if indices:

        # 最小索引保证所有后续依赖组都会重新确认。
        target_index = min(index for index in indices if index is not None)  # 首个返工问题组。

        # 更新交互游标指向最早返工组。
        state["current_group_index"] = target_index  # 当前返工问题组索引。

        # 仅保留返工组之前仍然有效的确认记录。
        state["confirmed_group_indices"] = [  # 未受返工影响的确认索引。
            index  # 保留返工起点之前的历史确认。
            for index in state.get("confirmed_group_indices", [])  # 扫描返工前的确认历史。
            if int(index) < target_index  # 丢弃受返工影响的组。
        ]

        # 答案返工完成后要求用户重新确认最早受影响组。
        state["status"] = "awaiting_group_confirmation"  # 等待审查返工组确认。

    # 仅修正附加需求时直接回到最终摘要确认。
    else:

        # 新的附加需求需要用户再次确认完整答案摘要。
        state["status"] = "awaiting_final_alignment"  # 等待返工后最终对齐。

    # 持久化返工后的状态和新的问题组游标。
    write_state(project, state)

    # 返回更新后的返工交互载荷供用户重新确认。
    return interactive_payload(project, state)

# 写入前访谈检查防止活动状态绕过恢复与确认流程。
def ensure_no_pending_interview_on_write(project: Path, answers: dict[str, Any]) -> list[str]:
    """阻止未完成或与写入答案不一致的设计访谈进入写入阶段。

    参数：project 为项目根目录，answers 为本次准备写入的最终答案。
    返回：空列表表示不存在待处理访谈，否则返回阻断原因。
    """

    # 读取持久化状态以判断是否仍存在未闭合访谈。
    state = read_state(project)  # 当前项目的设计访谈状态。

    # 没有活动状态时，写入流程无需处理访谈恢复。
    if not is_active_state(state):

        # 空错误列表允许调用方继续执行写入门禁。
        return []

    # 只从合法状态映射中提取已确认答案。
    state_answers = state.get("answers", {}) if isinstance(state, dict) else {}  # 持久化访谈答案。

    # 已完成且答案仍与本次写入一致时不构成待处理状态。
    if (
        state_answers == {key: answers[key] for key in state_answers if key in answers}
        and state.get("status") == "completed"
    ):

        # 一致的完成态允许重复执行写入。
        return []

    # 其余活动状态必须先恢复或重置，避免跳过访谈确认。
    return ["design interview is still pending; use --resume or --reset-interview before --write"]

# 远程策略检查区分显式禁用与尚未回答。
def explicit_remote_server_error(answers: dict[str, Any]) -> list[str]:
    """验证最终答案是否显式声明远程服务器使用策略。

    参数：answers 为准备写入项目画像的答案映射。
    返回：字段存在且为布尔值时为空，否则返回缺失诊断。
    """

    # 只有显式布尔值才能区分“不使用”与“尚未回答”。
    if USE_REMOTE_SERVER_KEY in answers and isinstance(answers.get(USE_REMOTE_SERVER_KEY), bool):

        # 有效选择已经满足远程执行策略门禁。
        return []

    # 缺失或类型错误都要求用户重新确认远程策略。
    return ["use_remote_server must be explicitly provided before --write"]

# 附加需求检查要求开放问题留下明确答案记录。
def explicit_extra_requirements_error(answers: dict[str, Any]) -> list[str]:
    """验证最终答案是否显式提供附加需求字段。

    参数：answers 为准备写入项目画像的答案映射。
    返回：字段存在时为空，否则返回缺失诊断。
    """

    # 空文本也是明确回答，因此这里只检查键是否存在。
    if EXTRA_REQUIREMENTS_KEY in answers:

        # 已确认无附加需求同样满足写入门禁。
        return []

    # 字段缺失表示访谈尚未覆盖最后的开放需求问题。
    return ["extra_requirements must be explicitly provided before --write"]

# 写入总门禁合并访谈、对齐与设计审查的阻断证据。
def ensure_design_review_approved_on_write(
    project: Path,
    answers: dict[str, Any],
    profile: dict[str, Any],
) -> list[str]:
    """汇总写入前的访谈完成度、显式回答与设计审查门禁。

    参数：project 为项目根，answers 为最终答案，profile 为待写入设计画像。
    返回：全部写入阻断原因；空列表表示可进入受管写入。
    """

    # 按门禁顺序累计诊断，确保一次反馈覆盖全部缺口。
    list_errors: list[str] = []  # 写入前设计治理错误集合。

    # 活动访谈必须先闭合，防止绕过未确认问题。
    list_errors.extend(ensure_no_pending_interview_on_write(project, answers))

    # 远程服务器策略必须是显式布尔选择。
    list_errors.extend(explicit_remote_server_error(answers))

    # 开放附加需求问题必须显式回答，即使答案为空。
    list_errors.extend(explicit_extra_requirements_error(answers))

    # 保存原始对齐值以同时验证布尔类型和值。
    alignment_confirmed = answers.get(ALIGNMENT_KEY)  # 最终答案中的对齐确认标志。

    # 最终对齐标志证明用户确认了完整答案摘要。
    if not isinstance(alignment_confirmed, bool) or not alignment_confirmed:

        # 未确认对齐时禁止生成受管项目规则。
        list_errors.append("alignment_confirmed must be true before --write")

    # 用户显式提供设计审查证据时才进入子智能体审查门禁。
    if DESIGN_REVIEW_KEY in answers:

        # 已有审查载荷时验证其内容、批准状态和项目一致性。
        review_errors = validate_design_review(  # 写入前设计审查诊断。
            project,  # 将审查证据绑定到当前项目。
            answers,  # 提供完整访谈答案供交叉校验。
            answers.get(DESIGN_REVIEW_KEY),  # 读取待验证的审查载荷。
            profile,  # 对照最终设计画像检查一致性。
            require_approval=True,  # 显式请求审查时必须具有批准结论。
        )

        # 将显式审查诊断并入其他写入门禁错误。
        list_errors.extend(review_errors)

    # 调用方统一决定如何展示或终止这些诊断。
    return list_errors

# 默认语言检查保证生成规则拥有确定的自然语言合同。
def explicit_default_language_error(answers: dict[str, Any]) -> list[str]:
    """验证项目默认会话语言已经获得非空显式回答。

    参数：answers 为准备写入项目画像的答案映射。
    返回：语言有效时为空，否则返回缺失诊断。
    """

    # 去除空白后仍有内容才视为明确的会话语言选择。
    if str(answers.get("default_conversation_language", "")).strip():

        # 非空语言值满足生成本地约定的前置条件。
        return []

    # 缺失语言会使生成规则无法确定自然语言输出合同。
    return ["default_conversation_language must be explicitly provided before --write"]

# 兼容问题载荷保留旧入口的分支选择与对齐摘要合同。
def legacy_question_payload(project: Path, kind: str | None) -> dict[str, Any]:
    """构造兼容旧版非交互式调用的设计问题载荷。

    参数：project 为项目根，kind 为可选的显式项目类型。
    返回：附带对齐摘要的分支选择或具体问题载荷。
    """

    # 先从仓库事实推断类型，供未选分支时展示建议。
    inferred = infer_kind(project)  # 基于项目结构推断的开发类型。

    # 未指定类型时只返回分支选择和公共问题。
    if not kind:

        # 对齐包装器保证旧入口也公开统一的设计摘要。
        return attach_alignment(
            {
                "project": str(project),  # 当前问题所属项目根。
                "inferred_kind": inferred,  # 供用户参考的自动推断类型。
                "branch_options": ["skill", "engineering"],  # 旧入口支持的显式分支。
                "questions": [with_options(item) for item in COMMON_QUESTIONS],  # 分支前公共问题。
                "next": "Ask question 1, then rerun with --kind skill or --kind engineering.",  # 后续动作。
            },
            {"development_type": inferred},  # 初始对齐答案仅含推断类型。
            inferred,  # 摘要按推断分支选择标签。
        )

    # 已指定类型时返回该分支的完整问题与分组。
    return attach_alignment(
        {
            "project": str(project),  # 显式分支问题所属的项目根。
            "kind": kind,  # 调用方明确选择的开发类型。
            "inferred_kind": inferred,  # 保留自动推断值供差异审阅。
            "questions": questions_for(kind),  # 所选类型的完整问题列表。
            "question_groups": groups_for(kind),  # 交互展示使用的问题分组。
        },
        {"development_type": kind},  # 对齐摘要采用显式类型。
        kind,  # 分支标签与问题集合保持一致。
    )
