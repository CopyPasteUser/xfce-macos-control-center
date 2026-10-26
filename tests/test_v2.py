#!/usr/bin/env python3
"""Behavior tests: real threads and data, no GTK/network/hardware side effects."""
import ast
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import types
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'macos-control-center').read_text())
functions = {n.name:n for n in tree.body if isinstance(n, ast.FunctionDef)}
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ControlCenter')
methods = {n.name:n for n in cls.body if isinstance(n, ast.FunctionDef)}
ns = dict(globals())
for name in ('_validate_devices', '_magic_packet', '_resource_policy', '_action_category', '_filter_actions', '_system_snapshot'):
    exec(compile(ast.Module(body=[functions[name]], type_ignores=[]), '<helpers>', 'exec'), ns)

def method(name):
    exec(compile(ast.Module(body=[methods[name]], type_ignores=[]), '<method>', 'exec'), ns)
    return ns[name]

validate=ns['_validate_devices']
valid={'name':'NAS','url':'http://nas.home.arpa:5000/','mac':'00:11:22:33:44:55','broadcast':'192.168.1.255'}
assert validate([valid]) == [valid]
assert validate([]) == []
assert validate([dict(valid, url='https://[::1]/')])
for field, bad in [('url','file:///etc/passwd'), ('url','javascript:alert(1)'), ('url','https://u:p@example.org/'),
                   ('url','http://example.org:99999'), ('url','http://['), ('url','http://bad host/'),
                   ('mac','00:11:22:33:44'), ('mac','$(touch /tmp/no)'), ('broadcast','example.org'),
                   ('name','\n'), ('name','x'*65)]:
    assert validate([dict(valid, **{field:bad})]) is None, (field,bad)
assert validate([dict(valid,url='',mac='')]) is None
assert validate([valid]*31) is None
packet=ns['_magic_packet']('00:11:22:33:44:55')
assert len(packet)==102 and packet[:6]==b'\xff'*6 and packet[6:]==bytes.fromhex('001122334455')*16
assert ns['_magic_packet']('00-11-22-33-44-55')==packet
for key, seconds, max_workers in [('light',30,2),('balanced',10,4),('responsive',3,8)]:
    assert ns['_resource_policy'](key,cores=64)==(seconds,max_workers)
    assert ns['_resource_policy'](key,cores=1)[1]==2
assert ns['_resource_policy']('custom',cores=4,custom_seconds=17)==(17,4)
print('V2-DEVICE-VALIDATION-WOL-PROFILES-OK')

specs=[dict(key='quick_notes',title='Kurznotizen'),dict(key='devices',title='Meine Geräte'),dict(key='mic',title='Mikrofon')]
filter_actions=ns['_filter_actions']
assert filter_actions(specs,'GERÄTE')==[specs[1]]
assert filter_actions(specs, category='tools')==[specs[0]]
assert filter_actions(specs, category='device')==[specs[2]]
assert filter_actions(specs,'not-found')==[]
assert len(filter_actions(specs*5, compact=True))==8
assert len(filter_actions(specs*5, query='mikro',compact=True))==5
print('V2-ACTION-SEARCH-CATEGORIES-COMPACT-OK')

# Gate one reader, fail another: quick results must be dispatched before the
# slow reader completes, while a failed reader must not drop other results.
release=threading.Event();quick=threading.Event();delivered=[]
class Idle:
    @staticmethod
    def idle_add(callback,*args):
        delivered.append(args[0])
        if 'vol' in args[0]: quick.set()
        return 1
ns.update(GLib=Idle, which=lambda command: True, wifi_on=lambda: True, wifi_ssid=lambda:'Test',
          vpn_state=lambda:([],''), volume_pct=lambda backend=None:37, sink_muted=lambda backend=None:False,
          brightness_pct=lambda:(50,100),kbd_pct=lambda:(None,0),battery=lambda:(None,''),
          battery_extra=lambda:None,nightshift_on=lambda:None,media_info=lambda:None)
def slow():
    assert release.wait(2)
    return {'status':'ready','powered':True}
