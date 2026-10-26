#!/usr/bin/env python3
"""Exercise the GTK page-routing methods without creating a display."""
import ast
from pathlib import Path
from types import MethodType, SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "macos-control-center"
tree = ast.parse(SOURCE.read_text())
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ControlCenter")
methods = {node.name: node for node in klass.body if isinstance(node, ast.FunctionDef)}
namespace = {"Gtk": SimpleNamespace(Label=lambda **kw: SimpleNamespace(**kw)), "T": lambda key: key}
exec(compile(ast.Module(body=[methods["_navigate_page"], methods["_detail_toggle"]], type_ignores=[]), str(SOURCE), "exec"), namespace)


class Stack:
    def __init__(self):
        self.page = "main"

    def set_visible_child_name(self, page):
        self.page = page


class List:
    def get_children(self):
        return []

    def remove(self, *_args):
        return None

    def pack_start(self, *_args):
        return None

    def show_all(self):
        return None


class Label:
    def set_text(self, *_args):
        return None


def center():
    obj = SimpleNamespace(
        _content_stack=Stack(), _schedule_dynamic_resize=lambda *_: None,
        _detail_head=Label(), _detail_set_msg=lambda *_: None,
        _detail_reload=lambda: None, _network_list=List(),
        _DETAIL_HEAD={"wifi": "Wi-Fi", "bt": "Bluetooth", "vpn": "VPN"},
    )
    obj._navigate_page = MethodType(namespace["_navigate_page"], obj)
    obj._detail_toggle = MethodType(namespace["_detail_toggle"], obj)
    return obj


cc = center()
for mode, page in (("wifi", "detail"), ("bt", "detail"), ("vpn", "detail"),
                   ("sound", "sound"), ("network", "network")):
    cc._detail_toggle(mode)
    assert cc._content_stack.page == page, (mode, cc._content_stack.page)
    cc._navigate_page("main")
    assert cc._content_stack.page == "main"
cc._detail_toggle("wifi")
cc._navigate_page("main")
cc._detail_toggle("sound")
cc._navigate_page("main")
assert cc._content_stack.page == "main"

worker = ast.get_source_segment(SOURCE.read_text(), methods["_detail_worker"])
apply = ast.get_source_segment(SOURCE.read_text(), methods["_detail_fill"])
assert "_navigate_page" not in worker and "_navigate_page" not in apply
print("MAIN-WIFI-BACK-SOUND-BACK-NETWORK-BACK-OK")
