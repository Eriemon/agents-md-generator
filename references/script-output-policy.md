# Script Output Policy

Generated root `AGENTS.md` files summarize this policy from `.agents/global-rule-overrides.json`. The default local governance value is seeded from `config/script-output-policy-default.json`; keep full examples here so root instructions stay compact.

## Defaults

- Human-readable process output uses one of three exact prefixes:
  - Normal information: `> INFO: [{kind}]`
  - Warnings: `> WARNING: [{kind}]`
  - Errors: `> ERR: [{kind}]`
- `Kind` values come from `script_output_policy.kinds` in `.agents/global-rule-overrides.json`; implementation code must not hard-code the Kind list.
- Python INFO/progress output is enabled by default and must support `--quiet` to suppress normal process output. Warnings and errors remain visible.
- Multi-line human-readable process messages repeat the prefix on every line.
- Machine-readable output is exempt: JSON stdout, generated file content, protocol streams, and AGENTS drafts must not be prefixed.

## Default Kind Values

The default Kind list is intentionally broad and configurable:

```json
[
  "Python", "Shell", "Bash", "PowerShell", "Bat", "Cmd",
  "TCL", "MakeFile", "CMake", "Ninja",
  "C", "CPP", "CUDA", "OpenCL",
  "Verilog", "SystemVerilog", "VHDL",
  "Vivado", "Vitis", "HLS", "XSim", "Verilator",
  "Node", "JavaScript", "TypeScript",
  "Java", "Go", "Rust",
  "Docker", "Git", "SQL"
]
```

Add or remove Kind values in JSON config, then rerender AGENTS.md. Do not edit validators or Python source to recognize a new tool family.

## Examples

Python script progress:

```text
> INFO: [Python] Loading project facts
> WARNING: [Python] Optional pyproject.toml was not found
> ERR: [Python] Failed to parse AGENTS.md metadata
```

Verilog simulation:

```text
> INFO: [Verilog] Running xsim behavioral simulation
> WARNING: [Verilog] Timescale differs between testbench and DUT
> ERR: [Verilog] Simulation timed out before done_o asserted
```

Machine-readable JSON stdout remains raw:

```json
{"ok": true, "errors": []}
```
