"""Windows survey without WMI, secrets, or dataset traversal."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import platform
import shutil
import subprocess
import winreg

class Memory(ctypes.Structure):
    _fields_ = [("length", wintypes.DWORD), ("load", wintypes.DWORD)] + [(name, ctypes.c_ulonglong) for name in ("total_physical", "available_physical", "total_pagefile", "available_pagefile", "total_virtual", "available_virtual", "extended")]
class Display(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR*32), ("DeviceString", wintypes.WCHAR*128), ("StateFlags", wintypes.DWORD), ("DeviceID", wintypes.WCHAR*128), ("DeviceKey", wintypes.WCHAR*128)]
root = Path(__file__).resolve().parents[1]
report = {"os": platform.platform(), "python": platform.python_version(), "workspace": str(root)}
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
    report['cpu'] = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
m = Memory(); m.length = ctypes.sizeof(m)
if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
    report['ram_bytes'] = m.total_physical
report['display_adapters'] = []
for i in range(32):
    d = Display(); d.cb = ctypes.sizeof(d)
    if not ctypes.windll.user32.EnumDisplayDevicesW(None, i, ctypes.byref(d), 0): break
    report['display_adapters'].append({'name': d.DeviceString, 'id': d.DeviceID})
report['gpu_driver_cuda_status'] = 'unverified; nvidia-smi unavailable and WMI permission denied'
report['disk_free_bytes'] = shutil.disk_usage(root).free
report['disk_total_bytes'] = shutil.disk_usage(root).total
p = subprocess.run(['uv', '--version'], capture_output=True, text=True)
report['uv'] = p.stdout.strip()
path = root / 'outputs/hardware.json'
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
