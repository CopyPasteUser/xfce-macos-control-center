#!/usr/bin/env python3
"""Static release gates; complements runtime tests, never claims hardware proof."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "macos-control-center"
tree = ast.parse(source.read_text(), filename=str(source))
for path in ROOT.rglob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
for scope in [tree] + [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]:
    names = [node.name for node in scope.body if isinstance(node, ast.FunctionDef)]
    assert len(names) == len(set(names)), "duplicate runtime method/function"
for node in ast.walk(tree):
    if isinstance(node, ast.Dict):
        keys = [key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        assert len(keys) == len(set(keys)), f"duplicate dictionary key at {node.lineno}"
    if not isinstance(node, ast.Call): continue
    name = ast.unparse(node.func)
    if name in ("subprocess.run", "subprocess.check_output", "subprocess.call"):
        assert any(keyword.arg == "timeout" for keyword in node.keywords), f"unbounded {name}:{node.lineno}"
    assert not any(keyword.arg == "shell" and not
                   (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
                   for keyword in node.keywords), f"shell subprocess at {node.lineno}"
    assert name not in ("os.system", "os.popen", "eval", "exec"), f"dynamic execution at {node.lineno}"
    if name.startswith("logging."):
        assert not any(isinstance(value, ast.Name) and value.id in ("pw", "password", "secret", "private_key")
                       for value in ast.walk(node)), "secret passed to logging"
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in ("bluetooth_set_power", "bluetooth_state", "diagnose"):
        text = ast.get_source_segment(source.read_text(), node)
        assert '"sudo"' not in text and '"pkexec"' not in text
        assert '"start"' not in text and '"restart"' not in text, "service activation in hardware/diagnostic path"
print("STRICT-STATIC-AUDIT-PYTHON-SYNTAX-DUPLICATES-TIMEOUTS-SHELL-LOGGING-OK")
