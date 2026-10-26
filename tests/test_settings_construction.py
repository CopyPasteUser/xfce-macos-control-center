#!/usr/bin/env python3
"""Execute the actual settings constructors, not source-string assertions.

The headless widget double checks parenting and signals. With an available
display the identical scenario additionally uses real GTK widgets and Stack.
"""
import ast
import logging
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
schema = runpy.run_path(str(ROOT / "tests/test_settings_themes.py"))
ns = schema["namespace"].copy()
tree = schema["tree"]
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ControlCenter")
names = {"_settings_group", "_settings_separator", "_settings_choice", "_settings_toggle",
         "_fill_settings", "_fill_theme_options", "_fill_accent_options",
         "_act_toggle", "_act_close", "_act_fill"}
methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]


class Widget:
    def __init__(self, **kwargs):
        self.children, self.signals, self.parent = [], {}, None
        self.reveal = False
    def add(self, child):
        assert child.parent is None, "widget already parented"
        self.children.append(child)
        child.parent = self
    def pack_start(self, child, *_args): self.add(child)
    pack_end = pack_start
    def remove(self, child):
        self.children.remove(child)
        child.parent = None
    def get_children(self): return list(self.children)
    def connect(self, signal, callback):
        self.signals[signal] = callback
        return len(self.signals)
    def clicked(self): self.signals["clicked"](self)
    def set_reveal_child(self, value): self.reveal = value
    def get_reveal_child(self): return self.reveal
    def get_style_context(self): return self
    def get_accessible(self): return self
    def __getattr__(self, name):
        if name.startswith(("set_", "add_class", "remove_class", "override_", "show_all", "parse")):
            return lambda *_args: None
        raise AttributeError(name)


fake_gtk = SimpleNamespace(**{key: Widget for key in ("Box", "Button", "Label", "EventBox", "Separator", "Switch", "Revealer")},
    Image=SimpleNamespace(new_from_icon_name=lambda *_: Widget()),
    Orientation=SimpleNamespace(VERTICAL=1, HORIZONTAL=0), Align=SimpleNamespace(CENTER=0),
    ReliefStyle=SimpleNamespace(NONE=0), StateFlags=SimpleNamespace(NORMAL=0), IconSize=SimpleNamespace(MENU=0))


def scenario(gtk, gdk, real=False):
    ns.update(Gtk=gtk, Gdk=gdk, CFG=dict(schema["values"]["DEFAULT_CONFIG"]),
              T=lambda key, **kwargs: key, APP_VERSION="test", logging=logging,
              GLib=SimpleNamespace(timeout_add=lambda *_: 0))
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(ROOT / "macos-control-center"), "exec"), ns)
    Harness = type("SettingsHarness", (), {name: ns[name] for name in names})
    app = Harness()
    app._act_list, app._act_rev = gtk.Box(), gtk.Revealer()
    app._act_rev.add(app._act_list)
    app._act_mode, app._act_btns, app.POLL_SECONDS = None, {}, 10
    for name in ("_clear_confirm", "_clear_power_confirmation", "_schedule_dynamic_resize", "_shrink",
                 "_toggle_compact_setting", "_toggle_media_card", "_toggle_media_thumbnail",
                 "_toggle_reduce_motion", "_toggle_stay_open", "_cycle_poll_interval", "_head"):
        setattr(app, name, lambda *_: None)
    app._animation_duration = lambda value: 0
    def item(text, callback):
        button = gtk.Button(label=text) if real else gtk.Button()
        button.connect("clicked", lambda *_: callback())
        app._act_list.pack_start(button, False, False, 0)
    app._item = item
    errors = []
    app._toast = lambda message, **kwargs: errors.append(message)
    button = gtk.Button()
    button.connect("clicked", lambda *_: app._act_toggle("settings"))
    if real:
        stack, main = gtk.Stack(), gtk.Box()
        main.add(button)
        main.add(app._act_rev)
        stack.add_named(main, "main")
        stack.show_all()
        stack.set_visible_child_name("main")
    for _ in range(5):
        button.clicked()
        assert not errors and app._act_rev.get_reveal_child()
        assert len(app._act_list.get_children()) > 5
        if real:
            assert stack.get_child_by_name("main") is main
            assert stack.get_visible_child_name() == "main"
        app._act_list.get_children()[0].clicked()  # actual Back signal
        assert app._act_mode is None and not app._act_rev.get_reveal_child()
    for mode in ("settings_theme", "settings_accent"):
        app._act_toggle(mode)
        assert not errors and app._act_rev.get_reveal_child()
        app._act_close()
    # Constructor failures must print a traceback and leave navigation reusable.
    original = app._fill_settings
    app._fill_settings = lambda: (_ for _ in ()).throw(ValueError("preview constructor failure"))
    with patch.object(logging, "exception") as log:
        button.clicked()
        log.assert_called_once()
    assert errors and not app._act_rev.get_reveal_child()
    errors.clear()
    app._fill_settings = original
    button.clicked()
    assert not errors and app._act_rev.get_reveal_child()
    if real: stack.destroy()


scenario(fake_gtk, SimpleNamespace(RGBA=Widget))
print("SETTINGS-CONSTRUCTION-PREVIEWS-SIGNALS-BACK-REOPEN-ERROR-RECOVERY-OK")
from gi.repository import Gtk, Gdk
if Gtk.init_check()[0]:
    scenario(Gtk, Gdk, real=True)
    print("SETTINGS-REAL-GTK-STACK-REGISTRATION-OK")
else:
    print("SKIP: real GTK Settings/Stack integration requires an accessible display")
