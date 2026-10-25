#!/usr/bin/env python3
"""Isolierter Test für Update, Daemon-Neustart-Logik und Desktop-Einträge."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
source_text = SOURCE.read_text(encoding="utf-8")
version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert f'APP_VERSION = "{version}"' in source_text
main_block = source_text[source_text.index("def main():"):source_text.index('if __name__ == "__main__":')]
assert main_block.index("GLib.unix_signal_add(") < main_block.index('with open(PIDFILE, "w", encoding="ascii")')
assert 'def on_show_signal():' in main_block
assert 'def on_hide_signal():' in main_block
assert 'signal.SIGUSR1, on_show_signal' in main_block
assert 'signal.SIGUSR2, on_hide_signal' in main_block
assert 'GLib.idle_add(publish_ready)' in main_block, "Runtime-Bereitschaft erst in der GTK-Hauptschleife melden"
assert 'runtime state' in main_block.lower() or 'publish_ready' in main_block
assert "Application version: " + version in source_text or 'T("diag_version", v=APP_VERSION)' in source_text
assert (ROOT / "update.sh").is_file()
assert "cc_stop_control_center_instances" in (ROOT / "install.sh").read_text(encoding="utf-8")
assert "cc_start_and_show_control_center" in (ROOT / "install.sh").read_text(encoding="utf-8")
installer_text = (ROOT / "install.sh").read_text(encoding="utf-8")
assert '[[ ! -f "$HERE/macos-control-center" || ! -r "$HERE/macos-control-center" ]]' in installer_text
assert 'install -m 0755 "$HERE/macos-control-center" "$STAGED_APP"' in installer_text

with tempfile.TemporaryDirectory(prefix="cc-update-test-") as temp:
    base = Path(temp)
    home = base / "Home with spaces"
    data = base / "XDG Data with spaces"
    config = base / "XDG Config with spaces"
    runtime = base / "Runtime"
    bindir = base / "XDG Bin with spaces"
    stubbin = base / "stubs"
    for folder in (home, data, config, runtime, bindir, stubbin):
        folder.mkdir(parents=True, exist_ok=True)

    # Fake only the system GTK import preflight. It does not fake the application,
    # filesystem operations, update process handling, desktop files or backups.
    fake_python = stubbin / "python3"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${1:-}" == "-c" ]]; then exit 0; fi\n'
        'exec /usr/bin/python3 "$@"\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    # Regression: some GUI archive managers strip the executable bit from the
    # Python entrypoint. The installer must still accept a readable source file
    # and set 0755 on the persistent installed copy itself.
    mode_loss = base / "zip extracted without executable bits"
    (mode_loss / "scripts").mkdir(parents=True)
    for rel in (
        "install.sh", "update.sh", "macos-control-center", "macos-control-center-toggle",
        "VERSION", "uninstall.sh", "status.sh",
    ):
        shutil.copy2(ROOT / rel, mode_loss / rel)
    (mode_loss / "assets").mkdir(parents=True)
    shutil.copy2(ROOT / "assets" / "macos-control-center.svg", mode_loss / "assets" / "macos-control-center.svg")
    shutil.copy2(ROOT / "scripts" / "daemon-lifecycle.sh", mode_loss / "scripts" / "daemon-lifecycle.sh")
    (mode_loss / "install.sh").chmod(0o644)
    (mode_loss / "update.sh").chmod(0o644)
    (mode_loss / "macos-control-center").chmod(0o644)
    (mode_loss / "macos-control-center-toggle").chmod(0o644)
    (mode_loss / "scripts" / "daemon-lifecycle.sh").write_text(
        "#!/usr/bin/env bash\n"
        "cc_stop_control_center_instances() { return 0; }\n"
        "cc_start_and_show_control_center() { return 0; }\n",
        encoding="utf-8",
    )
    mode_env = os.environ.copy()
    mode_env.update({
        "HOME": str(base / "Mode-loss Home"),
        "XDG_DATA_HOME": str(base / "Mode-loss Data"),
        "XDG_CONFIG_HOME": str(base / "Mode-loss Config"),
        "XDG_RUNTIME_DIR": str(base / "Mode-loss Runtime"),
        "XDG_BIN_HOME": str(base / "Mode-loss Bin"),
        "PATH": str(stubbin) + os.pathsep + "/usr/bin:/bin",
    })
    for key in ("HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR", "XDG_BIN_HOME"):
        Path(mode_env[key]).mkdir(parents=True, exist_ok=True)
    mode_install = subprocess.run(
        ["bash", str(mode_loss / "update.sh"), "--no-start"],
        cwd=mode_loss, env=mode_env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
    )
    assert mode_install.returncode == 0, mode_install.stdout
    mode_installed = Path(mode_env["XDG_DATA_HOME"]) / "macos-control-center" / "app" / "macos-control-center"
    assert mode_installed.is_file() and os.access(mode_installed, os.X_OK), mode_install.stdout
    assert mode_installed.read_bytes() == (mode_loss / "macos-control-center").read_bytes()
    print("ZIP-MODE-LOSS-UPDATE-OK")

    env = os.environ.copy()
    env.update({
        "HOME": str(home),
        "XDG_DATA_HOME": str(data),
        "XDG_CONFIG_HOME": str(config),
        "XDG_RUNTIME_DIR": str(runtime),
        "XDG_BIN_HOME": str(bindir),
        "PATH": str(stubbin) + os.pathsep + "/usr/bin:/bin",
    })
    config_dir = config / "macos-control-center"
    config_dir.mkdir(parents=True)
    sentinel = config_dir / "config.json"
    sentinel.write_text('{"vpn_preferred":"simon","poll_seconds":10}\n', encoding="utf-8")

    # First install into isolated XDG locations. The no-start option prevents GTK
    # from being launched in the test environment (where PyGObject may be absent).
    install = subprocess.run(
        ["bash", str(ROOT / "install.sh"), "--no-start"],
        cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=30,
    )
    assert install.returncode == 0, install.stdout
    assert "Installation/Aktualisierung erfolgreich (Daemon-Start mit --no-start ausdrücklich übersprungen)." in install.stdout
    assert "prüfe jetzt den Daemon-Start" in install.stdout

    app_root = data / "macos-control-center"
    app = app_root / "app" / "macos-control-center"
    app_version = app_root / "app" / "VERSION"
    desktop = data / "applications" / "macos-control-center.desktop"
    autostart = config / "autostart" / "macos-control-center-resident.desktop"
    toggle = bindir / "macos-control-center-toggle"
    assert app.is_file() and os.access(app, os.X_OK)
    assert app_version.read_text(encoding="utf-8").strip() == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert desktop.is_file() and autostart.is_file() and toggle.is_file()
    assert (app_root / "scripts" / "macos-control-center-toggle").is_file()
    assert (app_root / "assets" / "macos-control-center.svg").is_file()
    normal_wrapper = (bindir / "macos-control-center").read_text(encoding="utf-8")
    assert '"--daemon"' in normal_wrapper and 'scripts/macos-control-center-toggle' in normal_wrapper
    assert 'exec "' + str(app_root / "scripts" / "macos-control-center-toggle") + '" "$@"' in toggle.read_text(encoding="utf-8")
    assert (app_root / "status.sh").is_file()
    assert (app_root / "doctor.sh").is_file()
    desktop_text = desktop.read_text(encoding="utf-8")
    assert 'Exec="' + str(toggle) + '"' in desktop_text
    assert "Categories=Settings;\n" in desktop_text
    assert "Categories=Settings;Utility;" not in desktop_text
    assert "--daemon" in autostart.read_text(encoding="utf-8")
    assert sentinel.read_text(encoding="utf-8") == '{"vpn_preferred":"simon","poll_seconds":10}\n'

    # Simulate a resident process launched from an older source checkout path.
    # Update must find it even when the PID file is the only normal hint.
    legacy_dir = base / "legacy checkout"
    legacy_dir.mkdir()
    fake_app = legacy_dir / "macos-control-center"
    fake_app.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(90)\n", encoding="utf-8")
    fake_app.chmod(0o755)
    legacy = subprocess.Popen([sys.executable, str(fake_app), "--daemon"])
    try:
        for _ in range(50):
            if Path(f"/proc/{legacy.pid}/cmdline").exists():
                break
            time.sleep(0.05)
        (runtime / "macos-control-center.pid").write_text(str(legacy.pid), encoding="ascii")

        update = subprocess.run(
            ["bash", str(ROOT / "update.sh"), "--no-start"],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=30,
        )
        assert update.returncode == 0, update.stdout
        assert "Beende laufende Control-Center-Instanz" in update.stdout, update.stdout
        assert "Aktualisierung erfolgreich" in update.stdout, update.stdout
        assert "Release im Archiv:" in update.stdout, update.stdout
        legacy.wait(timeout=3)
        assert not (runtime / "macos-control-center.pid").exists()
        assert app.read_bytes() == (ROOT / "macos-control-center").read_bytes()
        backups = list((app_root / "backups").glob("macos-control-center.*"))
        assert backups, "Vorherige Version wurde nicht gesichert"
        assert sentinel.read_text(encoding="utf-8") == '{"vpn_preferred":"simon","poll_seconds":10}\n'

        status = subprocess.run(
            ["bash", str(ROOT / "status.sh")],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=15,
        )
        assert status.returncode == 0, status.stdout
        assert "Release-Datei:" in status.stdout
        assert "installierte Datei sind identisch" in status.stdout

        # Test the exact production start helper with a lightweight fake GTK process.
        # It writes the same runtime metadata contract before handling SIGUSR1.
        toggle_marker = base / "toggle-signal-received.txt"
        (legacy_dir / "VERSION").write_text(version + "\n", encoding="utf-8")
        fake_app.write_text(            "#!/usr/bin/env python3\n"
            "import json, os, signal, sys, time\n"
            "from pathlib import Path\n"
            "def on_toggle(*args):\n"
            "    Path(os.environ['CC_TEST_TOGGLE_MARKER']).write_text(str(os.getpid()), encoding='utf-8')\n"
            "signal.signal(signal.SIGUSR1, on_toggle)\n"
            "pidfile = os.environ['CC_PIDFILE']\n"
            "statefile = os.environ['CC_STATEFILE']\n"
            "Path(pidfile).write_text(str(os.getpid()), encoding='ascii')\n"
            "version = Path(__file__).with_name('VERSION').read_text(encoding='utf-8').strip()\n"
            "Path(statefile).write_text(json.dumps({'pid': os.getpid(), 'version': version, 'script': str(Path(__file__).resolve()), 'resident': True, 'visible': False, 'started_at': 'test'}), encoding='utf-8')\n"
            "while True: time.sleep(0.05)\n",
            encoding='utf-8',
        )
        fake_app.chmod(0o755)
        marker_env = env.copy()
        marker_env.update({
            "CC_TEST_TOGGLE_MARKER": str(toggle_marker),
            "CC_LIFECYCLE": str(ROOT / "scripts" / "daemon-lifecycle.sh"),
            "CC_FAKE_APP": str(fake_app),
            "CC_APP_ROOT": str(app_root),
        })
        starter = subprocess.run(
            ["bash", "-c", 'source "$CC_LIFECYCLE"; cc_start_and_show_control_center "$CC_FAKE_APP" "$CC_APP_ROOT" show; for n in $(seq 1 20); do [[ -f "$CC_TEST_TOGGLE_MARKER" ]] && break; sleep 0.05; done; [[ -f "$CC_TEST_TOGGLE_MARKER" ]] || exit 7; cc_stop_control_center_instances; echo LIFECYCLE-START-SHOW-OK'],
            cwd=ROOT, env=marker_env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=20,
        )
        assert starter.returncode == 0, starter.stdout
        assert "LIFECYCLE-START-SHOW-OK" in starter.stdout, starter.stdout
        assert toggle_marker.exists()
        assert not (runtime / "macos-control-center.pid").exists()
        assert not (runtime / "macos-control-center.pid.state.json").exists()

        # Uninstaller preserves configuration and leaves no stale resident process.
        uninstall = subprocess.run(
            ["bash", str(ROOT / "uninstall.sh")],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=30,
        )
        assert uninstall.returncode == 0, uninstall.stdout
        assert not app.exists()
        assert not (app_root / "scripts" / "macos-control-center-toggle").exists()
        assert not (app_root / "assets" / "macos-control-center.svg").exists()
        assert not desktop.exists()
        assert not autostart.exists()
        assert not (app_root / "status.sh").exists()
        assert not (app_root / "doctor.sh").exists()
        assert sentinel.exists(), "Benutzerkonfiguration darf nicht entfernt werden"
        assert backups, "Recovery-Backups dürfen bei normaler Deinstallation erhalten bleiben"
    finally:
        if legacy.poll() is None:
            legacy.terminate()
            try:
                legacy.wait(timeout=2)
            except subprocess.TimeoutExpired:
                legacy.kill()
                legacy.wait(timeout=2)

print("INSTALL-UPDATE-LIFECYCLE-OK")
