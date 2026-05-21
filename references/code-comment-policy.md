# Code Comment Policy

Generated root `AGENTS.md` files summarize this policy from `.agents/global-rule-overrides.json`. Keep detailed examples here and in evals instead of expanding the root file.

## Defaults

- Language: 中文.
- Add comments only for non-obvious intent, invariants, risk, generation boundaries, or public API behavior.
- Do not add comments that restate obvious code.
- Update stale comments when behavior changes.
- 禁止未经明确要求的批量 AI 注释.
- Generated code must preserve line breaks and blank-line separation; 不能把语句、注释、函数粘连到一起.

## Python

Use docstrings for public functions/classes. Put ordinary explanatory comments above the code they explain, not as right-side trailing comments.

Good:

```python
def load_profile(path: Path) -> dict[str, Any]:
    """Load a verified profile; callers receive an empty dict for missing files."""
    if not path.exists():
        return {}

    # Invariant: only JSON objects are valid control profiles.
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
```

Bad:

```python
profile = json.loads(raw)  # Load JSON.
```

## C/C++

Put function, module/core behavior, variable-definition, and special behavior comments above the code. Prioritize ownership/lifetime, ABI, concurrency, memory, and undefined-behavior risks. Put `#define` macro comments on the right side.

Good:

```cpp
// Ownership: caller retains the buffer; this view must not outlive packet.
PacketView view(packet.data(), packet.size());

#define AXIS_WORD_BYTES 64  // AXI stream word width in bytes.
```

Bad:

```cpp
PacketView view(packet.data(), packet.size()); // Create view.
```

## Verilog/SystemVerilog

For Verilog/SystemVerilog: module descriptions go above `module`; signal declarations and definitions (`input`, `output`, `inout`, `parameter`, `localparam`, `integer`, `logic`, `wire`, `reg`, `real`) use right-side comments; `assign` uses right-side comments; `task`, `function`, `generate`, and `always` explanations go above the statement; register assignments inside `always` blocks use right-side comments.

Good:

```verilog
// Align AXI stream output after the BRAM read latency.
always @(posedge clk) begin
  valid_o <= valid_d1; // One-cycle delayed valid for data_o.
end

assign ready_o = ready_i & enabled; // Backpressure gated by enable.
```

Bad:

```verilog
// assign valid_d1 to valid_o
assign valid_o = valid_d1;
```
