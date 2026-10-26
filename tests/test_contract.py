#!/usr/bin/env python3
"""Sichere Quelltext-/Konfigurationstests; importiert GTK nicht und schaltet nichts um."""
from pathlib import Path
import ast
import json
import os
import stat
import tempfile
import sys
import logging
import urllib.parse, ipaddress, re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
TEXT = SOURCE.read_text(encoding="utf-8")
TREE = ast.parse(TEXT, filename=str(SOURCE))

# Syntax ist bereits durch ast.parse geprüft.
assert isinstance(TREE, ast.Module)

# Unverhandelbare LocalSend-Sandbox.
localsend = None
str_table = None
nodes = {node.name: node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
assignments = {}
for node in TREE.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node.value
        if any(isinstance(t, ast.Name) and t.id == "STR" for t in node.targets):
            str_table = ast.literal_eval(node.value)

localsend = ast.literal_eval(assignments["LOCALSEND_CMD"])
assert localsend == ["flatpak", "run", "--nofilesystem=/mnt/medien", "org.localsend.localsend_app"]
assert "--filesystem=/mnt/medien" not in " ".join(localsend)

# Release identifiers and runtime state path must be defined in the shipped code.
assert ast.literal_eval(assignments["APP_VERSION"]) == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert "STATEFILE" in assignments, "STATEFILE muss definiert sein, sonst stürzt der Daemon beim Start ab"
statefile_ast = ast.dump(assignments["STATEFILE"])
assert "CC_STATEFILE" in statefile_ast and "PIDFILE" in statefile_ast

# Window must stay opaque; do not change the visual to RGBA.
assert "self.set_app_paintable(False)" in TEXT
assert "self.set_visual(" not in TEXT
assert '"controlcenter":' in TEXT and 'assets/macos-control-center.svg' in (ROOT / "install.sh").read_text(encoding="utf-8")
assert "set_keep_above(True)" in TEXT
assert "SIGUSR1" in TEXT and "--daemon" in TEXT and "PIDFILE" in TEXT

# Every user-facing translation contains all five language variants.
assert str_table is not None
for key, value in str_table.items():
    assert isinstance(value, tuple) and len(value) == 5, f"Übersetzung unvollständig: {key}"
literal_ui_keys = {
    node.args[0].value
    for node in ast.walk(TREE)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name) and node.func.id == "T"
    and node.args and isinstance(node.args[0], ast.Constant)
    and isinstance(node.args[0].value, str)
}
missing_ui_keys = sorted(literal_ui_keys - set(str_table))
assert not missing_ui_keys, f"UI-Übersetzungen fehlen: {missing_ui_keys}"
for key in ("customize_tiles", "tiles_reset", "tiles_up", "tiles_down", "tiles_not_ready", "tile_display",
    "settings_title", "refresh_now", "poll_interval", "motion_on", "motion_off",
    "diagnostics", "copy_diagnostics", "diagnostics_copied", "tile_context_settings",
    "settings_system", "status_label"):
    assert key in str_table, f"Fehlender UI-Text: {key}"

# Run pure config/order helpers without importing GI or starting a UI.
pure_names = {
    "QUICK_ACTION_KEYS", "DEFAULT_CONFIG", "_CFG_LANGS", "_adaptive_height", "_ease_out_cubic",
    "_validate_devices", "_cfg_value", "_order_quick_actions", "_persist_config", "_write_default_config", "load_config",
}
pure_nodes = []
for node in TREE.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in pure_names for t in node.targets):
        if any(isinstance(t, ast.Name) and t.id in pure_names for t in node.targets):
            pure_nodes.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in pure_names:
        pure_nodes.append(node)

ns = {
    "os": os, "json": json, "tempfile": tempfile, "urllib": urllib, "ipaddress": ipaddress, "re": re,
    "VPN_PREFERRED": "simon",
    "logging": logging,
}
exec(compile(ast.Module(body=pure_nodes, type_ignores=[]), str(SOURCE), "exec"), ns)

