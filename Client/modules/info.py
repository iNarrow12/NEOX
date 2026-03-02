import psutil
import platform
import getpass
import socket
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/api/info")

# Filesystem types that are virtual/not real disks
VIRTUAL_FS = {
    'tmpfs', 'devtmpfs', 'devfs', 'overlay', 'aufs', 'squashfs',
    'proc', 'sysfs', 'cgroup', 'cgroup2', 'pstore', 'bpf',
    'tracefs', 'debugfs', 'securityfs', 'fusectl', 'hugetlbfs',
    'mqueue', 'ramfs', 'efivarfs', 'configfs', 'fuse.portal'
}

@router.get("/all")
async def get_all_info():
    cpu = {
        "percent": psutil.cpu_percent(interval=0.5),
        "cores": psutil.cpu_count(logical=False),
        "freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0
    }
    mem = psutil.virtual_memory()
    ram = {
        "total": round(mem.total / (1024**3), 2),
        "used": round(mem.used / (1024**3), 2),
        "free": round(mem.free / (1024**3), 2),
        "percent": mem.percent
    }

    disk = []
    seen = set()
    for part in psutil.disk_partitions(all=False):
        if part.fstype.lower() in VIRTUAL_FS:
            continue
        if part.device.startswith('/dev/loop'):
            continue
        if part.mountpoint in seen:
            continue
        seen.add(part.mountpoint)
        try:
            usage = psutil.disk_usage(part.mountpoint)
            if usage.total < 100 * 1024 * 1024:
                continue
            disk.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": round(usage.total / (1024**3), 2),
                "used": round(usage.used / (1024**3), 2),
                "free": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except (PermissionError, OSError):
            pass

    net = psutil.net_io_counters()
    os_info = {
        "platform": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "username": getpass.getuser(),
        "boot": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")
    }
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "network": {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv},
        "os": os_info
    }

@router.get("/processes")
async def get_processes():
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            procs.append({
                "pid": p.info['pid'],
                "name": p.info['name'],
                "cpu_percent": round(p.info['cpu_percent'] or 0, 1),
                "memory_percent": round(p.info['memory_percent'] or 0, 1),
                "status": p.info['status']
            })
        except:
            continue
    procs.sort(key=lambda x: x['cpu_percent'], reverse=True)
    return procs[:20]