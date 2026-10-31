import os
import platform
import time
import psutil
from typing import Dict, Any, List
from apps.agent.app.docker.client import docker_manager

_last_net_io = None
_last_net_time = None

def get_system_info() -> Dict[str, Any]:
    uname = platform.uname()
    return {
        "hostname": uname.node,
        "os_name": uname.system,
        "os_version": uname.release,
        "architecture": uname.machine,
        "processor": uname.processor,
        "python_version": platform.python_version()
    }

def get_metrics_snapshot() -> Dict[str, Any]:
    global _last_net_io, _last_net_time

    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_count(logical=True) or 1

    # Load average (Linux/Unix)
    load_avg = [0.0, 0.0, 0.0]
    if hasattr(os, "getloadavg"):
        try:
            load_avg = [round(x, 2) for x in os.getloadavg()]
        except Exception:
            pass

    # Memory & Swap
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Primary Disk
    disk = psutil.disk_usage('/') if platform.system() != 'Windows' else psutil.disk_usage('C:\\')

    # Disk partitions
    partitions_data = []
    try:
        for p in psutil.disk_partitions(all=False):
            if "cdrom" in p.opts or not p.fstype:
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
                partitions_data.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "percent": usage.percent
                })
            except (PermissionError, Exception):
                pass
    except Exception:
        pass

    # Network delta
    net_io = psutil.net_io_counters()
    now = time.time()

    rx_rate = 0.0
    tx_rate = 0.0
    if _last_net_io and _last_net_time:
        elapsed = max(now - _last_net_time, 0.001)
        rx_rate = (net_io.bytes_recv - _last_net_io.bytes_recv) / elapsed
        tx_rate = (net_io.bytes_sent - _last_net_io.bytes_sent) / elapsed

    _last_net_io = net_io
    _last_net_time = now

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(now - boot_time)

    # Per-container live stats from Docker
    container_stats = []
    try:
        container_stats = docker_manager.get_all_container_stats()
    except Exception:
        pass

    return {
        "cpu_usage": round(cpu_percent, 1),
        "cpu_cores": cpu_cores,
        "load_avg": load_avg,
        "memory_usage": round(mem.percent, 1),
        "memory_used_bytes": mem.used,
        "memory_total_bytes": mem.total,
        "memory_available_bytes": mem.available,
        "swap_used_bytes": swap.used,
        "swap_total_bytes": swap.total,
        "disk_usage": round(disk.percent, 1),
        "disk_used_bytes": disk.used,
        "disk_total_bytes": disk.total,
        "disk_partitions": partitions_data,
        "network_rx_bytes_per_sec": round(rx_rate, 1),
        "network_tx_bytes_per_sec": round(tx_rate, 1),
        "uptime_seconds": uptime_seconds,
        "container_stats": container_stats
    }
