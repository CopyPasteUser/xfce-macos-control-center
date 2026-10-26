#!/usr/bin/env python3
"""Command-aware hardware and actual callback regressions (no hardware writes)."""
import ast
import contextlib
import io
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace as NS, MethodType

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
tree = ast.parse(SOURCE.read_text())
names = {"_command_result", "_bluetooth_error_status", "bluetooth_state", "bluetooth_set_power", "diagnose"}
ns = dict(subprocess=subprocess, logging=logging, os=os, sys=sys, re=re, time=time, json=json,
          which=lambda name: name in ("bluetoothctl", "rfkill", "gdbus"))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names],
                        type_ignores=[]), str(SOURCE), "exec"), ns)


class Bluetooth:
    def __init__(self, *, powered=False, soft=False, hard=False, service=True,
                 adapter=True, hidden=False, failure=None):
        self.powered, self.soft, self.hard = powered, soft, hard
        self.service, self.adapter, self.hidden = service, adapter, hidden
        self.failure, self.calls = failure, []
    def __call__(self, command, **kwargs):
        assert 0 < kwargs["timeout"] <= 8
        self.calls.append(command)
        output, code = "", 0
        if command == ["bluetoothctl", "list"]:
            if self.service and self.adapter and not (self.hidden and self.soft):
                output = "Controller 00:11:22:33:44:55 Adapter [default]\n"
        elif command == ["bluetoothctl", "show"]:
            output = "Powered: " + ("yes" if self.powered else "no") + "\n"
        elif command[0] == "gdbus":
            assert "--system" in command and command[-1] == "org.bluez"
            output = "(true,)" if self.service else "(false,)"
        elif command == ["rfkill", "list", "bluetooth"]:
            output = f"0: platform: Bluetooth\nSoft blocked: {'yes' if self.soft else 'no'}\nHard blocked: {'yes' if self.hard else 'no'}\n"
        elif command == ["rfkill", "unblock", "bluetooth"]:
            assert not self.hard
            self.soft = False
        elif command[:2] == ["bluetoothctl", "power"]:
            assert self.service and self.adapter and not self.soft and not self.hard
            if self.failure == "timeout": raise subprocess.TimeoutExpired(command, 8)
            if self.failure == "semantic": output = "Failed to set power on: org.bluez.Error.Failed"
            elif self.failure == "permission": output, code = "org.bluez.Error.NotAuthorized", 1
            elif self.failure != "unchanged": self.powered = command[-1] == "on"
        else:
            raise AssertionError("Unexpected or privileged command: " + repr(command))
        return NS(stdout=output, stderr="", returncode=code)


for options, target, expected in [
    ({}, True, "ready"), ({"powered": True}, False, "ready"),
    ({"soft": True}, True, "ready"),
    ({"soft": True, "hidden": True}, True, "ready"),
    ({"hard": True}, True, "blocked"),
    ({"adapter": False}, True, "adapter_unavailable"),
    ({"service": False}, True, "service"),
    ({"failure": "timeout"}, True, "timeout"),
    ({"failure": "semantic"}, True, "error"),
    ({"failure": "unchanged"}, True, "error"),
    ({"failure": "permission"}, True, "permission"),
]:
    backend = Bluetooth(**options)
    result = ns["bluetooth_set_power"](target, runner=backend)
    assert result["status"] == expected, (options, result)
    if expected == "ready": assert backend.powered is target
    if options.get("hidden"):
        assert backend.calls.index(["rfkill", "unblock", "bluetooth"]) < backend.calls.index(["bluetoothctl", "power", "on"])
    if expected in ("blocked", "service", "adapter_unavailable"):
        assert not any(c[:2] == ["bluetoothctl", "power"] for c in backend.calls)

methods = {n.name: n for n in next(n for n in tree.body if isinstance(n, ast.ClassDef)
                                  and n.name == "ControlCenter").body if isinstance(n, ast.FunctionDef)}
class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ControlCenter")
method_names = [n.name for n in class_node.body if isinstance(n, ast.FunctionDef)]
assert len(method_names) == len(set(method_names)), "Duplicate methods silently override runtime callbacks"
# Exercise the real click -> Thread target -> backend -> GLib -> UI path.
for name in ("on_bt", "_bt_worker", "_bt_apply_result"):
    exec(compile(ast.Module(body=[methods[name]], type_ignores=[]), str(SOURCE), "exec"), ns)
