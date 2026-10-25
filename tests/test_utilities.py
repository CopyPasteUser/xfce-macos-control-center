#!/usr/bin/env python3
"""Runtime regression tests for notes, storage analysis, and hwmon parsing."""
import ast
import glob
import heapq
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "macos-control-center"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
needed = {
    "notes_storage_dir", "_canonical_note_id", "save_quick_note",
    "delete_quick_note", "list_quick_notes", "_scan_storage",
    "_read_hwmon_sensors",
}
funcs = {
    node.name: node for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in needed
}
assert set(funcs) == needed, f"Missing utility functions: {sorted(needed - set(funcs))}"
ns = {
    "os": os, "glob": glob, "heapq": heapq, "json": json,
    "shutil": shutil, "stat": stat, "subprocess": subprocess,
    "tempfile": tempfile, "time": time, "uuid": uuid,
}
for name in needed:
    exec(compile(ast.Module(body=[funcs[name]], type_ignores=[]), str(SOURCE), "exec"), ns)

# Multi-note persistence, permissions, validation, and legacy migration.
with tempfile.TemporaryDirectory(prefix="cc-notes-test-") as td:
    ns["os"].environ["XDG_DATA_HOME"] = td
    save = ns["save_quick_note"]
    list_notes = ns["list_quick_notes"]
    delete = ns["delete_quick_note"]
    folder = Path(ns["notes_storage_dir"]())

    first_id = save(None, "Projekt", "Erste Notiz")
    second_id = save(None, "Einkauf", "Milch\nBrot")
    notes = list_notes()
    assert len(notes) == 2
    assert {item["title"] for item in notes} == {"Projekt", "Einkauf"}
    assert next(x for x in notes if x["id"] == second_id)["text"] == "Milch\nBrot"
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE((folder / f"{first_id}.json").stat().st_mode) == 0o600
    assert delete(first_id) is True and delete(first_id) is False
    try:
        delete("../../outside")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid note ID was accepted")

# Legacy single-note import when no modern note exists.
with tempfile.TemporaryDirectory(prefix="cc-notes-legacy-") as td:
    ns["os"].environ["XDG_DATA_HOME"] = td
    legacy = Path(td) / "macos-control-center" / "quick-note.txt"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("Legacy note", encoding="utf-8")
    imported = ns["list_quick_notes"]()
    assert len(imported) == 1 and imported[0]["text"] == "Legacy note"

# Storage analyzer: folder totals, largest files, type aggregation, bounds and no symlink traversal.
with tempfile.TemporaryDirectory(prefix="cc-storage-test-") as td:
    base = Path(td)
    (base / "Videos").mkdir()
    (base / "Documents").mkdir()
    (base / "Videos" / "episode.mkv").write_bytes(b"v" * 4096)
    (base / "Videos" / "sample.mp4").write_bytes(b"m" * 1024)
    (base / "Documents" / "notes.txt").write_bytes(b"n" * 256)
    outside = base.parent / (base.name + "-outside")
    outside.mkdir()
    (outside / "not-counted.bin").write_bytes(b"x" * 16384)
    try:
        (base / "outside-link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pass
    scan = ns["_scan_storage"]

    largest = scan(str(base), mode="largest", depth=5, limit=10)
    assert largest["rows"] and largest["rows"][0]["label"].endswith("episode.mkv")
    assert all("not-counted.bin" not in row["label"] for row in largest["rows"])

    types = scan(str(base), mode="types", depth=5, limit=10)
    type_sizes = {row["label"]: row["size"] for row in types["rows"]}
    assert type_sizes[".mkv"] == 4096 and type_sizes[".mp4"] == 1024

    folders = scan(str(base), mode="folders", depth=2, limit=10)
    assert folders["mode"] == "folders"
    assert any(row["label"] == "Videos" and row["size"] >= 5120 for row in folders["rows"])
    assert folders["free"] >= 0 and folders["used"] >= 0

    try:
        scan(str(base), mode="invalid")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid storage scan mode was accepted")
    shutil.rmtree(outside, ignore_errors=True)

# Fan sensor parser reads only; supports sparse/unavailable sysfs entries.
with tempfile.TemporaryDirectory(prefix="cc-hwmon-test-") as td:
    hwmon = Path(td) / "hwmon0"
    hwmon.mkdir()
    def write(name, value):
        (hwmon / name).write_text(str(value), encoding="utf-8")
    write("name", "testchip")
    write("fan1_input", 1240)
    write("fan1_label", "CPU Fan")
    write("fan1_min", 500)
    write("fan1_max", 4000)
    write("temp1_input", 47000)
    write("temp1_label", "CPU Package")
    write("temp1_crit", 95000)
    sensors = ns["_read_hwmon_sensors"](td)
    fan = next(x for x in sensors if x["kind"] == "fan")
    temp = next(x for x in sensors if x["kind"] == "temperature")
    assert fan["value"] == 1240 and fan["minimum"] == 500 and fan["maximum"] == 4000
    assert temp["value"] == 47 and temp["critical"] == 95
    assert all(not key.lower().startswith("pwm") for item in sensors for key in item)

print("MULTI-NOTES-RUNTIME-OK")
print("STORAGE-ANALYZER-RUNTIME-OK")
print("HWMON-PARSER-RUNTIME-OK")
