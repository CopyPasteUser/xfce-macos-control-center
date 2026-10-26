#!/usr/bin/env python3
"""Preference -> persistence -> live media visibility using actual methods."""
import ast
import runpy
import tempfile
from pathlib import Path
from types import MethodType, SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
schema = runpy.run_path(str(ROOT / "tests/test_settings_themes.py"))
ns = schema["namespace"].copy()
cfg = ns["CFG"] = dict(ns["DEFAULT_CONFIG"], media_thumbnail=False)
ns["T"] = lambda key: key
ns["Gtk"] = NS(IconSize=NS(MENU=0))
ns["GLib"] = NS(timeout_add=lambda *_: 0)
methods = {n.name: n for n in next(n for n in schema["tree"].body if isinstance(n, ast.ClassDef)
                                  and n.name == "ControlCenter").body if isinstance(n, ast.FunctionDef)}
for name in ("_save_setting", "_toggle_preference", "_set_media", "_toast"):
    exec(compile(ast.Module(body=[methods[name]], type_ignores=[]), "preferences", "exec"), ns)

class Widget:
    def __init__(self): self.visible, self.text = True, ""
    def get_visible(self): return self.visible
    def set_visible(self, value): self.visible = value
    def show(self): self.visible = True
    def hide(self): self.visible = False
    def set_text(self, text): self.text = text
    def __getattr__(self, name):
        if name.startswith("set_"): return lambda *_: None
        raise AttributeError(name)

app = NS(_media_box=Widget(), _m_progress_row=Widget(), _m_title=Widget(), _m_artist=Widget(),
         _m_time=Widget(), _m_progress=Widget(), _m_play_img=Widget(), _media_controls=[Widget()],
         _m_art_url=None, _m_art_generation=0, _reset_media_cover=lambda:None,
         _schedule_dynamic_resize=lambda *_:None, _act_fill=lambda:None,
         _format_media_time=lambda value:str(value), _toast=lambda *a, **kw:None,
         _last={"media": ("Track", "Artist", True, "", 15, 60)})
for name in ("_save_setting", "_toggle_preference", "_set_media"):
    setattr(app, name, MethodType(ns[name], app))
with tempfile.TemporaryDirectory() as directory:
    ns["CONFIG_DIR"], ns["CONFIG_FILE"] = directory, str(Path(directory) / "config.json")
    app._set_media(app._last["media"])
    assert app._m_progress_row.visible
    assert app._toggle_preference("media_progress")
    assert not app._m_progress_row.visible
    assert ns["load_config"]()["media_progress"] is False
    assert app._toggle_preference("media_hide_idle")
    app._set_media(None)
    assert not app._media_box.visible
    app._set_media(app._last["media"])
    assert app._media_box.visible and app._m_title.text == "Track"
    assert app._toggle_preference("feedback")
    assert ns["load_config"]()["feedback"] is False
    # With success feedback disabled, errors must still reach the toast widget.
    toast = NS(_toast_label=Widget(), _toast_src=0,
               _toast_box=NS(get_style_context=lambda:NS(add_class=lambda *_:None, remove_class=lambda *_:None)),
               _toast_revealer=Widget(), _animation_duration=lambda value:value,
               _schedule_dynamic_resize=lambda *_:None, _hide_toast=lambda:None)
    MethodType(ns["_toast"], toast)("success")
    assert toast._toast_label.text == ""
    MethodType(ns["_toast"], toast)("error", error=True)
    assert toast._toast_label.text == "error"
    for key in ("media_progress", "media_hide_idle", "feedback"):
        assert ns["_cfg_value"](key, "false") is None
    before = dict(cfg)
    ns["_persist_config"] = lambda value:False
    assert app._toggle_preference("media_progress") is False
    assert cfg == before
print("PREFERENCES-PERSISTENCE-MEDIA-LIVE-VISIBILITY-FEEDBACK-ROLLBACK-OK")
