#!/usr/bin/env python3
"""Test runtime version metadata without requiring GTK/PyGObject."""
from pathlib import Path
import ast
import json
import os
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "macos-control-center"
tree = ast.parse(source.read_text(encoding="utf-8"))

# Evaluate only the global path assignments without importing GTK. This catches
# a missing STATEFILE name before trying to start the actual resident daemon.
path_assignments = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"PIDFILE", "STATEFILE"}:
                path_assignments[target.id] = node
assert set(path_assignments) == {"PIDFILE", "STATEFILE"}, "PIDFILE/STATEFILE müssen beide definiert sein"
old_pid = os.environ.get("CC_PIDFILE")
old_state = os.environ.get("CC_STATEFILE")
try:
    with tempfile.TemporaryDirectory(prefix="cc-state-path-") as td:
        expected_pid = str(Path(td) / "macos-control-center.pid")
        os.environ["CC_PIDFILE"] = expected_pid
        os.environ.pop("CC_STATEFILE", None)
        env_ns = {"os": os}
        exec(compile(ast.Module(body=[path_assignments["PIDFILE"], path_assignments["STATEFILE"]], type_ignores=[]), str(source), "exec"), env_ns)
        assert env_ns["PIDFILE"] == expected_pid
        assert env_ns["STATEFILE"] == expected_pid + ".state.json"
        expected_state = str(Path(td) / "custom-state.json")
        os.environ["CC_STATEFILE"] = expected_state
        env_ns = {"os": os}
        exec(compile(ast.Module(body=[path_assignments["PIDFILE"], path_assignments["STATEFILE"]], type_ignores=[]), str(source), "exec"), env_ns)
        assert env_ns["STATEFILE"] == expected_state
finally:
    if old_pid is None:
        os.environ.pop("CC_PIDFILE", None)
    else:
        os.environ["CC_PIDFILE"] = old_pid
    if old_state is None:
        os.environ.pop("CC_STATEFILE", None)
    else:
        os.environ["CC_STATEFILE"] = old_state
functions = {
    node.name: node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name in {"_write_runtime_state", "_remove_runtime_state"}
}
assert set(functions) == {"_write_runtime_state", "_remove_runtime_state"}
version_node = next(
    node for node in tree.body if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "APP_VERSION" for target in node.targets)
)
version = ast.literal_eval(version_node.value)
ns = {"os": os, "json": json, "tempfile": tempfile, "sys": sys, "time": time,
      "APP_VERSION": version, "PROCESS_STARTED_AT": "test-start-time", "STATEFILE": ""}
exec(compile(ast.Module(body=list(functions.values()), type_ignores=[]), str(source), "exec"), ns)
with tempfile.TemporaryDirectory(prefix="cc-runtime-state-") as td:
    ns["STATEFILE"] = str(Path(td) / "state.json")
    assert ns["_write_runtime_state"](True)
    path = Path(ns["STATEFILE"])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pid"] == os.getpid()
    assert data["version"] == version
    assert data["resident"] is True
    assert data["visible"] is False
    assert data["updated_at"]
    assert data["started_at"] == "test-start-time"
    assert Path(data["script"]).resolve() == Path(sys.argv[0]).resolve()
    assert ns["_write_runtime_state"](True, visible=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["visible"] is True
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    ns["_remove_runtime_state"](os.getpid())
    assert not path.exists()
print("RUNTIME-VERSION-STATE-OK")
