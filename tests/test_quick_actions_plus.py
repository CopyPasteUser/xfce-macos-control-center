#!/usr/bin/env python3
"""Static regression checks for the clean icon rail and optional quick actions."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "macos-control-center"
text = path.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(path))
assignments = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = node.value
keys = ast.literal_eval(assignments["QUICK_ACTION_KEYS"])
new_keys = {
    "shotmenu", "home", "downloads", "files", "terminal", "clipboard",
    "network_settings", "bluetooth_manager", "sound_settings", "power_settings",
    "keyboard_settings", "mouse_settings", "notify_settings", "dnd",
    "app_finder", "screenshots", "show_desktop", "xfce_settings",
}
assert new_keys <= set(keys), f"Neue Aktionen fehlen: {new_keys - set(keys)}"
assert len(new_keys) >= 10
strings = ast.literal_eval(assignments["STR"])
for key in (
    "quick_screenshot", "quick_home", "quick_downloads", "quick_files", "quick_terminal",
    "quick_clipboard", "quick_network", "quick_bluetooth", "quick_sound",
    "quick_power_settings", "quick_keyboard", "quick_mouse", "quick_notify_settings",
    "quick_dnd", "quick_app_finder", "quick_screenshots", "quick_show_desktop",
    "quick_xfce_settings", "dnd_on", "dnd_off", "power_confirm_tip", "power_sleep",
    "power_restart", "power_shutdown", "power_logout", "power_screen_off",
):
    assert key in strings and len(strings[key]) == 5, f"Übersetzung unvollständig: {key}"

for icon in ("grid", "settings", "home", "folder", "download", "terminal", "clipboard",
             "network", "btdevice", "sound", "moon", "restart", "logout", "display_off",
             "mouse", "bell", "apps", "desktop"):
    assert f'"{icon}": _svg' in text, f"SVG fehlt: {icon}"

assert 'add("shot", T("quick_screenshot")' not in text, "Screenshot soll nur als Quick Action, nicht in der unteren Leiste erscheinen"
assert 'dict(key="shotmenu", svg="camera", title=T("quick_screenshot")' in text
assert 'add("power", T("act_power")' in text
assert 'add("tiles", T("customize_tiles")' in text
assert 'add("settings", T("settings_title")' in text
assert 'add("lock"' not in text and 'add("mc"' not in text
assert 'MISSION_CENTER_CMD' not in text
assert '"act_lock":' not in text
assert 'def _power_icon_action(' in text and 'def _fill_power(self):' in text
power = text[text.index('    def _fill_power(self):'):text.index('    def _conf_item(', text.index('    def _fill_power(self):'))]
assert 'self._power_icon_action' in power
assert 'self._item(' not in power, "Energiemenü verwendet noch Text-Aktionszeilen"
assert 'def _settings_candidates(key):' in text
assert 'def notification_dnd_state()' in text
assert 'color=(ACCENT if initial_on else _inactive_icon_color())' in text
assert 'rgba(10,132,255,0.17)' in text
print("QUICK-ACTIONS-PLUS-OK")
print("ICON-RAIL-OK")
print("POWER-ICON-MENU-OK")
print("MONOCHROME-ACCENT-STATE-OK")