class ImmediateThread:
    def __init__(self, target, args=(), **kwargs): self.target, self.args = target, args
    def start(self): self.target(*self.args)
ns["threading"] = NS(Thread=ImmediateThread)
ns["GLib"] = NS(idle_add=lambda fn, *args: fn(*args))
ns["T"] = lambda value: value
backend = Bluetooth()
ns["bluetooth_power_impl"] = ns["bluetooth_set_power"]
ns["bluetooth_set_power"] = lambda enabled: ns["bluetooth_power_impl"](enabled, runner=backend)
labels, sensitivity, toasts = [], [], []
ui = NS(_bt_pending=False, _bt_generation=0, _st={"bt": False}, _destroyed=False,
        btn_bt=(NS(set_sensitive=sensitivity.append), None, NS(set_text=labels.append)),
        _flip=lambda *_: None, _toast=lambda text, **kwargs: toasts.append(text))
for name in ("on_bt", "_bt_worker", "_bt_apply_result"):
    setattr(ui, name, MethodType(ns[name], ui))
ui.on_bt(None)
assert backend.powered and ui._st["bt"] and not ui._bt_pending and toasts[-1] == "on"
ui.on_bt(None)
assert not backend.powered and not ui._st["bt"] and not ui._bt_pending and toasts[-1] == "off"
assert sensitivity == [False, True, False, True]
backend = Bluetooth(soft=True, hidden=True)
ui._st.clear()  # no adapter/Powered value was available at initial polling
ui.on_bt(None)
assert backend.powered and ui._st["bt"] and not ui._bt_pending
for name in ("_apply", "_detail_complete"):
    exec(compile(ast.Module(body=[methods[name]], type_ignores=[]), str(SOURCE), "exec"), ns)
ns["GLib"] = NS(get_monotonic_time=lambda: 0)
ns["T"] = lambda value: value
updates = []
app = NS(_destroyed=False, _bt_pending=False, _bt_generation=2, _updating=False,
         _chg=lambda *args: updates.append(args) or True, btn_ns=None, _hold=1,
         _bat_lab=None, _specs=[])
apply = MethodType(ns["_apply"], app)
apply({"bt": {"status": "ready", "powered": False}, "_bt_generation": 1, "_partial": True})
assert not updates
app._bt_pending = True
apply({"bt": {"status": "ready", "powered": False}, "_bt_generation": 2, "_partial": True})
assert not updates

effects = []
page = NS(_detail_jobs={"wifi"}, _destroyed=False, _current_page="main", _detail_mode="wifi",
          _detail_generation=3, _detail_reload=lambda: effects.append("reload"),
          _detail_fill=lambda *args: effects.append("fill"))
complete = MethodType(ns["_detail_complete"], page)
complete("wifi", 1, [])
assert not effects and not page._detail_jobs
page._current_page = "detail"
complete("wifi", 1, [])
assert effects == ["reload"]
complete("wifi", 3, [])
assert effects == ["reload", "fill"]
page._destroyed = True
complete("wifi", 3, [])
assert effects == ["reload", "fill"]
print("BLUETOOTH-REALISTIC-CLI-SEMANTICS-HIDDEN-SOFTBLOCK-AND-READBACK-OK")
print("STALE-POLL-PAGE-LEAVE-REENTRY-DESTROYED-CALLBACKS-OK")

# Every completion below must return before touching destroyed GTK widgets.
for name, args in {
    "_vpn_done": (([], ""), True), "_wifi_done": ("network", "ok"),
    "_pw_done": ("network", "ok", 1), "_kbd_level_done": (1, False),
    "_dnd_done": (True, True, True), "_tiles_refresh_apply": ({},),
    "_plane_done": (True,), "_pp_done": ("balanced",),
    "_inp_done": ("tpad", True), "_rot_done": (("output", "normal"),),
    "_nightshift_done": (True,), "_wake_done": (True,),
}.items():
    exec(compile(ast.Module(body=[methods[name]], type_ignores=[]), str(SOURCE), "exec"), ns)
    assert MethodType(ns[name], NS(_destroyed=True))(*args) is False
password_page = NS(_destroyed=False, _pw_generation=5, _pw_ssid="same-network")
assert MethodType(ns["_pw_done"], password_page)("same-network", "ok", 4) is False
print("DESTROYED-WIDGET-AND-PASSWORD-REENTRY-GUARDS-OK")
