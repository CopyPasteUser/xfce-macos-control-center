#!/usr/bin/env python3
"""Exercise the GTK window's focus/toggle state logic without importing Gtk."""
import ast
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
center = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ControlCenter")
required = {
    "_publish_runtime_state", "_cancel_focus_hide", "_dismiss",
    "_on_focus_out", "_hide_after_focus_check", "_toggle_visibility",
    "_force_show", "_force_hide",
}
methods = [n for n in center.body if isinstance(n, ast.FunctionDef) and n.name in required]
assert {n.name for n in methods} == required

class FakeGLib:
    def __init__(self):
        self.next_id = 1
        self.callbacks = {}
    def timeout_add(self, ms, callback, *args):
        ident = self.next_id
        self.next_id += 1
        self.callbacks[ident] = (callback, args)
        return ident
    def source_remove(self, ident):
        self.callbacks.pop(ident, None)
    def run(self, ident):
        entry = self.callbacks.pop(ident, None)
        if not entry:
            return False
        callback, args = entry
        return callback(*args)

class FakeWindow:
    def __init__(self):
        self._resident = True
        self._focus_hide_src = 0
        self._focus_guard_until = 0.0
        self._visibility_generation = 0
        self._runtime_state_callback = self.record_runtime
        self.visible = False
        self.focused = False
        self.updates = []
        self.globals = namespace
    def get_visible(self): return self.visible
    def hide(self): self.visible = False
    def show_all(self): self.visible = True
    def set_keep_above(self, _value): pass
    def present(self): self.focused = True
    def grab_focus(self): self.focused = True
    def get_window(self): return self
    def has_toplevel_focus(self): return self.focused
    def is_active(self): return self.focused
    def _schedule_dynamic_resize(self, _delay): pass
    def _tick_once(self): return False
    def record_runtime(self): self.updates.append(self.visible)

glib = FakeGLib()
namespace = {"GLib": glib, "time": time, "CFG": {"stay_open": False}}
exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE), "exec"), namespace)
window = FakeWindow()
for name in required:
    setattr(window, name, namespace[name].__get__(window, FakeWindow))

# First click opens the window and creates a focus-transfer grace interval.
window._toggle_visibility()
assert window.get_visible()
assert window._focus_guard_until > time.monotonic()
# WM focus hand-off during the guard must not instantly close it.
window._on_focus_out()
assert window.get_visible() and window._focus_hide_src != 0
first_focus_check = window._focus_hide_src
# The WM has now delivered focus; the delayed initial check must preserve the popup.
window._focus_guard_until = time.monotonic() - 1
window.focused = True
glib.run(first_focus_check)
assert window.get_visible()

# A genuine later focus loss closes the resident window after the debounce.
window.focused = False
window._on_focus_out()
pending = window._focus_hide_src
assert pending and pending in glib.callbacks
glib_result = glib.run(pending)
assert not window.get_visible()
assert window.updates[-1] is False

# A queued focus-out from the previous visibility generation must not close a
# newly reopened popup after a fast double-click.
window._toggle_visibility()
assert window.get_visible()
window._focus_guard_until = time.monotonic() - 1
window.focused = False
window._on_focus_out()
stale_id = window._focus_hide_src
assert stale_id
window._toggle_visibility()  # hide; cancels the delayed focus close
window._toggle_visibility()  # reopen, new generation
assert window.get_visible()
assert stale_id not in glib.callbacks

# The explicit stay-open preference disables auto-hide.
namespace["CFG"]["stay_open"] = True
window._on_focus_out()
assert window.get_visible() and window._focus_hide_src == 0
print("FOCUS-TOGGLE-LOGIC-OK")