assert ns["_cfg_value"]("poll_seconds", 3) == 3
assert ns["_cfg_value"]("poll_seconds", 61) is None
assert ns["_cfg_value"]("poll_seconds", True) is None
assert ns["_cfg_value"]("language", "DE") == "de"
assert ns["_cfg_value"]("language", "xx") is None
assert ns["_cfg_value"]("quick_actions", "auto") == "auto"
assert ns["_cfg_value"]("quick_actions", ["mic", "out"]) == ["mic", "out"]
assert ns["_cfg_value"]("quick_actions", ["mic", "mic"]) is None
assert ns["_cfg_value"]("quick_actions", ["mic", "arbitrary-shell"]) is None
assert ns["_cfg_value"]("quick_actions", 1) is None
assert ns["_cfg_value"]("reduce_motion", True) is True
assert ns["_cfg_value"]("reduce_motion", 1) is None
assert ns["_cfg_value"]("stay_open", True) is True
assert ns["_cfg_value"]("stay_open", 1) is None
assert ns["_adaptive_height"](900, 600) == 600
assert ns["_adaptive_height"](400, 600) == 400
assert ns["_adaptive_height"](0, 600) == 1
assert ns["_ease_out_cubic"](0) == 0.0
assert ns["_ease_out_cubic"](1) == 1.0
assert 0.8 < ns["_ease_out_cubic"](0.5) < 0.9

specs = [{"key": "mic"}, {"key": "rot"}, {"key": "out"}]
assert [x["key"] for x in ns["_order_quick_actions"](specs, "auto")] == ["mic", "rot", "out"]
assert [x["key"] for x in ns["_order_quick_actions"](specs, ["out", "mic"])] == ["out", "mic"]
assert ns["_order_quick_actions"](specs, []) == []

# Atomic config write and permission contract.
with tempfile.TemporaryDirectory(prefix="cc-test-") as td:
    ns["CONFIG_DIR"] = os.path.join(td, "cfg")
    ns["CONFIG_FILE"] = os.path.join(ns["CONFIG_DIR"], "config.json")
    assert ns["_persist_config"]({"poll_seconds": 10, "quick_actions": ["mic"]})
    stored = json.loads(Path(ns["CONFIG_FILE"]).read_text(encoding="utf-8"))
    assert stored == {"poll_seconds": 10, "quick_actions": ["mic"]}
    assert stat.S_IMODE(os.stat(ns["CONFIG_DIR"]).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(ns["CONFIG_FILE"]).st_mode) == 0o600

# Migration behavior for older config files.
with tempfile.TemporaryDirectory(prefix="cc-migrate-") as td:
    ns["CONFIG_DIR"] = td
    ns["CONFIG_FILE"] = os.path.join(td, "config.json")
    Path(ns["CONFIG_FILE"]).write_text(json.dumps({"vpn_preferred": "simon", "poll_seconds": 10}), encoding="utf-8")
    cfg = ns["load_config"]()
    assert cfg["vpn_preferred"] == "simon"
    assert cfg["poll_seconds"] == 10
    assert cfg["quick_actions"] == "auto"
    assert cfg["language"] == "auto"
    assert cfg["reduce_motion"] is False
    assert cfg["stay_open"] is False

# Verify key editor paths are connected in the UI.
for marker in (
    'add("tiles", T("customize_tiles")',
    'elif self._act_mode == "tiles":',
    'def _fill_tiles(self):',
    'def _toggle_quick_action(self, key, enabled):',
    'def _move_quick_action(self, key, offset):',
    'def _reset_quick_actions(self):',
    'def _fill_settings(self):',
    'def _fill_diag(self):',
    'def _toast(self, message, error=False, timeout_ms=2600):',
    'def _build_header(self, root):',
    'def _toggle_stay_open(self):',
    'self._header_status.set_text(T("status_ready"))',
):
    assert marker in TEXT, f"Schnellaktionseditor unvollständig: {marker}"

print("CONTRACT-OK")
print("CONFIG-OK")
print("LANG-OK")
print("QUICK-ACTIONS-OK")
print("SECURITY-OK")
