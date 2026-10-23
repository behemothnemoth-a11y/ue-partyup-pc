"""Read Windows' default multimedia output without changing audio settings."""
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import uuid


class GUID(ctypes.Structure):
    _fields_ = [('data', ctypes.c_ubyte * 16)]

    @classmethod
    def parse(cls, value):
        result = cls()
        result.data[:] = uuid.UUID(value).bytes_le
        return result


def default_endpoint_id():
    if sys.platform != 'win32':
        raise RuntimeError('Windows audio output inspection is available on Windows only.')
    ole = ctypes.OleDLL('ole32')
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    initialized = ole.CoInitializeEx(None, 0)
    if initialized < 0 and initialized != -2147417850:  # RPC_E_CHANGED_MODE
        raise OSError(f'Audio COM initialization failed ({initialized}).')
    enumerator, device = ctypes.c_void_p(), ctypes.c_void_p()
    text = ctypes.c_void_p()
    def invoke(pointer, index, *types):
        table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *types)(table[index])
    def check(code):
        if code < 0:
            raise OSError(f'Windows audio query failed ({code}).')
    try:
        clsid = GUID.parse('BCDE0395-E52F-467C-8E3D-C4579291692E')
        iid = GUID.parse('A95664D2-9614-4F35-A746-DE8DB63617E6')
        ole.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        check(ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(enumerator)))
        check(invoke(enumerator, 4, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))(
            enumerator, 0, 1, ctypes.byref(device)))  # render / multimedia
        check(invoke(device, 5, ctypes.POINTER(ctypes.c_void_p))(device, ctypes.byref(text)))
        return ctypes.wstring_at(text)
    finally:
        if text:
            ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
            ole.CoTaskMemFree(text)
        for pointer in (device, enumerator):
            if pointer:
                invoke(pointer, 2)(pointer)
        if initialized >= 0:
            ole.CoUninitialize()


def inspect_audio_route(host_address, guest_addresses):
    """Compare device containers, never names alone. Per-app overrides are unknown."""
    endpoint = default_endpoint_id()
    # Endpoint ID comes from Windows, and is passed as an argument rather than code.
    script = r'''
param($endpoint)
$id='SWD\MMDEVAPI\'+$endpoint
$device=Get-PnpDevice -InstanceId $id -ErrorAction Stop
$container=(Get-PnpDeviceProperty -InstanceId $id -KeyName 'DEVPKEY_Device_ContainerId' -ErrorAction Stop).Data
$addresses=@(Get-PnpDevice -Class Bluetooth -ErrorAction Stop | Where-Object { $_.InstanceId -match 'DEV_([0-9A-Fa-f]{12})' } | ForEach-Object {
  $candidate=$_
  $match=[regex]::Match($candidate.InstanceId,'DEV_([0-9A-Fa-f]{12})')
  $other=(Get-PnpDeviceProperty -InstanceId $candidate.InstanceId -KeyName 'DEVPKEY_Device_ContainerId' -ErrorAction SilentlyContinue).Data
  if($other -eq $container){$match.Groups[1].Value}
})
@{name=$device.FriendlyName; addresses=$addresses} | ConvertTo-Json -Compress
'''
    # Use a temporary script-free command with a single fixed PowerShell expression.
    # The endpoint is validated against Windows' documented ID shape before quoting.
    import re
    if not re.fullmatch(r'\{[0-9.]+\}\.\{[0-9A-Fa-f-]+\}', endpoint):
        raise RuntimeError('Unrecognized Windows endpoint identity; route not inferred.')
    command = '& { ' + script + " } '" + endpoint + "'"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, timeout=25,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Windows could not resolve the audio endpoint container.')
    data = json.loads(result.stdout)
    addresses = {int(value, 16) for value in data.get('addresses', [])}
    role = 'main' if host_address in addresses else 'guest' if addresses.intersection(guest_addresses) else 'other'
    return {'name': data.get('name', 'Unknown output'), 'role': role}