ns['bluetooth_state']=slow
poll=method('_poll_collect')
with ThreadPoolExecutor(max_workers=4) as pool:
    subject=types.SimpleNamespace(_bt_generation=0,_audio_control_backend='pactl',_poll_executor=pool,btn_ns=None,_specs=[{'key':'broken','read':lambda:1/0}],_apply=lambda d:None)
    result={}
    worker=threading.Thread(target=lambda: result.update(poll(subject,1)))
    worker.start()
    assert quick.wait(1),'fast volume blocked behind Bluetooth'
    assert worker.is_alive(),'slow reader gate not exercised'
    assert any(d.get('vol')==37 for d in delivered)
    release.set();worker.join(2)
    assert not worker.is_alive()
    assert result['_errors']==['broken']
    assert any(d.get('bt',{}).get('powered') is True for d in delivered)
print('V2-POLL-INDEPENDENCE-FAILURE-ISOLATION-OK')

# Apply every sparse result independently, then finish and settle poll state.
class Widget:
    def __init__(self): self.value=None
    def set_text(self,v): self.value=v
    def set_value(self,v): self.value=v
ns.update(GLib=types.SimpleNamespace(get_monotonic_time=lambda:100,idle_add=lambda *a:None),KBD_DIR=None,T=lambda k,**kw:k)
apply=method('_apply')
a=types.SimpleNamespace(_destroyed=False,_updating=False,_polling=True,_poll_errors=[],_poll_ms=0,
  _bt_pending=False,_bt_generation=0,
  _profile_pending=False,_rerun=False,_resident_primed=False,_st={},_hold=0,_muted=False,
  btn_wifi=(None,None,Widget()),btn_bt=(None,None,Widget()),btn_ns=None,bl_mod=None,
  vol_mod=types.SimpleNamespace(scale=Widget()),_bat_lab=None,_specs=[],_last_tt='',
  _chg=lambda *args:True,_flip=lambda *args:None,_vpn_apply=lambda *args:None,
  _refresh_volume_icon=lambda:None,_set_media=lambda *args:None)
for d in delivered:
    apply(a,d)
    assert a._polling,'partial update prematurely released polling guard'
assert a.vol_mod.scale.value==37
assert a._st['wifi'] is True
apply(a,{'_errors':['broken'],'_elapsed_ms':123})
assert not a._polling and a._resident_primed and a._poll_errors==['broken'] and a._poll_ms==123
print('V2-SPARSE-UI-UPDATE-LIFECYCLE-OK')

# Profile switches during polling defer executor replacement to completion.
configure=method('_configure_polling')
a=types.SimpleNamespace(_polling=True,_profile_pending=False)
configure(a)
assert a._profile_pending

# Monotonic deadline, restart cleanup, completion once; no external notification.
ns.update(which=lambda command:False,T=lambda k,**kw:k)
focus_tick=method('_focus_tick')
f=types.SimpleNamespace(_destroyed=False,_focus_deadline=time.monotonic()+120,_focus_source=3,_focus_label=Widget())
assert focus_tick(f) is True and '02:00' in f._focus_label.value
f._focus_deadline=time.monotonic()-1
assert focus_tick(f) is False and f._focus_deadline is None and f._focus_source==0
assert focus_tick(f) is False
print('V2-FOCUS-DEADLINE-COMPLETION-OK')

# Slow brightness service cannot block the UI caller. Intermediate values are
# coalesced, and the final value is actually sent after the first call unblocks.
entered=threading.Event();unblock=threading.Event();completed=threading.Event();written=[]
class Bus:
    def call_sync(self,*args):
        written.append(args[4][1][2])
        assert args[7]==1500
        if len(written)==1:
            entered.set();assert unblock.wait(2)
        else: completed.set()
ns.update(Gio=types.SimpleNamespace(bus_get_sync=lambda *a:Bus(),BusType=types.SimpleNamespace(SYSTEM=1),DBusCallFlags=types.SimpleNamespace(NONE=0)),
          GLib=types.SimpleNamespace(Variant=lambda *a:a,idle_add=lambda *a:None),BACKLIGHT='test')
writer=method('_brightness_worker');submit=method('_apply_brightness')
f=types.SimpleNamespace(_brightness_lock=threading.Lock(),_brightness_pending=None,_brightness_running=False,_bl_max=100,_brightness_failed=lambda:None)
f._brightness_worker=lambda:writer(f)
submit(f,10);assert entered.wait(1)
submit(f,40);submit(f,90)
assert written==[10]
unblock.set();assert completed.wait(1)
assert written==[10,90]
print('V2-BRIGHTNESS-NONBLOCKING-COALESCING-OK')
