#!/usr/bin/env python3
"""Regression tests for the release's media/network/actions and utility features."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "macos-control-center"
text = source.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(source))
assignments = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node.value

version = ast.literal_eval(assignments["APP_VERSION"])
assert version == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert version == "2.1.0"

keys = ast.literal_eval(assignments["QUICK_ACTION_KEYS"])
assert {"quick_notes", "storage_analyzer", "fan_control", "shotmenu", "kbd_light"} <= set(keys)
translations = ast.literal_eval(assignments["STR"])
required_strings = (
    "network_dns", "media_thumbnail_help", "quick_notes", "notes_new", "notes_delete",
    "storage_title", "storage_mode_folders", "storage_mode_largest", "storage_mode_types",
    "storage_cancel", "storage_export_csv", "fan_control", "fan_read_only",
    "fan_refresh", "fan_export_csv", "fan_history_temp", "fan_history_rpm",
    "theme_midnight", "theme_graphite", "theme_frosted", "theme_light",
    "accent_blue", "accent_purple", "accent_teal", "accent_pink", "accent_red",
    "accent_orange", "accent_yellow", "accent_green", "accent_graphite",
    "setting_theme", "setting_accent", "setting_language", "setting_media_card",
    "setting_animation_speed", "language_auto", "language_de", "language_en",
    "language_it", "language_fr", "language_es", "animation_smooth", "animation_fast",
    "animation_off", "kbd_off", "kbd_on", "kbd_bright", "kbd_cycle_tip",
)
for key in required_strings:
    assert key in translations and len(translations[key]) == 5, f"Missing/incomplete translation: {key}"

center = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ControlCenter")
methods = {n.name: n for n in center.body if isinstance(n, ast.FunctionDef)}
def method_text(name):
    assert name in methods, "Missing method: " + name
    return ast.get_source_segment(text, methods[name])

# Screenshot stays available as a tile, but is removed from the bottom icon rail.
assert '_build_header(root)' not in text
actions = method_text("_build_actions")
assert 'add("shot"' not in actions and 'add("lock"' not in actions and 'add("mc"' not in actions
assert 'add("power"' in actions and 'add("tiles"' in actions and 'add("settings"' in actions
assert 'dict(key="shotmenu", svg="camera", title=T("quick_screenshot")' in text

# Direct Control Center pickers/settings and keyboard accessibility.
for method in ("_fill_theme_options", "_fill_accent_options", "_fill_language_options",
               "_fill_animation_options", "_select_setting", "_select_language",
               "_settings_group", "_settings_choice", "_settings_toggle",
               "_fill_settings", "_fill_diag", "_copy_diagnostics"):
    assert method in methods, f"Missing settings/diagnostics method: {method}"
assert "_focus_guard_until = time.monotonic() + 0.75" in text
assert "def _force_show(self)" in text and "def _force_hide(self)" in text
assert "signal.SIGUSR2, on_hide_signal" in text

# Keyboard backlight is a single cyclic tile, not a standalone row of confusing controls.
assert 'dict(' in text and 'key="kbd_light", svg="kbd_light"' in text
assert 'def _cycle_kbd_level(self):' in text
assert 'def _read_kbd_action_level(self):' in text
assert 'def _apply_kbd_action_level(self, level):' in text
assert 'self._keyboard_module(kp)' not in text
assert 'root.pack_start(self.kbd_mod' not in text
assert 'KBD_DIR and self._kbd_max > 0' in text

# Media displays player-provided cover art and timeline data where available.
media_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "media_info")
media_source = ast.get_source_segment(text, media_fn)
assert '{{mpris:artUrl}}' in media_source and '{{mpris:length}}' in media_source
assert '"playerctl", "position"' in media_source
assert "self._m_progress.set_fraction" in method_text("_set_media")
assert 'set_size_request(56, 56)' in method_text("_build_media")
assert "self._media_controls.append(b)" in method_text("_build_media")
assert "button.set_sensitive(False)" in method_text("_set_media")
assert "self._m_progress_row.hide()" in method_text("_set_media")
# Runtime visibility and persistence are exercised by test_preferences_runtime.py.
assert 'CFG.get("media_progress", True)' in method_text("_set_media")
assert "_media_cover_worker" in methods and "_format_media_time" in methods

# Wi-Fi details expose IP, gateway, DNS and reuse already-fetched connection data.
summary = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "wifi_connection_summary")
summary_src = ast.get_source_segment(text, summary)
assert '"IP4.DNS"' in summary_src and "networks=None" in summary_src
assert 'wifi_connection_summary(networks)' in method_text("_detail_worker")
assert '"network_dns"' in method_text("_detail_fill")

# Multi-note storage is atomic/private, supports create/delete/list and legacy migration.
for name in ("notes_storage_dir", "_canonical_note_id", "save_quick_note", "delete_quick_note", "list_quick_notes"):
    assert any(isinstance(node, ast.FunctionDef) and node.name == name for node in tree.body), name
save_note_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "save_quick_note")
save_note_src = ast.get_source_segment(text, save_note_fn)
assert 'os.fchmod(fd, 0o600)' in save_note_src and 'os.replace(tmp, path)' in save_note_src
assert 'selector.connect("changed", select_note)' in method_text("_open_quick_notes")
assert 'Gdk.KEY_s' in method_text("_open_quick_notes")

# Storage analyzer has folder-depth, largest-file and type aggregation modes with cancel and export.
scan_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_scan_storage")
scan_src = ast.get_source_segment(text, scan_fn)
for marker in ('"folders", "largest", "types"', '"-x"', '"--max-depth=', 'followlinks=False', 'cancel_event', 'timeout'):
    assert marker in scan_src, f"Storage safety/performance marker missing: {marker}"
storage_ui = method_text("_open_storage_analyzer")
for marker in ("storage_mode_largest", "storage_mode_types", "cancel_scan", "export_csv", "open_selected", "copy_selected"):
    assert marker in storage_ui, f"Storage UI feature missing: {marker}"

# Fan tooling is a read-only hardware monitor and delegates actual control to CoolerControl.
assert 'dict(key="fan_control"' in text
sensors_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_read_hwmon_sensors")
sensor_src = ast.get_source_segment(text, sensors_fn)
assert 'fan*_input' in sensor_src and 'temp*_input' in sensor_src
assert '"minimum"' in sensor_src and '"maximum"' in sensor_src and '"critical"' in sensor_src
assert 'pwm' not in sensor_src.lower(), "Fan monitor must not write PWM controls"
fan_ui = method_text("_open_fan_control")
for marker in ('coolercontrol', 'fan_export_csv', 'fan_history_temp', 'refresh_async', 'threading.Thread'):
    assert marker in fan_ui, f"Fan monitor feature missing: {marker}"

# Launcher must route visible state to explicit hide rather than always sending show.
launcher = (ROOT / "macos-control-center-toggle").read_text(encoding="utf-8")
assert 'runtime_visibility "$pid"' in launcher
assert 'signal_name=USR2' in launcher and 'signal_name=USR1' in launcher
assert 'state.get("visible"), bool' in launcher
assert '"visible": bool(visible)' in text

# Non-negotiable LocalSend sandbox preserved.
localsend = ast.literal_eval(assignments["LOCALSEND_CMD"])
assert localsend == ["flatpak", "run", "--nofilesystem=/mnt/medien", "org.localsend.localsend_app"]
print("PRODUCT-FEATURES-OK")
print("MEDIA-PREVIEW-OK")
print("NETWORK-DETAILS-OK")
print("SETTINGS-PICKERS-OK")
print("MULTI-NOTES-STORAGE-FAN-OK")
print("KEYBOARD-LIGHT-QUICK-ACTION-OK")
print("TOGGLE-SHOW-HIDE-CONTRACT-OK")
