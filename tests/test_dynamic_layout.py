#!/usr/bin/env python3
"""Static+pure tests for bounded animated GTK layout; no GTK import required."""
from pathlib import Path
import ast, os, json, tempfile, sys
root = Path(__file__).resolve().parents[1]
path = root / "macos-control-center"
text = path.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(path))
fn = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ControlCenter")
methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
for name in ("_adaptive_height", "_ease_out_cubic"):
    assert name in fn, name
ns = {}
exec(compile(ast.Module(body=[fn["_adaptive_height"], fn["_ease_out_cubic"]], type_ignores=[]), str(path), "exec"), ns)
assert ns["_adaptive_height"](900, 520) == 520
assert ns["_adaptive_height"](330, 520) == 330
assert ns["_adaptive_height"](0, 520) == 1
assert ns["_ease_out_cubic"](0) == 0
assert ns["_ease_out_cubic"](1) == 1
assert ns["_ease_out_cubic"](.5) > .8
for name in ("_available_popup_height", "_initialize_dynamic_size", "_schedule_dynamic_resize", "_begin_dynamic_resize", "_resize_step", "_toast", "_hide_toast", "_fill_settings", "_fill_diag", "_copy_diagnostics", "_tile_button_press", "_publish_runtime_state", "_cancel_focus_hide", "_hide_after_focus_check"):
    assert name in methods, "missing method: " + name
for marker in (
    "Gtk.ScrolledWindow()", "Gtk.PolicyType.AUTOMATIC", "set_propagate_natural_height(False)",
    "set_size_request(-1, height)", "self.resize(data[\"width\"], height)",
    "_ease_out_cubic(progress)", "def _fill_settings(self):", "def _fill_diag(self):",
    "Gdk.KEY_Page_Down", "Gdk.KEY_comma", "reduce_motion", "timeout_ms=2600",
    'screen.connect("size-changed", self._on_screen_size_changed)',
    'b.get_accessible().set_name(text)',
    'self._focus_guard_until = time.monotonic() + 0.75',
    'delay_ms, self._hide_after_focus_check, generation',
    'self._publish_runtime_state()',
):
    assert marker in text, "missing dynamic/production feature marker: " + marker
assert "self.resize(self.get_size()[0], 1)" not in text, "old resize-to-1 hack regressed"
print("DYNAMIC-RESIZE-OK")
print("SETTINGS-DIAGNOSTICS-OK")
print("KEYBOARD-ACCESSIBILITY-OK")
