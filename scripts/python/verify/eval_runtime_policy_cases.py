"""agents-md-generator 技能评估用例实现分片二。"""

from __future__ import annotations

from eval_runtime_core import *  # noqa: F403 - eval case shards share the runner context intentionally.

from eval_runtime_foundation_cases import *  # noqa: F403 - later cases reuse earlier helpers when needed.


def case_root_version_sync_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill_dir = project / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "VERSION").write_text("v0.4.4\n", encoding="utf-8")
        installed_skill = helper.make_installed_skill_fixture(project, version="v0.4.3")
        (project / "AGENTS.md").write_text(
            "\n".join(
                [
                    "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",
                    "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",
                    "<!-- Last updated: 2026-05-14T10:00:00 | Last verified: never -->",
                    "<!-- AGENTS-METADATA: agents_version=v0.4.2; generator_version=v0.4.2; default_language=中文 -->",
                    "# AGENTS.md",
                    "<!-- AGENTS-GENERATED:START control-profile -->",
                    "## Control Profile",
                    "- Strong control: complete.",
                    "- Version: v0.4.2.",
                    "<!-- AGENTS-GENERATED:END control-profile -->",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        preview = run_json_script(
            "manage_docs.py",
            "sync-root-agents",
            project,
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
        applied = run_json_script(
            "manage_docs.py",
            "sync-root-agents",
            project,
            "--write",
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
        synced_text = (project / "AGENTS.md").read_text(encoding="utf-8")
        after_sync = run_json_script(
            "manage_docs.py",
            "sync-root-agents",
            project,
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
    with_checks = {
        "preview_detects_control_profile_drift": "control_profile_version_mismatch" in preview.get("reasons", []),
        "write_updates_root_metadata": "agents_version=v0.4.3; generator_version=v0.4.3; default_language=中文" in synced_text,
        "write_updates_control_profile_to_project_skill_version": "- Version: v0.4.4." in synced_text,
        "write_does_not_force_control_profile_to_generator_version": "- Version: v0.4.3." not in synced_text,
        "second_preview_is_clean": after_sync.get("sync_required") is False and after_sync.get("reasons") == [],
    }
    without_checks = {
        "preview_detects_control_profile_drift": False,
        "write_updates_root_metadata": False,
        "write_updates_control_profile_to_project_skill_version": False,
        "write_does_not_force_control_profile_to_generator_version": False,
        "second_preview_is_clean": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"preview": preview, "applied": applied, "after_sync": after_sync},
        without_skill_detail={"baseline": "older sync-root-agents guidance could leave Control Profile version drift behind or force it to the generator version after the suggested repair command ran"},
    )


def case_source_repo_render_version_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        skill_dir = project / "skills" / "agents-md-generator"
        skill_dir.mkdir(parents=True)
        (project / ".agents").mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: agents-md-generator\ndescription: Use when testing source render version\n---\n# Skill\n",
            encoding="utf-8",
        )
        (skill_dir / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
        (project / ".agents" / "agents-control.json").write_text(
            json.dumps(
                {
                    "kind": "skill",
                    "name": "agents-md-generator",
                    "default_conversation_language": "中文",
                    "git_management": "no-git-management",
                }
            ),
            encoding="utf-8",
        )
        installed_skill = helper.make_installed_skill_fixture(root, version="v1.0.4")
        returncode, stdout, stderr = run_script(
            "render_agents.py",
            project,
            "--profile",
            project / ".agents" / "agents-control.json",
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
    expected_metadata = "<!-- AGENTS-METADATA: agents_version=v9.9.9; generator_version=v9.9.9; default_language=中文 -->"
    with_checks = {
        "render_succeeds": returncode == 0,
        "metadata_uses_source_version": expected_metadata in stdout,
        "control_profile_uses_source_version": "- Version: v9.9.9." in stdout,
        "stale_installed_metadata_absent": "agents_version=v1.0.4" not in stdout,
    }
    without_checks = {
        "render_succeeds": False,
        "metadata_uses_source_version": False,
        "control_profile_uses_source_version": False,
        "stale_installed_metadata_absent": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"stdout_head": stdout[:300], "stderr": stderr},
        without_skill_detail={"baseline": "a stale installed skill can leak its version into source-release root metadata"},
    )


def case_language_skill_routing_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    required_snippets = (
        "编码行为配置来源：`.agents/global-rule-overrides.json`",
        "注释质量：只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释",
        "严禁把代码压缩到一行",
        "炫技代码",
        "语言技能路由（Python）：",
        "readable-python-generator",
        "语言技能路由（脚本）：",
        "readable-script-generator",
        "Python 目标继续使用 `readable-python-generator`",
        "脚本包装器调用 Python",
    )
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "workspace"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('demo')\n", encoding="utf-8")
        render_returncode, _render_stdout, render_stderr = run_script("render_agents.py", project, "--write", cwd=REPO_ROOT)
        agents_path = project / "AGENTS.md"
        agents_text = agents_path.read_text(encoding="utf-8", errors="ignore") if agents_path.exists() else ""
        verify = run_json_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_text = agents_text.replace("readable-script-generator", "script helper")
        agents_path.write_text(missing_text, encoding="utf-8")
        missing_returncode, missing_stdout, missing_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_verify = json.loads(missing_stdout) if missing_stdout.strip() else {"errors": [missing_stderr]}
        agents_path.write_text(agents_text, encoding="utf-8")
        config_path = project / ".agents" / "global-rule-overrides.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        weakened_config = json.loads(json.dumps(config, ensure_ascii=False))
        weakened_config.get("coding_behavior", {}).get("language_skill_routing", {})["python"] = "Python 任务使用通用代码助手。"
        config_path.write_text(json.dumps(weakened_config, ensure_ascii=False, indent=2), encoding="utf-8")
        weakened_returncode, weakened_stdout, weakened_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        weakened_verify = json.loads(weakened_stdout) if weakened_stdout.strip() else {"errors": [weakened_stderr]}
    missing_errors = missing_verify.get("errors", [])
    weakened_errors = weakened_verify.get("errors", [])
    with_checks = {
        "render_succeeded": render_returncode == 0,
        "rendered_language_skill_routing": "## Coding Behavior Baseline" in agents_text or "## Local conventions" in agents_text,
        "policy_rules": all(snippet in agents_text for snippet in required_snippets),
        "verify_accepts_policy": verify.get("errors") == [],
        "verify_rejects_missing_policy": bool(missing_errors) and any("language skill routing" in item for item in missing_errors),
        "verify_rejects_weakened_policy": bool(weakened_errors) and any("coding_behavior.language_skill_routing" in item for item in weakened_errors),
        "config_written": bool(config.get("coding_behavior", {}).get("language_skill_routing")),
    }
    without_checks = {
        "render_succeeded": False,
        "rendered_language_skill_routing": False,
        "policy_rules": False,
        "verify_accepts_policy": False,
        "verify_rejects_missing_policy": False,
        "verify_rejects_weakened_policy": False,
        "config_written": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "verify": verify,
            "missing_verify": missing_verify,
            "weakened_verify": weakened_verify,
            "render_stderr": render_stderr,
        },
        without_skill_detail={"baseline": "unguided baseline may create AGENTS.md but does not lock language-specific skill routing or reject its removal"},
    )


def case_script_output_policy_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    required_snippets = (
        "## Script Output Policy",
        "配置来源：`.agents/global-rule-overrides.json`",
        "`Kind` 列表只从该 JSON 读取",
        "`> INFO: [{kind}]`",
        "`> WARNING: [{kind}]`",
        "`> ERR: [{kind}]`",
        "`--quiet`",
        "机器可读输出不套前缀",
    )
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "workspace"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('demo')\n", encoding="utf-8")
        render_returncode, _render_stdout, render_stderr = run_script("render_agents.py", project, "--write", cwd=REPO_ROOT)
        agents_path = project / "AGENTS.md"
        agents_text = agents_path.read_text(encoding="utf-8", errors="ignore") if agents_path.exists() else ""
        verify = run_json_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_text = agents_text.replace("`Kind` 列表只从该 JSON 读取", "Kind 列表规则已移除")
        agents_path.write_text(missing_text, encoding="utf-8")
        missing_returncode, missing_stdout, missing_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_verify = json.loads(missing_stdout) if missing_stdout.strip() else {"errors": [missing_stderr]}
        agents_path.write_text(agents_text, encoding="utf-8")
        config_path = project / ".agents" / "global-rule-overrides.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        weakened_config = json.loads(json.dumps(config, ensure_ascii=False))
        weakened_config.get("script_output_policy", {}).setdefault("format", {})["warning"] = "WARNING [{kind}]"
        config_path.write_text(json.dumps(weakened_config, ensure_ascii=False, indent=2), encoding="utf-8")
        weakened_returncode, weakened_stdout, weakened_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        weakened_verify = json.loads(weakened_stdout) if weakened_stdout.strip() else {"errors": [weakened_stderr]}
    script_output_config = config.get("script_output_policy", {})
    with_checks = {
        "render_succeeded": render_returncode == 0,
        "rendered_policy": all(snippet in agents_text for snippet in required_snippets if snippet != "## Script Output Policy")
        and ("## Script Output Policy" in agents_text or "## Local conventions" in agents_text),
        "config_written": bool(script_output_config),
        "kind_config_extensible": isinstance(script_output_config.get("kinds"), list) and "Verilator" in script_output_config.get("kinds", []),
        "verify_accepts_policy": verify.get("errors") == [],
        "verify_rejects_missing_policy": bool(missing_verify.get("errors")) and any("Script Output Policy" in item for item in missing_verify.get("errors", [])),
        "verify_rejects_weakened_policy": bool(weakened_verify.get("errors")) and any("script_output_policy" in item for item in weakened_verify.get("errors", [])),
    }
    without_checks = {
        "render_succeeded": False,
        "rendered_policy": False,
        "config_written": False,
        "kind_config_extensible": False,
        "verify_accepts_policy": False,
        "verify_rejects_missing_policy": False,
        "verify_rejects_weakened_policy": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "verify": verify,
            "missing_verify": missing_verify,
            "weakened_verify": weakened_verify,
            "render_stderr": render_stderr,
            "missing_returncode": missing_returncode,
            "weakened_returncode": weakened_returncode,
        },
        without_skill_detail={"baseline": "unguided baseline may mention log style but does not render configurable Kind policy or reject weakened output formats"},
    )


def case_plan_mode_language_lock_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    script_guide = (SKILL_DIR / "references" / "script-guide.md").read_text(encoding="utf-8")
    review_checklist = (SKILL_DIR / "references" / "review-checklist.md").read_text(encoding="utf-8")
    verify_script = script_path("verify_agents.py").read_text(encoding="utf-8")
    current_version = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "workspace"
        project.mkdir()
        (project / ".agents").mkdir()
        (project / ".agents" / "agents-control.json").write_text(
            json.dumps({"kind": "engineering", "default_conversation_language": "中文"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (project / "AGENTS.md").write_text(
            "\n".join(
                [
                    f"<!-- AGENTS-METADATA: agents_version={current_version}; generator_version={current_version}; default_language=中文 -->",
                    "# AGENTS.md",
                    "## Conversation Completion Contract",
                    "- All natural-language responses must use the configured default language (`中文`) unless the user explicitly switches languages.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        verify = run_json_script("verify_agents.py", project, cwd=REPO_ROOT)

    verify_errors = verify.get("errors", [])
    with_checks = {
        "repo_agents_mentions_generic_language_lock": "All natural-language responses must use the configured default language (`中文`)" in agents_text,
        "repo_agents_mentions_plan_mode_lock": "In Plan Mode, any content inside `<proposed_plan>` must use the configured default language (`中文`)" in agents_text,
        "skill_mentions_plan_mode_lock": "Plan Mode" in skill_text and "<proposed_plan>" in skill_text,
        "script_guide_mentions_plan_mode_lock": "Plan Mode" in script_guide and "<proposed_plan>" in script_guide,
        "review_checklist_mentions_plan_mode_lock": "Plan Mode" in review_checklist and "<proposed_plan>" in review_checklist,
        "verify_script_has_plan_mode_guard": "PLAN_LANGUAGE_LOCK_RE" in verify_script,
        "verify_rejects_missing_plan_mode_lock": bool(verify_errors) and any("missing enforced Plan Mode default-language rule" in item for item in verify_errors),
    }
    without_checks = {
        "repo_agents_mentions_generic_language_lock": False,
        "repo_agents_mentions_plan_mode_lock": False,
        "skill_mentions_plan_mode_lock": False,
        "script_guide_mentions_plan_mode_lock": False,
        "review_checklist_mentions_plan_mode_lock": False,
        "verify_script_has_plan_mode_guard": False,
        "verify_rejects_missing_plan_mode_lock": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"verify": verify},
        without_skill_detail={"baseline": "older language governance locked only generic natural-language replies and left Plan Mode `<proposed_plan>` body text without a hard verifier guard"},
    )


def case_codex_token_usage_review_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    openai_text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
    script_guide = (SKILL_DIR / "references" / "script-guide.md").read_text(encoding="utf-8")
    token_usage_script_path = script_path("codex_token_usage_review.py")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        codex_home = root / "codex-home"
        sessions_root = codex_home / "sessions" / "2026" / "05" / "27"
        sessions_root.mkdir(parents=True)
        (sessions_root / "fixture-a.jsonl").write_text(
            json.dumps(
                {
                    "timestamp": "2026-05-27T04:00:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 100,
                                "cached_input_tokens": 20,
                                "output_tokens": 10,
                                "reasoning_output_tokens": 5,
                                "total_tokens": 110,
                            }
                        },
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        success = run_json_script(
            "codex_token_usage_review.py",
            "--hours",
            "48",
            "--now",
            "2026-05-27T05:36:00Z",
            "--json",
            "--sessions-root",
            codex_home / "sessions",
            cwd=REPO_ROOT,
            env={"CODEX_HOME": str(codex_home)},
        )

        isolated_codex_home = root / "no-codex-home"
        isolated_codex_home.mkdir()
        bypass_root = root / "external-sessions" / "2026" / "05" / "27"
        bypass_root.mkdir(parents=True)
        refused = run_json_script(
            "codex_token_usage_review.py",
            "--hours",
            "48",
            "--now",
            "2026-05-27T05:36:00Z",
            "--json",
            "--sessions-root",
            bypass_root.parent.parent.parent,
            cwd=REPO_ROOT,
            env={"CODEX_HOME": str(isolated_codex_home)},
        )

        outside_root = root / "outside-sessions"
        outside_root.mkdir()
        outside_tree = run_json_script(
            "codex_token_usage_review.py",
            "--hours",
            "48",
            "--now",
            "2026-05-27T05:36:00Z",
            "--json",
            "--sessions-root",
            outside_root,
            cwd=REPO_ROOT,
            env={"CODEX_HOME": str(codex_home)},
        )

    with_checks = {
        "script_exists": token_usage_script_path.is_file(),
        "skill_mentions_explicit_trigger": "如果用户明确要求进行 Codex Token 用量统计" in skill_text,
        "openai_mentions_explicit_trigger": "explicitly asks for Codex token usage statistics" in openai_text,
        "script_guide_mentions_guard": "仅在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时执行" in script_guide,
        "script_reports_totals": success.get("ok") is True and success.get("grand_total", {}).get("total_tokens") == 110,
        "script_refuses_without_codex_root": refused.get("ok") is False and refused.get("reason") == "codex_sessions_not_found",
        "script_rejects_outside_tree": outside_tree.get("ok") is False and outside_tree.get("reason") == "sessions_root_outside_codex_root",
    }
    without_checks = {
        "script_exists": False,
        "skill_mentions_explicit_trigger": False,
        "openai_mentions_explicit_trigger": False,
        "script_guide_mentions_guard": False,
        "script_reports_totals": False,
        "script_refuses_without_codex_root": False,
        "script_rejects_outside_tree": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"success": success, "refused": refused, "outside_tree": outside_tree},
        without_skill_detail={"baseline": "unguided baseline has no controlled internal Codex token usage tool path"},
    )


def case_governance_runtime_de_vendoring(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill, installed = helper.make_rendered_governed_skill_project(project, name="demo-skill")
        agents_text = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")

        bad_agents = agents_text.replace(
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check <project>",
            "python scripts/manage_docs.py resume-check <project>",
        )
        (project / "AGENTS.md").write_text(bad_agents, encoding="utf-8")
        verify = run_json_script(
            "verify_agents.py",
            project,
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed)},
        )

    with_checks = {
        "agents_use_installed_runtime": "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check <project>" in agents_text,
        "agents_use_installed_dir_manager_runtime": "python <codex-home>/skills/agents-md-generator/scripts/python/dirs/manage_dirs.py review <project> --input change.json" in agents_text,
        "agents_omit_project_local_runtime": "python scripts/manage_docs.py" not in agents_text and f"python skills/{skill.name}/scripts/manage_docs.py" not in agents_text,
        "verify_rejects_vendored_runtime": any(
            "project-local governance runtime command is forbidden for non-owner repositories" in item
            for item in verify.get("errors", [])
        ),
    }
    without_checks = {
        "agents_use_installed_runtime": False,
        "agents_use_installed_dir_manager_runtime": False,
        "agents_omit_project_local_runtime": False,
        "verify_rejects_vendored_runtime": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"verify": verify},
        without_skill_detail={"baseline": "older routing let external workspaces point governance commands at project-local scripts/, encouraging vendoring of agents-md-generator runtime files"},
    )


def case_installed_runtime_owner_repo_local_commands(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        project = workspace / "owner"
        current_version = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()
        skill, _fixture_installed = helper.make_rendered_governed_skill_project(
            project,
            name="agents-md-generator",
            project_version=current_version,
            installed_version=current_version,
        )
        local_manage_docs = skill / "scripts" / "python" / "docs" / "manage_docs.py"
        local_manage_docs.parent.mkdir(parents=True, exist_ok=True)
        local_manage_docs.write_text("print('owner local runtime')\n", encoding="utf-8")
        agents_text = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
        local_command = "python skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check <project>"
        if local_command not in agents_text:
            agents_text += f"\n## Owner Runtime Command\n- `{local_command}`\n"
        (project / "AGENTS.md").write_text(agents_text, encoding="utf-8")

        codex_home = workspace / "codex-home"
        codex_home.mkdir()
        installed_runtime = workspace / "installed-runtime" / "agents-md-generator"
        shutil.copytree(SKILL_DIR, installed_runtime, ignore=shutil.ignore_patterns("__pycache__"))
        import subprocess

        command_env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            CODEX_HOME=str(codex_home),
            AGENTS_MD_INSTALLED_SKILL_DIR=str(installed_runtime),
        )
        subprocess.run(
            [
                sys.executable,
                str(installed_runtime / "scripts" / "python" / "docs" / "manage_docs.py"),
                "sync-global-codex-agents",
                str(project),
                "--write",
                "--codex-home",
                str(codex_home),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
            env=command_env,
        )
        result = subprocess.run(
            [sys.executable, str(installed_runtime / "scripts" / "python" / "verify" / "verify_agents.py"), str(project)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=command_env,
        )
        verify = json.loads(result.stdout) if result.stdout.strip() else {"errors": [result.stderr]}

    with_checks = {
        "installed_runtime_invoked": str(installed_runtime / "scripts" / "python" / "verify" / "verify_agents.py") in " ".join(result.args),
        "owner_repo_keeps_local_command": local_command in agents_text,
        "verify_accepts_owner_local_runtime": not any(
            "project-local governance runtime command is forbidden for non-owner repositories" in item
            for item in verify.get("errors", [])
        ),
        "no_non_owner_runtime_error": not any(
            "project-local governance runtime command is forbidden for non-owner repositories" in item
            for item in verify.get("errors", [])
        ),
    }
    without_checks = {
        "installed_runtime_invoked": True,
        "owner_repo_keeps_local_command": True,
        "verify_accepts_owner_local_runtime": False,
        "no_non_owner_runtime_error": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"verify": verify},
        without_skill_detail={"baseline": "installed runtime verification can misclassify the agents-md-generator source repository as a non-owner and reject its required repo-local governance commands"},
    )


def case_handoff_naming_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill, _installed = helper.make_rendered_governed_skill_project(project, name="demo-skill")
        current = project / "docs" / "handoff" / "HANDOFF.md"
        renamed = project / "docs" / "handoff" / "RENAMED.md"
        current.rename(renamed)
        helper.git_commit_all(project, "rename handoff incorrectly")

        scaffold_returncode, scaffold_stdout, _scaffold_stderr = run_script("manage_docs.py", "scaffold", project, cwd=REPO_ROOT)
        verify = run_json_script("manage_docs.py", "verify", project, cwd=REPO_ROOT)
        work_folder = run_json_script(
            "manage_docs.py",
            "work-folder-gate",
            project,
            "--skill-dir",
            f"skills/{skill.name}",
            "--mode",
            "development",
            cwd=REPO_ROOT,
        )
        repair = run_json_script("manage_docs.py", "repair-handoff-names", project, "--write", cwd=REPO_ROOT)
        repaired_verify = run_json_script("manage_docs.py", "verify", project, cwd=REPO_ROOT)

    verify_errors = verify.get("errors", [])
    work_folder_errors = work_folder.get("errors", [])
    with_checks = {
        "scaffold_blocked_on_rename": scaffold_returncode != 0 and "current handoff must be exactly docs/handoff/HANDOFF.md" in scaffold_stdout,
        "verify_rejects_rename": any("handoff naming drift" in item for item in verify_errors),
        "work_folder_gate_rejects_rename": any("docs-verify: handoff naming drift" in item for item in work_folder_errors),
        "repair_succeeds": repair.get("errors") == [] and repair.get("handoff_naming", {}).get("blocking") is False,
        "verify_passes_after_repair": repaired_verify.get("errors") == [],
    }
    without_checks = {
        "scaffold_blocked_on_rename": False,
        "verify_rejects_rename": False,
        "work_folder_gate_rejects_rename": False,
        "repair_succeeds": False,
        "verify_passes_after_repair": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "verify": verify,
            "work_folder_gate": work_folder,
            "repair": repair,
            "repaired_verify": repaired_verify,
        },
        without_skill_detail={"baseline": "a weaker governance baseline would silently replace the renamed handoff with a fresh HANDOFF.md and lose the naming drift evidence"},
    )


def case_workspace_settings_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill, _installed = helper.make_rendered_governed_skill_project(project, name="demo-skill")
        settings_dir = project / ".settings"
        settings_dir.mkdir(exist_ok=True)
        (settings_dir / "project.local.json").write_text("{}", encoding="utf-8")
        (project / "project.local.json").write_text("{}", encoding="utf-8")
        helper.git_commit_all(project, "add workspace settings drift")

        verify = run_json_script("manage_docs.py", "verify", project, cwd=REPO_ROOT)
        structure_gate = run_json_script("manage_dirs.py", "structure-gate", project, cwd=REPO_ROOT)

        remote_change = project / "remote-settings.json"
        remote_change.write_text(
            json.dumps({"changes": [{"action": "create", "environment": "remote", "path": ".settings/server_list.local.json"}]}),
            encoding="utf-8",
        )
        remote_block = run_json_script("manage_dirs.py", "review", project, "--input", remote_change, cwd=REPO_ROOT)

        agents_text = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")

    with_checks = {
        "verify_or_structure_rejects_root_settings_drift": bool(verify.get("errors")) or structure_gate.get("approved") is False,
        "remote_review_blocks_local_settings": any("local-only workspace settings" in item for item in remote_block.get("reasons", [])),
        "agents_mentions_local_settings_contract": ".settings/project.local.json" in agents_text or structure_gate.get("approved") is False,
        "agents_mentions_remote_settings_contract": ".settings/project.remote.json" in agents_text or remote_block.get("approved") is False,
        "agents_mentions_remote_local_block": ("server_list.local.json" in agents_text and ".settings/*.local.json" in agents_text) or remote_block.get("approved") is False,
    }
    without_checks = {
        "verify_or_structure_rejects_root_settings_drift": False,
        "remote_review_blocks_local_settings": False,
        "agents_mentions_local_settings_contract": False,
        "agents_mentions_remote_settings_contract": False,
        "agents_mentions_remote_local_block": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "verify": verify,
            "structure_gate": structure_gate,
            "remote_review": remote_block,
        },
        without_skill_detail={"baseline": "weaker guidance can leave project.local.json at the repo root and does not formally block .settings/*.local.json from remote workspaces"},
    )


def case_governance_cli_entrypoint_smoke(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill, _installed = helper.make_rendered_governed_skill_project(project, name="demo-skill")
        agents_text = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8", errors="ignore")

        docs_help = run_script("manage_docs.py", "-h", cwd=REPO_ROOT)
        resume_check = run_script("manage_docs.py", "resume-check", project, cwd=REPO_ROOT)
        memory_gate = run_script("manage_docs.py", "memory-gate", project, cwd=REPO_ROOT)
        work_folder_gate = run_script(
            "manage_docs.py",
            "work-folder-gate",
            project,
            "--skill-dir",
            skill,
            "--mode",
            "development",
            cwd=REPO_ROOT,
        )
        structure_gate = run_script("manage_dirs.py", "structure-gate", project, cwd=REPO_ROOT)
        render_agents = run_script("render_agents.py", project, cwd=REPO_ROOT)
        design_help = run_script("collect_design_profile.py", "--help", cwd=REPO_ROOT)
        eval_help = run_script("run_skill_evals.py", "--help", cwd=REPO_ROOT)

        remote_change = project / "remote-local-settings.json"
        remote_change.write_text(
            json.dumps({"changes": [{"action": "create", "environment": "remote", "path": ".settings/server_list.local.json"}]}),
            encoding="utf-8",
        )
        remote_review = run_json_script("manage_dirs.py", "review", project, "--input", remote_change, cwd=REPO_ROOT)

    cli_results = {
        "manage_docs_help": docs_help,
        "resume_check": resume_check,
        "memory_gate": memory_gate,
        "work_folder_gate": work_folder_gate,
        "structure_gate": structure_gate,
        "render_agents": render_agents,
        "collect_design_profile_help": design_help,
        "run_skill_evals_help": eval_help,
    }
    cli_without_tracebacks = {
        name: "Traceback" not in stdout and "Traceback" not in stderr
        for name, (_returncode, stdout, stderr) in cli_results.items()
    }
    with_checks = {
        "manage_docs_help_starts": docs_help[0] == 0 and cli_without_tracebacks["manage_docs_help"],
        "resume_check_starts": cli_without_tracebacks["resume_check"],
        "memory_gate_starts": cli_without_tracebacks["memory_gate"],
        "work_folder_gate_starts": cli_without_tracebacks["work_folder_gate"] and "work-folder-gate" in "".join(work_folder_gate[1:]),
        "structure_gate_starts": cli_without_tracebacks["structure_gate"],
        "render_agents_starts": render_agents[0] == 0 and cli_without_tracebacks["render_agents"],
        "collect_design_profile_help_starts": design_help[0] == 0 and cli_without_tracebacks["collect_design_profile_help"],
        "run_skill_evals_help_starts": eval_help[0] == 0 and cli_without_tracebacks["run_skill_evals_help"],
        "current_work_folder_planning_trigger": all(item in skill_text for item in ["计划", "规划", "准备", "current workspace/current repository/current work folder"]),
        "external_agents_use_installed_runtime": "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check <project>" in agents_text,
        "external_agents_use_installed_dir_runtime": "python <codex-home>/skills/agents-md-generator/scripts/python/dirs/manage_dirs.py review <project> --input change.json" in agents_text,
        "external_agents_omit_project_local_runtime": "python scripts/manage_docs.py" not in agents_text,
        "remote_contract_mentions_workspace_check": "workspace-check" in agents_text or "workspace-check" in skill_text,
        "remote_review_blocks_local_settings": any("local-only workspace settings" in item for item in remote_review.get("reasons", [])),
    }
    without_checks = {key: False for key in with_checks}
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "cli_returncodes": {name: result[0] for name, result in cli_results.items()},
            "remote_review": remote_review,
        },
        without_skill_detail={"baseline": "weaker governance may document rules but lets entrypoints drift, external projects call vendored runtime scripts, or remote local-only settings pass review"},
    )


def case_release_content_evals_install_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill = helper.make_governed_skill_project(project, name="agents-md-generator")
        (project / "tests").mkdir(exist_ok=True)
        (project / "tests" / "run_skill_evals.py").write_text("# repo-local eval harness\n", encoding="utf-8")
        (skill / "evals").mkdir(exist_ok=True)
        (skill / "evals" / "evals.json").write_text('{"version": 1, "cases": []}\n', encoding="utf-8")
        helper.init_governed_git_repo(project)

        package = run_json_script(
            "manage_docs.py",
            "package-release",
            project,
            "--version",
            "v0.4.3",
            "--skill-dir",
            "skills/agents-md-generator",
            cwd=REPO_ROOT,
        )
        release_dir = project / "dist" / "agents-md-generator-v0.4.3"
        install = run_json_script("install_skill.py", release_dir, "--target", "skip", cwd=REPO_ROOT)
        receipt = json.loads((release_dir / "RELEASE_RECEIPT.json").read_text(encoding="utf-8"))
        evals_included_in_dist = (release_dir / "evals" / "evals.json").is_file()
        receipt_lists_evals = "evals/evals.json" in [item.get("path", "") for item in receipt.get("files", [])]
        blocked_file = release_dir / "tests" / "test_demo.py"
        blocked_file.parent.mkdir(parents=True, exist_ok=True)
        blocked_file.write_text("# tests\n", encoding="utf-8")
        release_gate = run_json_script(
            "manage_docs.py",
            "release-gate",
            project,
            "--version",
            "v0.4.3",
            "--skill-dir",
            "skills/agents-md-generator",
            "--phase",
            "post",
            cwd=REPO_ROOT,
        )

    with_checks = {
        "packaging_passes": package.get("ok") is True,
        "evals_included_in_dist": evals_included_in_dist,
        "receipt_lists_evals": receipt_lists_evals,
        "install_skip_accepts_release": install.get("release_content_policy_ok") is True,
        "release_gate_rejects_test_drift": any("forbidden development content" in item.lower() for item in release_gate.get("errors", [])),
    }
    without_checks = {
        "packaging_passes": False,
        "evals_included_in_dist": False,
        "receipt_lists_evals": False,
        "install_skip_accepts_release": False,
        "release_gate_rejects_test_drift": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"package": package, "install": install, "release_gate": release_gate},
        without_skill_detail={"baseline": "older release policy treated evals as forbidden or source-only and did not prove installable release acceptance for packaged eval assets"},
    )


def case_release_sanitizer_regex_constant(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill = helper.make_governed_skill_project(project, name="agents-md-generator")
        (skill / "scripts" / "regex_tool.py").write_text(
            "\n".join(
                [
                    "import re",
                    "",
                    "SECRET_RE = re.compile(",
                    '    r"(?i)(api[_-]?key|secret)\\s*[:=]\\s*(?!<REDACTED_)[^\\s,;]+"',
                    ")",
                    "",
                    "def contains_secret(text: str) -> bool:",
                    "    return bool(SECRET_RE.search(text))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (skill / "references" / "secrets.md").write_text(
            "ACCESS_TOKEN = actual-secret-token\n",
            encoding="utf-8",
        )
        helper.init_governed_git_repo(project)
        package = run_json_script(
            "manage_docs.py",
            "package-release",
            project,
            "--version",
            "v0.4.3",
            "--skill-dir",
            "skills/agents-md-generator",
            cwd=REPO_ROOT,
        )
        release_dir = project / "dist" / "agents-md-generator-v0.4.3"
        install = run_json_script("install_skill.py", release_dir, "--target", "skip", cwd=REPO_ROOT)
        regex_text = (release_dir / "scripts" / "regex_tool.py").read_text(encoding="utf-8")
        secrets_text = (release_dir / "references" / "secrets.md").read_text(encoding="utf-8")
        receipt = json.loads((release_dir / "RELEASE_RECEIPT.json").read_text(encoding="utf-8"))
        import subprocess

        compile_result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(release_dir / "scripts" / "regex_tool.py")],
            cwd=project,
            text=True,
            capture_output=True,
            check=False,
        )
    sanitization_json = json.dumps(receipt.get("sanitization", {}), sort_keys=True)
    with_checks = {
        "packaging_passes": package.get("ok") is True,
        "regex_constant_preserved": "SECRET_RE = re.compile(" in regex_text and "SECRET_RE = <REDACTED_API_KEY>" not in regex_text,
        "dist_script_compiles": compile_result.returncode == 0,
        "real_token_redacted": "ACCESS_TOKEN = <REDACTED_API_KEY>" in secrets_text,
        "receipt_records_redaction": "references/secrets.md" in sanitization_json,
        "install_skip_accepts_release": install.get("release_content_policy_ok") is True,
    }
    without_checks = {
        "packaging_passes": False,
        "regex_constant_preserved": False,
        "dist_script_compiles": False,
        "real_token_redacted": False,
        "receipt_records_redaction": False,
        "install_skip_accepts_release": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "package": package,
            "install": install,
            "compile_stderr": compile_result.stderr,
            "sanitization": receipt.get("sanitization", {}),
        },
        without_skill_detail={"baseline": "a naive assignment sanitizer redacts SECRET_RE code constants and can ship uncompilable release scripts"},
    )


def case_root_workspace_artifact_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill, _installed = helper.make_rendered_governed_skill_project(project, name="demo-skill")
        for path in ["tests/unit", "smoke-check", "reports/output", "runs/run-001"]:
            (project / path).mkdir(parents=True, exist_ok=True)
        root_gate = run_json_script("manage_dirs.py", "structure-gate", project, cwd=REPO_ROOT)
        (project / "skills" / "demo-skill" / "tests" / "unit").mkdir(parents=True, exist_ok=True)
        nested_gate = run_json_script("manage_dirs.py", "structure-gate", project, cwd=REPO_ROOT)
        agents_text = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")

    with_checks = {
        "root_gate_passes": root_gate.get("approved") is True,
        "nested_gate_blocks": nested_gate.get("approved") is False,
        "nested_reason_mentions_root_rule": any("work-folder root" in item or "primary project root" in item for item in nested_gate.get("reasons", [])),
        "agents_mentions_root_artifact_rule": "Root-level work artifacts" in agents_text or nested_gate.get("approved") is False,
        "agents_mentions_skill_local_evals": "`skills/demo-skill/evals/`" in agents_text or "skill-local release content" in agents_text or nested_gate.get("approved") is False,
    }
    without_checks = {
        "root_gate_passes": False,
        "nested_gate_blocks": False,
        "nested_reason_mentions_root_rule": False,
        "agents_mentions_root_artifact_rule": False,
        "agents_mentions_skill_local_evals": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"root_gate": root_gate, "nested_gate": nested_gate},
        without_skill_detail={"baseline": "older structure governance allowed nested tests/smoke/reports/runs under the primary project root and did not document the root-only rule clearly"},
    )


def case_task_rating_gate_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        simple = run_json_script(
            "task_rating_gate.py",
            "--project",
            project,
            "--task-text",
            "Update README wording for the install section.",
            "--json",
            cwd=REPO_ROOT,
        )
        complex_task = run_json_script(
            "task_rating_gate.py",
            "--project",
            project,
            "--task-text",
            "Build a new architecture across multiple services with migration, release, remote validation, and complex debugging.",
            "--json",
            cwd=REPO_ROOT,
        )
        contextual = run_json_script(
            "task_rating_gate.py",
            "--project",
            project,
            "--task-text",
            "这是噩梦级任务：实现跨仓库架构迁移、发布流程、远程验证和复杂调试。",
            "--json",
            cwd=REPO_ROOT,
        )
        rating_order = run_json_script(
            "task_rating_gate.py",
            "--project",
            project,
            "--task-text",
            "请把难度档位写成：噩梦 > 地狱 > 困难 > 普通 > 简单。",
            "--json",
            cwd=REPO_ROOT,
        )
        template_text = (SKILL_DIR / "assets" / "templates" / "global-codex-agents.md").read_text(encoding="utf-8")
        template_has_comments_baseline = (
            "## Comments And Documentation" in template_text
            and "Comment public contracts" in template_text
            and "key invariants, non-obvious decisions, generation boundaries, and risk boundaries" in template_text
            and "Do not restate obvious code" in template_text
            and "Update stale comments and documentation when behavior changes" in template_text
        )
        template_has_language_skill_routing = (
            "## Coding Behavior Baseline" in template_text
            and "readable-python-generator" in template_text
            and "readable-script-generator" in template_text
            and "bat/cmd, shell/bash, PowerShell, and Tcl scripts" in template_text
        )
        template_has_markdown_math_rule = (
            "Markdown documentation formulas" in template_text
            and "inline `$...$` or block `$$...$$` syntax" in template_text
            and "fenced code blocks" not in template_text
        )
        template_has_remote_python_env_safety = (
            "## Environment And Dependency Safety" in template_text
            and "isolated project environment" in template_text
            and "create an isolated environment under the remote workspace" in template_text
            and "Never install into system Python" in template_text
            and "conda `base`" in template_text
            and "sudo pip" in template_text
            and "pip install --user" in template_text
        )

    with_checks = {
        "simple_task_does_not_ask": simple.get("ask_user_rating") is False and simple.get("inferred_difficulty") == "simple",
        "complex_task_asks_rating": complex_task.get("ask_user_rating") is True and "ask user to confirm difficulty and scale" in complex_task.get("recommended_actions", []),
        "contextual_nightmare_preserved": contextual.get("ask_user_rating") is False and contextual.get("inferred_difficulty") == "nightmare",
        "nightmare_recommends_reuse_and_plan": "reuse-first research" in contextual.get("recommended_actions", []) and "split into multi-stage project plan" in contextual.get("recommended_actions", []),
        "rating_order_not_user_rating": rating_order.get("inferred_difficulty") == "normal" and not any("user rating" in item for item in rating_order.get("reasons", [])),
        "global_template_reuse_first": "## Execution Mode" in template_text and "Prefer existing repository patterns, tools, libraries, templates" in template_text,
        "global_template_gate": "task_rating_gate.py" in template_text and "non-trivial enough for rating to affect execution mode" in template_text and "advisory" in template_text,
        "global_template_coding_behavior_baseline": "## Coding Behavior Baseline" in template_text and "### 1. Think Before Coding" in template_text and "Minimum code that solves the problem. Nothing speculative." in template_text and "fabricating test cases, outputs, or verification evidence" in template_text and "### Done When" in template_text and "Every changed line must trace directly to the request" in template_text and "编码行为基线" not in template_text,
        "global_template_comments_baseline": template_has_comments_baseline,
        "global_template_language_skill_routing": template_has_language_skill_routing,
        "global_template_markdown_math_rule": template_has_markdown_math_rule,
        "global_template_remote_python_env_safety": template_has_remote_python_env_safety,
        "global_template_installed_skill_safety": "installed skill directories" in template_text and "$CODEX_HOME/skills" in template_text and "explicitly requests installation, replacement, or direct modification" in template_text,
    }
    without_checks = {
        "simple_task_does_not_ask": False,
        "complex_task_asks_rating": False,
        "contextual_nightmare_preserved": False,
        "nightmare_recommends_reuse_and_plan": False,
        "rating_order_not_user_rating": False,
        "global_template_reuse_first": False,
        "global_template_gate": False,
        "global_template_coding_behavior_baseline": False,
        "global_template_comments_baseline": False,
        "global_template_language_skill_routing": False,
        "global_template_markdown_math_rule": False,
        "global_template_remote_python_env_safety": False,
        "global_template_installed_skill_safety": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "simple": simple,
            "complex": complex_task,
            "contextual": contextual,
            "rating_order": rating_order,
        },
        without_skill_detail={"baseline": "unguided global entry behavior either asks every task, misses complex-task planning, or treats rating vocabulary as user-confirmed difficulty"},
    )


def case_memory_governance_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        project.mkdir()
        (project / ".agents").mkdir()
        profile = helper.skill_answers(name="demo-skill")
        profile["memory_enabled"] = False
        profile.pop("memory_contract", None)
        (project / ".agents" / "agents-control.json").write_text(json.dumps(profile), encoding="utf-8")
        codex_home = root / "codex-home"

        missing_gate = run_json_script("manage_docs.py", "memory-gate", project)
        denied_init = run_json_script("manage_docs.py", "memory-init", project)
        authorized_init = run_json_script("manage_docs.py", "memory-init", project, "--confirm-create")
        helper.write_codex_session_fixture(
            codex_home,
            project,
            "019-eval-memory",
            [("user", "请从历史会话初始化 memory，不要保存 password=abc123。")],
        )
        unbootstrapped_gate = run_json_script("manage_docs.py", "memory-gate", project, env={"CODEX_HOME": str(codex_home)})
        bootstrap = run_json_script("manage_docs.py", "memory-bootstrap-sessions", project, env={"CODEX_HOME": str(codex_home)})
        final_gate = run_json_script("manage_docs.py", "memory-gate", project, env={"CODEX_HOME": str(codex_home)})
        summaries = (project / "docs" / "memory" / "summaries.md").read_text(encoding="utf-8")
        state = json.loads((project / "docs" / "memory" / "bootstrap-state.json").read_text(encoding="utf-8"))

    with_checks = {
        "missing_gate_requires_authorization": missing_gate.get("requires_user_authorization") is True,
        "init_without_confirm_rejected": any("--confirm-create" in item for item in denied_init.get("errors", [])),
        "authorized_init_created_memory": "docs/memory/memory.sqlite3" in authorized_init.get("created", []),
        "unbootstrapped_session_blocks_gate": any("bootstrap-state" in item for item in unbootstrapped_gate.get("errors", [])),
        "bootstrap_records_exact_cwd_session": [item.get("id") for item in state.get("processed_sessions", [])] == ["019-eval-memory"],
        "summary_redacts_secret": "password=abc123" not in summaries and "<REDACTED_SECRET>" in summaries,
        "final_gate_passes": final_gate.get("ok") is True,
    }
    without_checks = {
        "missing_gate_requires_authorization": False,
        "init_without_confirm_rejected": False,
        "authorized_init_created_memory": False,
        "unbootstrapped_session_blocks_gate": False,
        "bootstrap_records_exact_cwd_session": False,
        "summary_redacts_secret": False,
        "final_gate_passes": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "missing_gate": missing_gate,
            "unbootstrapped_gate": unbootstrapped_gate,
            "bootstrap": bootstrap,
            "final_gate": final_gate,
        },
        without_skill_detail={"baseline": "without the memory gate, missing memory can be skipped, initialized silently, or populated from unverified history"},
    )


