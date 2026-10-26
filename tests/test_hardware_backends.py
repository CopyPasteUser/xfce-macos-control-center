#!/usr/bin/env python3
"""Mocked regressions for audio discovery/selection and BlueZ power control."""
import ast
import json
import re
import subprocess
import logging
import time
import sys
from pathlib import Path
from types import MethodType, SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "macos-control-center"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
function_names = {
    "_command_result", "discover_audio_outputs", "set_audio_output",
    "_bluetooth_error_status", "bluetooth_state", "bluetooth_set_power",
    "volume_pct", "sink_muted", "mic_muted",
}
functions = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in function_names]
namespace = {"subprocess": subprocess, "json": json, "re": re, "os": __import__("os"),
             "logging": logging, "time": time, "sys": sys,
             "which": lambda name: "/usr/bin/" + name}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
discover = namespace["discover_audio_outputs"]
set_output = namespace["set_audio_output"]
bt_state = namespace["bluetooth_state"]
bt_power = namespace["bluetooth_set_power"]


class Runner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, command, **_kwargs):
        self.calls.append(command)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def result(stdout="", stderr="", code=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=code)


available_both = lambda _name: True
available_pactl = lambda name: name == "pactl"
available_bt = lambda name: name in ("bluetoothctl", "rfkill")


# Audio: PipeWire's Pulse compatibility service via pactl.
success = Runner([result(stdout='[{"name":"alsa_output.pci","description":"Built-in Audio"}]'),
                  result(stdout="alsa_output.pci\n"),
                  result(stdout="Server Name: PulseAudio (on PipeWire 1.2.7)\n")])
found = discover(runner=success, available=available_pactl)
assert found["status"] == "ready" and found["default"] == "alsa_output.pci"
assert found["devices"][0]["description"] == "Built-in Audio"
assert found["server"] == "PipeWire via PulseAudio"

def pipewire_read(*command):
    if command[:2] == ("pactl", "get-sink-volume"):
        return ""
    if command[:2] == ("wpctl", "get-volume"):
        return "Volume: 0.42 [MUTED]"
    return ""

namespace["shc"] = pipewire_read
assert namespace["volume_pct"]() == 42
assert namespace["sink_muted"]() is True
assert namespace["mic_muted"]() is True

empty = discover(runner=Runner([result(stdout="[]"), result(stdout="")]), available=available_pactl)
assert empty["status"] == "empty"
authoritative_empty = Runner([result(stdout="[]"), result()])
assert discover(runner=authoritative_empty, available=available_both)["status"] == "empty"
assert all(call[0] == "pactl" for call in authoritative_empty.calls)
for malformed in ('{}', '[{"name": []}]', '[null]'):
    assert discover(runner=Runner([result(stdout=malformed)]), available=available_pactl)["status"] == "error"
assert discover(runner=Runner([result(stdout="unexpected status format")]),
                available=lambda name:name == "wpctl")["status"] == "error"
missing_default = discover(runner=Runner([result(stdout='[{"name":"sink-a"}]'),
                                         result(stderr="No default sink", code=1)]),
                           available=available_pactl)
assert missing_default["status"] == "error"

failed = discover(runner=Runner([result(stderr="invalid request", code=1),
                                 result(stderr="Malformed status", code=2)]),
                  available=available_both)
assert failed["status"] == "error"
backend_unavailable = discover(runner=Runner([result(stderr="Connection refused", code=1),
                                               result(stderr="Could not connect to PipeWire", code=2)]),
                               available=available_both)
assert backend_unavailable["status"] == "backend_unavailable"

timed_out = discover(runner=Runner([subprocess.TimeoutExpired("pactl", 4)]),
                     available=available_pactl)
assert timed_out["status"] == "timeout"
assert discover(runner=Runner([]), available=lambda _name: False)["status"] == "unavailable"

# Native PipeWire fallback parses numeric IDs and the default marker.
fallback = discover(runner=Runner([result(stderr="Pulse unavailable", code=1),
                                   result(stdout="Audio\n ├─ Devices:\n │  48. Built-in Audio\n ├─ Sinks:\n │  * 52. Built-in Audio [vol: 0.5]\n │    53. HDMI [vol: 0.4]\n ├─ Sources:\n │  54. Mic\n")]),
                    available=available_both)
assert fallback["status"] == "ready" and fallback["backend"] == "wpctl"
assert fallback["default"] == "52" and len(fallback["devices"]) == 2

# Device switching checks command success and rereads the selected default.
switched = Runner([result(), result(),
                   result(stdout='[{"name":"alsa_output.usb","description":"USB Audio"}]'),
                   result(stdout="alsa_output.usb\n"), result(stdout="Server Name: PulseAudio\n")])
assert set_output({"id": "alsa_output.usb", "backend": "pactl"}, runner=switched)
assert switched.calls[0] == ["pactl", "set-default-sink", "alsa_output.usb"]
pipewire_switched = Runner([result(), result(stdout="Audio\n ├─ Sinks:\n │    52. Other\n │  * 60. USB Output [vol: 0.5]\n ├─ Sources:\n")])
assert set_output({"id": "60", "backend": "wpctl"}, runner=pipewire_switched)
assert pipewire_switched.calls[0] == ["wpctl", "set-default", "60"]
assert not set_output({"id": "52", "backend": "wpctl"}, runner=Runner([result(code=1)]))


