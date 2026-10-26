#!/usr/bin/env python3
"""Run shipped diagnostics without DISPLAY, config writes or daemon signals."""
import ast
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
for flag, section in (("--diagnose-bluetooth", "bluetooth"), ("--diagnose-audio", "audio"),
                      ("--diagnose", "capabilities")):
    with tempfile.TemporaryDirectory(prefix="cc-diag-test-") as directory:
        config = Path(directory) / "config"
        config.mkdir()
        pid = Path(directory) / "resident.pid"
        pid.write_text("do not modify")
        environment = {**os.environ, "XDG_CONFIG_HOME": str(config), "CC_PIDFILE": str(pid)}
        environment.pop("DISPLAY", None)
        result = subprocess.run(["bash", str(ROOT / "run.sh"), flag], env=environment,
                                capture_output=True, text=True, timeout=70)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert section in report and report["script"] == str(ROOT / "macos-control-center")
        assert not re.search(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", result.stdout + result.stderr)
        assert not list(config.rglob("*")), "read-only diagnostics wrote persistent config"
        assert pid.read_text() == "do not modify"
        assert not Path(str(pid) + ".state.json").exists()

# --direct must construct this process's window, not signal a stale daemon.
tree = ast.parse((ROOT / "macos-control-center").read_text())
main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
events = []
ns = dict(sys=NS(argv=["macos-control-center", "--direct"]), logging=logging,
          ControlCenter=lambda:NS(show_all=lambda:events.append("show"), present=lambda:events.append("present")),
          Gtk=NS(main=lambda:events.append("loop")))
exec(compile(ast.Module(body=[main], type_ignores=[]), "main", "exec"), ns)
ns["main"]()
assert events == ["show", "present", "loop"]
print("READ-ONLY-DIAGNOSTICS-NO-DISPLAY-NO-CONFIG-WRITES-NO-DAEMON-SIGNALS-OK")
print("DIRECT-DEBUG-INSTANCE-OK")
