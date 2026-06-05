import ctypes
from dataclasses import dataclass


@dataclass(frozen=True)
class HostResourceSnapshot:
    free_ram_mb: int


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ('dwLength', ctypes.c_ulong),
        ('dwMemoryLoad', ctypes.c_ulong),
        ('ullTotalPhys', ctypes.c_ulonglong),
        ('ullAvailPhys', ctypes.c_ulonglong),
        ('ullTotalPageFile', ctypes.c_ulonglong),
        ('ullAvailPageFile', ctypes.c_ulonglong),
        ('ullTotalVirtual', ctypes.c_ulonglong),
        ('ullAvailVirtual', ctypes.c_ulonglong),
        ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
    ]


def host_resource_snapshot():
    status = _MemoryStatus()
    status.dwLength = ctypes.sizeof(_MemoryStatus)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    return HostResourceSnapshot(free_ram_mb=int(status.ullAvailPhys / (1024 * 1024)))


def can_claim_slot(config, slot_number):
    snapshot = host_resource_snapshot()
    if snapshot.free_ram_mb < config.pause_all_if_free_ram_mb_lt:
        return False, snapshot, 'pause_all_low_ram'
    if slot_number == 2 and snapshot.free_ram_mb < config.pause_slot2_if_free_ram_mb_lt:
        return False, snapshot, 'pause_slot2_low_ram'
    return True, snapshot, ''