def bt_runner(powered, action=None, rfkill=None):
    outputs = [result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
               result(stdout="Powered: " + ("yes" if powered else "no") + "\n")]
    if action is not None:
        if rfkill is not None:
            outputs.append(rfkill)
        outputs.extend([action,
                        result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                        result(stdout="Powered: " + ("yes" if action.returncode == 0 and action.stdout == "ON" else "no") + "\n")])
    return Runner(outputs)


# Bluetooth ON/OFF require a verified post-command Powered state.
namespace["which"] = available_bt
on_runner = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                    result(stdout="0: hci0: Bluetooth\n Soft blocked: no\n Hard blocked: no\n"),
                    result(stdout="ON"), result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                    result(stdout="Powered: yes\n")])
assert bt_power(True, runner=on_runner)["powered"] is True
assert ["bluetoothctl", "power", "on"] in on_runner.calls

off_runner = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: yes\n"),
                     result(stdout="OFF"), result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                     result(stdout="Powered: no\n")])
assert bt_power(False, runner=off_runner)["powered"] is False

unverified_on = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                        result(stdout="0: hci0: Bluetooth\n Soft blocked: no\n Hard blocked: no\n"),
                        result(stdout="Command accepted"), result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                        result(stdout="Powered: no\n")])
verified = bt_power(True, runner=unverified_on)
assert verified["status"] == "error" and verified["powered"] is False

unavailable = bt_state(runner=Runner([result()]))
assert unavailable["status"] == "adapter_unavailable"

soft_blocked = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                       result(stdout="0: hci0: Bluetooth\n Soft blocked: yes\n Hard blocked: no\n"),
                       result(), result(stdout="ON"),
                       result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                       result(stdout="Powered: yes\n")])
assert bt_power(True, runner=soft_blocked)["powered"] is True
assert ["rfkill", "unblock", "bluetooth"] in soft_blocked.calls

hard_blocked = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                       result(stdout="0: hci0: Bluetooth\n Soft blocked: no\n Hard blocked: yes\n")])
assert bt_power(True, runner=hard_blocked)["status"] == "blocked"

backend_failure = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                         result(stdout="0: hci0: Bluetooth\n Soft blocked: no\n Hard blocked: no\n"),
                         result(stderr="Permission denied", code=1),
                         result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                         result(stdout="Powered: no\n")])
assert bt_power(True, runner=backend_failure) == {"status": "permission", "powered": False}

service_failure = bt_state(runner=Runner([result(stderr="Failed to connect to bus", code=1)]))
assert service_failure["status"] == "service"
bt_timeout = Runner([result(stdout="Controller 00:11:22:33:44:55 Adapter\n"), result(stdout="Powered: no\n"),
                    result(stdout="0: hci0: Bluetooth\n Soft blocked: no\n Hard blocked: no\n"),
                    subprocess.TimeoutExpired("bluetoothctl", 8),
                    result(stdout="Controller 00:11:22:33:44:55 Adapter\n"),
                    result(stdout="Powered: yes\n")])
assert bt_power(True, runner=bt_timeout) == {"status": "timeout", "powered": True}

late_methods = {node.name: node for node in next(n for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == "ControlCenter").body
                if isinstance(node, ast.FunctionDef)}
late_ns = {"T": lambda key: key, "which": lambda _name: True}
for name in ("_audio_refresh_apply", "_bt_apply_result"):
    exec(compile(ast.Module(body=[late_methods[name]], type_ignores=[]), str(SOURCE), "exec"), late_ns)
late_audio = SimpleNamespace(_audio_generation=3, _destroyed=False, _out_apply=lambda _v: (_ for _ in ()).throw(AssertionError("stale audio applied")))
assert MethodType(late_ns["_audio_refresh_apply"], late_audio)(2, {}) is False
applied = []
current_audio = SimpleNamespace(_audio_generation=3, _audio_refreshing=True, _destroyed=False,
                                _out_apply=applied.append)
assert MethodType(late_ns["_audio_refresh_apply"], current_audio)(3, {"status": "empty"}) is False
assert current_audio._audio_refreshing is False and applied == [{"status": "empty"}]
late_bt = SimpleNamespace(_bt_generation=3, _destroyed=False)
assert MethodType(late_ns["_bt_apply_result"], late_bt)(2, True, {}) is False

init_source = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), late_methods["__init__"])
assert "self._refresh_audio_outputs()" in init_source, "Audio discovery must not depend on a quick-action tile"

print("AUDIO-DISCOVERY-SUCCESS-EMPTY-ERROR-TIMEOUT-AND-SELECTION-OK")
print("BLUETOOTH-ON-OFF-UNAVAILABLE-SOFT-HARD-BLOCK-AND-ERROR-OK")
print("LATE-HARDWARE-RESULTS-IGNORED-OK")
