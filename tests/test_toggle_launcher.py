#!/usr/bin/env python3
"""Integration test for the self-healing launcher and explicit resident show/hide toggle."""
from pathlib import Path
import os
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "macos-control-center-toggle"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert HELPER.is_file()

with tempfile.TemporaryDirectory(prefix="cc-toggle-test-") as td:
    base = Path(td)
    home = base / "Home with spaces"
    data = base / "Data with spaces"
    runtime = base / "Runtime with spaces"
    for folder in (home, data, runtime):
        folder.mkdir(parents=True, exist_ok=True)
    app_root = data / "macos-control-center"
    app_dir = app_root / "app"
    scripts = app_root / "scripts"
    app_dir.mkdir(parents=True)
    scripts.mkdir(parents=True)
    app = app_dir / "macos-control-center"
    (app_dir / "VERSION").write_text(VERSION + "\n", encoding="utf-8")
    marker = base / "toggle-count.txt"
    fake_code = '''#!/usr/bin/env python3
import json, os, signal, sys, time
from pathlib import Path
pidfile = Path(os.environ["CC_PIDFILE"])
statefile = Path(os.environ["CC_STATEFILE"])
marker = Path(os.environ["CC_TEST_MARKER"])
version = Path(__file__).with_name("VERSION").read_text(encoding="utf-8").strip()
def record_signal(visible):
    # Publish state before the marker, so the test marker means the state write
    # has completed (matching the production atomic runtime-state contract).
    try:
        state = json.loads(statefile.read_text(encoding="utf-8"))
        state["visible"] = visible
        tmp = statefile.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        tmp.replace(statefile)
    except (OSError, ValueError): pass
    try: count = int(marker.read_text(encoding="ascii"))
    except (OSError, ValueError): count = 0
    marker.write_text(str(count + 1), encoding="ascii")
def on_show(_sig, _frame): record_signal(True)
def on_hide(_sig, _frame): record_signal(False)
def on_term(_sig, _frame): raise SystemExit(0)
signal.signal(signal.SIGUSR1, on_show)
signal.signal(signal.SIGUSR2, on_hide)
signal.signal(signal.SIGTERM, on_term)
pidfile.write_text(str(os.getpid()), encoding="ascii")
statefile.write_text(json.dumps({"pid":os.getpid(),"version":version,"script":str(Path(sys.argv[0]).resolve()),"resident":True,"visible":False,"started_at":"test"}), encoding="utf-8")
try:
    while True: time.sleep(0.05)
finally:
    try:
        if int(pidfile.read_text(encoding="ascii")) == os.getpid(): pidfile.unlink()
    except (OSError, ValueError): pass
    try:
        state=json.loads(statefile.read_text(encoding="utf-8"))
        if state.get("pid") == os.getpid(): statefile.unlink()
    except (OSError, ValueError): pass
'''
    app.write_text(fake_code, encoding="utf-8")
    app.chmod(0o755)
    shutil.copy2(HELPER, scripts / "macos-control-center-toggle")
    (scripts / "macos-control-center-toggle").chmod(0o755)

    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_DATA_HOME": str(data),
        "XDG_RUNTIME_DIR": str(runtime),
        "CC_TEST_MARKER": str(marker),
    })
    pidfile = runtime / "macos-control-center.pid"
    statefile = runtime / "macos-control-center.pid.state.json"
    log_path = app_root / "logs" / "daemon.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # Production log rotation: a large previous log is rotated on daemon start.
    log_path.write_bytes(b"x" * (1024 * 1024 + 128))
    # Deliberately simulate a stale PID left by a crashed daemon.
    pidfile.write_text("987654321\n", encoding="ascii")

    def invoke():
        return subprocess.run(
            ["bash", str(scripts / "macos-control-center-toggle")],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=15,
        )

    first = invoke()
    assert first.returncode == 0, first.stdout
    assert "bereit und geöffnet" in first.stdout, first.stdout
    assert pidfile.is_file() and statefile.is_file()
    assert (app_root / "logs" / "daemon.log.1").is_file(), "großes Log wurde nicht rotiert"
    assert log_path.stat().st_size < 4096, "aktives Log wurde nicht neu angelegt"
    first_pid = int(pidfile.read_text(encoding="ascii").strip())

    for _ in range(40):
        if marker.exists() and marker.read_text(encoding="ascii") == "1":
            break
        time.sleep(0.025)
    assert marker.is_file() and marker.read_text(encoding="ascii") == "1"
    assert json.loads(statefile.read_text(encoding="utf-8"))["visible"] is True

    second = invoke()
    assert second.returncode == 0, second.stdout
    assert "umgeschaltet" in second.stdout, second.stdout
    assert int(pidfile.read_text(encoding="ascii").strip()) == first_pid, "zweiter Klick hat Duplikat gestartet"
    for _ in range(40):
        if marker.read_text(encoding="ascii") == "2":
            break
        time.sleep(0.025)
    assert marker.read_text(encoding="ascii") == "2", "zweiter Klick hat kein Hide-Signal zugestellt"
    assert json.loads(statefile.read_text(encoding="utf-8"))["visible"] is False

    # Clean up fake resident so tests don't leave any background process.
    os.kill(first_pid, signal.SIGTERM)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            os.kill(first_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)

    # Regression: a daemon from an older source checkout must not be toggled
    # by the installed starter. It must be replaced with the selected release.
    old_checkout = home / "Old project checkout"
    old_checkout.mkdir(parents=True, exist_ok=True)
    old_app = old_checkout / "macos-control-center"
    (old_checkout / "VERSION").write_text("0.9.9\n", encoding="utf-8")
    old_app.write_text(fake_code, encoding="utf-8")
    old_app.chmod(0o755)
    old_marker = base / "old-toggle-count.txt"
    try:
        marker.unlink()
    except FileNotFoundError:
        pass
    old_env = env.copy()
    old_env["CC_TEST_MARKER"] = str(old_marker)
    old_env["CC_PIDFILE"] = str(pidfile)
    old_env["CC_STATEFILE"] = str(statefile)
    old_proc = subprocess.Popen(
        [sys.executable, str(old_app), "--daemon"], cwd=old_checkout,
        env=old_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        ready_deadline = time.monotonic() + 4
        while time.monotonic() < ready_deadline:
            if pidfile.exists() and statefile.exists():
                try:
                    if int(pidfile.read_text(encoding="ascii").strip()) == old_proc.pid:
                        break
                except (OSError, ValueError):
                    pass
            time.sleep(0.025)
        assert pidfile.exists() and int(pidfile.read_text(encoding="ascii").strip()) == old_proc.pid
        old_state = json.loads(statefile.read_text(encoding="utf-8"))
        assert Path(old_state["script"]).resolve() == old_app.resolve()

        replaced = invoke()
        assert replaced.returncode == 0, replaced.stdout
        assert "bereit und geöffnet" in replaced.stdout, replaced.stdout
        new_pid = int(pidfile.read_text(encoding="ascii").strip())
        new_state = json.loads(statefile.read_text(encoding="utf-8"))
        assert new_pid != old_proc.pid, "veralteter Checkout wurde weiterverwendet"
        assert Path(new_state["script"]).resolve() == app.resolve()
        assert new_state["version"] == VERSION
        assert not old_marker.exists(), "alter Daemon hat Toggle-Signal erhalten"
        for _ in range(40):
            if marker.exists() and marker.read_text(encoding="ascii") == "1":
                break
            time.sleep(0.025)
        assert marker.exists() and marker.read_text(encoding="ascii") == "1"
        os.kill(new_pid, signal.SIGTERM)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if not Path(f"/proc/{new_pid}").exists():
                break
            time.sleep(0.05)
        print("TOGGLE-REPLACES-OLD-CHECKOUT-OK")
    finally:
        try:
            old_proc.terminate()
            old_proc.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                old_proc.kill()
            except ProcessLookupError:
                pass
    print("TOGGLE-SELF-HEAL-OK")
    print("TOGGLE-SECOND-CLICK-OK")
