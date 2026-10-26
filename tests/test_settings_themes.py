#!/usr/bin/env python3
"""Validate persisted settings schema and every GTK3 theme/accent stylesheet."""
import ast
import copy
import json
import os
import re
import tempfile
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
values = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in {"DEFAULT_CONFIG", "_CFG_LANGS", "_CFG_THEMES", "_CFG_ACCENTS",
                    "UI_TOKENS", "THEME_TOKENS", "ACCENT_PALETTE"}:
            value_node = copy.deepcopy(node.value)
            if name == "DEFAULT_CONFIG":
                class ConfigNames(ast.NodeTransformer):
                    def visit_Name(self, value):
                        return ast.copy_location(ast.Constant(value=""), value) if value.id == "VPN_PREFERRED" else value
                value_node = ConfigNames().visit(value_node)
            values[name] = ast.literal_eval(value_node)

namespace = dict(values)
namespace.update({"QUICK_ACTION_KEYS": (), "_validate_devices": lambda value: value,
                  "json": json, "os": os, "tempfile": tempfile, "logging": logging})
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
exec(compile(ast.Module(body=[functions["_cfg_value"]], type_ignores=[]), str(SOURCE), "exec"), namespace)
exec(compile(ast.Module(body=[functions["_persist_config"]], type_ignores=[]), str(SOURCE), "exec"), namespace)
exec(compile(ast.Module(body=[functions["load_config"]], type_ignores=[]), str(SOURCE), "exec"), namespace)

assert namespace["_cfg_value"]("theme", "frosted") == "frosted"
assert namespace["_cfg_value"]("theme", "unknown") is None
assert namespace["_cfg_value"]("accent_color", "orange") == "orange"
assert namespace["_cfg_value"]("accent_color", "unknown") is None
assert namespace["_cfg_value"]("media_card", False) is False
assert namespace["_cfg_value"]("media_card", "false") is None
assert namespace["DEFAULT_CONFIG"]["media_card"] is True
required_tokens = {"window_background", "card_surface", "elevated_surface", "secondary_surface",
                   "border_separator", "primary_text", "secondary_text", "disabled_text",
                   "hover", "pressed", "active_surface", "slider_background",
                   "slider_thumb", "accent_treatment", "focus_treatment"}
assert all(required_tokens <= set(tokens) for tokens in namespace["THEME_TOKENS"].values())

with tempfile.TemporaryDirectory(prefix="cc-settings-test-") as temp:
    namespace["CONFIG_DIR"] = temp
    namespace["CONFIG_FILE"] = str(Path(temp) / "config.json")
    config = dict(namespace["DEFAULT_CONFIG"], theme="frosted", accent_color="orange", media_card=False)
    assert namespace["_persist_config"](config)
    assert json.loads(Path(namespace["CONFIG_FILE"]).read_text()) == config
    assert os.stat(namespace["CONFIG_FILE"]).st_mode & 0o777 == 0o600
    # Old config keys remain valid; unknown theme values fall back independently.
    Path(namespace["CONFIG_FILE"]).write_text(json.dumps({"theme": "old-experiment",
                                                            "accent_color": "cyan",
                                                            "compact_actions": False}))
    namespace["_write_default_config"] = lambda: None
    migrated = namespace["load_config"]()
    assert migrated["theme"] == "midnight" and migrated["accent_color"] == "blue"
    assert migrated["compact_actions"] is False and migrated["media_card"] is True
    assert migrated["resource_profile"] == "custom"
    assert migrated["schema_version"] == 1
    damaged = b'{"theme": "midnight", broken'
    Path(namespace["CONFIG_FILE"]).write_bytes(damaged)
    assert namespace["load_config"]()["theme"] == "midnight"
    assert namespace["_persist_config"](config)
    backups = list(Path(temp).glob("config-corrupt-*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == damaged
    assert backups[0].stat().st_mode & 0o777 == 0o600
    future = '{"schema_version": 99, "future_field": true}'
    Path(namespace["CONFIG_FILE"]).write_text(future)
    assert not namespace["_persist_config"](config)
    assert Path(namespace["CONFIG_FILE"]).read_text() == future

# Evaluate the app's stylesheet template and run it through GTK's actual CSS parser.
ui_node = next(n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "UI_TOKENS" for t in n.targets))
css_node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "CSS" for t in n.targets))
namespace["CSS"] = eval(compile(ast.Expression(css_node.value), str(SOURCE), "eval"), namespace)
theme_fn = functions["_theme_css"]
namespace["re"] = re
exec(compile(ast.Module(body=[functions["_accent_for_theme"], theme_fn], type_ignores=[]),
             str(SOURCE), "exec"), namespace)
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
except (ImportError, ValueError) as exc:
    raise AssertionError("GTK3 CSS parser is required for the theme regression suite") from exc

for theme in namespace["_CFG_THEMES"]:
    for accent in namespace["_CFG_ACCENTS"]:
        css = namespace["_theme_css"](theme, accent)
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        assert css.count("{") == css.count("}")
        assert f"{namespace['THEME_TOKENS'][theme]['window_background']}" in css
        assert namespace["_accent_for_theme"](theme, accent)[0] in css

def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return sum(weight * value for weight, value in zip((0.2126, 0.7152, 0.0722), linear))

for accent in namespace["_CFG_ACCENTS"]:
    color, _rgb = namespace["_accent_for_theme"]("light", accent)
    assert 1.05 / (luminance(color) + 0.05) >= 3.0, accent

assert len({(namespace["UI_TOKENS"]["radius_card"], namespace["UI_TOKENS"]["padding_card"],
             namespace["UI_TOKENS"]["section_gap"], namespace["UI_TOKENS"]["control_height"])
            for _theme in namespace["_CFG_THEMES"]}) == 1

print("SETTINGS-SCHEMA-AND-ATOMIC-PERSISTENCE-OK")
print(f"GTK3-CSS-PARSED-{len(namespace['_CFG_THEMES'])}-THEMES-X-{len(namespace['_CFG_ACCENTS'])}-ACCENTS-OK")
